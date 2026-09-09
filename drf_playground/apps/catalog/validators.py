"""Plain validators. Usable both as model field validators and as serializer validators."""

from django.core.exceptions import ValidationError


def normalize_isbn(value: str) -> str:
    """Strip separators commonly found in ISBNs: ``978-0-306-40615-7`` becomes ``9780306406157``."""
    return value.replace("-", "").replace(" ", "")


def isbn13_check_digit(first_twelve: str) -> str:
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(first_twelve))
    return str((10 - total % 10) % 10)


def validate_isbn13(value: str) -> None:
    digits = normalize_isbn(value)
    if len(digits) != 13 or not digits.isdigit():
        raise ValidationError("ISBN must contain exactly 13 digits.", code="invalid_isbn")
    if isbn13_check_digit(digits[:12]) != digits[12]:
        raise ValidationError("ISBN-13 checksum does not match.", code="invalid_isbn")
