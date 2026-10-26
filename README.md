# Con Edison Rate Optimizer

A local Python 3.12+ CLI for auditable residential electricity rate analysis.
Import smart-meter CSV or Green Button ESPI XML, inspect its quality, replay the
same consumption through verified SC1 tariffs, and create an offline HTML report.
No accounts, backend, database, telemetry, or network calls at runtime.

**Current scope:** verified Standard (Rate I) and voluntary TOU (Rate III)
**base delivery**, for billing periods from **February 1 through October 26, 2026**.
The exclusive October 27 cutoff is the research verification limit, not a tariff
expiration. Dates outside that window fail explicitly. Demand plans are documented
but unsupported; their exact meter integration conventions need verification.

Whole bills and switching recommendations require additional inputs. The tool
does not turn unknown supply, adjustments, or taxes into zero. A lower base
delivery cost alone is not a whole-bill savings recommendation.

## Install

```powershell
git clone https://github.com/QFREEE/coned-rate-optimizer.git
cd coned-rate-optimizer
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\coned-optimize --help
```

On macOS/Linux use `python3.12 -m venv .venv` and `.venv/bin/` instead of
`.venv\Scripts\`. Once activated, the commands below work as written. If you use
uv, `uv sync --locked --extra dev` installs the pinned dependency set from
`uv.lock`; prefix commands with `uv run --locked`.

## One-command report

Download electricity **interval consumption** under Con Edison My Account →
Usage → Green Button Download. Choose one meter, electricity consumption, the
finest available resolution, and CSV or XML. Keep real files under `private/`,
which is ignored by Git. Do not commit your usage or bills.

```console
coned-optimize report private/usage.csv --output reports/my-house.html
```

Open the HTML file in a browser. It contains the ranked base-delivery comparison,
monthly breakdowns, static charts, coverage, restrictions, tariff leaf references,
and explicit recommendation blockers. It works offline and uses no external assets.

```console
coned-optimize inspect private/usage.xml
coned-optimize compare private/usage.csv --bill private/bills.csv
coned-optimize report private/usage.xml --bill private/bills.csv --components private/components.csv --baseline standard --output reports/audit.html --json reports/audit.json
```

`--baseline tou` selects an existing Rate III baseline. Existing legacy TOU,
standby, demand, solar/net-metered, and special-rider baselines are unsupported.

## Verified rules

Research preceded implementation; see [research and citations](docs/research.md),
[plan](docs/implementation-plan.md), and [tariff configuration](src/coned_optimize/tariffs/2026-02-01.json).

| Plan | Enabled | Base-delivery rules |
|---|---|---|
| SC1 Rate I | Yes | $21/30 days; winter $0.16402/kWh; summer first prorated 250 kWh $0.16402, excess $0.18858 |
| SC1 Rate III | Yes | $21/30 days; 08:00–24:00 **all days including weekends/holidays**: summer $0.2786, winter $0.1711/kWh; midnight–08:00 $0.0522 |
| SC1 Rate IV / Steady Use | No | Top-three daily 60-minute-demand structure verified; utility endpoint convention unresolved |
| Rider Z / Smart Energy | No | Demand convention unresolved; pilot variants cannot be assumed eligible |
| SC1 Rate II | No | Closed to new applicants since March 2014 |
| SC1 Rate V | No | Special standby service |

Summer is June–September. Charges and tier thresholds use elapsed local service
days/30. Rate/season changes use day-share proration across the billing cycle
per General Rule 10.5.1; energy is not allocated proportionally into missing
intervals. Actual customer-reading seasonal elections and early termination
within 30 days of opening service are unsupported.

The package includes a dated excerpt of relevant tariff leaves. The official
[Con Edison PSC10 index](https://www.coned.com/en/rates-tariffs/rates/electric-rates-schedule/electric-psc-10)
and filed schedules remain authoritative. To extend date coverage, review the
current/historical leaf revisions and publish a new bounded JSON version. The
engine supports multiple non-overlapping versions and prorates changes by service
day. It never fetches or updates rates silently.

## Data formats and quality

Canonical CSV (timestamps indicate interval **starts and exclusive ends**):

```csv
start,end,kwh
2026-07-01T00:00:00-04:00,2026-07-01T00:15:00-04:00,0.30
```

`duration_seconds` can replace `end`. Common ConEd headers
`TYPE,DATE,START TIME,END TIME,USAGE,UNITS,NOTES` and `USAGE (kWh)` are accepted,
including metadata lines before the table. In that native layout the documented
inclusive end minute `00:14` is normalized to exclusive `00:15`; canonical
`start/end` fields are never adjusted. Only electricity interval energy in kWh
or Wh is accepted. `NOTES`/quality flags other than actual/0 are rejected.

XML requires one consumption stream and a single ReadingType: electricity (1),
forward/import (1), energy (12), delta accumulation (4), Wh (72); the decimal
multiplier and UTC epoch interval start/duration are respected. Valid quality 0
and revenue quality 19 are accepted; other flagged readings are rejected. Multiple
meter channels/ReadingTypes require a separate single-stream export. This strict
subset avoids silently treating cumulative readings or export as consumption.

Offsets and UTC are preferred. Unambiguous naive timestamps mean
`America/New_York`. Ambiguous fall-back clock times and nonexistent spring-forward
times are reported invalid; the tool never guesses which repeated hour was meant.
If your CSV lacks offsets at fall-back, use XML or obtain explicit-offset data.

`inspect` reports invalid records, duplicate timestamps, overlaps, gap spans,
observed kWh, actual start/end, and completeness within the observation span.
Comparison separately measures completeness against **each entire billing period**.
Default calendar buckets stop at the tariff verification cutoff if it falls inside
the final observed month; they do not include unverified future prices. Actual
bill boundaries are never clipped, and a bill outside verified dates is rejected.
Invalid/overlapping/duplicate data blocks comparison. Missing intervals remain
missing; partial periods show observed energy costs plus full-period fixed charges,
are labeled incomplete, and block recommendations. TOU refuses observations that
span multiple price windows, such as daily totals. Intervals crossing bill boundaries
are rejected rather than split with assumed uniform consumption.

## Bills and reconciliation

Actual bill CSV uses explicit meter-read boundaries, with `end` exclusive:

```csv
start,end,delivery,supply,adjustments,taxes,total
2026-07-01,2026-08-01,108.89,59.52,14.88,6.51,189.80
```

Those are **synthetic values**, not current supply or tax rates. `delivery` here
means customer charge plus base delivery energy; `adjustments` groups all other
pre-tax charges. Map real bill line items accordingly. If the bill combines base
delivery and adjustments, separate them using its line items before importing.
`total` is optional but checked against the component sum when supplied. Credits
can be negative. Periods cannot overlap; multiple historical months are welcome.

The report shows modeled minus actual component differences and unexplained
amounts. Default tolerance is $1 per component **and total**, configurable with
`--tolerance` from $0 to $5. Baseline agreement does not establish missing TOU
supply or tax rates.

## Additional components and eligibility

Con Edison full-service **supply differs by rate plan**, despite an unchanged
supplier. Do not reuse Standard supply for TOU. For an ESCO, verify the actual
contract before entering an unchanged price for both plans. The application
does not change suppliers or enroll you in anything.

An optional component CSV provides a separate row for each exact bill period
and each supported plan. See [synthetic example](examples/components.csv):

```text
start,end,plan,supply_per_kwh,supply_fixed,adjustments_per_kwh,adjustments_fixed,tax_percent,tax_fixed,source,verified
```

The model computes supply as `kWh * supply_per_kwh + supply_fixed`, adjustments
similarly, then tax as `(base_delivery + supply + adjustments) * tax_percent / 100
+ tax_fixed`. Each component rounds half-up to cents. Fixed amounts are **for
the entire billing period**, already prorated where required. These are an input
interface for documented effective bill-cycle rates, not a substitute for
reconstructing time-dependent MSC energy/capacity or tax-exempt subcomponents.
If that formula cannot represent your sourced charges, leave components absent
or `verified=false`; the application will retain a delivery-only or assumption-based
comparison. Never mark assumed averages or copied bill totals verified merely
to make reconciliation pass.

`source` must explain the rate statement/contract and calculation. `verified=true`
is **your explicit attestation** that all these effective charges and their tax
base were independently established for that plan and bill period. It is not
verification by the application. Missing plan rows never inherit baseline values.

Use `--eligible standard,tou` only after confirming SC1 classification, meter
requirements, full-service obligations, and the 18-month reenrollment restrictions
on your own account. ZIP alone is insufficient. A lowest-cost historical modeled
plan is identified only when all periods are complete, every component has
user-attested sources, both plans are confirmed eligible, and all baseline bills
reconcile. This remains a historical comparison, not a future savings guarantee.

## Reproducible synthetic demonstration

```console
python examples/generate.py
coned-optimize inspect examples/usage.csv
coned-optimize report examples/usage.csv --bill examples/bills.csv --components examples/components.csv --eligible standard,tou --output reports/demo.html --json reports/demo.json
python -m pytest -q
```

The 5,952 quarter-hour observations cover July–August 2026, consuming 992 kWh:

| Two-month historical simulation | Standard | TOU |
|---|---:|---:|
| Verified base delivery | $217.78 | $185.02 |
| Whole bill using **synthetic** additional components | $379.60 | $345.68 |

TOU base delivery is $32.76 lower because this fixture concentrates usage
overnight. The synthetic baseline reconciles; no switching recommendation is
issued because additional charges are explicitly unverified. These observations
cover summer only; no annual savings are projected.

## Architecture and tests

- `ingest.py`: CSV/XML parsing and interval quality.
- `engine.py`: dated tariff selection, periods, pricing, input components, reconciliation, recommendation gates.
- `report.py`: terminal tables and self-contained HTML/SVG.
- `cli.py`: offline orchestration and errors.
- `tariffs/`: human-readable effective-dated rates and official sources.

Tests cover DST gaps/folds, XML units and unsafe metadata, duplicate/overlapping
data, summer tiers, TOU boundaries/weekends/holidays, version/season proration,
bill boundaries, demand top-three arithmetic (not an enabled demand simulator),
reconciliation, missing alternative supply, and report safety. CI runs on Python
3.12 and 3.13. Contributions should include source-backed tariff updates and
boundary tests. This project is independent of Con Edison and RateMate.
