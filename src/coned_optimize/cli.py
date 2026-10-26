"""Command-line entry point. No network calls."""
import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from defusedxml.common import DefusedXmlException
from xml.etree.ElementTree import ParseError

from .engine import Catalog, compare, read_bills, read_components
from .ingest import load_usage
from .report import html_report, terminal
from .bill_audit import audit_bills, audit_html


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline Con Edison SC1 historical rate comparison")
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit-bills", help="Check extracted bill line items without inventing missing charges")
    audit.add_argument("line_items", type=Path)
    audit.add_argument("--sales-tax-percent", required=True, help="Sales tax percentage explicitly printed on these bills")
    audit.add_argument("--electric-only-full-service", action="store_true", help="Confirm electric-only ConEd full-service billing for BPP check")
    audit.add_argument("--output", type=Path, default=Path("bill-audit.html"))
    audit.add_argument("--json", dest="json_output", type=Path)
    inspect = sub.add_parser("inspect", help="Inspect coverage and interval quality")
    inspect.add_argument("usage", type=Path)
    for name in ("compare", "report"):
        cmd = sub.add_parser(name, help="Compare verified tariffs over the same observed consumption")
        cmd.add_argument("usage", type=Path)
        cmd.add_argument("--bill", type=Path, help="Actual component CSV; also supplies exact billing periods")
        cmd.add_argument("--components", type=Path, help="Separate plan-specific supply/adjustment/tax inputs")
        cmd.add_argument("--baseline", choices=["standard", "tou"], default="standard")
        cmd.add_argument("--eligible", default="", help="Comma-separated account-verified eligible plans, e.g. standard,tou")
        cmd.add_argument("--tariffs", type=Path, help="Directory of audited tariff versions")
        cmd.add_argument("--tolerance", default="1.00", help="Reconciliation tolerance in dollars (default 1.00)")
        cmd.add_argument("--json", dest="json_output", type=Path, help="Save structured audit results")
        cmd.add_argument("--output", type=Path, default=Path("report.html") if name == "report" else None,
                         help="Write a self-contained offline HTML report")
    args = parser.parse_args(argv)
    try:
        if args.command == "audit-bills":
            result = audit_bills(args.line_items, sales_tax_percent=args.sales_tax_percent,
                                 electric_only_full_service=args.electric_only_full_service)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(audit_html(result), encoding="utf-8")
            if args.json_output:
                args.json_output.parent.mkdir(parents=True, exist_ok=True)
                args.json_output.write_text(json.dumps(result, indent=2), encoding="utf-8")
            for row in result["bills"]:
                print(row["period"], f'{sum(c["matches"] for c in row["checks"])}/{len(row["checks"])} partial checks match;',
                      "$"+row["delivery_line_less_base_energy"]+" unallocated delivery difference")
            print("Full reconciliation remains incomplete. Report:", args.output.resolve())
            return 0
        usage = load_usage(args.usage)
        if args.command == "inspect":
            print(json.dumps(usage.summary(), indent=2))
            return 0 if usage.safe else 2
        tolerance = Decimal(args.tolerance)
        if not tolerance.is_finite() or tolerance < 0 or tolerance > Decimal("5"):
            raise ValueError("Tolerance must be finite, between $0 and $5")
        eligible = set(filter(None, args.eligible.split(",")))
        if not eligible <= {"standard", "tou"}:
            raise ValueError("Only standard,tou can be confirmed eligible; other plans are unsupported")
        periods, bills = read_bills(args.bill) if args.bill else (None, None)
        result = compare(usage, catalog=Catalog(args.tariffs), bills=bills, periods=periods,
                         components=read_components(args.components), baseline=args.baseline,
                         eligible=eligible, tolerance=tolerance)
        print(terminal(result))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(html_report(result), encoding="utf-8")
            print(f"\nOffline report: {args.output.resolve()}")
        if args.json_output:
            args.json_output.parent.mkdir(parents=True, exist_ok=True)
            args.json_output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return 0
    except (ValueError, InvalidOperation, OSError, KeyError, DefusedXmlException, ParseError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
