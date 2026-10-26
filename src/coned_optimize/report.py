"""Self-contained report; no remote assets, scripts, tracking, or uploads."""
from __future__ import annotations

import html
import json
from decimal import Decimal


def esc(value):
    return html.escape(str(value))


def amount(value):
    return f"${value}" if value is not None else "Unavailable"


def terminal(result):
    lines = ["CON EDISON | Historical usage replay", f"Ranking basis: {result['ranking_basis']}",
             "Plan                     Base delivery  Modeled total  Delivery difference  Savings / %"]
    for p in result["plans"]:
        if p["supported"]:
            lines.append(f"{p['id']:<24} {amount(p['delivery']):>13} {amount(p['total']):>14} "
                         f"{amount(p['delivery_difference']):>20} {amount(p['modeled_savings'])} / {p['savings_percent'] or 'N/A'}")
        else:
            lines.append(f"{p['id']}: UNSUPPORTED - {p['limitation']}")
    lines.extend(["", "MONTHLY / BILLING-PERIOD BREAKDOWN", "Plan | Period [start/end exclusive] | kWh | Coverage | Base delivery | Supply | Adjustments | Taxes | Total"])
    for p in result["plans"]:
        for row in p["months"]:
            lines.append(" | ".join([p["id"], row["period"], row["kwh"], f"{row['completeness_percent']}%",
                                     *[amount(row[c]) for c in ("delivery", "supply", "adjustments", "taxes", "total")]]))
    lines.extend(["", "BASELINE RECONCILIATION (modeled minus actual)"])
    for v in result["validation"]:
        lines.append(f"{v['period']}: " + ("reconciled" if v["reconciled"] else "UNRECONCILED")
                     + " " + json.dumps(v.get("difference", v.get("reason"))))
    if result["recommendation"]:
        lines.append(f"\nLowest historical modeled cost: {result['recommendation']} (using user-attested component inputs).")
    else:
        lines.append("\nNo switching recommendation or verified whole-bill savings.")
        lines.extend("- " + s for s in result["recommendation_blockers"])
    for p in result["plans"]:
        lines.append(f"{p['id']} eligibility: {p['eligibility']} Confirmed: {p['eligible']}")
        lines.extend("  Restriction: " + s for s in p["restrictions"])
    lines.extend(["", *result["limitations"]])
    return "\n".join(lines)


def html_report(result):
    modeled = [p for p in result["plans"] if p["supported"]]
    whole = result["ranking_basis"] == "modeled_total"
    measure = "total" if whole else "delivery"
    max_cost = max(float(p[measure]) for p in modeled) or 1
    chart = []
    for i, p in enumerate(modeled):
        y = i*62+8
        width = float(p[measure])/max_cost*430
        chart.append(f'<text x="0" y="{y+20}">{esc(p["id"])}</text>'
                     f'<rect x="100" y="{y}" width="{width:.2f}" height="30" rx="4" fill="{["#267d70", "#516bc4"][i%2]}"/>'
                     f'<text x="545" y="{y+20}">{amount(p[measure])}</text>')
    sections = []
    for p in result["plans"]:
        body = f'<p>{esc(p["eligibility"])} Account eligibility confirmed: {p["eligible"]}.</p>'
        if not p["supported"]:
            body += f'<p class="notice">Unsupported: {esc(p["limitation"])}</p>'
        else:
            body += f'<p>Base delivery: <b>{amount(p["delivery"])}</b> · Modeled whole bill: <b>{amount(p["total"])}</b>'
            body += f' · Delivery difference vs baseline: {amount(p["delivery_difference"])}'
            body += f' · Modeled savings: {amount(p["modeled_savings"])} ({esc(p["savings_percent"] or "N/A")}%)</p>'
            body += '<div class="scroll"><table><thead><tr>' + ''.join(f'<th>{c}</th>' for c in
                     ["Period (end exclusive)", "kWh", "Coverage", "Fixed", "Energy", "Base delivery", "Supply", "Adjustments", "Taxes", "Total"]) + '</tr></thead><tbody>'
            for r in p["months"]:
                values = [r["period"], r["kwh"], str(r["completeness_percent"])+"%", *[amount(r[c]) for c in
                         ("customer_charge", "energy_delivery", "delivery", "supply", "adjustments", "taxes", "total")]]
                body += '<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in values) + '</tr>'
            body += '</tbody></table></div>'
            body += '<details><summary>Calculation evidence</summary><pre>' + esc(json.dumps(p["months"], indent=2)) + '</pre></details>'
        body += '<ul>' + ''.join(f'<li>{esc(r)}</li>' for r in p["restrictions"]) + '</ul>'
        sections.append(f'<section><h2>{esc(p["name"])}</h2>{body}</section>')
    status = ("Lowest historical modeled cost: " + result["recommendation"] + ". Based on user-attested component inputs."
              if result["recommendation"] else "No switching recommendation. Whole-bill savings are not verified.")
    blockers = ''.join(f'<li>{esc(b)}</li>' for b in result["recommendation_blockers"])
    explanation = ("Rate III prices midnight–08:00 energy lower, and daytime energy higher, than standard base delivery. "
                   "Standard also charges a higher summer tier above a prorated 250 kWh. The result depends on the "
                   "observed timing and quantity of consumption. Supply, adjustments and taxes can change the ranking. "
                   "Unsupported demand plans are excluded. No annual savings have been projected.")
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'">
<title>Con Edison | Historical rate comparison</title><style>
body{{font:16px/1.55 system-ui,sans-serif;color:#182a34;background:#f1f5f5;margin:0}}main{{max-width:1200px;margin:auto;padding:30px}}
h1{{font-size:2.1rem}}h2{{font-size:1.3rem}}section{{background:white;padding:22px;margin:22px 0;border-radius:10px}}
.notice{{padding:16px;background:#fff1d6;border-left:4px solid #a05b00}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:.9rem}}
td,th{{padding:9px;text-align:left;border-bottom:1px solid #d8e1e3;white-space:nowrap}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.85rem}}
svg{{width:100%;max-width:750px}}svg text{{font-size:16px;fill:#182a34}}summary{{cursor:pointer}}.muted{{color:#415562}}
</style><main><p class="muted">LOCAL ANALYSIS · VERIFIED BASE TARIFFS · USD</p><h1>Con Edison rate comparison</h1>
<p>Historical periods: {esc(', '.join(result['periods']))}. Baseline: {esc(result['baseline'])}.</p>
<div class="notice"><b>{esc(status)}</b><ul>{blockers}</ul></div>
<section><h2>{'Modeled whole-bill' if whole else 'Base delivery only'} comparison</h2>
<svg viewBox="0 0 670 {len(modeled)*62+15}" role="img" aria-label="Historical cost comparison bar chart"><title>Historical costs in dollars</title>{''.join(chart)}</svg>
<p>{explanation}</p></section>{''.join(sections)}
<section><h2>Data quality</h2><pre>{esc(json.dumps(result['quality'], indent=2))}</pre>
<p>Intervals outside selected bills: {result['excluded_intervals']}. Coverage is measured in elapsed UTC seconds, accounting for daylight saving time.</p></section>
<section><h2>Baseline reconciliation</h2><p>Modeled minus actual, by component and total. Tolerance: ${esc(result['tolerance'])} per component and total.</p>
<pre>{esc(json.dumps(result['validation'], indent=2))}</pre></section>
<section><h2>Assumptions and limitations</h2><ul>{''.join('<li>'+esc(s)+'</li>' for s in result['limitations'])}</ul></section>
<p class="muted">Generated locally. No remote resources or personal account identifiers are embedded by the application. Review input source labels before sharing.</p></main></html>'''
