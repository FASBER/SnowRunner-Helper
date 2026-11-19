"""Fail-closed parsing of an Ed25519-signed release manifest.

Wire format: {"payload": {...}, "signature": "<base64 Ed25519 signature>"}
Only the canonical JSON bytes of payload are signed. No update/install action is
permitted if verification, version parsing or URL validation fails.
"""
import base64
import binascii
import json
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

_VERSION = re.compile(r'^\d+\.\d+\.\d+$')
_SHA = re.compile(r'^[a-f0-9]{64}$')

class UpdateSecurityError(ValueError):
    pass

def canonical_payload(payload):
    if not isinstance(payload, dict):
        raise UpdateSecurityError('Update payload must be a JSON object')
    return json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')

def version_tuple(value):
    if not isinstance(value, str) or not _VERSION.fullmatch(value):
        raise UpdateSecurityError('Expected semantic version X.Y.Z')
    return tuple(map(int, value.split('.')))

def validate_https_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise UpdateSecurityError('Invalid HTTPS URL')
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise UpdateSecurityError('Invalid URL port') from exc
    if (parsed.scheme.lower() != 'https' or not parsed.hostname or
        parsed.username or parsed.password or parsed.fragment or
        not parsed.netloc or '\\' in value or any(ord(c) < 33 for c in value)):
        raise UpdateSecurityError('Only clean HTTPS URLs are accepted')
    if port is not None and not (1 <= port <= 65535):
        raise UpdateSecurityError('Invalid URL port')
    return value

@dataclass(frozen=True)
class Release:
    version: str
    channel: str
    url: str
    sha256: str
    size: int
    notes: str


def verify_manifest(raw, public_key_base64, *, channel='stable', max_size=1_073_741_824):
    if not public_key_base64:
        raise UpdateSecurityError('Release signing public key is not configured')
    if not isinstance(raw, (bytes, bytearray)) or len(raw) > 65536:
        raise UpdateSecurityError('Invalid release manifest size')
    try:
        envelope = json.loads(raw)
        if not isinstance(envelope, dict) or set(envelope) != {'payload', 'signature'}:
            raise UpdateSecurityError('Invalid manifest fields')
        payload = envelope['payload']
        pub_raw = base64.b64decode(public_key_base64, validate=True)
        signature = base64.b64decode(envelope['signature'], validate=True)
        if len(pub_raw) != 32 or len(signature) != 64:
            raise UpdateSecurityError('Invalid signing key or signature length')
        Ed25519PublicKey.from_public_bytes(pub_raw).verify(signature, canonical_payload(payload))
    except (UnicodeError, json.JSONDecodeError, binascii.Error, InvalidSignature,
            TypeError, KeyError, ValueError) as exc:
        raise UpdateSecurityError('Manifest signature or encoding is invalid') from exc
    try:
        # Reject unknown fields as a safeguard against ambiguous future schemas.
        if set(payload) != {'version', 'channel', 'url', 'sha256', 'size', 'notes'}:
            raise UpdateSecurityError('Unsupported release payload fields')
        version_tuple(payload['version'])
        if payload['channel'] != channel:
            raise UpdateSecurityError('Release channel mismatch')
        url = validate_https_url(payload['url'])
        digest = payload['sha256']
        if not isinstance(digest, str) or not _SHA.fullmatch(digest):
            raise UpdateSecurityError('Invalid SHA-256 checksum')
        size = payload['size']
        if isinstance(size, bool) or not isinstance(size, int) or size < 1 or size > max_size:
            raise UpdateSecurityError('Invalid installer size')
        notes = payload['notes']
        if not isinstance(notes, str) or len(notes) > 4000:
            raise UpdateSecurityError('Invalid release notes')
    except (TypeError, KeyError) as exc:
        raise UpdateSecurityError('Invalid release fields') from exc
    return Release(payload['version'], channel, url, digest, size, notes)
