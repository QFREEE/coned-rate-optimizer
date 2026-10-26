import csv
from pathlib import Path

import pytest

from coned_optimize.bill_audit import audit_bills, audit_html
from coned_optimize.cli import main


def fixture(tmp_path, **changes):
    # Synthetic values, unrelated to household account data.
    row = dict(start="2026-08-01",end="2026-08-31",kwh="500",basic_service="22.80",
               delivery_energy="100.00",system_benefits="8.00",delivery_grt="4.44",
               delivery_sales_tax="5.41",delivery_total="140.65",supply_energy="50.00",
               merchant_function="2.00",supply_grt="0.53",supply_sales_tax="2.10",
               supply_total="54.63",electricity_total="195.28")
    row.update(changes)
    path=tmp_path/"lines.csv"
    with path.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader();writer.writerow(row)
    return path


def test_partial_arithmetic_checks_do_not_claim_full_reconciliation(tmp_path):
    result=audit_bills(fixture(tmp_path),sales_tax_percent="4",electric_only_full_service=True)
    row=result["bills"][0]
    assert len(row["checks"])==8 and all(c["matches"] for c in row["checks"])
    assert not row["fully_reconciled"]
    assert row["delivery_line_less_base_energy"]=="11.85"
    assert "Unallocated" in row["residual_status"]
    assert "jurisdiction not verified" in next(c for c in row["checks"] if c["name"]=="village_delivery_grt_consistency")["basis"]


def test_temporary_grt_uses_bill_end_not_service_day_proration(tmp_path):
    result=audit_bills(fixture(tmp_path,start="2026-06-15",end="2026-07-15",delivery_grt="4.78"),sales_tax_percent="4")
    check=next(c for c in result["bills"][0]["checks"] if c["name"]=="village_delivery_grt_consistency")
    assert check["expected"]=="4.78" and check["matches"]
    assert not any(c["name"]=="basic_service" for c in result["bills"][0]["checks"])


def test_mismatch_is_preserved(tmp_path):
    result=audit_bills(fixture(tmp_path,delivery_sales_tax="6.00"),sales_tax_percent="4")
    check=next(c for c in result["bills"][0]["checks"] if c["name"]=="delivery_sales_tax")
    assert check["difference"]=="0.59" and not check["matches"]


@pytest.mark.parametrize("tax",["NaN","Infinity","-1"])
def test_invalid_tax_rejected(tmp_path,tax):
    with pytest.raises(ValueError):audit_bills(fixture(tmp_path),sales_tax_percent=tax)


def test_audit_cli_writes_offline_artifacts(tmp_path):
    output=tmp_path/"audit.html"
    assert main(["audit-bills",str(fixture(tmp_path)),"--sales-tax-percent","4","--output",str(output)])==0
    assert "Full bills remain unreconciled" in output.read_text(encoding="utf-8")
    assert "<script" not in output.read_text(encoding="utf-8")
