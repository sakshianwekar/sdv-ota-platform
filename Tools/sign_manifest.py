import json, os, base64, argparse, hashlib
from cryptography.hazmat.primitives import serialization

def load_private_key(path="Tools/keys/ota_signing_key.pem"):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)

def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def build_and_sign_manifest(binary_path, version, ecu, private_key):
    checksum = sha256_of_file(binary_path)
    size = os.path.getsize(binary_path)

    manifest = {
        "version": version,
        "ecu": ecu,
        "size": size,
        "checksum": f"sha256:{checksum}",
    }

    canonical_payload = json.dumps(manifest, sort_keys=True).encode("utf-8")
    signature_bytes = private_key.sign(canonical_payload)
    manifest["signature"] = f"ed25519:{base64.b64encode(signature_bytes).decode()}"

    return manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--ecu", required=True)
    parser.add_argument("--out", default="manifest.json")
    args = parser.parse_args()

    private_key = load_private_key()
    manifest = build_and_sign_manifest(args.binary, args.version, args.ecu, private_key)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Signed manifest written to {args.out}")