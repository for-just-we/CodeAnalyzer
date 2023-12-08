from enum import IntEnum

class MatchingResult(IntEnum):
    """Matching result of a signature."""
    NO = 0
    YES = 1
    UNCERTAIN = 2