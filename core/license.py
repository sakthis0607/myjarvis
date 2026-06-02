"""
Jarvis AI Assistant - License Key System
-----------------------------------------
Uses HMAC-SHA256 to generate and validate license keys.
Keys encode the tier (free/pro/enterprise) and an expiry date.

Format: TIER-YYYYMMDD-HMAC[:16].upper()
Example: PRO-20261231-A3F9B2C1D4E5F6A7
"""
import hmac
import hashlib
import datetime
import config

# !! CHANGE THIS SECRET IN PRODUCTION — keep it private !!
_SECRET = b"jarvis-secret-key-change-me-2024"

TIERS = {
    "FREE": "free",
    "PRO": "pro",
    "ENT": "enterprise",
}

TIER_FEATURES = {
    "free": {
        "label": "Free",
        "max_history": 5,
        "voice_commands": True,
        "custom_skills": False,
        "priority_support": False,
    },
    "pro": {
        "label": "Pro",
        "max_history": 50,
        "voice_commands": True,
        "custom_skills": True,
        "priority_support": False,
    },
    "enterprise": {
        "label": "Enterprise",
        "max_history": 500,
        "voice_commands": True,
        "custom_skills": True,
        "priority_support": True,
    },
}


def _sign(payload: str) -> str:
    sig = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return sig[:16].upper()


def generate_key(tier: str = "PRO", expiry_date: str = "20261231") -> str:
    """
    Generate a license key.
    tier: 'FREE' | 'PRO' | 'ENT'
    expiry_date: 'YYYYMMDD'
    """
    tier = tier.upper()
    if tier not in TIERS:
        raise ValueError(f"Invalid tier: {tier}. Choose from {list(TIERS.keys())}")
    payload = f"{tier}-{expiry_date}"
    sig = _sign(payload)
    return f"{payload}-{sig}"


def validate_key(key: str) -> dict:
    """
    Validate a license key.
    Returns dict with: valid (bool), tier (str), expiry (str), message (str)
    """
    result = {"valid": False, "tier": "free", "expiry": "", "message": ""}

    if not key or key.strip() == "":
        result["message"] = "No license key provided. Running in Free tier."
        return result

    parts = key.strip().upper().split("-")
    if len(parts) != 3:
        result["message"] = "Invalid key format."
        return result

    tier_code, expiry, provided_sig = parts

    if tier_code not in TIERS:
        result["message"] = "Unknown tier in license key."
        return result

    # Check expiry
    try:
        expiry_dt = datetime.datetime.strptime(expiry, "%Y%m%d").date()
        if expiry_dt < datetime.date.today():
            result["message"] = f"License expired on {expiry_dt.strftime('%B %d, %Y')}."
            return result
    except ValueError:
        result["message"] = "Invalid expiry date in license key."
        return result

    # Verify signature
    payload = f"{tier_code}-{expiry}"
    expected_sig = _sign(payload)
    if not hmac.compare_digest(provided_sig, expected_sig):
        result["message"] = "License key signature is invalid."
        return result

    result["valid"] = True
    result["tier"] = TIERS[tier_code]
    result["expiry"] = expiry_dt.strftime("%B %d, %Y")
    result["message"] = f"✓ {TIERS[tier_code].capitalize()} license active until {result['expiry']}."
    return result


def activate_license(key: str) -> dict:
    """Validate and save the license key to config."""
    result = validate_key(key)
    if result["valid"]:
        config.set_value("license_key", key.strip().upper())
        config.set_value("tier", result["tier"])
    return result


def get_current_tier() -> str:
    key = config.get("license_key")
    result = validate_key(key)
    if result["valid"]:
        return result["tier"]
    return "free"


def get_features() -> dict:
    tier = get_current_tier()
    return TIER_FEATURES.get(tier, TIER_FEATURES["free"])
