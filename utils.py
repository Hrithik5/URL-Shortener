"""
utils.py
Base-62 encoding/decoding for converting integer IDs to short codes.

Alphabet: a-z A-Z 0-9  (62 characters)
A 7-character Base-62 code can represent up to 62^7 ≈ 3.5 trillion URLs.
"""
import string

BASE62 = string.ascii_lowercase + string.ascii_uppercase + string.digits  # 62 chars


def encode(num: int) -> str:
    """Convert a positive integer to a Base-62 string."""
    if num == 0:
        return BASE62[0]   # edge-case fix: empty loop would return ""
    base = len(BASE62)
    result = []
    while num > 0:
        num, rem = divmod(num, base)
        result.append(BASE62[rem])
    # Pad with the 0th character ('a') to ensure it is at least 7 characters
    encoded = "".join(reversed(result))
    return encoded.rjust(7, BASE62[0])


def decode(s: str) -> int:
    """Convert a Base-62 string back to its integer value."""
    base = len(BASE62)
    num = 0
    for char in s:
        num = num * base + BASE62.index(char)
    return num