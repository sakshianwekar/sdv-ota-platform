import json, base64, hashlib
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

def load_public_key(path="Tools/keys/ota_public_key.pem"):
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())

def verify_signature(manifest, public_key):
    manifest = dict(manifest)
    sig_field = manifest.pop("signature", None)
    if not sig_field or not sig_field.startswith("ed25519:"):
        return False

    sig_bytes = base64.b64decode(sig_field.split(":", 1)[1])
    canonical_payload = json.dumps(manifest, sort_keys=True).encode("utf-8")

    try:
        public_key.verify(sig_bytes, canonical_payload)
        return True
    except InvalidSignature:
        return False

def verify_checksum(binary_path, manifest):
    expected = manifest["checksum"].split(":", 1)[1]
    h = hashlib.sha256()
    with open(binary_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest() == expected