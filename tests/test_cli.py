import json
from pathlib import Path

from coned_optimize.cli import main
from coned_optimize.engine import compare
from coned_optimize.ingest import load_usage
from coned_optimize.report import html_report

ROOT = Path(__file__).parents[1]


def test_offline_report_and_json(tmp_path, capsys):
    out, audit = tmp_path / "report.html", tmp_path / "audit.json"
    assert main(["report", str(ROOT/"examples/usage.csv"), "--bill", str(ROOT/"examples/bills.csv"),
                 "--components", str(ROOT/"examples/components.csv"), "--output", str(out), "--json", str(audit)]) == 0
    document = out.read_text(encoding="utf-8")
    assert '<svg' in document and 'default-src' in document
    assert '<script' not in document and 'src="http' not in document
    assert 'No switching recommendation' in document
    assert json.loads(audit.read_text())["recommendation"] is None
    assert 'MONTHLY' in capsys.readouterr().out


def test_report_escapes_untrusted_labels():
    result = compare(load_usage(ROOT/"examples/usage.csv"))
    result["plans"][0]["eligibility"] = '<img src=x onerror="alert(1)">'
    assert '<img src=x' not in html_report(result)


def test_inspect_and_clean_error_paths(tmp_path, capsys):
    assert main(["inspect", str(ROOT/"examples/green-button.xml")]) == 0
    assert main(["compare", str(tmp_path/"missing.csv")]) == 2
    assert 'Error:' in capsys.readouterr().err
    assert main(["compare", str(ROOT/"examples/usage.csv"), "--tolerance", "NaN"]) == 2
