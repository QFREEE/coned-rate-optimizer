# Demand measurement and dated billing adjustments

Public-source follow-up, October 26, 2026. No household files or identifying information were used in searches. Research only: application code and tariff configuration were not changed.

## Demand verdict: rolling rule verified; rounding unresolved

**The earlier rolling-versus-clock-hour uncertainty is resolved.** Con Edison's [SC1 Rate IV Assessment, December 30, 2023](https://www.coned.com/-/media/files/coned/documents/accountandbilling/your-bill/steady-use-rate/rate-assessment.pdf), section II.C (printed page 3/PDF page 9) and VII.A (printed page 47/PDF page 53), explicitly describes summing four successive 15-minute energy intervals every 15 minutes, provided all intervals belong to the same peak/off-peak period. Average the three highest **daily** maxima separately for each billing period/time band. Clock-hour measurement is discussed as a possible improvement requiring further analysis, not the existing calculation. Its example gives rolling maximum 12 kW versus clock-hour maximum 8 kW. The study used actual consumption but assumed calendar-month supply cycles, so its methodological simplification must not replace household bill dates.

For Rider Z, the [PSC order issued March 18, 2019, Case 18-E-0397](https://documents.dps.ny.gov/public/Common/ViewDoc.aspx?DocRefId=%7B2BAB4E9E-0147-4F80-A1CC-A4F1EA7182CA%7D), page 5, expressly says customers are billed rolling 60-minute demands measured on the quarter hour; erroneous clock-hour load-research calculations required a rate correction. Con Edison's [pilot evaluation](https://documents.dps.ny.gov/public/Common/ViewDoc.aspx?DocRefId=%7B507AA68C-0000-C213-9F13-B33CB2E8FDF5%7D), section 1.1 footnote 5, also specifies four consecutive quarter-hour intervals and three distinct days.

The [current tariff](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/electric-tariff.pdf), leaves 389.3 and 327.6, remains the governing top-three-daily, same-period, ending-day rule. The verified structural formula can be implemented without estimating demand from a single 15-minute peak. **No official rule establishing intermediate demand rounding, final demand decimal precision, or tie-breaking cent rounding was located in this bounded review.** Do not invent such conventions. Complete contiguous quarter-hour data and actual cycle boundaries are necessary; unrounded demand arithmetic should be identified explicitly until reconciled with billed demand.

**Boundary detail not independently settled:** the tariff says demand ends in each day and consists of intervals ending in the same time period. No special rule was found assigning an interval ending exactly at midnight to the preceding service day rather than the literal endpoint date, or spelling out inclusion of exact noon/20:00 endpoints. An implementation must document its endpoint convention and test midnight, holiday, and period boundaries. Do not use an unspecified convention to claim the utility's exact billed daily maxima. Rounding alone need not prevent structural unrounded simulation; boundary conventions can change the selected maxima and need separate treatment.

**Separate determinant warning:** the 2026 SBC statement uses monthly maximum demand for its company-administered demand charge. That is a distinct determinant from average top-three peak/off-peak demand. Its exact integration/rounding application for SC1 Rate IV should be confirmed before claiming fully reconstructed demand-plan totals.

## Verified dated components for June–October 2026

All numbers are dollars, not cents. Parentheses in source statements indicate negative credits. Rates shown are before GRT and sales tax. Check the [official statement index](https://www.coned.com/en/rates-tariffs/rates/electric-rates-schedule/electric-psc-10) and supersessions when extending beyond the research date.

| Component | Verified SC1 amount | Primary statement |
|---|---:|---|
| MAC from June 1 | −0.00071/kWh | [June MAC](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/monthly-adjustment-clause/mac-202606.pdf) |
| MAC from July 1 | 0.00040/kWh | [July MAC](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/monthly-adjustment-clause/mac-202607.pdf) |
| MAC from August 1 | 0.00236/kWh | [August MAC](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/monthly-adjustment-clause/mac-202608.pdf) |
| MAC from September 1 | 0.00422/kWh | [September MAC](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/monthly-adjustment-clause/mac-202609.pdf) |
| MAC from October 1 | 0.00452/kWh | [October MAC](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/monthly-adjustment-clause/mac-202610.pdf) |
| RDM from February 1, before August change | +0.00738/kWh | [February RDM](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/revenue-decoupling-mechanism/rdm-202602.pdf) |
| RDM from August 1 | −0.00815/kWh | [August RDM](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/revenue-decoupling-mechanism/rdm-202608.pdf) |
| CES delivery from February 1 | 0.000201/kWh | [CESD](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/clean-energy-standard-delivery/cesd-202602.pdf) |
| SBC from March 1, Rates I/II/III | NYSERDA 0.0039/kWh **plus** company-administered 0.0039/kWh = 0.0078/kWh | [SBC](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/system-benefits-charge/sbc-202603.pdf) |
| SBC from March 1, Rate IV/Rider Z | NYSERDA 0.0039/kWh **plus** company-administered 0.85/kW monthly maximum demand; Rider Z V/VI use subscribed demand | [same SBC statement](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/system-benefits-charge/sbc-202603.pdf) |
| Delivery revenue from February 1 | −0.000112/kWh, Rates I–IV/Rider Z | [SDR](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/delivery-revenue-surcharge/sdr-202602.pdf) |
| DLM from May 1 | 0.0023/kWh, listed Rates I–IV | [DLM](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/dynamic-load-management/dlm-202605.pdf) |
| AMP from May 1 | 0.0011/kWh, listed Rates I–IV | [AMP](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/arrears-management-program/amp-202605.pdf) |
| EV make-ready from February 1 | 0.0020/kWh, listed Rates I–IV | [EVS](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/electric-vehicle-make-ready/evs-202602.pdf) |

For Rider Z, do not infer eligibility/application from a table that explicitly lists only SC1 Rates I–IV; consult the rider's incorporation of SC1/GR26 terms. Also include applicable [VDER cost recovery, December 2025 statement](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/vder-value-stack-cost-recovery/vder-cr-202512.pdf); page 1 separates NYC/Westchester supply and delivery components. Its visually arranged table needs careful column verification before transcription; no combined VDER rate is asserted here.

### MAC adjustment is additional, and uses the bill's to-date

The [official Con Edison MAC-adjustment summary](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/delivery/adjustment-factor-mac/macadj-2023-present.pdf) gives the following reconciliation/uncollectible/transition components. It expressly disclaims replacing PSC-filed statements; these values are research leads until checked against those statements.

| Effective date | Reconciliation $/kWh | Uncollectible $/kWh | Transition $/kWh |
|---|---:|---:|---:|
| May 14, 2026 | −0.000278 | +0.000080 | −0.000002 |
| June 15 | −0.002230 | +0.000083 | −0.000002 |
| July 15 | +0.010455 | −0.000023 | −0.000002 |
| August 13 | +0.004618 | −0.000009 | −0.000002 |
| September 14 | +0.006636 | +0.000086 | −0.000002 |
| October 14 | +0.015557 | +0.000104 | −0.000002 |

General Rule 26.1.3, tariff leaf 345, assigns monthly bills the MAC adjustment effective on their **to-date**, rather than prorating this factor over interval service dates. A base-MAC-only reconstruction omits these substantial adjustments.

### Supply MFC

Full-service SC1 total MFC changes monthly; this does not apply to every ESCO supply arrangement. Verified per-kWh totals:

| From first of month | Total MFC | Source |
|---|---:|---|
| June 2026 | 0.005139 | [June](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/supply/merchant-function-charge/mfc-202606.pdf) |
| July | 0.005132 | [July](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/supply/merchant-function-charge/mfc-202607.pdf) |
| August | 0.005393 | [August](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/supply/merchant-function-charge/mfc-202608.pdf) |
| September | 0.006204 | [September](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/supply/merchant-function-charge/mfc-202609.pdf) |
| October | 0.006482 | [October](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/supply/merchant-function-charge/mfc-202610.pdf) |

MSC itself remains plan-, zone-, and billing-cycle-sensitive; MFC is not a replacement for energy/capacity supply charges. No supply rate is inferred from household bills or personal account data in this research.

### GRT, billing processing, and boundary rules

The [GRT statement effective June 2, 2026](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/other/increase-rates-charges/grt-202606.pdf) lists residential delivery increases of 3.3927% for all villages, 2.3347% for towns; commodity is 1.0101% for villages, 0% for towns. For monthly bills with to-dates June 2–July 30, delivery percentages receive temporary additions: 0.2639 percentage points for specified 1% municipalities including villages except Buchanan, or 0.2612 for 0% municipalities including towns/Buchanan. Municipality must be established, not assumed from ZIP. General Rule 30.2 applies the statement effective on the bill's to-date. GRT is distinct from sales tax; no household-specific sales-tax rate was established here.

Tariff General Rule 26.3, leaves 353–354: electric-only full-service or separate utility/nonutility billing has a $1.80 **per bill** processing charge; utility-consolidated/ESCO-consolidated examples show zero. Combined electric/gas accounts allocate a single applicable $1.80 charge between services, with electric receiving $1.80 less the applicable gas charge. Do not add $1.80 to both fuels or prorate a per-bill charge as a monthly customer charge.

General Rule 10.5 remains the basis for ordinary day-share rate-change proration and monthly charges/blocks scaled by elapsed days/30; it has exceptions. Component-specific to-date rules above override indiscriminate interval-date allocation. Precise baseline reconciliation still needs actual billing periods, supplier/bill arrangement, municipality/tax status, billed usage rounding, and each applicable adjustment. **Verdict:** rolling demand formula and the listed statement amounts are verified; exact utility demand rounding, SBC demand determinant details, VDER column transcription, and full baseline reconstruction remain unresolved.
