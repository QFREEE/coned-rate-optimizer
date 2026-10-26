"""Generate synthetic examples only. Run from the repository root."""
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
NY = ZoneInfo("America/New_York")
start = datetime(2026, 7, 1, tzinfo=NY).astimezone(timezone.utc)
end = datetime(2026, 9, 1, tzinfo=NY).astimezone(timezone.utc)
with (ROOT / "usage.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream)
    writer.writerow(["start", "end", "kwh"])
    while start < end:
        finish = start + timedelta(minutes=15)
        writer.writerow([start.isoformat(), finish.isoformat(), "0.30" if start.astimezone(NY).hour < 8 else "0.10"])
        start = finish

with (ROOT / "bills.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream)
    writer.writerow(["start", "end", "delivery", "supply", "adjustments", "taxes", "total"])
    for start, end in [("2026-07-01", "2026-08-01"), ("2026-08-01", "2026-09-01")]:
        writer.writerow([start, end, "108.89", "59.52", "14.88", "6.51", "189.80"])

with (ROOT / "components.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream)
    writer.writerow(["start", "end", "plan", "supply_per_kwh", "supply_fixed", "adjustments_per_kwh",
                     "adjustments_fixed", "tax_percent", "tax_fixed", "source", "verified"])
    for start, end in [("2026-07-01", "2026-08-01"), ("2026-08-01", "2026-09-01")]:
        for plan in ["standard", "tou"]:
            writer.writerow([start, end, plan, ".12", "0", ".03", "0", "3.55", "0",
                             "SYNTHETIC demonstration inputs, not ConEd supply/adjustment/tax rates", "false"])
