import pytest

from uk_tax.money import Nominal, Real, deflate_threshold


def test_real_arithmetic():
    assert Real(100) + Real(50) == Real(150)
    assert Real(100) - Real(30) == Real(70)
    assert Real(100) * 2 == Real(200)


def test_nominal_arithmetic():
    assert Nominal(100) + Nominal(50) == Nominal(150)


def test_mixing_real_and_nominal_raises():
    with pytest.raises(TypeError):
        Real(100) + Nominal(100)  # type: ignore[operator]
    with pytest.raises(TypeError):
        Nominal(100) - Real(50)  # type: ignore[operator]


def test_ordering_requires_same_type():
    assert Real(50) < Real(100)
    with pytest.raises(TypeError):
        Real(50) < Nominal(100)  # type: ignore[operator]


def test_deflate_threshold_matches_spec_formula():
    # real = nominal / (1 + inflation)^years_elapsed
    result = deflate_threshold(Nominal(12570), inflation=0.03, years_elapsed=2)
    assert result == Real(12570 / (1.03**2))


def test_deflate_threshold_zero_years_is_unchanged():
    assert deflate_threshold(Nominal(12570), inflation=0.03, years_elapsed=0) == Real(12570)
