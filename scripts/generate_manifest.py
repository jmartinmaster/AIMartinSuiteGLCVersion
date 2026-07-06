#!/usr/bin/env python3
# scripts/generate_manifest.py
#
# Generates a signed manifest.json for AIMartinSuite updates.
# Uses the private key in .vault to sign the manifest.
#

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

# Add project root to Python search path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.models.update_manager_model import (
    discover_module_payload_options,
    discover_documentation_payload_options,
)
from app.external_data_registry import ExternalDataRegistry
from app.utils.crypto_utils import sign_data
from app.app_identity import load_version_from_main


def compute_sha256(file_path: Path) -> str:
    """Computes SHA256 of a file, normalizing CRLF to LF line endings."""
    with open(file_path, "rb") as f:
        content = f.read()
    # Normalize line endings to match GitHub's raw server representation (LF)
    normalized_content = content.replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized_content).hexdigest()


def generate_manifest(channel: str, output_path: Path, private_key_hex: str):
    print(f"Generating manifest for channel: {channel}...")
    
    registry = ExternalDataRegistry()
    modules_path = str(project_root / "app")
    
    # Discover all module options
    module_options = discover_module_payload_options(modules_path, data_registry=registry)
    
    artifacts = {}
    
    # Add module payload files
    for option in module_options:
        payload_paths = option.get("payload_paths") or [option.get("relative_path")]
        for rel_path in payload_paths:
            # Normalize path separators to forward slashes for cross-platform matching
            norm_path = rel_path.replace("\\", "/").lstrip("/")
            local_file = project_root / norm_path
            if local_file.is_file():
                sha256_hash = compute_sha256(local_file)
                artifacts[norm_path] = {"sha256": sha256_hash}
                print(f"  Added module artifact: {norm_path} ({sha256_hash[:8]})")
            else:
                print(f"  Warning: Discovered payload path does not exist: {local_file}")

    # Add documentation files
    doc_options = discover_documentation_payload_options()
    for option in doc_options:
        rel_path = option.get("relative_path")
        if rel_path:
            norm_path = rel_path.replace("\\", "/").lstrip("/")
            local_file = project_root / norm_path
            if local_file.is_file():
                sha256_hash = compute_sha256(local_file)
                artifacts[norm_path] = {"sha256": sha256_hash}
                print(f"  Added doc artifact: {norm_path} ({sha256_hash[:8]})")
            else:
                print(f"  Warning: Discovered doc path does not exist: {local_file}")

    version = load_version_from_main()
    print(f"Detected application version: {version}")

    # Construct the manifest dictionary
    manifest_data = {
        "version": version,
        "release_channel": channel,
        "artifacts": artifacts
    }

    # Serialize cleanly and canonically
    canonical_data = json.dumps(manifest_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    
    # Sign canonical data
    signature = sign_data(private_key_hex, canonical_data)
    manifest_data["signature"] = signature
    
    # Save the manifest to file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=4)
        
    print(f"Manifest successfully generated and written to: {output_path}")
    print(f"Signature: {signature}")


def main():
    parser = argparse.ArgumentParser(description="Generate a signed manifest.json for updates.")
    parser.add_argument(
        "--channel",
        choices=["stable", "dev"],
        default="stable",
        help="Release channel for this manifest (default: stable)"
    )
    parser.add_argument(
        "--output",
        default="manifest.json",
        help="Output file path (default: manifest.json)"
    )
    args = parser.parse_args()

    vault_path = project_root / ".vault"
    if not vault_path.exists():
        print("Error: .vault file not found in project root.", file=sys.stderr)
        sys.exit(1)
        
    with open(vault_path, "r", encoding="utf-8") as f:
        private_key_hex = f.read().strip()

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = project_root / output_path
        
    generate_manifest(args.channel, output_path, private_key_hex)


if __name__ == "__main__":
    main()
