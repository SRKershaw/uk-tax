"""tax_class -> income/gain character.

A pure lookup over UK asset-type-to-tax-treatment classification — which
income category a holding's distributions fall into (non-savings,
savings, or dividends), and how a disposal gain is treated (fully
chargeable to CGT, exempt from CGT entirely, or taxed as income instead
of as a gain). Domain vocabulary, not any particular app's asset schema.
"""

from dataclasses import dataclass
from typing import Literal

IncomeCategory = Literal["non_savings", "savings", "dividends"]
GainTreatment = Literal["exempt", "chargeable", "taxed_as_income"]

TaxClass = Literal[
    "cash",
    "gilt",
    "qcb",
    "non_qcb_bond",
    "bond_fund_inc",
    "bond_fund_acc",
    "equity_fund_inc",
    "equity_fund_acc",
    "equity_direct",
    "offshore_non_reporting",
    "investment_trust_interest",
    "reit_pid",
    "commodity",
]


@dataclass(frozen=True, slots=True)
class TaxClassCharacter:
    income_category: IncomeCategory | None  # None where the class has no income (e.g. `commodity`)
    gain_treatment: GainTreatment


# Two simplifications worth knowing about: `reit_pid` (property income
# distributions) is taxed here like ordinary non-savings income — no
# special PID band is modelled, though real PID has its own 20%
# withholding and fills bands independently of salary/pension income.
# `offshore_non_reporting`'s ongoing distributions are treated as
# equity-like (dividend rates); its DISPOSAL gain (via
# `compute_capital_gains_tax`'s caller) should be routed through the
# taxed_as_income treatment below, not the CGT rates, since non-reporting
# funds' gains are taxed as income with no annual exemption.
_CHARACTERS: dict[TaxClass, TaxClassCharacter] = {
    "cash": TaxClassCharacter("savings", "exempt"),
    "gilt": TaxClassCharacter("savings", "exempt"),
    "qcb": TaxClassCharacter("savings", "exempt"),
    "non_qcb_bond": TaxClassCharacter("savings", "chargeable"),
    "bond_fund_inc": TaxClassCharacter("savings", "chargeable"),
    "bond_fund_acc": TaxClassCharacter("savings", "chargeable"),
    "equity_fund_inc": TaxClassCharacter("dividends", "chargeable"),
    "equity_fund_acc": TaxClassCharacter("dividends", "chargeable"),
    "equity_direct": TaxClassCharacter("dividends", "chargeable"),
    "offshore_non_reporting": TaxClassCharacter("dividends", "taxed_as_income"),
    "investment_trust_interest": TaxClassCharacter("savings", "chargeable"),
    "reit_pid": TaxClassCharacter("non_savings", "chargeable"),
    "commodity": TaxClassCharacter(None, "chargeable"),
}


def tax_class_character(tax_class: TaxClass) -> TaxClassCharacter:
    return _CHARACTERS[tax_class]
