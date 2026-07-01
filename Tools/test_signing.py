import sys, os, copy
sys.path.insert(0, os.path.dirname(__file__))

from sign_manifest import build_and_sign_manifest, load_private_key
from verify_manifest import verify_signature, verify_checksum, load_public_key

priv = load_private_key()
pub = load_public_key()

binary = "Firmware/motor_ecu/build/motor_ecu_v1.1"  # adjust to your real path

manifest = build_and_sign_manifest(binary, "1.1", "MotorECU", priv)

assert verify_signature(manifest, pub) == True, "Valid signature should pass"
assert verify_checksum(binary, manifest) == True, "Valid checksum should pass"

tampered = copy.deepcopy(manifest)
tampered["checksum"] = "sha256:" + "0" * 64
assert verify_signature(tampered, pub) == False, "Tampered checksum should fail signature check"

tampered2 = copy.deepcopy(manifest)
tampered2["signature"] = "ed25519:" + "A" * 20 + tampered2["signature"][30:]
assert verify_signature(tampered2, pub) == False, "Tampered signature should fail"

print("All signing/verification tests passed.")