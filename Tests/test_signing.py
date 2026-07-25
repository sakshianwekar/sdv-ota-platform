import sys, os, copy

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "Tools"))

from sign_manifest import build_and_sign_manifest, load_private_key
from verify_manifest import verify_signature, verify_checksum, load_public_key

priv = load_private_key(os.path.join(REPO_ROOT, "Tools/keys/ota_signing_key.pem"))
pub = load_public_key(os.path.join(REPO_ROOT, "Tools/keys/ota_public_key.pem"))

binary = os.path.join(REPO_ROOT, "Firmware/motor_ecu_v1.1/build/motor_ecu")
if os.name == "nt" and not os.path.isfile(binary):
    binary = binary + ".exe"

if not os.path.isfile(binary):
    print(f"SKIP: binary not built yet ({binary})")
    sys.exit(0)

manifest = build_and_sign_manifest(binary, "1.1", "MotorECU", priv)

assert verify_signature(manifest, pub) is True, "Valid signature should pass"
assert verify_checksum(binary, manifest) is True, "Valid checksum should pass"

tampered = copy.deepcopy(manifest)
tampered["checksum"] = "sha256:" + "0" * 64
assert verify_signature(tampered, pub) is False, "Tampered checksum should fail signature check"

tampered2 = copy.deepcopy(manifest)
tampered2["signature"] = "ed25519:" + "A" * 20 + tampered2["signature"][30:]
assert verify_signature(tampered2, pub) is False, "Tampered signature should fail"

print("All signing/verification tests passed.")
