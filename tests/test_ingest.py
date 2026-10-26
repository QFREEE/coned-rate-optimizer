from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from coned_optimize.ingest import NY, load_usage, timestamp

ROOT = Path(__file__).parents[1]


def csv_file(tmp_path, rows):
    path = tmp_path / "usage.csv"
    path.write_text("start,end,kwh\n" + rows, encoding="utf-8")
    return path


def test_native_inclusive_display_minutes():
    usage = load_usage(ROOT / "examples/coned-layout.csv")
    assert usage.safe and usage.gaps == 0
    assert all((r.end-r.start).total_seconds() == 900 for r in usage.intervals)
    assert usage.intervals[0].start.astimezone(NY).hour == 0


@pytest.mark.parametrize("wall", ["2026-03-08T02:30", "2026-11-01T01:30"])
def test_dst_unresolvable_wall_clock_rejected(wall):
    with pytest.raises(ValueError, match="Ambiguous or nonexistent"):
        timestamp(wall)


def test_fall_back_explicit_offsets_are_distinct(tmp_path):
    path = csv_file(tmp_path, "2026-11-01T01:00:00-04:00,2026-11-01T01:15:00-04:00,1\n"
                    "2026-11-01T01:00:00-05:00,2026-11-01T01:15:00-05:00,2\n")
    usage = load_usage(path)
    assert usage.safe and usage.duplicates == 0
    assert usage.intervals[1].start-usage.intervals[0].start == timedelta(hours=1)
    assert usage.gaps == 1


def test_spring_transition_contiguous(tmp_path):
    usage = load_usage(csv_file(tmp_path, "2026-03-08T01:45:00-05:00,2026-03-08T03:00:00-04:00,.1\n"
                    "2026-03-08T03:00:00-04:00,2026-03-08T03:15:00-04:00,.2\n"))
    assert usage.safe and usage.gaps == 0
    assert usage.summary()["span_completeness_percent"] == 100


def test_duplicates_overlaps_invalid_and_gaps_reported(tmp_path):
    usage = load_usage(csv_file(tmp_path, "2026-07-01T00:00,2026-07-01T00:15,1\n"
                  "2026-07-01T00:00,2026-07-01T00:15,1\n"
                  "2026-07-01T00:10,2026-07-01T00:20,2\n"
                  "2026-07-01T00:30,2026-07-01T00:45,1\n"
                  "2026-07-01T00:45,2026-07-01T01:00,NaN\n"
                  "2026-07-01T01:00,2026-07-01T01:15,-1\n"))
    assert (usage.duplicates, usage.overlaps, usage.gaps, usage.invalid) == (1, 2, 1, 2)
    assert not usage.safe
    assert len(usage.intervals) == 4  # no silent deduplication


def test_xml_units_multiplier_and_metadata(tmp_path):
    usage = load_usage(ROOT / "examples/green-button.xml")
    assert usage.safe
    assert usage.intervals[0].kwh == Decimal(".3")
    path = tmp_path / "scaled.xml"
    path.write_text((ROOT / "examples/green-button.xml").read_text().replace(
        "<e:powerOfTenMultiplier>0", "<e:powerOfTenMultiplier>-1"))
    assert load_usage(path).intervals[0].kwh == Decimal(".03")


@pytest.mark.parametrize("old,new", [("<e:uom>72", "<e:uom>38"),
    ("<e:flowDirection>1", "<e:flowDirection>19"),
    ("<e:accumulationBehaviour>4", "<e:accumulationBehaviour>1"),
    ("<e:commodity>1", "<e:commodity>7")])
def test_xml_non_consumption_rejected(tmp_path, old, new):
    path = tmp_path / "bad.xml"
    path.write_text((ROOT / "examples/green-button.xml").read_text().replace(old, new))
    with pytest.raises(ValueError, match="ReadingType"):
        load_usage(path)


def test_xml_estimated_quality_rejected(tmp_path):
    path = tmp_path / "bad.xml"
    path.write_text((ROOT / "examples/green-button.xml").read_text().replace(
        "<e:value>300</e:value>", "<e:value>300</e:value><e:ReadingQuality><e:quality>17</e:quality></e:ReadingQuality>"))
    usage = load_usage(path)
    assert usage.invalid == 1 and not usage.safe


def test_csv_estimated_quality_rejected(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("start,end,kwh,quality\n2026-07-01T00:00,2026-07-01T00:15,1,estimated\n")
    assert load_usage(path).invalid == 1
