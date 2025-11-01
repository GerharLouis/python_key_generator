"""
keygen_pro.py
---------------------
An advanced version of the hardware-locked license generator.

This script builds on top of `keygen_lock.py` to provide:
    • Multi-license generation
    • JSON export for records
    • Optional batch license creation
    • Clean, reusable functions

💡 Usage:
    from keygen_pro import generate_license, batch_generate_licenses
    license_str = generate_license("MY_PRODUCT", "2025-12-01", 10)
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict

from keygen_lock import HardwareLicense, get_hardware_id


# =====================================================
# CONFIGURATION
# =====================================================

# You can override this by setting PYKG_SECRET in your environment.
# Each developer should use their own secret key.
SECRET_KEY = os.environ.get("PYKG_SECRET", "ExampleKey123!").encode("utf-8")


# =====================================================
# LICENSE GENERATION UTILITIES
# =====================================================

def generate_license(
    product: str,
    expiry_date: str,
    max_users: int,
    hwid: str = None
) -> str:
    """
    Generate a license for a single hardware ID.

    Args:
        product (str): Product name.
        expiry_date (str): Expiration date (YYYY-MM-DD).
        max_users (int): Maximum allowed users.
        hwid (str): Optional custom hardware ID. Defaults to local system.

    Returns:
        str: License key string.
    """
    hwid = hwid or get_hardware_id()
    license_gen = HardwareLicense(secret_key=SECRET_KEY)
    return license_gen.generate_license(product, expiry_date, max_users, hwid)


def batch_generate_licenses(
    product: str,
    days_valid: int,
    max_users: int,
    hwids: List[str]
) -> List[Dict[str, str]]:
    """
    Generate multiple licenses at once for a list of hardware IDs.

    Args:
        product (str): Product name.
        days_valid (int): Days before license expires.
        max_users (int): Max number of users.
        hwids (List[str]): List of hardware IDs.

    Returns:
        List[Dict[str, str]]: List of generated licenses with metadata.
    """
    license_gen = HardwareLicense(secret_key=SECRET_KEY)
    expiry_date = (datetime.now().date() + timedelta(days=days_valid)).isoformat()
    results = []

    for hw in hwids:
        key = license_gen.generate_license(product, expiry_date, max_users, hw)
        results.append({
            "hwid": hw,
            "product": product,
            "expiry": expiry_date,
            "users": max_users,
            "license": key
        })

    return results


def save_licenses_to_file(licenses: List[Dict[str, str]], filename: str = "licenses.json") -> None:
    """
    Save a list of generated licenses to a JSON file.

    Args:
        licenses (List[Dict[str, str]]): License data.
        filename (str): Output file name.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(licenses, f, indent=4)
    print(f"[✔] Saved {len(licenses)} licenses to '{filename}'")


# =====================================================
# DEMO USAGE
# =====================================================

if __name__ == "__main__":
    print("🔑 Python Key Generator Pro (Demo Mode)")
    hwid = get_hardware_id()
    expiry = (datetime.now().date() + timedelta(days=30)).isoformat()
    product_name = "DEMO_PRODUCT"
    max_users = 5

    print(f"\nGenerating license for product '{product_name}'")
    print(f"Hardware ID: {hwid}")
    print(f"Expires on:  {expiry}")

    license_key = generate_license(product_name, expiry, max_users, hwid)
    print("\nGenerated license key:")
    print(license_key)

    # Optional: batch example
    print("\nBatch generation example (3 sample HWIDs):")
    sample_hwids = [f"HWID_{i:03d}" for i in range(1, 4)]
    batch = batch_generate_licenses(product_name, 30, max_users, sample_hwids)
    save_licenses_to_file(batch)
