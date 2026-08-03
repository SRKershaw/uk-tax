# uk-tax

A pure UK personal tax engine — income tax (non-savings, savings, dividends), Personal
Allowance including the taper above £100,000, and Capital Gains Tax. No web framework,
no database, no I/O of any kind: pass in income figures and a rates table, get back a
liability and an itemised breakdown of how it was reached.

Extracted from the [drawdown](https://github.com/SRKershaw/drawdown) retirement-planning
project, where it's `backend/src/drawdown/kernel/tax`. Built to be portable from the
start — this is that same code, copied out and renamed, with no changes to the tax
logic itself.

## What it covers

- Income Tax on non-savings income (earnings, pension, trading profits)
- Income Tax on savings interest — Starting Rate for Savings + Personal Savings Allowance
- Income Tax on dividends — Dividend Allowance
- Personal Allowance, including the taper from £100,000 to £125,140
- Capital Gains Tax — separate tax, own annual exemption, own two rates
- A `tax_class` → income/gain character lookup for common UK asset types (gilts, QCBs,
  equity funds, offshore non-reporting funds, REITs, etc.)

See `SPEC.md` for the full rules, current rates, worked examples, and the specific
mechanics that are easy to get wrong (band ordering, the PSA's boundary being strict
`>` rather than `>=`, nil-rate slices still consuming band capacity, and so on).

**Out of scope**, deliberately — see `SPEC.md` §1 for the full list and reasoning:
Scottish/Welsh rates, National Insurance, student loan repayments, Marriage Allowance,
Gift Aid/pension relief band extension, High Income Child Benefit Charge, and the
pre-April-2027 Personal Allowance reallocation election.

## Install

```
uv sync
```

or with plain pip: `pip install -e .`

## Use

```python
from uk_tax.money import Real
from uk_tax.tax import tax
from uk_tax.tax.types import TaxYearParameters

# 2026/27 rates — see SPEC.md §3.1 for the source and any later year's figures
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

result = tax(
    non_savings=Real(30000),
    savings=Real(2000),
    dividends=Real(5000),
    gains=Real(15000),
    params=PARAMS,
)

print(result.liability.value)  # total tax due, as a plain float
for charge in result.charges:  # itemised: which band, how much, at what rate
    print(charge.category, charge.band, charge.amount.value, charge.rate, charge.tax.value)
```

`tax()` combines income tax and CGT. Call `compute_income_tax(...)` or
`compute_capital_gains_tax(...)` directly (both importable from `uk_tax.tax`) if you
only need one or the other.

## Why money is a `Real` type, not a plain float

`Real` (`uk_tax.money.Real`) exists to catch one specific class of bug: mixing
"today's terms" money with money still expressed in a future year's nominal terms —
which matters the moment any of this feeds a multi-year plan where tax thresholds get
inflated forward but pound values don't. `Real + Real` works; `Real + Nominal` raises
`TypeError` immediately rather than silently producing a wrong number. If your
application only ever works in today's terms, this is just a thin wrapper — construct
everything as `Real(...)`.

## Testing

```
uv run pytest
```

55 tests: every worked example in `SPEC.md` §7 (13 published LITRG examples plus 10
Personal Allowance taper edge cases), the Capital Gains Tax example, and structural
tests for band-widening under the taper, nil-rate-band consumption, and the PSA's
strict-`>` boundary.

## Status

Extracted 2026-08-03. Validated against 13 published LITRG worked examples, HMRC's own
SAIM1110 example (see `SPEC.md` for why the beneficial-reallocation election it
illustrates isn't modelled here), and a second independently-checked spreadsheet.
Known gap: savings tax rates diverge from non-savings rates from 6 April 2027 (Finance
Act 2026, enacted) — `TaxYearParameters` has one shared rate triple for both, correct
for 2026/27, not yet extended for 2027/28+.
