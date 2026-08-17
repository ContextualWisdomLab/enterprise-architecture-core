"""Fail-closed Keyverse OIDC bearer verification for EA read surfaces."""

from __future__ import annotations

import base64
import binascii
import json
import subprocess
import tempfile
import textwrap
import time
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

_MAX_JWKS_BYTES = 1_048_576


class AuthorizationError(ValueError):
    """Describe a bearer rejection without exposing token material."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "invalid_token",
        http_status: int = 401,
        next_action: str = "Obtain a current Keyverse access token and retry.",
    ) -> None:
        """Record safe client-facing rejection metadata."""

        super().__init__(message)
        self.error_code = error_code
        self.http_status = http_status
        self.next_action = next_action


@dataclass(frozen=True, slots=True)
class KeyverseAuthorizationConfig:
    """Closed OIDC relying-party values required to authorize one read request."""

    issuer_uri: str
    audience: str
    jwks_url: str
    tenant_claim: str
    role_claim: str
    allowed_roles: frozenset[str]


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    """Verified identity context safe to bind to the EA database query port."""

    tenant_record_id: UUID
    role_code: str
    subject_id: str
    issuer_uri: str


JwksLoader = Callable[[str, str], Mapping[str, Any]]
SignatureVerifier = Callable[[bytes, bytes, Mapping[str, Any]], bool]
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def _same_origin_jwks(issuer_uri: str, jwks_url: str) -> bool:
    """Require HTTPS JWKS under the configured issuer origin and path."""

    try:
        issuer = urlparse(issuer_uri)
        jwks = urlparse(jwks_url)
        same_port = issuer.port == jwks.port
    except ValueError:
        return False
    if (
        issuer.scheme != "https"
        or jwks.scheme != "https"
        or issuer.username is not None
        or jwks.username is not None
        or issuer.hostname != jwks.hostname
        or not same_port
        or jwks.query
        or jwks.fragment
    ):
        return False
    issuer_path = issuer.path.rstrip("/")
    return bool(issuer_path) and jwks.path.startswith(f"{issuer_path}/")


def build_keyverse_authorization_config(
    environ: Mapping[str, str],
) -> KeyverseAuthorizationConfig | None:
    """Build an exact Keyverse RP profile or return ``None`` to fail closed."""

    values = {
        "issuer_uri": environ.get("EA_OIDC_ISSUER", "").strip(),
        "audience": environ.get("EA_OIDC_AUDIENCE", "").strip(),
        "jwks_url": environ.get("EA_OIDC_JWKS_URL", "").strip(),
        "tenant_claim": environ.get("EA_TENANT_CLAIM", "").strip(),
        "role_claim": environ.get("EA_ROLE_CLAIM", "").strip(),
    }
    allowed_roles = frozenset(
        role.strip()
        for role in environ.get("EA_READ_ROLES", "").split(",")
        if role.strip()
    )
    if not all(values.values()) or not allowed_roles:
        return None
    if not _same_origin_jwks(values["issuer_uri"], values["jwks_url"]):
        return None
    return KeyverseAuthorizationConfig(
        issuer_uri=values["issuer_uri"],
        audience=values["audience"],
        jwks_url=values["jwks_url"],
        tenant_claim=values["tenant_claim"],
        role_claim=values["role_claim"],
        allowed_roles=allowed_roles,
    )


def _reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject ambiguous JSON objects such as duplicate JWT or JWK members."""

    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(f"duplicate JSON member: {name}")
        result[name] = value
    return result


def _reject_json_constant(value: str) -> None:
    """Reject non-standard NaN and Infinity JSON constants."""

    raise ValueError(f"non-standard JSON constant: {value}")


def _decode_base64url(value: str, field_name: str) -> bytes:
    """Decode one strict base64url value used by JWT/JWK data."""

    if not value or "=" in value:
        raise AuthorizationError(f"{field_name} is not canonical base64url")
    padding = "=" * ((4 - len(value) % 4) % 4)
    try:
        return base64.b64decode(
            f"{value}{padding}",
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError) as error:
        raise AuthorizationError(f"{field_name} is not valid base64url") from error


def _decode_json_object(segment: str, field_name: str) -> Mapping[str, Any]:
    """Decode one strict JWT JSON object."""

    raw_value = _decode_base64url(segment, field_name)
    try:
        decoded = raw_value.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_members,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise AuthorizationError(f"{field_name} is not valid JSON") from error
    if not isinstance(value, Mapping):
        raise AuthorizationError(f"{field_name} must be a JSON object")
    return value


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent a configured JWKS URL from becoming a redirect-based SSRF hop."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        """Reject every redirect instead of following it."""

        del req, fp, code, msg, headers, newurl
        return None


def load_keyverse_jwks(jwks_url: str, issuer_uri: str) -> Mapping[str, Any]:
    """Fetch one bounded same-origin Keyverse JWKS without following redirects."""

    if not _same_origin_jwks(issuer_uri, jwks_url):
        raise AuthorizationError("JWKS location is outside the configured issuer")
    request = urllib.request.Request(
        jwks_url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    opener = urllib.request.build_opener(_NoRedirectHandler())
    try:
        with opener.open(request, timeout=3) as response:
            payload = response.read(_MAX_JWKS_BYTES + 1)
    except OSError as error:
        raise AuthorizationError("Keyverse signing keys are unavailable") from error
    if len(payload) > _MAX_JWKS_BYTES:
        raise AuthorizationError("Keyverse JWKS exceeds the bounded response size")
    try:
        document = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_members,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise AuthorizationError("Keyverse JWKS is not valid JSON") from error
    if not isinstance(document, Mapping):
        raise AuthorizationError("Keyverse JWKS must be a JSON object")
    return document


def _der_length(length: int) -> bytes:
    """Encode a non-negative DER content length."""

    if length < 128:
        return bytes((length,))
    encoded = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes((0x80 | len(encoded),)) + encoded


def _der_integer(value: bytes) -> bytes:
    """Encode one positive unsigned RSA integer as DER INTEGER."""

    normalized = value.lstrip(b"\x00")
    if not normalized:
        raise AuthorizationError("RSA key integer must be positive")
    if normalized[0] & 0x80:
        normalized = b"\x00" + normalized
    return b"\x02" + _der_length(len(normalized)) + normalized


def _der_sequence(content: bytes) -> bytes:
    """Encode one DER SEQUENCE."""

    return b"\x30" + _der_length(len(content)) + content


def _rsa_public_key_pem(jwk: Mapping[str, Any]) -> bytes:
    """Build an RSA SubjectPublicKeyInfo PEM from one strict signing JWK."""

    if jwk.get("kty") != "RSA" or jwk.get("alg") not in {None, "RS256"}:
        raise AuthorizationError("Keyverse signing key is not an RS256 RSA key")
    if jwk.get("use") not in {None, "sig"}:
        raise AuthorizationError("Keyverse RSA key is not a signing key")
    modulus = jwk.get("n")
    exponent = jwk.get("e")
    if not isinstance(modulus, str) or not isinstance(exponent, str):
        raise AuthorizationError("Keyverse RSA key is missing modulus or exponent")
    rsa_key = _der_sequence(
        _der_integer(_decode_base64url(modulus, "JWK modulus"))
        + _der_integer(_decode_base64url(exponent, "JWK exponent"))
    )
    algorithm_identifier = bytes.fromhex("300d06092a864886f70d0101010500")
    bit_string_content = b"\x00" + rsa_key
    subject_public_key = (
        b"\x03" + _der_length(len(bit_string_content)) + bit_string_content
    )
    spki = _der_sequence(algorithm_identifier + subject_public_key)
    encoded = base64.b64encode(spki).decode("ascii")
    body = "\n".join(textwrap.wrap(encoded, 64))
    return f"-----BEGIN PUBLIC KEY-----\n{body}\n-----END PUBLIC KEY-----\n".encode()


def verify_rs256_signature(
    signing_input: bytes,
    signature: bytes,
    jwk: Mapping[str, Any],
    *,
    runner: CommandRunner = subprocess.run,
) -> bool:
    """Verify an RS256 JWT signature with the operating-system OpenSSL binary."""

    public_key = _rsa_public_key_pem(jwk)
    try:
        with tempfile.TemporaryDirectory(prefix="ea-jwt-") as directory:
            root = Path(directory)
            key_path = root / "public.pem"
            signature_path = root / "signature.bin"
            input_path = root / "signing-input.bin"
            key_path.write_bytes(public_key)
            signature_path.write_bytes(signature)
            input_path.write_bytes(signing_input)
            result = runner(
                [
                    "openssl",
                    "dgst",
                    "-sha256",
                    "-verify",
                    str(key_path),
                    "-signature",
                    str(signature_path),
                    str(input_path),
                ],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _select_signing_key(
    jwks: Mapping[str, Any],
    key_id: str,
) -> Mapping[str, Any]:
    """Select exactly one RSA signing key by immutable JWT ``kid``."""

    keys = jwks.get("keys")
    if not isinstance(keys, Sequence) or isinstance(keys, (str, bytes)):
        raise AuthorizationError("Keyverse JWKS keys must be an array")
    matches = [
        key
        for key in keys
        if isinstance(key, Mapping) and key.get("kid") == key_id
    ]
    if len(matches) != 1:
        raise AuthorizationError("JWT signing key id is absent or ambiguous")
    return matches[0]


def _audience_contains(audience_claim: Any, expected_audience: str) -> bool:
    """Return whether an OIDC audience claim contains the exact RP audience."""

    if isinstance(audience_claim, str):
        return audience_claim == expected_audience
    if isinstance(audience_claim, Sequence) and not isinstance(
        audience_claim,
        (str, bytes),
    ):
        return all(isinstance(value, str) for value in audience_claim) and (
            expected_audience in audience_claim
        )
    return False


def verify_keyverse_bearer(
    authorization_header: str | None,
    config: KeyverseAuthorizationConfig,
    *,
    jwks_loader: JwksLoader = load_keyverse_jwks,
    signature_verifier: SignatureVerifier = verify_rs256_signature,
    now_epoch: int | None = None,
) -> AuthorizationContext:
    """Verify one Keyverse RS256 bearer and bind its tenant/role claims."""

    if not authorization_header or not authorization_header.startswith("Bearer "):
        raise AuthorizationError(
            "Keyverse bearer authorization is required",
            error_code="authorization_required",
            next_action=(
                "Authenticate with Keyverse and send one Bearer access token."
            ),
        )
    token = authorization_header.removeprefix("Bearer ")
    segments = token.split(".")
    if len(segments) != 3 or any(not segment for segment in segments):
        raise AuthorizationError("JWT must contain exactly three non-empty segments")
    header = _decode_json_object(segments[0], "JWT header")
    claims = _decode_json_object(segments[1], "JWT claims")
    if header.get("alg") != "RS256":
        raise AuthorizationError("JWT algorithm must be RS256")
    key_id = header.get("kid")
    if not isinstance(key_id, str) or not key_id:
        raise AuthorizationError("JWT header requires a signing key id")
    if header.get("typ") not in {None, "JWT", "at+jwt"}:
        raise AuthorizationError("JWT type is not an accepted access-token type")
    jwk = _select_signing_key(
        jwks_loader(config.jwks_url, config.issuer_uri),
        key_id,
    )
    signature = _decode_base64url(segments[2], "JWT signature")
    signing_input = f"{segments[0]}.{segments[1]}".encode("ascii")
    if not signature_verifier(signing_input, signature, jwk):
        raise AuthorizationError("JWT signature verification failed")
    if claims.get("iss") != config.issuer_uri:
        raise AuthorizationError("JWT issuer does not match Keyverse")
    if not _audience_contains(claims.get("aud"), config.audience):
        raise AuthorizationError("JWT audience does not include this service")
    expiry = claims.get("exp")
    current_epoch = int(time.time()) if now_epoch is None else now_epoch
    expiry_invalid = (
        not isinstance(expiry, int)
        or isinstance(expiry, bool)
        or current_epoch >= expiry
    )
    if expiry_invalid:
        raise AuthorizationError("JWT is expired or lacks an integer expiration")
    not_before = claims.get("nbf")
    if not_before is not None:
        nbf_invalid = (
            not isinstance(not_before, int)
            or isinstance(not_before, bool)
            or current_epoch < not_before
        )
        if nbf_invalid:
            raise AuthorizationError("JWT is not yet valid")
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AuthorizationError("JWT subject is required")
    tenant_value = claims.get(config.tenant_claim)
    if not isinstance(tenant_value, str):
        raise AuthorizationError("JWT tenant claim must be a UUID string")
    try:
        tenant_record_id = UUID(tenant_value)
    except ValueError as error:
        raise AuthorizationError("JWT tenant claim must be a UUID string") from error
    role_code = claims.get(config.role_claim)
    if not isinstance(role_code, str) or role_code not in config.allowed_roles:
        raise AuthorizationError(
            "JWT role is not authorized for architecture reads",
            error_code="forbidden",
            http_status=403,
            next_action="Request an approved Enterprise Architecture read role.",
        )
    return AuthorizationContext(
        tenant_record_id=tenant_record_id,
        role_code=role_code,
        subject_id=subject,
        issuer_uri=config.issuer_uri,
    )
