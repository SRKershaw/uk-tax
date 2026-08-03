"""A pure UK personal tax engine. No web framework, no database, no I/O of
any kind — a caller passes in income figures and a rates table, gets back
a liability and an itemised set of charges.

Public interface: `tax(non_savings, savings, dividends, gains, params) ->
TaxResult`. Plain dataclasses in and out. Year and person are the
caller's concern: pick the right TaxYearParameters for the year you're
computing, sum the right person's income first (income splitting between
spouses, if relevant, also isn't this package's concern).
"""

from uk_tax.money import Real
from uk_tax.tax.capital_gains import calculate_gain, compute_capital_gains_tax
from uk_tax.tax.income import compute_income_tax
from uk_tax.tax.types import BandCharge, TaxResult, TaxYearParameters

__all__ = [
    "tax",
    "compute_income_tax",
    "compute_capital_gains_tax",
    "calculate_gain",
    "BandCharge",
    "TaxResult",
    "TaxYearParameters",
]


def tax(non_savings: Real, savings: Real, dividends: Real, gains: Real, params: TaxYearParameters) -> TaxResult:
    """Non-savings -> savings -> dividends (income tax, in that mandatory
    order), then gains as a wholly separate tax stacked on top of gross
    total income."""
    total_income = non_savings.value + savings.value + dividends.value
    income_result = compute_income_tax(non_savings, savings, dividends, params)
    gains_result = compute_capital_gains_tax(gains, total_income, params)

    return TaxResult(
        liability=Real(income_result.liability.value + gains_result.liability.value),
        charges=income_result.charges + gains_result.charges,
    )
