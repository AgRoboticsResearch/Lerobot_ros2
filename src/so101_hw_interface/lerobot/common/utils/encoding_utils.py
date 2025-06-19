"""Minimal stubs for Feetech SDK dependency.

These replicate the behaviour expected by FeetechMotorsBus:
 * bit *sign_bit* acts as a sign flag (1 => negative)
 * remaining bits are magnitude (absolute value)

The functions work with integers (typically 16-bit register values).
"""

def encode_sign_magnitude(value: int, sign_bit: int = 15) -> int:
    """Convert *value* to sign-magnitude representation.

    Parameters
    ----------
    value : int
        Signed integer to encode.
    sign_bit : int, optional
        Which bit index stores the sign (default 15 -> highest bit in 16-bit word).
    """
    if value < 0:
        magnitude = -value
        return (1 << sign_bit) | magnitude
    else:
        return value & ((1 << sign_bit) - 1)

def decode_sign_magnitude(register_value: int, sign_bit: int = 15) -> int:
    """Decode sign-magnitude *register_value* back to signed integer."""
    sign = (register_value >> sign_bit) & 0x1
    magnitude = register_value & ((1 << sign_bit) - 1)
    return -magnitude if sign else magnitude 