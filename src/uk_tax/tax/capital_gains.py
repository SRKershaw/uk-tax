"""Capital gains: gain calculation on disposal and CGT.

CGT is a wholly separate tax from income tax, with its own annual
exemption and own two rates. A gain stacks on top of *gross total income*
purely to work out how much of the basic-rate band remains for the
18%/24% split — no shared "band position" bookkeeping with income tax is
needed, since gross total income against a fixed threshold already
captures that directly.
"""

from uk_tax.money import Real
from uk_tax.tax.types import BandCharge, TaxResult, TaxYearParameters


def calculate_gain(disposal_value: Real, holding_value: Real, holding_basis: Real) -> Real:
    """g = (V-B)/V, gain = X*g. g is invariant under partial disposal, so
    this is correct for a disposal of any size X (disposal_value) from a
    holding currently worth V (holding_value) with cost basis B
    (holding_basis)."""
    if holding_value.value == 0:
        return Real(0)
    fraction = (holding_value.value - holding_basis.value) / holding_value.value
    return Real(disposal_value.value * fraction)


def compute_capital_gains_tax(gain: Real, total_income: float, params: TaxYearParameters) -> TaxResult:
    """Two rates by basic-rate band remaining after gross total income;
    the annual exempt amount is applied before rate determination.

    Assumes a chargeable gain — exempt asset classes (e.g. gilts) and
    special treatments (e.g. non-reporting offshore funds, taxed as
    income with no annual exemption) are the caller's concern; this
    function doesn't know about asset types at all."""
    higher_rate_start = params.personal_allowance.value + params.basic_rate_band.value
    aea_used = min(gain.value, params.cgt_annual_exempt_amount.value)
    taxable_gain = gain.value - aea_used
    basic_remaining = max(0.0, higher_rate_start - total_income)

    at_lower = min(taxable_gain, basic_remaining)
    at_higher = max(0.0, taxable_gain - at_lower)

    charges = []
    if aea_used > 0:
        charges.append(BandCharge("gains", "cgt_annual_exempt_amount", Real(aea_used), 0.0, Real(0)))
    if at_lower > 0:
        charges.append(
            BandCharge("gains", "cgt_lower_rate", Real(at_lower), params.cgt_lower_rate, Real(at_lower * params.cgt_lower_rate))
        )
    if at_higher > 0:
        charges.append(
            BandCharge(
                "gains", "cgt_higher_rate", Real(at_higher), params.cgt_higher_rate, Real(at_higher * params.cgt_higher_rate)
            )
        )

    liability = sum(c.tax.value for c in charges)
    return TaxResult(liability=Real(liability), charges=tuple(charges))
