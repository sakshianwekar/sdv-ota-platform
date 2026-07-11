import tarfile, json, os, shutil
from package_firmware import package_firmware
from verify_manifest import verify_signature, verify_checksum, load_public_key

binary = "Firmware/motor_ecu_v1.1/build/motor_ecu"
package_path = package_firmware(binary, "1.1", "MotorECU")

extract_dir = "Tools/output/_extracted"
if os.path.exists(extract_dir):
    shutil.rmtree(extract_dir)
os.makedirs(extract_dir)

with tarfile.open(package_path, "r:gz") as tar:
    tar.extractall(extract_dir)

with open(os.path.join(extract_dir, "manifest.json")) as f:
    manifest = json.load(f)

extracted_binary = os.path.join(extract_dir, "firmware.bin")
public_key = load_public_key()

assert verify_signature(manifest, public_key), "Signature check failed on unpacked package"
assert verify_checksum(extracted_binary, manifest), "Checksum check failed on unpacked package"

print("Package round trip verified: signature and checksum both pass.")