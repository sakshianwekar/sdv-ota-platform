from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import argparse
import os
import sys

KEY_DIR = "Tools/keys"
PRIVATE_KEY_PATH = os.path.join(KEY_DIR, "ota_signing_key.pem")
PUBLIC_KEY_PATH = os.path.join(KEY_DIR, "ota_public_key.pem")


def load_private_key(path=PRIVATE_KEY_PATH):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_public_key(path=PUBLIC_KEY_PATH):
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def keys_match():
    if not (os.path.isfile(PRIVATE_KEY_PATH) and os.path.isfile(PUBLIC_KEY_PATH)):
        return False
    private_key = load_private_key()
    public_key = load_public_key()
    derived = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    stored = open(PUBLIC_KEY_PATH, "rb").read()
    return derived == stored


def generate_keys():
    os.makedirs(KEY_DIR, exist_ok=True)

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ))

    print("Keypair generated. Keep ota_signing_key.pem private and out of git.")


def main():
    parser = argparse.ArgumentParser(description="Generate OTA signing keypair")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate keys even if a valid keypair already exists",
    )
    args = parser.parse_args()

    if not args.force and keys_match():
        print("Valid keypair already exists — skipping generation.")
        return

    if os.path.isfile(PRIVATE_KEY_PATH) or os.path.isfile(PUBLIC_KEY_PATH):
        if not keys_match():
            print(
                "WARNING: private/public key mismatch detected — regenerating keypair.",
                file=sys.stderr,
            )
            print(
                "Re-package firmware after this (e.g. FAST=1 ./Scripts/run_demo.sh).",
                file=sys.stderr,
            )

    generate_keys()


if __name__ == "__main__":
    main()