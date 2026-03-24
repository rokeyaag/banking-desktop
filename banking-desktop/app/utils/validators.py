import re

def validate_email(email: str) -> tuple[bool, str]:
    if not email or len(email) < 5:
        return False, "Email is too short."
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return False, "Invalid email format."
    return True, ""

def validate_password(pw: str) -> tuple[bool, str]:
    if len(pw) < 6:
        return False, "Password must be at least 6 characters."
    return True, ""

def validate_pin(pin: str) -> tuple[bool, str]:
    if not pin.isdigit():
        return False, "PIN must contain only digits."
    if not (4 <= len(pin) <= 6):
        return False, "PIN must be 4–6 digits."
    return True, ""

def validate_amount(amount_str: str) -> tuple[bool, str]:
    try:
        val = float(amount_str)
        if val <= 0:
            return False, "Amount must be greater than zero."
        return True, ""
    except (ValueError, TypeError):
        return False, "Invalid amount."

def validate_full_name(name: str) -> tuple[bool, str]:
    if not name or len(name.strip()) < 2:
        return False, "Full name must be at least 2 characters."
    return True, ""
