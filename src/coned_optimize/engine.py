"""Versioned base-delivery calculations; unknown bill components stay unknown."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from importlib.resources import files
from pathlib import Path

from .ingest import NY, UTC, Usage

D = Decimal
ZERO = D(0)


def money(value):
    return str(value.quantize(D(".01"), rounding=ROUND_HALF_UP)) if value is not None else None


@dataclass(frozen=True)
class Period:
    start: date
    end: date  # exclusive meter-read boundary

    def __post_init__(self):
        if self.end <= self.start:
            raise ValueError("Billing period end must be after start")

    @property
    def days(self):
        return (self.end-self.start).days

    @property
    def bounds(self):
        return tuple(datetime.combine(day, time(), NY).astimezone(UTC) for day in (self.start, self.end))

    @property
    def key(self):
        return f"{self.start}/{self.end}"


def calendar_periods(usage):
    if not usage.intervals:
        raise ValueError("No valid usage intervals")
    start = usage.intervals[0].start.astimezone(NY).date().replace(day=1)
    last = (usage.intervals[-1].end-timedelta(microseconds=1)).astimezone(NY).date()
    result = []
    while start <= last:
        end = (start.replace(day=28)+timedelta(days=4)).replace(day=1)
        result.append(Period(start, end))
        start = end
    return result


def check_periods(periods):
    ordered = sorted(periods, key=lambda p: p.start)
    if not ordered:
        raise ValueError("No billing periods supplied")
    if any(a.end > b.start for a, b in zip(ordered, ordered[1:])):
        raise ValueError("Billing periods overlap or are duplicated")
    return ordered


class Catalog:
    def __init__(self, directory=None):
        root = Path(directory) if directory else files("coned_optimize").joinpath("tariffs")
        self.versions = [json.loads(p.read_text(encoding="utf-8")) for p in root.iterdir() if p.name.endswith(".json")]
        self.versions.sort(key=lambda v: v["effective_start"])
        if not self.versions:
            raise ValueError("No tariff versions found")
        for a, b in zip(self.versions, self.versions[1:]):
            if a["effective_end"] > b["effective_start"]:
                raise ValueError("Overlapping tariff versions")

    def at(self, day):
        matched = [v for v in self.versions if v["effective_start"] <= day.isoformat() < v["effective_end"]]
        if len(matched) != 1:
            raise ValueError(f"No verified tariff for {day}. Bundled coverage is "
                             + ", ".join(f'{v["effective_start"]} to {v["effective_end"]} exclusive' for v in self.versions))
        return matched[0]

    def days(self, period):
        return [(self.at(period.start+timedelta(days=i)), period.start+timedelta(days=i)) for i in range(period.days)]


def tier_cost(kwh, tiers, days):
    cost, previous = ZERO, ZERO
    for tier in tiers:
        limit = tier["up_to_kwh_per_30_days"]
        upper = D(limit)*D(days)/30 if limit is not None else kwh
        quantity = max(ZERO, min(kwh, upper)-previous)
        cost += quantity*D(tier["rate"])
        previous = upper
    return cost


def peak(dt, config):
    dt = dt.astimezone(NY)
    # Currently only Rate III is enabled, whose window includes every day/holiday.
    if config.get("exclude_holidays"):
        raise ValueError("Holiday-based plan requires a verified integration implementation")
    return (dt.weekday() in config["peak_weekdays"]
            and config["peak_start_hour"] <= dt.hour < config["peak_end_hour"])


def top_three_daily_demand(daily_maxima):
    """Verified arithmetic ONLY, not an interval-to-billing-demand implementation.

    Callers must supply already verified daily integrated maxima. Never used to rank plans.
    """
    values = [D(v) for v in daily_maxima]
    if len(values) < 3 or any(not v.is_finite() or v < 0 for v in values):
        raise ValueError("At least three finite nonnegative daily maxima are required")
    return sum(sorted(values, reverse=True)[:3], ZERO)/3


def _period_usage(usage, period):
    start, end = period.bounds
    rows = [r for r in usage.intervals if r.start < end and r.end > start]
    if any(r.start < start or r.end > end for r in rows):
        raise ValueError(f"Interval crosses billing boundary {period.key}; export finer data, no kWh split assumed")
    covered = sum((r.end-r.start).total_seconds() for r in rows)
    return rows, D(str(covered))/D(str((end-start).total_seconds()))


def simulate_base(usage, period, plan, catalog):
    if not usage.safe:
        raise ValueError("Unsafe usage: fix invalid, duplicate, or overlapping intervals before comparing")
    rows, completeness = _period_usage(usage, period)
    versions = catalog.days(period)
    configs = [v["plans"][plan] for v, _ in versions]
    if any(not c["supported"] for c in configs):
        raise ValueError(configs[0].get("unsupported_reason", "Unsupported tariff"))
    kwh = sum((r.kwh for r in rows), ZERO)
    fixed = sum((D(c["monthly_customer_charge"])/30 for c in configs), ZERO)
    energy = ZERO
    peak_kwh = None
    if plan == "standard":
        # GR10.5.1: day-weighted rates applied to whole bill consumption, not invented daily kWh.
        for (version, day), config in zip(versions, configs):
            if day.month in version["summer_months"]:
                daily_share = tier_cost(kwh, config["summer_tiers"], period.days)
            else:
                daily_share = kwh*D(config["winter_kwh_rate"])
            energy += daily_share/D(period.days)
    elif plan == "tou":
        window = lambda c: tuple(str(c[k]) for k in ("peak_start_hour", "peak_end_hour", "peak_weekdays", "exclude_holidays"))
        if len({window(c) for c in configs}) != 1:
            raise ValueError("TOU window changes inside this billing period are unsupported")
        peak_kwh = ZERO
        for row in rows:
            # Verify all hours spanned by the observation; do not distribute daily energy into hours.
            points = [row.start, row.end-timedelta(microseconds=1)]
            point = row.start.replace(minute=0, second=0, microsecond=0)+timedelta(hours=1)
            while point < row.end:
                points.append(point)
                point += timedelta(hours=1)
            flags = {peak(p, configs[0]) for p in points}
            if len(flags) != 1:
                raise ValueError("Interval spans TOU windows; finer interval data required")
            if True in flags:
                peak_kwh += row.kwh
        for (version, day), config in zip(versions, configs):
            rate = config["summer_peak_kwh_rate"] if day.month in version["summer_months"] else config["winter_peak_kwh_rate"]
            energy += (peak_kwh*D(rate)+(kwh-peak_kwh)*D(config["offpeak_kwh_rate"]))/D(period.days)
    else:
        raise ValueError("No verified implementation for this tariff")
    return dict(period=period.key, start=str(period.start), end=str(period.end), days=period.days,
                kwh=str(kwh), completeness_percent=round(float(completeness*100), 3),
                complete=completeness == 1, customer_charge=money(fixed), energy_delivery=money(energy),
                delivery=money(fixed+energy), peak_kwh=str(peak_kwh) if peak_kwh is not None else None,
                peak_demand_kw=None, supply=None, adjustments=None, taxes=None, total=None,
                evidence=[dict(source=v["source_url"], leaf=v["plans"][plan]["source_leaf"],
                               effective_start=v["effective_start"], verified_on=v["verified_on"])
                          for v in {v["effective_start"]: v for v, _ in versions}.values()])


COMPONENTS = ("delivery", "supply", "adjustments", "taxes")


def read_bills(path):
    """Actual amounts: delivery=base, adjustments=all other pre-tax charges.

    Any unseparated delivery adjustments stay unexplained rather than being copied into a model.
    """
    result = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"start", "end", *COMPONENTS}
        if not required <= set(reader.fieldnames or []):
            raise ValueError("Bills CSV requires start,end,delivery,supply,adjustments,taxes (optional total)")
        for row in reader:
            period = Period(date.fromisoformat(row["start"]), date.fromisoformat(row["end"]))
            if period.key in result:
                raise ValueError("Duplicate bill period")
            amounts = {c: D(row[c]) for c in COMPONENTS}
            if any(not n.is_finite() for n in amounts.values()):
                raise ValueError("Bill amounts must be finite")
            if row.get("total") and abs(D(row["total"])-sum(amounts.values(), ZERO)) > D(".01"):
                raise ValueError("Bill total does not equal component sum")
            result[period.key] = amounts
    periods = check_periods([Period(*map(date.fromisoformat, key.split("/"))) for key in result])
    return periods, result


def read_components(path):
    """Explicit, plan-specific whole-cycle inputs; never inherit a baseline's supply."""
    if not path:
        return {}
    result = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"start", "end", "plan", "supply_per_kwh", "supply_fixed", "adjustments_per_kwh",
                    "adjustments_fixed", "tax_percent", "tax_fixed", "source", "verified"}
        if not required <= set(reader.fieldnames or []):
            raise ValueError("Component CSV requires " + ",".join(sorted(required)))
        for row in reader:
            period = Period(date.fromisoformat(row["start"]), date.fromisoformat(row["end"]))
            key = (period.key, row["plan"])
            if key in result:
                raise ValueError("Duplicate component input for period/plan")
            if row["plan"] not in {"standard", "tou"}:
                raise ValueError("Component plan must be standard or tou")
            if not row["source"].strip() or row["verified"].lower() not in {"true", "false"}:
                raise ValueError("Components need a source and verified=true/false")
            for keyname in required - {"start", "end", "plan", "source", "verified"}:
                row[keyname] = D(row[keyname])
                if not row[keyname].is_finite():
                    raise ValueError("Component rates must be finite")
            result[key] = row
    return result


def apply_components(row, inputs):
    if not inputs:
        row["components_verified"] = False
        return
    kwh = D(row["kwh"])
    supply = D(money(kwh*inputs["supply_per_kwh"] + inputs["supply_fixed"]))
    adjustments = D(money(kwh*inputs["adjustments_per_kwh"] + inputs["adjustments_fixed"]))
    taxes = D(money((D(row["delivery"])+supply+adjustments)*inputs["tax_percent"]/100 + inputs["tax_fixed"]))
    row.update(supply=money(supply), adjustments=money(adjustments), taxes=money(taxes),
               total=money(D(row["delivery"])+supply+adjustments+taxes),
               components_verified=inputs["verified"].lower() == "true", component_source=inputs["source"])


def reconcile(rows, bills, tolerance=D("1.00")):
    comparisons = []
    for row in rows:
        actual = bills.get(row["period"])
        if actual is None:
            comparisons.append(dict(period=row["period"], reconciled=False, reason="No actual bill"))
            continue
        differences = {c: money(D(row[c])-actual[c]) if row[c] is not None else None for c in COMPONENTS}
        total_delta = money(D(row["total"])-sum(actual.values(), ZERO)) if row["total"] is not None else None
        ok = (row["complete"] and all(v is not None and abs(D(v)) <= tolerance for v in differences.values())
              and total_delta is not None and abs(D(total_delta)) <= tolerance)
        comparisons.append(dict(period=row["period"], reconciled=ok, difference=differences,
                                total_difference=total_delta, actual={c: money(actual[c]) for c in COMPONENTS},
                                unexplained=[c for c, delta in differences.items() if delta is None or abs(D(delta)) > tolerance]))
    return comparisons


def compare(usage: Usage, *, catalog=None, bills=None, periods=None, components=None,
            baseline="standard", eligible=(), tolerance=D("1.00")):
    catalog = catalog or Catalog()
    if baseline not in {"standard", "tou"}:
        raise ValueError("Baseline must have a verified implementation: standard or tou")
    if not usage.safe:
        raise ValueError("Usage has invalid, duplicate or overlapping intervals; run inspect and correct source data")
    if periods is None:
        periods = calendar_periods(usage)
        # A current month's unobserved future days cannot be assigned unverified rates.
        # Only a synthetic calendar bucket is clipped; actual bill boundaries never are.
        cutoff = date.fromisoformat(catalog.versions[-1]["effective_end"])
        if periods[-1].start < cutoff < periods[-1].end:
            periods[-1] = Period(periods[-1].start, cutoff)
    periods = check_periods(periods)
    # Validate the entire requested bill period, even if observations are absent on some days.
    for period in periods:
        catalog.days(period)
    components = components or {}
    plans = []
    for plan_id, config in catalog.at(periods[-1].start)["plans"].items():
        result = dict(id=plan_id, name=config["name"], restrictions=config["restrictions"],
                      eligibility=config["eligibility"], eligible=plan_id in eligible, supported=config["supported"],
                      limitation=config.get("unsupported_reason"), months=[])
        if config["supported"]:
            try:
                for period in periods:
                    row = simulate_base(usage, period, plan_id, catalog)
                    apply_components(row, components.get((period.key, plan_id)))
                    result["months"].append(row)
                result["delivery"] = money(sum((D(r["delivery"]) for r in result["months"]), ZERO))
                result["total"] = (money(sum((D(r["total"]) for r in result["months"]), ZERO))
                                   if all(r["total"] is not None for r in result["months"]) else None)
            except ValueError as exc:
                result.update(supported=False, limitation=str(exc), months=[])
        plans.append(result)
    modeled = [p for p in plans if p["supported"]]
    base = next((p for p in modeled if p["id"] == baseline), None)
    if base is None:
        raise ValueError("Baseline cannot be simulated for these observations")
    validation = reconcile(base["months"], bills or {}, tolerance)
    excluded = sum(1 for r in usage.intervals if not any(a <= r.start and r.end <= b for a, b in (p.bounds for p in periods)))
    gates = []
    if not bills:
        gates.append("Actual bills have not been supplied")
    if not all(v["reconciled"] for v in validation):
        gates.append("Baseline is not reconciled by component and total within the configured tolerance")
    if not all(r["complete"] for p in modeled for r in p["months"]) or excluded:
        gates.append("Observation coverage is incomplete for the comparison periods or falls outside bill periods")
    if not all(r.get("components_verified") for p in modeled for r in p["months"]):
        gates.append("Plan-specific supply, adjustments and taxes lack complete user-verified source inputs")
    if not all(p["eligible"] for p in modeled):
        gates.append("Account eligibility and switching restrictions have not been confirmed for every modeled plan")
    for p in modeled:
        p["delivery_difference"] = money(D(base["delivery"])-D(p["delivery"]))
        p["modeled_savings"] = money(D(base["total"])-D(p["total"])) if base["total"] is not None and p["total"] is not None else None
        p["savings_percent"] = (str((D(p["modeled_savings"])/D(base["total"])*100).quantize(D(".01")))
                                 if p["modeled_savings"] is not None and D(base["total"]) else None)
    full = all(p["total"] is not None for p in modeled)
    modeled.sort(key=lambda p: D(p["total"] if full else p["delivery"]))
    recommendation = modeled[0]["id"] if not gates else None
    return dict(quality=usage.summary(), periods=[p.key for p in periods], baseline=baseline,
                excluded_intervals=excluded, ranking_basis="modeled_total" if full else "base_delivery_only",
                plans=modeled+[p for p in plans if not p["supported"]], validation=validation,
                tolerance=str(tolerance), recommendation=recommendation, recommendation_blockers=gates,
                limitations=["Historical usage replay only; no annual savings projection. Unobserved seasons remain unknown.",
                             "Only bundled verified tariff dates are supported; no historical or future price carry-forward.",
                             "Default calendar months are not actual meter-read billing periods; the final bucket is clipped at the verification cutoff. Pass actual bills to reconcile.",
                             "Supply remains separate; ConEd full-service supply may change under TOU without changing supplier.",
                             "Base delivery excludes GR25/26/30 statements and taxes unless explicit component inputs are provided.",
                             "Component inputs are user-attested, not independently verified by this application; inspect their sources.",
                             "Thirty-day minimum on early service termination, credits, net metering, guarantees and special riders are unsupported.",
                             "Season/effective changes use GR10.5 day-share proration; actual seasonal meter-reading elections are unsupported.",
                             "Dollar components round half-up at period end; utility subcomponent rounding can differ.",
                             "Incomplete periods show observed energy plus full-period fixed charges and tier thresholds; no missing energy is invented."])
