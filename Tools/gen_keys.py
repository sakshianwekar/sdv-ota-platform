from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import os

os.makedirs("Tools/keys", exist_ok=True)

private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()

with open("Tools/keys/ota_signing_key.pem", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))

with open("Tools/keys/ota_public_key.pem", "wb") as f:
    f.write(public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ))

print("Keypair generated. Keep ota_signing_key.pem private and out of git.")