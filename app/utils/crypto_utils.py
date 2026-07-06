# Production Logging Center (GLC Edition)
# Copyright (C) 2026 Jamie Martin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from app.app_identity import PUBLISHER_PUBLIC_KEY
DEFAULT_PUBLIC_KEY = PUBLISHER_PUBLIC_KEY

def verify_signature(public_key_hex: str, signature_hex: str, data: bytes) -> bool:
    """
    Verifies an Ed25519 signature against the data using a hex-encoded public key.
    Returns True if valid, False otherwise (or raises an exception).
    """
    try:
        pub_bytes = bytes.fromhex(public_key_hex)
        sig_bytes = bytes.fromhex(signature_hex)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        public_key.verify(sig_bytes, data)
        return True
    except InvalidSignature:
        return False
    except Exception as exc:
        raise ValueError(f"Signature verification failed: {exc}")

def sign_data(private_key_hex: str, data: bytes) -> str:
    """
    Signs data using a hex-encoded private key and returns the hex-encoded signature.
    """
    try:
        priv_bytes = bytes.fromhex(private_key_hex)
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
        signature = private_key.sign(data)
        return signature.hex()
    except Exception as exc:
        raise ValueError(f"Signing failed: {exc}")

def verify_manifest(manifest_dict: dict, public_key_hex: str = DEFAULT_PUBLIC_KEY) -> bool:
    """
    Verifies the signature embedded in a manifest dictionary.
    Assumes the signature is hex-encoded under the 'signature' key.
    """
    if not isinstance(manifest_dict, dict):
        raise TypeError("Manifest must be a dictionary.")
    
    signature = manifest_dict.get("signature")
    if not signature:
        raise ValueError("Manifest is unsigned (missing 'signature' field).")
        
    # Exclude the signature itself from signature verification
    clean_dict = {k: v for k, v in manifest_dict.items() if k != "signature"}
    
    # Serialize cleanly and canonically
    canonical_data = json.dumps(clean_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return verify_signature(public_key_hex, signature, canonical_data)
