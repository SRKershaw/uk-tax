import pytest

from uk_tax.money import Real
from uk_tax.tax import tax
from uk_tax.tax.capital_gains import calculate_gain, compute_capital_gains_tax
from tests.test_income_tax import PARAMS


def test_gain_calculation_matches_spec_formula():
    # g = (V-B)/V, gain = X*g
    # Holding worth £10,000, cost basis £6,000 -> g = 0.4
    gain = calculate_gain(disposal_value=Real(2000), holding_value=Real(10000), holding_basis=Real(6000))
    assert gain == Real(2000 * 0.4)


def test_gain_fraction_invariant_under_partial_disposal():
    # Disposing half vs all of the same holding should yield the same g.
    full = calculate_gain(disposal_value=Real(10000), holding_value=Real(10000), holding_basis=Real(6000))
    half = calculate_gain(disposal_value=Real(5000), holding_value=Real(10000), holding_basis=Real(6000))
    assert half.value == pytest.approx(full.value / 2)


def test_gain_within_annual_exempt_amount_is_untaxed():
    result = compute_capital_gains_tax(Real(3000), total_income=0.0, params=PARAMS)
    assert result.liability == Real(0)


def test_gain_above_aea_with_no_income_uses_basic_rate_first():
    # SPEC.md §6: total income £20,000, gain £15,000 -> AEA (3000)
    # exempt, then 12000 taxable, entirely at 18% since £30,270 of
    # basic-rate band remains (higher_rate_start 50270 - total_income 20000).
    result = compute_capital_gains_tax(Real(15000), total_income=20000.0, params=PARAMS)
    assert result.liability.value == pytest.approx(2160.00)


def test_gain_stacked_on_income_that_already_filled_basic_band_is_all_higher_rate():
    # Total income exactly at the higher-rate threshold (£50,270) leaves
    # no basic-rate band remaining -> the gain (after AEA) falls entirely
    # in the higher CGT rate.
    higher_rate_start = PARAMS.personal_allowance.value + PARAMS.basic_rate_band.value
    result = compute_capital_gains_tax(Real(3000 + 5000), total_income=higher_rate_start, params=PARAMS)
    assert result.liability.value == pytest.approx(5000 * 0.24)


def test_combined_tax_function_sums_income_and_gains():
    result = tax(Real(50270), Real(0), Real(0), Real(3000), PARAMS)
    # Income: (50270-12570)*0.20 = 7540. Gains: fully within AEA -> 0.
    assert result.liability.value == pytest.approx(7540)
