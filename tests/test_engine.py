import json
from datetime import date, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

import pytest

from coned_optimize.engine import (Catalog, Period, compare, read_bills, read_components, peak,
                                   simulate_base, top_three_daily_demand)
from coned_optimize.ingest import Interval, Usage, NY, UTC, load_usage, timestamp

ROOT = Path(__file__).parents[1]


def data(start, end, kwh=".25"):
    start, end = timestamp(start), timestamp(end)
    rows = []
    while start < end:
        finish = min(start+timedelta(minutes=15), end)
        rows.append(Interval(start, finish, D(kwh)))
        start = finish
    return Usage(rows)


def test_31_day_customer_and_summer_tier_proration():
    usage = data("2026-07-01", "2026-08-01")  # 744 kWh
    row = simulate_base(usage, Period(date(2026,7,1), date(2026,8,1)), "standard", Catalog())
    assert row["customer_charge"] == "21.70"
    # 258.3333*.16402 + (744-258.3333)*.18858 + 21.70
    assert row["delivery"] == "155.66"
    assert row["complete"]


def test_winter_and_dst_23_hour_day():
    usage = data("2026-03-08", "2026-03-09")
    row = simulate_base(usage, Period(date(2026,3,8), date(2026,3,9)), "standard", Catalog())
    assert len(usage.intervals) == 92
    assert row["complete"] and row["completeness_percent"] == 100
    assert row["kwh"] == "23.00" and row["delivery"] == "4.47"


@pytest.mark.parametrize("value,expected", [("2026-07-04T07:59:59", False),
    ("2026-07-04T08:00", True), ("2026-07-04T23:59:59", True),
    ("2026-07-05T00:00", False), ("2026-07-05T12:00", True)])
def test_tou_boundaries_weekends_holidays(value, expected):
    config = Catalog().at(date(2026,7,4))["plans"]["tou"]
    assert peak(timestamp(value), config) is expected


def test_tou_rejects_daily_energy_instead_of_inventing_hourly_load():
    usage = Usage([Interval(timestamp("2026-07-01"), timestamp("2026-07-02"), D(24))])
    with pytest.raises(ValueError, match="spans TOU"):
        simulate_base(usage, Period(date(2026,7,1),date(2026,7,2)), "tou", Catalog())


def test_season_crossing_uses_day_shares_not_observed_season_allocation():
    # Four-day bill, 2 summer / 2 winter days. All 100 kWh happened in winter.
    usage = Usage([Interval(timestamp("2026-05-30"), timestamp("2026-05-31"), D(100))])
    period = Period(date(2026,5,30),date(2026,6,3))
    row = simulate_base(usage, period, "standard", Catalog())
    # winter 16.402, summer 18.0393333, mean17.2206667 + fixed2.8
    assert row["delivery"] == "20.02"
    assert not row["complete"]


def test_tariff_version_changes_are_weighted_and_not_carried_forward(tmp_path):
    original = Catalog().versions[0]
    first = json.loads(json.dumps(original))
    first["effective_end"] = "2026-03-16"
    second = json.loads(json.dumps(original))
    second["effective_start"] = "2026-03-16"
    second["plans"]["standard"]["winter_kwh_rate"] = ".20"
    (tmp_path / "a.json").write_text(json.dumps(first))
    (tmp_path / "b.json").write_text(json.dumps(second))
    row = simulate_base(data("2026-03-01", "2026-04-01"), Period(date(2026,3,1),date(2026,4,1)), "standard", Catalog(tmp_path))
    assert row["delivery"] == "157.36"  # DST: 743 kWh*(15*.16402+16*.20)/31 +21.7
    with pytest.raises(ValueError, match="No verified tariff"):
        Catalog().at(date(2026,1,31))
    with pytest.raises(ValueError, match="No verified tariff"):
        Catalog().at(date(2026,10,27))


def test_gap_and_partial_month_never_scaled():
    usage = data("2026-07-10", "2026-07-11")
    result = compare(usage)
    standard = next(p for p in result["plans"] if p["id"] == "standard")
    assert standard["months"][0]["kwh"] == "24.00"
    assert standard["months"][0]["customer_charge"] == "21.70"
    assert standard["months"][0]["completeness_percent"] == 3.226
    assert result["recommendation"] is None and standard["total"] is None


def test_interval_crossing_bill_boundary_fails():
    usage = Usage([Interval(timestamp("2026-06-30T23:45"), timestamp("2026-07-01T00:15"),D(1))])
    with pytest.raises(ValueError, match="crosses billing"):
        simulate_base(usage, Period(date(2026,7,1),date(2026,8,1)),"standard", Catalog())


def test_demand_top_three_is_not_monthly_or_quarter_hour_max():
    assert top_three_daily_demand(["1", "9", "6", "3"]) == 6
    with pytest.raises(ValueError):
        top_three_daily_demand([1,2])
    assert not Catalog().at(date(2026,7,1))["plans"]["steady_use"]["supported"]


def test_synthetic_bill_reconciliation_and_recommendation_gates():
    usage = load_usage(ROOT / "examples/usage.csv")
    periods, bills = read_bills(ROOT / "examples/bills.csv")
    components = read_components(ROOT / "examples/components.csv")
    result = compare(usage, periods=periods, bills=bills, components=components, eligible={"standard","tou"})
    assert all(v["reconciled"] for v in result["validation"])
    assert result["recommendation"] is None  # synthetic component assumptions aren't verified
    standard = next(p for p in result["plans"] if p["id"] == "standard")
    tou = next(p for p in result["plans"] if p["id"] == "tou")
    assert standard["delivery"] == "217.78" and tou["delivery"] == "185.02"
    assert standard["total"] == "379.60" and tou["total"] == "345.68"
    # Exercise the explicit user-attestation gate with synthetic data; never publish these as real rates.
    for row in components.values():
        row["verified"] = "true"
    assert compare(usage, periods=periods, bills=bills, components=components,
                   eligible={"standard","tou"})["recommendation"] == "tou"
    bills[periods[0].key]["supply"] += D(5)
    bad = compare(usage, periods=periods, bills=bills, components=components, eligible={"standard","tou"})
    assert bad["recommendation"] is None
    assert "supply" in bad["validation"][0]["unexplained"]


def test_no_inheritance_of_baseline_supply():
    usage = load_usage(ROOT / "examples/usage.csv")
    periods, bills = read_bills(ROOT / "examples/bills.csv")
    components = {k:v for k,v in read_components(ROOT / "examples/components.csv").items() if k[1]=="standard"}
    result = compare(usage, periods=periods, bills=bills, components=components)
    tou = next(p for p in result["plans"] if p["id"] == "tou")
    assert tou["total"] is None and tou["modeled_savings"] is None
    assert all(r["supply"] is None for r in tou["months"])


def test_bill_period_overlap_and_total_mismatch_rejected(tmp_path):
    path = tmp_path / "bill.csv"
    path.write_text("start,end,delivery,supply,adjustments,taxes,total\n2026-07-01,2026-08-01,1,2,3,4,12\n")
    with pytest.raises(ValueError, match="total"):
        read_bills(path)
    path.write_text("start,end,delivery,supply,adjustments,taxes\n2026-07-01,2026-08-01,1,2,3,4\n2026-07-15,2026-08-15,1,2,3,4\n")
    with pytest.raises(ValueError, match="overlap"):
        read_bills(path)


def test_current_month_bucket_stops_at_verified_cutoff():
    result = compare(data("2026-10-01", "2026-10-26"))
    assert result["periods"] == ["2026-10-01/2026-10-27"]
    assert result["recommendation"] is None
    # Actual bill dates remain exact and are never silently truncated.
    with pytest.raises(ValueError, match="No verified tariff"):
        compare(data("2026-10-01", "2026-10-26"), periods=[Period(date(2026,10,1),date(2026,11,1))])
