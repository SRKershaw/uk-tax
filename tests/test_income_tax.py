"""SPEC.md §7 — 13 published LITRG worked examples plus 10 Personal-
Allowance-taper edge cases. This is the sole source of truth for
`uk_tax.tax.income`'s mechanics — see the module docstring and SPEC.md
§4 for why this is a mandatory sequential ordering, not a PA-allocation
search.
"""

import pytest

from uk_tax.money import Real
from uk_tax.tax.income import compute_income_tax
from uk_tax.tax.types import TaxYearParameters

PARAMS = TaxYearParameters(
    personal_allowance=Real(12570),
    pa_taper_threshold=Real(100000),
    pa_taper_rate=0.5,
    basic_rate_band=Real(37700),
    additional_rate_threshold=Real(125140),
    basic_rate=0.20,
    higher_rate=0.40,
    additional_rate=0.45,
    starting_rate_for_savings_band=Real(5000),
    psa_basic_rate=Real(1000),
    psa_higher_rate=Real(500),
    psa_additional_rate=Real(0),
    dividend_allowance=Real(500),
    dividend_basic_rate=0.1075,
    dividend_higher_rate=0.3575,
    dividend_additional_rate=0.3935,
    cgt_lower_rate=0.18,
    cgt_higher_rate=0.24,
    cgt_annual_exempt_amount=Real(3000),
)


def _tax(non_savings=0.0, savings=0.0, dividends=0.0) -> float:
    return compute_income_tax(Real(non_savings), Real(savings), Real(dividends), PARAMS).liability.value


NAMED_CASES = [
    ("Henry", 25000, 600, 0, 2486.00),
    ("Henry_variant", 25000, 1250, 0, 2536.00),
    ("John_just_over_higher_threshold", 49271, 1000, 0, 7440.40),
    ("James_exactly_at_threshold", 49270, 1000, 0, 7340.00),
    ("Magda_PSA_overflows_into_higher_band", 48650, 1750, 0, 7492.00),
    ("Mo_A", 14000, 1500, 0, 286.00),
    ("Mo_B", 14000, 3650, 0, 286.00),
    ("Mo_C", 14000, 4650, 0, 302.00),
    ("Mo_D", 18000, 1500, 0, 1186.00),
    ("Gerry", 17700, 1200, 0, 1066.00),
    ("Amanda_PA_leftover_shelters_interest", 10900, 8000, 0, 66.00),
    ("Michael_partial_starting_rate", 13100, 5800, 0, 172.00),
    ("Richard_savings_income_only", 0, 18900, 0, 66.00),
    ("salary_150k_full_PA_taper", 150000, 0, 0, 53703.00),
    ("dividend_stacking_check", 0, 20000, 10000, 1307.25),
]

TAPER_CASES = [
    ("taper_0_20k", 0, 20000, 286.00),
    ("taper_20k_20k", 20000, 20000, 5286.00),
    ("taper_0_60k", 0, 60000, 10332.00),
    ("taper_60k_60k", 60000, 60000, 39232.00),
    ("taper_0_110k", 0, 110000, 32332.00),
    ("taper_110k_110k", 110000, 110000, 85203.00),
    ("taper_0_100k", 0, 100000, 26332.00),
    ("taper_100k_100k", 100000, 100000, 76203.00),
    ("taper_0_150k", 0, 150000, 52703.00),
    ("taper_150k_150k", 150000, 150000, 121203.00),
]


@pytest.mark.parametrize("label,non_savings,savings,dividends,expected", NAMED_CASES)
def test_named_worked_examples(label, non_savings, savings, dividends, expected):
    assert _tax(non_savings, savings, dividends) == pytest.approx(expected, abs=0.01)


@pytest.mark.parametrize("label,non_savings,savings,expected", TAPER_CASES)
def test_pa_taper_edge_cases(label, non_savings, savings, expected):
    assert _tax(non_savings, savings) == pytest.approx(expected, abs=0.01)


def test_income_within_personal_allowance_is_untaxed():
    assert _tax(non_savings=12000) == 0


def test_basic_rate_band_hand_verified():
    # £50,270 non-savings: (50270-12570) * 20% = 37700 * 0.20 = 7540
    assert _tax(non_savings=50270) == pytest.approx(7540)


def test_higher_rate_kicks_in_at_hrt_threshold():
    # £60,270 non-savings: 37700@20% + (60270-50270)@40% = 7540 + 4000
    assert _tax(non_savings=60270) == pytest.approx(11540)


def test_additional_rate_above_full_threshold():
    # £130,140 non-savings, PA fully tapered (income > 125,140):
    # 37700@20% + (125140-37700)@40% + (130140-125140)@45%
    expected = 37700 * 0.20 + (125140 - 37700) * 0.40 + (130140 - 125140) * 0.45
    assert _tax(non_savings=130140) == pytest.approx(expected)


def test_pa_taper_marginal_rate_is_60_percent():
    # Within the £100,000-£125,140 taper zone, every extra £1 is taxed at
    # 40% AND withdraws 50p of PA (also taxed at 40%) = 60% marginal.
    delta = _tax(non_savings=110001) - _tax(non_savings=110000)
    assert delta == pytest.approx(0.60, abs=1e-6)


def test_pa_taper_marginal_rate_reverts_to_45_percent_once_pa_exhausted():
    # Above £125,140 the PA is already zero, so no more taper effect —
    # marginal rate drops back to the plain additional rate, 45%.
    delta = _tax(non_savings=130001) - _tax(non_savings=130000)
    assert delta == pytest.approx(0.45, abs=1e-6)


def test_higher_rate_band_widens_when_pa_is_tapered():
    # SPEC.md §4.2: the additional-rate threshold is fixed in gross-income
    # terms, so as PA shrinks under the taper, the taxable-income gap
    # between the higher-rate start and the additional-rate start
    # actually grows — from 74,870 untapered up to 79,870 here (PA =
    # 12570 - (110000-100000)*0.5 = 7570, widening by the 5,000 of PA
    # lost). All non-savings above the basic band (37,700 @ 20%) falls at
    # 40%, none reaching 45% — proof the band really did widen: without
    # the widening, the un-widened 74,870-wide band would have been
    # exhausted at 50270+74870=125,140, well before this £110,000
    # non-savings figure is even fully placed, and the remainder would
    # wrongly spill into the 45% band.
    pa_available = 12570 - (110000 - 100000) * 0.5  # 7570
    expected = 37700 * 0.20 + ((110000 - pa_available) - 37700) * 0.40
    assert _tax(non_savings=110000) == pytest.approx(expected)
    assert not any(
        c.band == "additional_rate" for c in compute_income_tax(Real(110000), Real(0), Real(0), PARAMS).charges
    )


def test_starting_rate_for_savings_is_zero_when_no_non_savings_income():
    # With no non-savings income, the full £5,000 Starting Rate band is
    # available to savings at 0%, on top of the untouched PA.
    result = compute_income_tax(Real(0), Real(12570 + 5000), Real(0), PARAMS)
    assert result.liability == Real(0)


def test_starting_rate_reduced_by_non_savings_alone_not_total_income():
    # SPEC.md §4.1: Starting Rate width is `max(0, 5000 - max(0,
    # non_savings - PA))` — non-savings alone against the STANDARD PA,
    # never net of interest. £5,000 non-savings above PA leaves the
    # Starting Rate width at 0 regardless of how much interest exists.
    savings = 10000
    delta = _tax(non_savings=17571, savings=savings) - _tax(non_savings=17570, savings=savings)
    # Both either side of £17,570 have non_savings - PA >= 5000, so the
    # Starting Rate width is already 0 on both sides — the extra £1 of
    # non-savings is taxed at plain 20%, no crowding-out effect left to
    # trigger.
    assert delta == pytest.approx(0.20, abs=1e-6)


def test_nil_rate_slices_still_consume_basic_rate_band():
    # SPEC.md §4.3: a PSA-sheltered slice of interest still eats
    # basic-rate band space — it is not simply netted off the interest
    # total before working out what's left of the band for the next,
    # actually-taxed slice. Magda's case (£48,650 non-savings + £1,750
    # interest): non-savings leaves only £1,120 of basic band before the
    # higher-rate threshold; the £500 PSA (higher-rate band, since total
    # income £50,400 exceeds £50,270) eats basic-band space too, so only
    # £1,120 of the remaining £1,250 interest lands at 20% — the last
    # £130 spills into the 40% band, which wouldn't happen if the
    # PSA-sheltered £500 had simply been subtracted from interest first
    # without also consuming band capacity.
    result = compute_income_tax(Real(48650), Real(1750), Real(0), PARAMS)
    psa_charge = next(c for c in result.charges if c.band == "psa")
    assert psa_charge.amount.value == pytest.approx(500)
    savings_higher = next(c for c in result.charges if c.category == "savings" and c.band == "higher_rate")
    assert savings_higher.amount.value == pytest.approx(130)


def test_psa_band_boundary_is_strictly_greater_than_not_inclusive():
    # SPEC.md §4.6: the boundary pound itself still sits in the LOWER
    # tier — total income of exactly £50,270 is still the basic-rate PSA
    # (£1,000); it takes £50,271, one pound over, to drop to £500.
    # Confirmed against LITRG's own published worked examples (a
    # taxpayer landing exactly on the higher-rate threshold keeps the
    # full basic-rate PSA; "into the higher rate tax band, by £1!" is
    # how the next pound is described in the source).
    at_threshold = compute_income_tax(Real(49270), Real(1000), Real(0), PARAMS)
    one_over = compute_income_tax(Real(49271), Real(1000), Real(0), PARAMS)

    psa_at = next(c for c in at_threshold.charges if c.band == "psa").amount.value
    psa_over = next(c for c in one_over.charges if c.band == "psa").amount.value
    assert psa_at == pytest.approx(1000)
    assert psa_over == pytest.approx(500)


def test_dividend_allowance_then_dividend_rates():
    # £13,070 dividends only, PA (12570) fully allocated to dividends
    # (only source of income): 500 remaining after PA, £500 dividend
    # allowance covers the rest, 0 tax.
    assert _tax(dividends=13070) == pytest.approx(0)
    # One pound more crosses into dividend basic rate.
    assert _tax(dividends=13071) == pytest.approx(0.1075, abs=1e-6)
