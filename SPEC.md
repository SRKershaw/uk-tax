# UK Personal Tax Calculations — Spec & Reference Implementation

VERSION 2

For: a Python tax-calculation module (earnings, interest, dividends, capital growth)
Tax year: 2026/27 (current), with 2027/28 rates included for the confirmed April 2027 changes
Status: every figure below has been checked against HMRC/GOV.UK, the House of Commons
Library, and 13 independently-published LITRG worked examples — all reproduced exactly
(see Section 6). Not legal or financial advice; verify against GOV.UK before shipping.

> **Note on this repo's actual implementation** (`src/uk_tax/`): it implements
> everything below, but structured slightly differently from Section 6's illustrative
> reference implementation — money values are wrapped in a `Real` type rather than
> plain floats (see `README.md`), and results come back as a `TaxResult` (a total
> liability plus an itemised list of `BandCharge`s) rather than a nested dict. Same
> numbers, same rules, different plumbing. `tests/` mirrors every case in Section 7
> against the actual module, not the illustrative one below.

---

## 1. Scope

**Covered:**

- Income Tax on non-savings, non-dividend income (earnings, pension, trading profits) — rest-of-UK rates
- Income Tax on savings interest (Starting Rate for Savings + Personal Savings Allowance)
- Income Tax on dividends (Dividend Allowance)
- Personal Allowance, including the taper above £100,000
- Capital Gains Tax (separate tax, own allowance, own two rates)

**Explicitly out of scope** (flag clearly in the app if any of these apply to a user):

- Scottish and Welsh income tax rates (Scottish rates diverge materially; Welsh rates
  currently mirror rUK but are set independently)
- National Insurance
- Student loan repayments
- Marriage Allowance / Blind Person's Allowance
- Gift Aid and relief-at-source pension contributions extending the basic-rate band
- High Income Child Benefit Charge
- Property income (gets its own separate rate band from 6 April 2027 — not modelled here)
- The pre-April-2027 Personal Allowance *reallocation* election (see Section 7) — this
  implementation always uses the mandatory ordering (non-savings → savings → dividends),
  which is also what becomes compulsory for everyone from 6 April 2027 anyway
- Joint account/dividend income splitting between spouses
- ISA and pension-wrapper income (assumed already excluded from whatever figures are passed in)

---

## 2. Order of taxation — the one rule everything else depends on

Income is always taxed in this fixed order, each type stacking on top of the last:

1. **Non-savings, non-dividend income** (earnings/pension/trading) — taxed first.
2. **Savings interest** — taxed second, using whatever Personal Allowance, and
   basic/higher-rate band space, non-savings income hasn't already used.
3. **Dividends** — taxed last, on top of both of the above.

**Capital Gains Tax is not part of this stack at all.** It's a wholly separate tax
with its own annual exemption and its own two rates. A gain is stacked on top of
*total income* purely to work out how much of the basic-rate band is left for the
18%/24% split — nothing else about it touches the income tax calculation.

---

## 3. Rates & thresholds

### 3.1 Current — 2026/27

| Item | Value |
| --- | --- |
| Personal Allowance | £12,570 |
| PA taper start / fully gone by | £100,000 / £125,140 (£1 lost per £2 over £100k) |
| Higher-rate threshold (total income) | £50,270 |
| Additional-rate threshold (total income) | £125,140 |
| Earnings: basic / higher / additional rate | 20% / 40% / 45% |
| Savings starting-rate limit | £5,000 (0% band) |
| Personal Savings Allowance: basic / higher / additional | £1,000 / £500 / £0 |
| Savings: basic / higher / additional rate | 20% / 40% / 45% *(same as earnings this year)* |
| Dividend Allowance | £500 (flat — same for everyone, unlike the PSA) |
| Dividends: basic / higher / additional rate | 10.75% / 35.75% / 39.35% |
| CGT Annual Exempt Amount | £3,000 |
| CGT: basic / higher rate | 18% / 24% (all asset types — shares, funds, property, crypto; no additional-rate tier) |

### 3.2 Confirmed changes from 6 April 2027 (Finance Act 2026 — already enacted, not a proposal)

| Item | 2026/27 | 2027/28 onward |
| --- | --- | --- |
| Savings: basic / higher / additional rate | 20% / 40% / 45% | **22% / 42% / 47%** |
| PA allocation order | mandatory non-savings → savings → dividends (as modelled here) | same — but the pre-2027 discretion to request a more favourable allocation disappears entirely |

Everything else in the table above (thresholds, PSA amounts, Dividend Allowance/rates,
CGT) is unaffected by the April 2027 change as far as currently legislated. Dividend
rates already rose (10.75%/35.75%/39.35%) on 6 April 2026 — that's a done deal already
baked into the "current" column above, not a future change.

---

## 4. Mechanics that are easy to get wrong

These are the actual bugs found and fixed while building this out — worth encoding as
comments/tests in the implementation, since they're the parts a naive reading of GOV.UK
guidance tends to miss.

**4.1 — Starting Rate for Savings is reduced by EARNINGS only, not total income.**
It's `MAX(0, £5,000 − MAX(0, earnings − £12,570))` — using the *standard, untapered*
Personal Allowance and *earnings alone*. A common mistake is subtracting the interest
itself (or total income) from the £5,000 limit, which wrongly zeroes it out whenever
interest is large relative to earnings.

**4.2 — The higher-rate band widens when the Personal Allowance is tapered.**
The additional-rate threshold (£125,140) is fixed in *total-income* terms, not
taxable-income terms. So as PA shrinks, the taxable-income gap between the higher-rate
start and the additional-rate start actually grows: `higher_band_width = £74,870 +
(£12,570 − PA_available)`. Skip this and you'll push income into the 45%/47% band too
early for anyone with income between £100,000 and £125,140+.

**4.3 — Nil-rate slices still consume band capacity.**
Interest/dividends sheltered by the Starting Rate, the PSA, or the Dividend Allowance
are taxed at 0% but still count as using up basic/higher-rate band space — they are
*not* simply subtracted from the income total before working out what's left of the
band for the next, actually-taxed slice. (This is explicit in LITRG's own worked
example: a £500 PSA-sheltered slice still eats £500 of the basic-rate band.)

**4.4 — PSA/Dividend Allowance tier depends on *combined* income.**
Whether someone gets the £1,000, £500, or £0 PSA (and whether dividends see 10.75%,
35.75% or 39.35%) is decided by adding *all* income together first, not by earnings
alone. It's genuinely possible for someone whose earnings alone would be basic-rate to
be pushed into the higher PSA/dividend tier purely by a large interest or dividend
payment.

**4.5 — The Personal Allowance taper uses total income across all three types.**
`reduction = MAX(0, (total_income − 100,000) / 2)`, where `total_income = earnings +
interest + dividends`.

**4.6 — The PSA tier boundaries are strictly-greater-than, not greater-or-equal.**
Total income of exactly £50,270 is still the *basic*-rate tier (£1,000 PSA); it takes
£50,271 — one pound over — to drop to the higher-rate tier (£500 PSA). LITRG's own
"James" (£50,270) vs "John" (£50,271) examples confirm this explicitly ("into the
higher rate tax band, by £1!"). The same strict-`>` convention is applied to the
additional-rate boundary (£125,140) for consistency, though no published worked
example tests that exact boundary pound.

---

## 5. Pseudocode

```
function personal_allowance_available(total_income):
    return max(0, PA - max(0, (total_income - PA_TAPER_START) / 2))

function earnings_tax(earnings, total_income):
    pa_available = personal_allowance_available(total_income)
    pa_used      = min(pa_available, earnings)
    basic_width  = HIGHER_RATE_START - PA                         # fixed £37,700
    higher_width = (ADDITIONAL_RATE_START - HIGHER_RATE_START)
                   + (PA - pa_available)                          # widens if tapered

    at_lower      = clamp( min(earnings, HIGHER_RATE_START) - pa_available, 0, basic_width )
    at_higher     = clamp( min(earnings, ADDITIONAL_RATE_START) - at_lower - pa_available, 0, higher_width )
    at_additional = earnings - at_lower - at_higher - pa_used

    tax = at_lower*RATE_LOWER + at_higher*RATE_HIGHER + at_additional*RATE_ADDITIONAL
    return { tax, basic_band_remaining: basic_width - at_lower,
             higher_band_remaining: higher_width - at_higher, pa_available, pa_used }

function savings_tax(earnings, interest, total_income, earnings_result):
    pa_leftover = earnings_result.pa_available - earnings_result.pa_used

    # NOTE: earnings only, standard PA - see 4.1
    starting_rate_available = max(0, STARTING_RATE_LIMIT - max(0, earnings - PA))

    # strict '>' - the boundary pound itself is still in the lower tier
    psa = PSA_ADDITIONAL if total_income > ADDITIONAL_RATE_START
          else PSA_HIGHER if total_income > HIGHER_RATE_START
          else PSA_BASIC

    after_pa            = max(0, interest - pa_leftover)
    starting_rate_used   = min(after_pa, starting_rate_available)
    after_starting_rate  = after_pa - starting_rate_used
    psa_used             = min(after_starting_rate, psa)
    taxable              = after_starting_rate - psa_used

    basic_remaining  = earnings_result.basic_band_remaining
    higher_remaining = earnings_result.higher_band_remaining

    # nil-rate slices still consume band space - see 4.3
    sr_in_basic  = min(starting_rate_used, basic_remaining)
    psa_in_basic = min(psa_used, max(0, basic_remaining - sr_in_basic))
    psa_in_higher = psa_used - psa_in_basic

    at_lower      = min(taxable, max(0, basic_remaining - sr_in_basic - psa_in_basic))
    at_higher     = min(max(0, taxable - at_lower), max(0, higher_remaining - psa_in_higher))
    at_additional = max(0, taxable - at_lower - at_higher)

    tax = at_lower*S_LOWER + at_higher*S_HIGHER + at_additional*S_ADDITIONAL
    return { tax, pa_leftover,
             basic_band_remaining:  basic_remaining  - sr_in_basic - psa_in_basic - at_lower,
             higher_band_remaining: higher_remaining - psa_in_higher - at_higher }

function dividend_tax(dividends, interest, savings_result):
    pa_leftover_after_savings = max(0, savings_result.pa_leftover - interest)
    after_pa = max(0, dividends - pa_leftover_after_savings)
    taxable  = max(0, after_pa - DIVIDEND_ALLOWANCE)               # flat, no tiering

    at_lower      = min(taxable, savings_result.basic_band_remaining)
    at_higher     = min(max(0, taxable - at_lower), savings_result.higher_band_remaining)
    at_additional = max(0, taxable - at_lower - at_higher)

    tax = at_lower*D_LOWER + at_higher*D_HIGHER + at_additional*D_ADDITIONAL
    return { tax }

function income_tax_total(earnings, interest, dividends):
    total_income = earnings + interest + dividends
    e = earnings_tax(earnings, total_income)
    s = savings_tax(earnings, interest, total_income, e)
    d = dividend_tax(dividends, interest, s)
    return e.tax + s.tax + d.tax

function capital_gains_tax(total_income, gain):                    # separate tax entirely
    taxable_gain = max(0, gain - CGT_ANNUAL_EXEMPT_AMOUNT)
    basic_remaining = max(0, HIGHER_RATE_START - total_income)
    at_lower  = min(taxable_gain, basic_remaining)
    at_higher = max(0, taxable_gain - at_lower)
    return at_lower*CGT_LOWER + at_higher*CGT_HIGHER
```

---

## 6. Python reference implementation

Validated (see Section 7) against 13 published LITRG examples plus every edge case
worked through while building this out, including full Personal Allowance taper. Drop
this in directly or adapt — the `TaxYearRates` dataclass is designed so switching to
2027/28 is a one-line change.

```python
"""
Reference implementation of UK personal tax calculations:
non-savings (earnings) income, savings interest, dividends, and CGT.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TaxYearRates:
    """All the constants a tax year needs. Swap this out to move between years."""
    personal_allowance: float = 12_570
    pa_taper_start: float = 100_000          # PA reduces above this...
    pa_taper_end: float = 125_140            # ...to zero by this point
    higher_rate_start: float = 50_270        # total-income point where 40% starts
    additional_rate_start: float = 125_140   # total-income point where 45% starts

    earnings_lower_rate: float = 0.20
    earnings_higher_rate: float = 0.40
    earnings_additional_rate: float = 0.45

    savings_starting_rate_limit: float = 5_000     # 0% band, up to this much interest
    savings_allowance_basic: float = 1_000         # PSA for basic-rate taxpayers
    savings_allowance_higher: float = 500          # PSA for higher-rate taxpayers
    # additional-rate taxpayers get £0 PSA

    savings_lower_rate: float = 0.20
    savings_higher_rate: float = 0.40
    savings_additional_rate: float = 0.45

    dividend_allowance: float = 500
    dividend_lower_rate: float = 0.1075
    dividend_higher_rate: float = 0.3575
    dividend_additional_rate: float = 0.3935

    cgt_annual_exempt_amount: float = 3_000
    cgt_lower_rate: float = 0.18
    cgt_higher_rate: float = 0.24


RATES_2026_27 = TaxYearRates()

RATES_2027_28 = TaxYearRates(
    savings_lower_rate=0.22,
    savings_higher_rate=0.42,
    savings_additional_rate=0.47,
    # Everything else unchanged as far as currently legislated (Finance Act 2026).
    # The mandatory PA-ordering rule (non-savings first, always) is already how
    # this implementation behaves in every tax year - no change needed for that.
)


def _n(x):
    """Excel's N(): treat None/blank as 0."""
    return x or 0


def personal_allowance_available(total_income: float, rates: TaxYearRates) -> float:
    """PA taper: reduced £1 for every £2 of total income above the taper start,
    down to zero once fully tapered."""
    reduction = max(0.0, (total_income - rates.pa_taper_start) / 2)
    return max(0.0, rates.personal_allowance - reduction)


def earnings_tax(earnings: float, total_income: float, rates: TaxYearRates) -> dict:
    """Tax on non-savings, non-dividend income (earnings/pension/trading).
    Always taxed first; always absorbs Personal Allowance first."""
    earnings = _n(earnings)
    pa_available = personal_allowance_available(total_income, rates)
    pa_used = min(pa_available, earnings)

    basic_width = rates.higher_rate_start - rates.personal_allowance          # 37,700, fixed
    # Higher-rate band widens when PA is tapered, because the additional-rate
    # threshold is fixed in TOTAL-income terms while the PA that gets subtracted
    # to reach "taxable income" shrinks - see spec section 4.2.
    higher_width = ((rates.additional_rate_start - rates.higher_rate_start)
                     + (rates.personal_allowance - pa_available))

    taxable = earnings - pa_used
    at_lower = min(max(0.0, min(earnings, rates.higher_rate_start) - pa_available), basic_width)
    at_higher = min(max(0.0, min(earnings, rates.additional_rate_start) - at_lower - pa_available),
                     higher_width)
    at_additional = earnings - at_higher - at_lower - pa_used

    tax = (at_lower * rates.earnings_lower_rate
           + at_higher * rates.earnings_higher_rate
           + at_additional * rates.earnings_additional_rate)

    return {
        "pa_available": pa_available, "pa_used": pa_used,
        "at_lower": at_lower, "at_higher": at_higher, "at_additional": at_additional,
        "tax": tax,
        # exposed for the savings/dividend calculations that stack on top of this
        "basic_band_remaining": basic_width - at_lower,
        "higher_band_remaining": max(0.0, higher_width - at_higher),
    }


def savings_tax(earnings: float, interest: float, total_income: float,
                 earnings_result: dict, rates: TaxYearRates) -> dict:
    """Tax on savings interest. Stacks on top of earnings. Handles, in order:
    leftover Personal Allowance, Starting Rate for Savings, then the PSA -
    and correctly treats all three as still consuming band capacity."""
    earnings = _n(earnings)
    interest = _n(interest)

    pa_available = earnings_result["pa_available"]
    pa_leftover = pa_available - earnings_result["pa_used"]

    # Starting Rate: reduced by EARNINGS only (not total income) in excess of the
    # STANDARD (untapered) Personal Allowance - this is the single most common
    # implementation bug. See spec section 4.1.
    starting_rate_available = max(0.0, rates.savings_starting_rate_limit
                                   - max(0.0, earnings - rates.personal_allowance))

    # NOTE: strict '>', not '>=' - LITRG's own worked examples confirm the
    # boundary pound (total income exactly £50,270, or exactly £125,140) still
    # sits in the LOWER tier. "James" at exactly £50,270 gets the full £1,000
    # PSA; "John" at £50,271 - one pound over - is the first to drop to £500.
    if total_income > rates.additional_rate_start:
        psa = 0.0
    elif total_income > rates.higher_rate_start:
        psa = rates.savings_allowance_higher
    else:
        psa = rates.savings_allowance_basic

    after_pa = max(0.0, interest - pa_leftover)
    starting_rate_used = min(after_pa, starting_rate_available)
    after_starting_rate = after_pa - starting_rate_used
    psa_used = min(after_starting_rate, psa)
    taxable = after_starting_rate - psa_used

    basic_remaining = earnings_result["basic_band_remaining"]
    higher_remaining = earnings_result["higher_band_remaining"]

    # Starting Rate always sits inside the basic band; PSA sits wherever the
    # marginal interest would otherwise land (basic first, spilling to higher).
    sr_in_basic = min(starting_rate_used, basic_remaining)
    psa_in_basic = min(psa_used, max(0.0, basic_remaining - sr_in_basic))
    psa_in_higher = psa_used - psa_in_basic

    at_lower = min(taxable, max(0.0, basic_remaining - sr_in_basic - psa_in_basic))
    at_higher = min(max(0.0, taxable - at_lower),
                     max(0.0, higher_remaining - psa_in_higher))
    at_additional = max(0.0, taxable - at_lower - at_higher)

    tax = (at_lower * rates.savings_lower_rate
           + at_higher * rates.savings_higher_rate
           + at_additional * rates.savings_additional_rate)

    return {
        "pa_leftover": pa_leftover, "starting_rate_available": starting_rate_available,
        "psa": psa, "at_lower": at_lower, "at_higher": at_higher,
        "at_additional": at_additional, "tax": tax,
        "basic_band_remaining": max(0.0, basic_remaining - sr_in_basic - psa_in_basic - at_lower),
        "higher_band_remaining": max(0.0, higher_remaining - psa_in_higher - at_higher),
    }


def dividend_tax(dividends: float, interest: float,
                  savings_result: dict, rates: TaxYearRates) -> dict:
    """Tax on dividends. Stacks last, on top of earnings and savings."""
    dividends = _n(dividends)

    pa_leftover_after_savings = max(0.0, savings_result["pa_leftover"] - _n(interest))
    after_pa = max(0.0, dividends - pa_leftover_after_savings)
    taxable = max(0.0, after_pa - rates.dividend_allowance)   # flat £500, no tiering

    basic_remaining = savings_result["basic_band_remaining"]
    higher_remaining = savings_result["higher_band_remaining"]

    at_lower = min(taxable, basic_remaining)
    at_higher = min(max(0.0, taxable - at_lower), higher_remaining)
    at_additional = max(0.0, taxable - at_lower - at_higher)

    tax = (at_lower * rates.dividend_lower_rate
           + at_higher * rates.dividend_higher_rate
           + at_additional * rates.dividend_additional_rate)

    return {"at_lower": at_lower, "at_higher": at_higher,
            "at_additional": at_additional, "tax": tax}


def income_tax_total(earnings: float, interest: float, dividends: float,
                      rates: TaxYearRates = RATES_2026_27) -> dict:
    """Full income tax calculation across all three income types."""
    total_income = _n(earnings) + _n(interest) + _n(dividends)
    e = earnings_tax(earnings, total_income, rates)
    s = savings_tax(earnings, interest, total_income, e, rates)
    d = dividend_tax(dividends, interest, s, rates)
    return {
        "total_income": total_income,
        "earnings": e, "savings": s, "dividends": d,
        "total_tax": round(e["tax"] + s["tax"] + d["tax"], 2),
    }


def capital_gains_tax(total_income: float, gain: float,
                       rates: TaxYearRates = RATES_2026_27) -> dict:
    """CGT is a wholly separate tax: own allowance, own two rates, no
    additional-rate tier. The gain stacks on top of total income only to
    determine the 18%/24% split."""
    taxable_gain = max(0.0, _n(gain) - rates.cgt_annual_exempt_amount)
    basic_band_remaining = max(0.0, rates.higher_rate_start - _n(total_income))
    at_lower = min(taxable_gain, basic_band_remaining)
    at_higher = max(0.0, taxable_gain - at_lower)
    tax = at_lower * rates.cgt_lower_rate + at_higher * rates.cgt_higher_rate
    return {"taxable_gain": taxable_gain, "at_lower": at_lower,
            "at_higher": at_higher, "tax": round(tax, 2)}
```

---

## 7. Validation suite

Every row below is a published worked example (mostly from LITRG's Personal Savings
Allowance and Starting Rate for Savings guidance pages) or a manually-verified edge
case, and the reference implementation above reproduces every one exactly.

| Case | Earnings | Interest | Dividends | Expected total tax |
| --- | ---: | ---: | ---: | ---: |
| Henry | £25,000 | £600 | £0 | £2,486.00 |
| Henry (variant) | £25,000 | £1,250 | £0 | £2,536.00 |
| John (just over higher threshold) | £49,271 | £1,000 | £0 | £7,440.40 |
| James (exactly at threshold) | £49,270 | £1,000 | £0 | £7,340.00 |
| Magda (PSA overflows into higher band) | £48,650 | £1,750 | £0 | £7,492.00 |
| Mo — scenario A | £14,000 | £1,500 | £0 | £286.00 |
| Mo — scenario B | £14,000 | £3,650 | £0 | £286.00 |
| Mo — scenario C | £14,000 | £4,650 | £0 | £302.00 |
| Mo — scenario D | £18,000 | £1,500 | £0 | £1,186.00 |
| Gerry | £17,700 | £1,200 | £0 | £1,066.00 |
| Amanda (PA leftover shelters interest) | £10,900 | £8,000 | £0 | £66.00 |
| Michael (partial Starting Rate) | £13,100 | £5,800 | £0 | £172.00 |
| Richard (savings income only) | £0 | £18,900 | £0 | £66.00 |
| £150k salary only (full PA taper check) | £150,000 | £0 | £0 | £53,703.00 |
| Dividend stacking check | £0 | £20,000 | £10,000 | £1,307.25 |

Plus PA-taper edge cases (earnings + interest, no dividends):

| Earnings | Interest | Expected total tax |
| ---: | ---: | ---: |
| £0 | £20,000 | £286.00 |
| £20,000 | £20,000 | £5,286.00 |
| £0 | £60,000 | £10,332.00 |
| £60,000 | £60,000 | £39,232.00 |
| £0 | £110,000 | £32,332.00 |
| £110,000 | £110,000 | £85,203.00 |
| £0 | £100,000 | £26,332.00 |
| £100,000 | £100,000 | £76,203.00 |
| £0 | £150,000 | £52,703.00 |
| £150,000 | £150,000 | £121,203.00 |

CGT check: total income £20,000, gain £15,000 → **£2,160.00** (all at 18%, since
£30,270 of basic-rate band remains against a £12,000 taxable gain).

**Ready-to-run pytest-style block** (paste directly, or adapt to your test framework):

```python
import pytest
from your_module import income_tax_total, capital_gains_tax

CASES = [
    ("Henry",             25000,    600,      0,  2486.00),
    ("Henry_variant",     25000,   1250,      0,  2536.00),
    ("John",              49271,   1000,      0,  7440.40),
    ("James",             49270,   1000,      0,  7340.00),
    ("Magda",             48650,   1750,      0,  7492.00),
    ("Mo_A",              14000,   1500,      0,   286.00),
    ("Mo_B",              14000,   3650,      0,   286.00),
    ("Mo_C",              14000,   4650,      0,   302.00),
    ("Mo_D",              18000,   1500,      0,  1186.00),
    ("Gerry",             17700,   1200,      0,  1066.00),
    ("Amanda",            10900,   8000,      0,    66.00),
    ("Michael",           13100,   5800,      0,   172.00),
    ("Richard",               0,  18900,      0,    66.00),
    ("salary_150k",      150000,      0,      0, 53703.00),
    ("dividend_stack",        0,  20000,  10000,  1307.25),
    ("taper_0_20k",           0,  20000,      0,   286.00),
    ("taper_20k_20k",     20000,  20000,      0,  5286.00),
    ("taper_0_60k",           0,  60000,      0, 10332.00),
    ("taper_60k_60k",     60000,  60000,      0, 39232.00),
    ("taper_0_110k",          0, 110000,      0, 32332.00),
    ("taper_110k_110k",  110000, 110000,      0, 85203.00),
    ("taper_0_100k",          0, 100000,      0, 26332.00),
    ("taper_100k_100k",  100000, 100000,      0, 76203.00),
    ("taper_0_150k",          0, 150000,      0, 52703.00),
    ("taper_150k_150k",  150000, 150000,      0, 121203.00),
]

@pytest.mark.parametrize("label,earnings,interest,dividends,expected", CASES)
def test_income_tax(label, earnings, interest, dividends, expected):
    result = income_tax_total(earnings, interest, dividends)
    assert result["total_tax"] == pytest.approx(expected, abs=0.01)

def test_cgt():
    result = capital_gains_tax(total_income=20000, gain=15000)
    assert result["tax"] == pytest.approx(2160.00, abs=0.01)
```

---

## 8. Sources

- HMRC / GOV.UK: `gov.uk/apply-tax-free-interest-on-savings`, `gov.uk/government/publications/changes-to-tax-rates-for-property-savings-and-dividend-income`
- House of Commons Library: *Direct taxes: Rates and allowances for 2025/26* (CBP-10237), *Budget 2025: income tax rates on income from property, savings and dividends* (CBP-10450)
- LITRG (Low Incomes Tax Reform Group, Chartered Institute of Taxation): Tax on savings income, Personal savings allowance, Starting rate for savings, Personal allowance — all worked examples reproduced exactly in Section 7
- Finance Act 2026 (enacted) — confirms the 2027/28 savings rates and PA ordering rule
