"""Plain, storage-agnostic types for the tax engine's public interface.

These are this package's own types — not an ORM row, not a framework
model from whatever app embeds this. A caller in any application can
construct a TaxYearParameters and call tax() without any web framework or
database library in scope at all.
"""

from dataclasses import dataclass

from uk_tax.money import Real


@dataclass(frozen=True, slots=True)
class TaxYearParameters:
    """One tax year's derived, already-real-terms band/rate table.

    Rates are fractions (0.20, not 20) — the natural unit for
    multiplication. Money fields are Real: if you're working from nominal
    tax-year thresholds (rare — thresholds are normally quoted in the
    terms of the year they apply to), deflate them to Real via
    `uk_tax.money.deflate_threshold` before constructing this. See
    SPEC.md for the current tax year's actual figures.
    """

    personal_allowance: Real
    pa_taper_threshold: Real
    pa_taper_rate: float  # ratio, e.g. 0.5 = £1 per £2 — not a percentage
    basic_rate_band: Real  # width above PA
    additional_rate_threshold: Real  # absolute, from £0
    basic_rate: float
    higher_rate: float
    additional_rate: float
    starting_rate_for_savings_band: Real
    psa_basic_rate: Real
    psa_higher_rate: Real
    psa_additional_rate: Real
    dividend_allowance: Real
    dividend_basic_rate: float
    dividend_higher_rate: float
    dividend_additional_rate: float
    cgt_lower_rate: float
    cgt_higher_rate: float
    cgt_annual_exempt_amount: Real


@dataclass(frozen=True, slots=True)
class BandCharge:
    """One line of the tax "workings" — a slice of income/gain in one
    category, taxed at one marginal rate."""

    category: str  # "non_savings" | "savings" | "dividends" | "gains"
    band: str  # e.g. "basic_rate", "starting_rate_for_savings", "psa", "dividend_allowance", "cgt_annual_exempt_amount"
    amount: Real
    rate: float
    tax: Real


@dataclass(frozen=True, slots=True)
class TaxResult:
    liability: Real
    charges: tuple[BandCharge, ...]
