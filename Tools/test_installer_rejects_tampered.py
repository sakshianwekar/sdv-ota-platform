import shutil, tarfile, json, os
from installer import install_package

shutil.copy("Tools/output/motorecu_v1.1.tar.gz", "Tools/output/tampered.tar.gz")

tmp = "Tools/output/_tamper_tmp"
if os.path.exists(tmp):
    shutil.rmtree(tmp)
os.makedirs(tmp)
with tarfile.open("Tools/output/tampered.tar.gz", "r:gz") as tar:
    tar.extractall(tmp)

with open(os.path.join(tmp, "firmware.bin"), "r+b") as f:
    f.seek(0)
    b = f.read(1)
    f.seek(0)
    f.write(bytes([b[0] ^ 0xFF]))

with tarfile.open("Tools/output/tampered.tar.gz", "w:gz") as tar:
    tar.add(os.path.join(tmp, "firmware.bin"), arcname="firmware.bin")
    tar.add(os.path.join(tmp, "manifest.json"), arcname="manifest.json")

try:
    install_package("Tools/output/tampered.tar.gz")
    print("FAIL: tampered package was accepted — this is a real problem")
except ValueError as e:
    print(f"PASS: tampered package correctly rejected — {e}")
