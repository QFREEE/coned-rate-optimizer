"""Conservative interval ingestion. No interpolation, inferred folds, or deduplication."""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from defusedxml import ElementTree as ET

NY = ZoneInfo("America/New_York")
UTC = timezone.utc


def timestamp(value: str) -> datetime:
    """Resolve explicit offsets or unambiguous New York wall times, to UTC."""
    value = value.strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        dt = None
        for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M:%S"):
            try:
                dt = datetime.strptime(value, fmt)
                break
            except ValueError:
                pass
        if dt is None:
            raise ValueError(f"Unrecognized timestamp: {value}")
    if dt.tzinfo:
        return dt.astimezone(UTC)
    candidates = {dt.replace(tzinfo=NY, fold=f).astimezone(UTC) for f in (0, 1)
                  if dt.replace(tzinfo=NY, fold=f).astimezone(UTC).astimezone(NY).replace(tzinfo=None) == dt}
    if len(candidates) != 1:
        raise ValueError(f"Ambiguous or nonexistent New York time {value}; supply UTC or an explicit offset")
    return candidates.pop()


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime
    kwh: Decimal


@dataclass
class Usage:
    intervals: list[Interval]
    issues: list[str] = field(default_factory=list)
    invalid: int = 0
    duplicates: int = 0
    overlaps: int = 0
    gaps: int = 0

    @property
    def safe(self):
        return bool(self.intervals) and not (self.invalid or self.duplicates or self.overlaps)

    def summary(self):
        rows = self.intervals
        span = (rows[-1].end - rows[0].start).total_seconds() if rows else 0
        covered = sum((r.end-r.start).total_seconds() for r in rows)
        return dict(intervals=len(rows), start=rows[0].start.astimezone(NY).isoformat() if rows else None,
                    end=rows[-1].end.astimezone(NY).isoformat() if rows else None,
                    kwh=str(sum((r.kwh for r in rows), Decimal(0))),
                    span_completeness_percent=round(100*covered/span, 3) if span and not self.overlaps else None,
                    invalid=self.invalid, duplicates=self.duplicates, overlaps=self.overlaps,
                    gaps=self.gaps, safe_to_simulate=self.safe, issues=self.issues)


def _key(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _csv_rows(path):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    # ConEd files can contain account metadata before the interval table.
    for idx, line in enumerate(lines):
        keys = {_key(v) for v in next(csv.reader([line]))}
        if keys & {"start", "starttime", "intervalstart", "startdatetime", "date", "startdate"}:
            break
    else:
        raise ValueError("No interval CSV header found; expected start/end/kwh or DATE/START TIME/END TIME/USAGE/UNITS")
    reader = csv.DictReader(io.StringIO("\n".join(lines[idx:])))
    for line_no, original in enumerate(reader, idx+2):
        row = {_key(k): (v or "").strip() for k, v in original.items() if k}
        def get(*names):
            return next((row[n] for n in names if row.get(n)), "")
        try:
            fuel = _key(get("type", "fuel", "servicetype"))
            if fuel and fuel not in {"electric", "electricity", "electricusage"}:
                raise ValueError("Select electricity consumption only; mixed fuels/channels are unsupported")
            units = get("units", "unit") or "kwh"
            if units.lower() not in {"kwh", "wh"}:
                raise ValueError(f"Unsupported unit {units}; expected interval energy")
            start_s = get("start", "intervalstart", "startdatetime", "starttime")
            end_s = get("end", "intervalend", "enddatetime", "endtime")
            date_s = get("date", "startdate")
            native = bool(date_s and get("starttime") and get("endtime"))
            if not start_s and get("startdate"):
                start_s, end_s = get("startdate"), get("enddate")
            if date_s and start_s and not re.search(r"\d{4}[-/]", start_s) and not re.search(r"\d/\d", start_s):
                start_s = date_s + " " + start_s
                end_s = get("enddate") or date_s
                end_s += " " + get("endtime")
            start = timestamp(start_s)
            if end_s:
                end = timestamp(end_s)
                # Time-only CSV exports represent midnight as 00:00 on the same DATE.
                if date_s and not get("enddate") and get("endtime") in {"00:00", "00:00:00", "12:00 AM"} and end < start:
                    local = end.astimezone(NY) + timedelta(days=1)
                    end = local.astimezone(UTC)
                # ConEd's documented display-minute layout: 00:00–00:14 means [00:00,00:15).
                # Only the native DATE/START TIME/END TIME layout gets this normalization.
                if native and end.second == 0 and end.minute in {14, 29, 44, 59}:
                    end += timedelta(minutes=1)
            elif get("durationseconds", "duration"):
                end = start + timedelta(seconds=int(get("durationseconds", "duration")))
            else:
                raise ValueError("Explicit end or duration_seconds is required; durations are not guessed")
            quality = get("quality", "readingquality", "notes")
            if quality and quality.lower() not in {"actual", "0"}:
                raise ValueError(f"Non-actual reading quality: {quality}")
            value = Decimal(get("kwh", "usage", "usagekwh", "consumption", "value"))
            if units.lower() == "wh":
                value /= 1000
            yield line_no, Interval(start, end, value), None
        except (ValueError, InvalidOperation) as exc:
            yield line_no, None, str(exc)


def _xml_rows(path):
    root = ET.parse(path).getroot()
    ns = {"e": "http://naesb.org/espi", "a": "http://www.w3.org/2005/Atom"}
    types = root.findall(".//e:ReadingType", ns)
    blocks = root.findall(".//e:IntervalBlock", ns)
    # Refuse mixing streams or selecting a ReadingType by document order.
    readings = root.findall(".//e:IntervalReading", ns)
    if len(types) != 1 or not blocks:
        raise ValueError("XML must contain exactly one ReadingType and one electricity consumption stream; export one meter/channel")
    rt = types[0]
    def metadata(name):
        return rt.findtext(f"e:{name}", namespaces=ns)
    if (metadata("uom") != "72" or metadata("commodity") != "1" or metadata("flowDirection") != "1"
            or metadata("accumulationBehaviour") != "4" or metadata("kind") != "12"):
        raise ValueError("XML requires ReadingType electricity(1), forward consumption(1), energy kind(12), delta accumulation(4), Wh(72)")
    # Distinct MeterReading links imply distinct channels, even with identical ReadingTypes.
    parents = set()
    for entry in root.findall("a:entry", ns):
        if entry.find("a:content/e:IntervalBlock", ns) is not None:
            parents.update(link.attrib.get("href") for link in entry.findall("a:link", ns)
                           if link.attrib.get("rel") == "up")
    if len(parents) > 1:
        raise ValueError("Multiple XML meter channels; export one consumption stream")
    if len(root.findall(".//e:MeterReading", ns)) > 1 or (len(blocks) > 1 and not parents):
        raise ValueError("XML channel association cannot be established; export a single meter/channel")
    power = int(metadata("powerOfTenMultiplier") or "0")
    for idx, reading in enumerate(readings, 1):
        try:
            def val(name):
                return reading.findtext("e:" + name, namespaces=ns)
            for quality in reading.findall("e:ReadingQuality", ns):
                code = quality.findtext("e:quality", namespaces=ns) or (quality.text or "").strip()
                if code not in {"0", "19"}:
                    raise ValueError(f"Unverified XML ReadingQuality {code}; estimated/suspect readings cannot be simulated")
            start = datetime.fromtimestamp(int(val("timePeriod/e:start")), UTC)
            end = start + timedelta(seconds=int(val("timePeriod/e:duration")))
            energy = Decimal(val("value")) * Decimal(10)**power / 1000
            yield idx, Interval(start, end, energy), None
        except (TypeError, ValueError, InvalidOperation) as exc:
            yield idx, None, str(exc)


def load_usage(path: str | Path) -> Usage:
    path = Path(path)
    if path.suffix.lower() not in {".xml", ".csv"}:
        raise ValueError("Usage must be .csv or .xml")
    result = Usage([])
    for line, interval, error in (_xml_rows(path) if path.suffix.lower() == ".xml" else _csv_rows(path)):
        if not error and (not interval.kwh.is_finite() or interval.kwh < 0 or interval.end <= interval.start):
            error = "Consumption must be finite and nonnegative; duration must be positive"
        if error:
            result.invalid += 1
            result.issues.append(f"Record {line}: {error}")
        else:
            result.intervals.append(interval)
    result.intervals.sort(key=lambda r: (r.start, r.end))
    furthest = None
    seen = set()
    for row in result.intervals:
        identity = (row.start, row.end)
        if identity in seen:
            result.duplicates += 1
            result.issues.append(f"Duplicate interval at {row.start.isoformat()}; no rows discarded")
        if furthest and row.start < furthest:
            result.overlaps += 1
            result.issues.append(f"Overlapping interval at {row.start.isoformat()}")
        if furthest and row.start > furthest:
            result.gaps += 1
            result.issues.append(f"Missing interval span {furthest.isoformat()} to {row.start.isoformat()}")
        furthest = max(furthest, row.end) if furthest else row.end
        seen.add(identity)
    return result
