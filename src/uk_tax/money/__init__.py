"""Real and Nominal as distinct types.

Money that's already expressed in today's terms (Real) and money that's
expressed in the terms of the year it applies to, i.e. affected by future
inflation (Nominal) are kept as genuinely different types. Arithmetic
between them raises `TypeError` rather than silently producing a wrong
number — this is the one class of bug that's easy to introduce and hard to
notice in any multi-year money calculation.

Scalar `float` only. The only permitted conversion is `deflate_threshold`.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Real:
    value: float

    def __add__(self, other: "Real") -> "Real":
        if not isinstance(other, Real):
            raise TypeError(f"Real + {type(other).__name__}: mixing Real and Nominal is not permitted")
        return Real(self.value + other.value)

    def __sub__(self, other: "Real") -> "Real":
        if not isinstance(other, Real):
            raise TypeError(f"Real - {type(other).__name__}: mixing Real and Nominal is not permitted")
        return Real(self.value - other.value)

    def __mul__(self, scalar: float) -> "Real":
        if isinstance(scalar, (Real, Nominal)):
            raise TypeError(f"Real * {type(scalar).__name__}: multiply by a plain scalar, not a money type")
        return Real(self.value * scalar)

    def __lt__(self, other: "Real") -> bool:
        if not isinstance(other, Real):
            raise TypeError(f"Real < {type(other).__name__}: mixing Real and Nominal is not permitted")
        return self.value < other.value

    def __le__(self, other: "Real") -> bool:
        if not isinstance(other, Real):
            raise TypeError(f"Real <= {type(other).__name__}: mixing Real and Nominal is not permitted")
        return self.value <= other.value


@dataclass(frozen=True, slots=True)
class Nominal:
    value: float

    def __add__(self, other: "Nominal") -> "Nominal":
        if not isinstance(other, Nominal):
            raise TypeError(f"Nominal + {type(other).__name__}: mixing Real and Nominal is not permitted")
        return Nominal(self.value + other.value)

    def __sub__(self, other: "Nominal") -> "Nominal":
        if not isinstance(other, Nominal):
            raise TypeError(f"Nominal - {type(other).__name__}: mixing Real and Nominal is not permitted")
        return Nominal(self.value - other.value)

    def __mul__(self, scalar: float) -> "Nominal":
        if isinstance(scalar, (Real, Nominal)):
            raise TypeError(f"Nominal * {type(scalar).__name__}: multiply by a plain scalar, not a money type")
        return Nominal(self.value * scalar)

    def __lt__(self, other: "Nominal") -> bool:
        if not isinstance(other, Nominal):
            raise TypeError(f"Nominal < {type(other).__name__}: mixing Real and Nominal is not permitted")
        return self.value < other.value

    def __le__(self, other: "Nominal") -> bool:
        if not isinstance(other, Nominal):
            raise TypeError(f"Nominal <= {type(other).__name__}: mixing Real and Nominal is not permitted")
        return self.value <= other.value


def deflate_threshold(nominal: Nominal, inflation: float, years_elapsed: int) -> Real:
    """Convert a Nominal tax threshold to Real terms: real = nominal / (1 + inflation)^years_elapsed."""
    return Real(nominal.value / (1 + inflation) ** years_elapsed)
