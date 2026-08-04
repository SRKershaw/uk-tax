"""Income tax: non-savings, savings, dividends.

Mandatory sequential ordering — non-savings, then savings, then dividends;
each stacks on whatever Personal Allowance and band capacity the previous
one left. Not a "beneficial reallocation" search: UK law permits electing
a more favourable Personal Allowance split across income types until 6
April 2027, but that election is deliberately not modelled (see SPEC.md
§1) — mandatory ordering is what becomes compulsory for everyone from
that date anyway, and modelling the election would require a materially
more complex search over candidate allocations for a benefit that only
ever matters in specific multi-category cases (see SPEC.md's "mechanics
that are easy to get wrong" for the reasoning and the resulting bias).

All internal mechanics work in plain floats; Real wrapping happens only at
the public boundary (inputs and BandCharge amounts).
"""

from uk_tax.money import Real
from uk_tax.tax.types import BandCharge, TaxResult, TaxYearParameters


def _taper_personal_allowance(total_income: float, params: TaxYearParameters) -> float:
    """Personal Allowance taper — withdrawn £1 per £2 (pa_taper_rate) above pa_taper_threshold."""
    excess = max(0.0, total_income - params.pa_taper_threshold.value)
    withdrawal = excess * params.pa_taper_rate
    return max(0.0, params.personal_allowance.value - withdrawal)


def _earnings_tax(non_savings: float, total_income: float, params: TaxYearParameters) -> dict:
    """Non-savings income — taxed first, always absorbs Personal Allowance
    up to its own gross amount (it has no allowance of its own to share)."""
    pa_available = _taper_personal_allowance(total_income, params)
    pa_used = min(pa_available, non_savings)

    higher_rate_start = params.personal_allowance.value + params.basic_rate_band.value
    basic_width = params.basic_rate_band.value
    # Higher-rate band widens under PA taper: additional_rate_threshold is
    # fixed in gross-income terms, while the PA subtracted to reach taxable
    # income shrinks — so the taxable-income gap between the two grows.
    higher_width = (params.additional_rate_threshold.value - higher_rate_start) + (
        params.personal_allowance.value - pa_available
    )

    at_lower = min(max(0.0, min(non_savings, higher_rate_start) - pa_available), basic_width)
    at_higher = min(
        max(0.0, min(non_savings, params.additional_rate_threshold.value) - at_lower - pa_available),
        higher_width,
    )
    at_additional = non_savings - at_higher - at_lower - pa_used

    charges: list[tuple[str, str, float, float]] = []
    if at_lower > 0:
        charges.append(("non_savings", "basic_rate", at_lower, params.basic_rate))
    if at_higher > 0:
        charges.append(("non_savings", "higher_rate", at_higher, params.higher_rate))
    if at_additional > 0:
        charges.append(("non_savings", "additional_rate", at_additional, params.additional_rate))

    return {
        "charges": charges,
        "pa_available": pa_available,
        "pa_used": pa_used,
        "basic_band_remaining": basic_width - at_lower,
        "higher_band_remaining": max(0.0, higher_width - at_higher),
    }


def _savings_tax(non_savings: float, savings: float, total_income: float, earnings: dict, params: TaxYearParameters) -> dict:
    """Savings interest — stacks on non-savings. Starting Rate, then PSA,
    then whatever's left of the basic/higher/additional bands, in order.
    Nil-rate slices (Starting Rate, PSA) still consume band capacity."""
    pa_leftover = earnings["pa_available"] - earnings["pa_used"]

    # Starting Rate width depends on non-savings income ALONE against the
    # STANDARD, untapered Personal Allowance — never total income, and
    # never net of interest. The single most common implementation bug
    # for this band (see SPEC.md §4.1).
    starting_rate_available = max(
        0.0,
        params.starting_rate_for_savings_band.value - max(0.0, non_savings - params.personal_allowance.value),
    )

    # PSA size is set by TOTAL combined income against the higher/
    # additional-rate thresholds. Strict '>', not '>=' — the boundary
    # pound itself still sits in the lower tier. Confirmed against
    # LITRG's own published worked examples (a taxpayer landing exactly
    # on the higher-rate threshold keeps the full basic-rate PSA; it
    # takes one pound over to drop to the higher-rate PSA) — see SPEC.md
    # §4.6. Applied to the additional-rate threshold too, for
    # consistency, though no published worked example tests that exact
    # boundary pound.
    higher_rate_start = params.personal_allowance.value + params.basic_rate_band.value
    if total_income > params.additional_rate_threshold.value:
        psa = params.psa_additional_rate.value
    elif total_income > higher_rate_start:
        psa = params.psa_higher_rate.value
    else:
        psa = params.psa_basic_rate.value

    after_pa = max(0.0, savings - pa_leftover)
    starting_rate_used = min(after_pa, starting_rate_available)
    after_starting_rate = after_pa - starting_rate_used
    psa_used = min(after_starting_rate, psa)
    taxable = after_starting_rate - psa_used

    basic_remaining = earnings["basic_band_remaining"]
    higher_remaining = earnings["higher_band_remaining"]

    sr_in_basic = min(starting_rate_used, basic_remaining)
    psa_in_basic = min(psa_used, max(0.0, basic_remaining - sr_in_basic))
    psa_in_higher = psa_used - psa_in_basic

    at_lower = min(taxable, max(0.0, basic_remaining - sr_in_basic - psa_in_basic))
    at_higher = min(max(0.0, taxable - at_lower), max(0.0, higher_remaining - psa_in_higher))
    at_additional = max(0.0, taxable - at_lower - at_higher)

    charges: list[tuple[str, str, float, float]] = []
    if starting_rate_used > 0:
        charges.append(("savings", "starting_rate_for_savings", starting_rate_used, 0.0))
    if psa_used > 0:
        charges.append(("savings", "psa", psa_used, 0.0))
    if at_lower > 0:
        charges.append(("savings", "basic_rate", at_lower, params.savings_basic_rate))
    if at_higher > 0:
        charges.append(("savings", "higher_rate", at_higher, params.savings_higher_rate))
    if at_additional > 0:
        charges.append(("savings", "additional_rate", at_additional, params.savings_additional_rate))

    return {
        "charges": charges,
        "pa_leftover": pa_leftover,
        "basic_band_remaining": max(0.0, basic_remaining - sr_in_basic - psa_in_basic - at_lower),
        "higher_band_remaining": max(0.0, higher_remaining - psa_in_higher - at_higher),
    }


def _dividend_tax(dividends: float, savings: float, savings_result: dict, params: TaxYearParameters) -> dict:
    """Dividends — stack last, on top of non-savings and savings."""
    pa_leftover_after_savings = max(0.0, savings_result["pa_leftover"] - savings)
    after_pa = max(0.0, dividends - pa_leftover_after_savings)
    dividend_allowance_used = min(after_pa, params.dividend_allowance.value)
    taxable = after_pa - dividend_allowance_used

    basic_remaining = savings_result["basic_band_remaining"]
    higher_remaining = savings_result["higher_band_remaining"]

    at_lower = min(taxable, basic_remaining)
    at_higher = min(max(0.0, taxable - at_lower), higher_remaining)
    at_additional = max(0.0, taxable - at_lower - at_higher)

    charges: list[tuple[str, str, float, float]] = []
    if dividend_allowance_used > 0:
        charges.append(("dividends", "dividend_allowance", dividend_allowance_used, 0.0))
    if at_lower > 0:
        charges.append(("dividends", "basic_rate", at_lower, params.dividend_basic_rate))
    if at_higher > 0:
        charges.append(("dividends", "higher_rate", at_higher, params.dividend_higher_rate))
    if at_additional > 0:
        charges.append(("dividends", "additional_rate", at_additional, params.dividend_additional_rate))

    return {"charges": charges}


def compute_income_tax(non_savings: Real, savings: Real, dividends: Real, params: TaxYearParameters) -> TaxResult:
    """Mandatory sequential ordering — see the module docstring for why
    this isn't a PA-allocation search."""
    total_income = non_savings.value + savings.value + dividends.value

    earnings = _earnings_tax(non_savings.value, total_income, params)
    savings_result = _savings_tax(non_savings.value, savings.value, total_income, earnings, params)
    dividends_result = _dividend_tax(dividends.value, savings.value, savings_result, params)

    all_charges = earnings["charges"] + savings_result["charges"] + dividends_result["charges"]
    band_charges = tuple(
        BandCharge(category=category, band=band, amount=Real(amount), rate=rate, tax=Real(amount * rate))
        for category, band, amount, rate in all_charges
    )
    liability = sum(c.tax.value for c in band_charges)
    return TaxResult(liability=Real(liability), charges=band_charges)
