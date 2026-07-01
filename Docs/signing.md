# Manifest Signing Convention

- Signature algorithm: Ed25519
- Payload signed: JSON of manifest fields (version, ecu, size, checksum), 
  serialized with sort_keys=True, "signature" field excluded from the signed payload
- Signature encoding: "ed25519:<base64>"
- Checksum encoding: "sha256:<hex>"
- Private key: Tools/keys/ota_signing_key.pem (never committed)
- Public key: Tools/keys/ota_public_key.pem (safe to commit, will be embedded in OTA_Client)