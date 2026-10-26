# Con Edison residential tariff research

Researched 2026-10-26, before application implementation. Scope: ordinary SC1 residential service in Con Edison territory, including Ossining/Westchester. An address or ZIP alone cannot establish an account's actual supplier, tariff, special riders, credits, or ability to reenroll.

## Authority and verified base rates

The authority is Con Edison PSC No. 10 and the PSC-filed adjustment statements. Con Edison warns its convenience copies do not replace the PSC's official schedules: [rates and tariffs](https://www.coned.com/en/rates-tariffs/rates). The [PSC10 index](https://www.coned.com/en/rates-tariffs/rates/electric-rates-schedule/electric-psc-10) supplies current tariff, historical tariffs, and separately dated adjustment statements.

Verified against the [current full tariff PDF](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/electric-tariff.pdf), leaves 388–390, effective February 1, 2026. Dollar values below exclude additional delivery charges, supply and taxes:

| SC1 option | Monthly customer charge | Base delivery calculation |
|---|---:|---|
| Rate I, Standard | $21 | October–May: $0.16402/kWh. June–September: first 250 kWh $0.16402, excess $0.18858 |
| Rate III, voluntary TOU | $21 | Peak 08:00–24:00 **every day including weekends and holidays**: June–September $0.2786/kWh, other months $0.1711. Off-peak $0.0522/kWh |
| Rate IV, Steady Use | $31 | Peak weekdays noon–20:00 excluding six named holidays: June–September $27.35/kW, other months $21.04/kW. Off-peak $7.17/kW |
| Rider Z Rate I, Smart Energy Plan | $21 | Peak weekdays noon–20:00 excluding holidays: summer $30.68/kW, other months $23.60/kW; off-peak $10.06/kW |

Rate II is legacy TOU closed to new applications since March 1, 2014. Rate V is standby service under General Rule 20, not a generic alternative for an ordinary household. Rider Z contains several pilot rates; customers not selected for the pilot who elect the rider are assigned Rate I, not a choice among all pilot variants (leaves 327.1–327.7).

The [January 2025 historical tariff](https://www.coned.com/-/media/files/coned/documents/rates/electric/historical/psc-10/tariff/sc-202501.pdf), leaves 388 and 389.1, has different rates: Standard $20/month and $0.16107/$0.18518; TOU $20/month, summer peak $0.3523, winter peak $0.1305, off-peak $0.0249. These are evidence of historical changes, **not permission to apply those rates throughout 2025**: intervening leaf revisions must be verified before a historical version is enabled. The bundled version is bounded to the verified 2026 period and must reject earlier/future periods rather than carry prices backward or forward indefinitely.

## Billing periods, switching, and demand

Follow-up: [billing and demand research](billing-demand-followup.md) resolves the
rolling-versus-clock-hour question using official Con Edison and PSC sources:
rolling60-minute demand is updated every15minutes. Exact boundary/day attribution
and the separate SBC monthly-maximum determinant remain unresolved. The earlier
uncertainty described below is retained as the initial research record, not the
current finding. Demand plan costs remain disabled.

General Rule 10.5 (leaf 85) prorates monthly charges by elapsed service days / 30, and kWh tier thresholds by the same factor. Per-kWh prices themselves are not prorated merely because a bill is not 30 days. When a bill crosses a rate change, 10.5.1 specifies day-share proration of rates; the SC1 customer-meter-reading provision on leaf 389.3 explicitly recognizes actual versus prorated seasonal bills. Calendar-month output from interval data should therefore be identified as a historical usage replay; actual bill boundaries are needed to reconcile a utility bill, and cycles crossing seasonal/effective changes require the tariff's proration rules. A customer terminating service within 30 days of commencement is an exception requiring at least 30 days' charges; an MVP without commencement/termination information must disclose that limitation.

Rate III full-service enrollment carries a one-year full-service commitment, also triggered when a retail-access Rate III customer switches to full service. Leaving Rate III or IV blocks reenrollment for 18 months. Rate IV requires operational AMI communications. [Steady Use enrollment guidance](https://www.coned.com/en/accounts-billing/steady-use-rate) confirms the marketing name, excludes SmartCharge NY incentives after enrollment, and describes a conditional heat-pump price guarantee. Do not assume every customer qualifies for a guarantee. Rider Z similarly requires AMI and imposes an 18-month reenrollment wait; unsolicited opt-in customers do not receive its pilot price guarantee.

Demand is **not the monthly maximum 15-minute kW**. Leaf 389.3 and Rider Z leaf 327.6 specify daily maximum integrated 60-minute demand within each applicable period, then the average of the three highest daily maxima for that period over the billing cycle. Holidays are New Year's Day January 1, Memorial Day last Monday in May, Independence Day July 4, Labor Day first Monday in September, Thanksgiving fourth Thursday in November, and Christmas December 25. No substitute observed weekday is specified here. The inspected tariff does not explicitly settle whether exported 15-minute observations must be integrated at every quarter-hour endpoint or clock-hour endpoints, nor utility rounding/endpoint conventions. Therefore demand prices and the verified structural rule can be displayed, but **demand plan simulation/recommendation must remain unsupported until those conventions are verified**. Incomplete interval data also cannot establish actual billing demand.

## Supply, adjustments, taxes

Leaf 390 and General Rules 25, 26, 30 separate supply, additional delivery adjustments, and percentage increases/taxes from base delivery. Full-service customers receive Con Edison supply; retail-access customers retain their ESCO contract. A delivery election does not change the supplier. Crucially, **Con Edison supply pricing can change with the elected rate**: GR25.1(b), leaf 330.1, uses TOU energy prices and, for Rate III, summer weekday 14:00–18:00 capacity allocation; Rate IV capacity applies during its on-peak period. It is unsafe to copy a Standard supply charge onto a Con Edison TOU counterfactual. [Steady Use guidance](https://www.coned.com/en/accounts-billing/steady-use-rate) explicitly confirms TOU supply for Con Edison customers and unchanged contractual pricing for ESCO customers.

The PSC10 index publishes effective-dated MAC, RDM, SBC, CES delivery/supply, MSC capacity/adjustments, MFC, GRT and other statements. MSC energy also depends on billing-cycle/load-zone inputs, not one published timeless cents/kWh number. Local sales taxes and exemptions cannot reliably be inferred from ZIP alone. The MVP should clearly show **base delivery only**, mark missing components unavailable, and offer explicit plan-specific component inputs for auditable reconstruction. Unavailable supply/tax amounts must not appear as zero-valued verified totals. Baseline agreement alone cannot validate an alternative's missing supply or tax inputs.

## Data export and methodology

[Con Edison's Green Button page](https://www.coned.com/en/save-money/make-better-energychoices-with-green-button) confirms CSV and XML downloads, up to one year of history, and precise smart-meter usage. It does not publicly guarantee a universal CSV header layout or every account's interval resolution. [DOE's Green Button explanation](https://www.energy.gov/data/green-button) identifies the ESPI XML standard; the [Green Button developer documentation](https://archive.greenbuttondata.org/developers/) describes Atom resources, IntervalBlock/IntervalReading, ReadingType metadata and time configuration. XML ingestion must associate each block with its own ReadingType rather than taking one feed-wide multiplier/unit; UTC epoch interval starts and durations avoid DST ambiguity. Local CSV clock times without offsets require explicit handling of ambiguous fall-back and nonexistent spring-forward readings. Never fabricate missing kWh or silently reinterpret gas, power, export, or cumulative registers as imported electricity energy.

[RateMate's public method](https://ratemate.energy/) describes replaying a household's usage through available plans and reconciling calculated bill line items to actual bills. Its [SC1 explanation](https://ratemate.energy/blog/coned-service-classification-explained) highlights the difference between energy and demand pricing. These supply methodological inspiration only; official tariffs override third-party summaries, including any claim that supply is always identical between SC1 Rate I and Rate IV. No proprietary implementation is used. Fewer than 12 months of observations supports a historical comparison for those months, not a precise annual saving or unqualified enrollment recommendation.

### Importer schema checks

The [Green Button Alliance ESPI schema](https://dev.greenbuttonalliance.org/espiusecase.html)
defines delta accumulation as 4, energy kind as 12, electricity commodity as 1,
forward flow as 1, and Wh units as 72. Reverse flow 19 and net flow 4 are not
ordinary import consumption. The [quality guidance](https://www.greenbuttonalliance.org/accuracy)
distinguishes valid/revenue quality from flags that can include estimation.
The importer accepts only a conservative single-stream energy subset.

A [Con Edison installer workshop, page 52](https://nysolarmap.com/media/1969/conedinstallerworkshop2019.pdf)
shows the native CSV table TYPE, DATE, START TIME, END TIME, USAGE, UNITS, NOTES.
Its display-minute interval 00:00–00:14 represents a quarter hour. The importer
normalizes that native inclusive end minute to 00:15, while preserving canonical
start/end CSV boundaries exactly. This is a utility-authored example, not a
guarantee that all current exports use identical headers.
