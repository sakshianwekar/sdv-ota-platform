import tarfile, json, os, shutil, subprocess, argparse
from verify_manifest import verify_signature, verify_checksum, load_public_key

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def install_package(package_path, bootloader_path="Bootloader/build/bootloader"):
    extract_dir = os.path.join(REPO_ROOT, "Tools/output/_install_tmp")
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)

    with tarfile.open(package_path, "r:gz") as tar:
        tar.extractall(extract_dir)

    manifest_path = os.path.join(extract_dir, "manifest.json")
    binary_path = os.path.join(extract_dir, "firmware.bin")

    with open(manifest_path) as f:
        manifest = json.load(f)

    public_key = load_public_key()

    if not verify_signature(manifest, public_key):
        raise ValueError("REJECTED: manifest signature invalid — refusing to install")

    if not verify_checksum(binary_path, manifest):
        raise ValueError("REJECTED: binary checksum mismatch — refusing to install")

    print(f"Verification passed for {manifest['ecu']} v{manifest['version']}")

    result = subprocess.run(
        [os.path.join(REPO_ROOT, bootloader_path), "stage", binary_path],
        capture_output=True, text=True, cwd=REPO_ROOT
    )

    if result.returncode != 0:
        raise RuntimeError(f"Bootloader stage failed:\n{result.stdout}\n{result.stderr}")

    print(f"Staged successfully:\n{result.stdout}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--bootloader", default="Bootloader/build/bootloader")
    args = parser.parse_args()

    install_package(args.package, args.bootloader)
