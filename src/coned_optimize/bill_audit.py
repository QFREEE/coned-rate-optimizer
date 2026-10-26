"""Partial, independent bill checks. Never fit an unknown charge to force agreement."""
import csv
import json
from datetime import date
from decimal import Decimal as D
from html import escape
from importlib.resources import files
from pathlib import Path

from .engine import Catalog, Period, money, tier_cost

AMOUNTS = ("basic_service", "delivery_energy", "system_benefits", "delivery_grt", "delivery_sales_tax",
           "delivery_total", "supply_energy", "merchant_function", "supply_grt", "supply_sales_tax",
           "supply_total", "electricity_total")


def audit_bills(path, *, sales_tax_percent, electric_only_full_service=False):
    tax = D(sales_tax_percent)
    if not tax.is_finite() or not 0 <= tax <= 100:
        raise ValueError("Bill-provided sales tax percent must be finite, between0 and100")
    rules = json.loads(files("coned_optimize").joinpath("reference_rules/bill-checks-2026.json").read_text())
    catalog, rows = Catalog(), []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"start", "end", "kwh", *AMOUNTS} <= set(reader.fieldnames or []):
            raise ValueError("Line-item CSV requires start,end,kwh and named electricity bill line items; see README")
        for source in reader:
            period = Period(date.fromisoformat(source["start"]), date.fromisoformat(source["end"]))
            if str(period.start) < rules["effective_start"] or str(period.end) > rules["effective_end"]:
                raise ValueError("Bill outside verified partial-audit rule dates")
            values = {k: D(source[k]) for k in (*AMOUNTS, "kwh")}
            if any(not v.is_finite() for v in values.values()) or values["kwh"] < 0:
                raise ValueError("Line items must be finite and consumption nonnegative")
            checks = []
            def check(name, expected, actual, basis):
                expected = D(money(expected))
                checks.append(dict(name=name, expected=money(expected), actual=money(actual),
                                   difference=money(actual-expected), matches=expected == actual, basis=basis))
            delivery_pre = sum((values[k] for k in ("basic_service", "delivery_energy", "system_benefits")), D(0))
            supply_pre = values["supply_energy"]+values["merchant_function"]
            check("delivery_line_sum", delivery_pre+values["delivery_grt"]+values["delivery_sales_tax"], values["delivery_total"], "Arithmetic using bill line items")
            check("supply_line_sum", supply_pre+values["supply_grt"]+values["supply_sales_tax"], values["supply_total"], "Arithmetic using bill line items")
            check("electricity_total", values["delivery_total"]+values["supply_total"], values["electricity_total"], "Arithmetic using bill line items")
            for side, subtotal in (("delivery", delivery_pre+values["delivery_grt"]), ("supply", supply_pre+values["supply_grt"])):
                check(side+"_sales_tax", subtotal*tax/100, values[side+"_sales_tax"], f"Bill-provided sales tax {tax}% applied to pre-tax line subtotal")
            versions = catalog.days(period)
            fixed = sum((D(v["plans"]["standard"]["monthly_customer_charge"])/30 for v, _ in versions), D(0))
            if electric_only_full_service:
                check("basic_service", fixed+D(rules["billing_payment_processing"]["amount_per_bill"]), values["basic_service"], "SC1 RateI customer charge days/30 plus GR26.3 electric-only full-service BPP per bill")
            grt = rules["gross_receipts"]
            delivery_pct = D(grt["village_residential_delivery_percent"])
            if grt["temporary_bill_end_start"] <= str(period.end) <= grt["temporary_bill_end_last"]:
                delivery_pct += D(grt["temporary_delivery_increase_percentage_points"])
            # These are conditional consistency checks; an invoice match is not proof of jurisdiction.
            check("village_delivery_grt_consistency", delivery_pre*delivery_pct/100, values["delivery_grt"], f"Conditional1%municipality monthly residential rate {delivery_pct}%; jurisdiction not verified")
            check("village_supply_grt_consistency", supply_pre*D(grt["village_residential_commodity_percent"])/100, values["supply_grt"], "Conditional village commodity rate; jurisdiction not verified")
            kwh = values["kwh"]
            base_energy = sum(((tier_cost(kwh,v["plans"]["standard"]["summer_tiers"],period.days)
                                if day.month in v["summer_months"] else kwh*D(v["plans"]["standard"]["winter_kwh_rate"]))
                               /D(period.days) for v,day in versions),D(0))
            rows.append(dict(period=period.key, billed_kwh=str(kwh), checks=checks,
                             base_energy_from_billed_kwh=money(base_energy),
                             delivery_line_less_base_energy=money(values["delivery_energy"]-base_energy),
                             residual_status="Unallocated difference, not a verified adjustment or billing error",
                             fully_reconciled=False))
    if not rows:
        raise ValueError("No bill rows")
    return dict(scope="Partial bill checks only", source_rules=rules, bills=rows,
                limitations=["Supply price, MFC, SBC and embedded delivery adjustments are not independently reconstructed.",
                             "Gross-receipts checks are conditional on municipality category; matching is not jurisdiction verification.",
                             "Sales tax percent is taken from the bill, not inferred from a ZIP.",
                             "Billed kWh is used here to isolate price arithmetic; interval usage must reconcile separately.",
                             "No full reconciliation, savings claim, or rate recommendation follows from these partial matches."])


def audit_html(result):
    def safe(value): return escape(str(value))
    sections=[]
    for bill in result["bills"]:
        table='<table><tr><th>Check</th><th>Expected</th><th>Billed</th><th>Billed minus expected</th></tr>'
        for c in bill["checks"]:
            table+='<tr>'+''.join('<td>'+safe(c[k])+'</td>' for k in ("name","expected","actual","difference"))+'</tr>'
        table+='</table>'
        sections.append('<section><h2>'+safe(bill["period"])+'</h2>'+table+'<p>Delivery line less modeled base energy: $'+safe(bill["delivery_line_less_base_energy"])+'. '+safe(bill['residual_status'])+'.</p></section>')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Partial bill reconciliation</title><style>body{font:16px/1.5 system-ui;max-width:1100px;margin:auto;padding:24px}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ccc;text-align:left}section{margin:30px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Partial bill reconciliation</h1><p>Source-backed checks and conditional tax consistency. Full bills remain unreconciled.</p>'+''.join(sections)+'<h2>Limitations</h2><ul>'+''.join('<li>'+safe(x)+'</li>' for x in result['limitations'])+'</ul><details><summary>Evidence and calculation details</summary><pre>'+safe(json.dumps(result,indent=2))+'</pre></details></html>'
