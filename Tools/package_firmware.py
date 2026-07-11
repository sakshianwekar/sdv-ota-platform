import tarfile, json, os, argparse
from sign_manifest import build_and_sign_manifest, load_private_key

def package_firmware(binary_path, version, ecu, output_dir="Tools/output"):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Build and sign the manifest (reuses Phase 8 code, no duplication)
    private_key = load_private_key()
    manifest = build_and_sign_manifest(binary_path, version, ecu, private_key)

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # 2. Bundle binary + manifest into one tarball
    package_name = f"{ecu.lower()}_v{version}.tar.gz"
    package_path = os.path.join(output_dir, package_name)

    with tarfile.open(package_path, "w:gz") as tar:
        tar.add(binary_path, arcname="firmware.bin")
        tar.add(manifest_path, arcname="manifest.json")

    return package_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--ecu", required=True)
    parser.add_argument("--out-dir", default="Tools/output")
    args = parser.parse_args()

    result_path = package_firmware(args.binary, args.version, args.ecu, args.out_dir)
    print(f"Package created: {result_path}")