def clamp_percent(value: float) -> float:
    """Clamp a numeric percent value to [0, 100]."""
    if value < 0:
        return 0.0
    if value > 100:
        return 100.0
    return float(value)
