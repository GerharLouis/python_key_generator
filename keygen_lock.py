"""
keygen_lock.py
---------------------
Open-source version of a simple hardware-based license generator and validator.

💡 How it works:
This file demonstrates how to generate and verify hardware-locked license keys
using HMAC signing for authenticity.

Each developer using this code should **replace SECRET_KEY** with their own value
(or load it securely from an environment variable).

Example:
    export PYKG_SECRET="MySuperSecretKey!"
or change the constant below directly.
"""

import base64
import hashlib
import hmac
import json
import platform
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
import os


# =====================================================
# CONFIGURATION
# =====================================================

# 🔑 Example key for demonstration only.
# Replace this with your own secret or load it via environment variable.
SECRET_KEY = os.environ.get("PYKG_SECRET", "ExampleKey123!").encode("utf-8")


# =====================================================
# HARDWARE ID GENERATOR
# =====================================================

def get_hardware_id() -> str:
    """
    Create a short unique identifier based on system hardware details.
    Developers may modify this logic to better suit their needs.
    """
    mac = uuid.getnode()
    sys_info = platform.system()
    cpu = platform.processor() or "GENCPU"
    base = f"{sys_info}-{cpu}-{mac}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16].upper()


# =====================================================
# LICENSE GENERATOR & VALIDATOR
# =====================================================

class HardwareLicense:
    """
    Handles license creation and verification based on:
      - Product name
      - Expiry date
      - Max users
      - Hardware ID (lock)
    """

    def __init__(self, secret_key: bytes = SECRET_KEY):
        self.secret_key = secret_key

    def _sign(self, data: bytes) -> bytes:
        """Generate short HMAC signature."""
        return hmac.new(self.secret_key, data, hashlib.sha256).digest()[:8]

    def generate_license(self, product: str, expiry_date: str, max_users: int, hwid: str) -> str:
        """
        Generate a base64-encoded license string tied to a hardware ID.

        Args:
            product (str): Product name
            expiry_date (str): Expiration date (YYYY-MM-DD)
            max_users (int): Maximum allowed users
            hwid (str): Hardware ID to lock license

        Returns:
            str: Encoded license key
        """
        payload = {
            "product": product.upper(),
            "exp": expiry_date,
            "users": int(max_users),
            "hwid": hwid
        }
        payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = self._sign(payload_bytes)
        token = base64.urlsafe_b64encode(payload_bytes + b"." + signature).decode("utf-8").rstrip("=")
        return token

    def verify_license(self, token: str, grace_days: int = 7) -> Dict[str, Any]:
        """
        Verify authenticity, hardware match, and expiry (with grace period).

        Args:
            token (str): License key string
            grace_days (int): Days allowed after expiry

        Returns:
            dict: Verification result
        """
        try:
            padding = "=" * ((4 - len(token) % 4) % 4)
            raw = base64.urlsafe_b64decode(token + padding)
            if b"." not in raw:
                return {"valid": False, "reason": "Invalid token format"}

            payload_bytes, signature = raw.rsplit(b".", 1)
            expected_sig = self._sign(payload_bytes)
            if not hmac.compare_digest(signature, expected_sig):
                return {"valid": False, "reason": "Invalid signature"}

            payload = json.loads(payload_bytes.decode("utf-8"))
            exp_date = datetime.strptime(payload["exp"], "%Y-%m-%d").date()
            today = datetime.now().date()
            days_left = (exp_date - today).days

            # Expiry check
            if days_left < 0:
                grace_remaining = grace_days + days_left
                if grace_remaining >= 0:
                    return {
                        "valid": True,
                        "grace": True,
                        "days_left": grace_remaining,
                        "reason": "License expired but within grace period",
                        "info": payload
                    }
                else:
                    return {"valid": False, "reason": "License and grace period expired"}

            # Hardware check
            current_hwid = get_hardware_id()
            if current_hwid != payload.get("hwid"):
                return {"valid": False, "reason": f"Hardware mismatch (expected {payload.get('hwid')})"}

            return {"valid": True, "grace": False, "days_left": days_left, "reason": "License valid", "info": payload}

        except Exception as e:
            return {"valid": False, "reason": f"Verification failed: {str(e)}"}


# =====================================================
# DEMO USAGE
# =====================================================
if __name__ == "__main__":
    gen = HardwareLicense()
    hwid = get_hardware_id()
    expiry = (datetime.now().date() + timedelta(days=30)).isoformat()
    key = gen.generate_license("DEMO_PRODUCT", expiry, 5, hwid)
    print("Generated key:\n", key)
    print("\nVerification result:")
    print(gen.verify_license(key))
