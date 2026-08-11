from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, Tuple


# Friendly names to day indices used by datetime.weekday()
DAY_NAME_TO_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
INDEX_TO_RRULE_DAY = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")

DEFAULT_TIMEZONE = "America/New_York"
DEFAULT_RAW_DATA = Path(__file__).parent / "data" / "sis9_courses_202601.json"


def parse_iso_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def parse_mmddyyyy(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%m/%d/%Y").date()
    except ValueError:
        return None


def parse_hhmm(hhmm: str) -> time:
    hhmm = hhmm.strip()
    if len(hhmm) != 4 or not hhmm.isdigit():
        raise ValueError(f"Invalid time format: {hhmm}")
    return time(int(hhmm[:2]), int(hhmm[2:]))


def load_schedules(input_path: Path) -> Dict[str, dict]:
    schedules = json.loads(input_path.read_text())
    if not isinstance(schedules, dict):
        raise ValueError("Expected the optimized schedules JSON to be an object of schedules.")
    return schedules


def load_section_metadata(raw_path: Path | None) -> Dict[str, dict]:
    """
    Build a CRN -> metadata map (start_date, end_date, location) from SIS9 raw data.
    """
    if not raw_path or not raw_path.exists():
        return {}

    metadata: Dict[str, dict] = {}
    raw_courses = json.loads(raw_path.read_text())

    for course in raw_courses:
        crn = course.get("courseReferenceNumber")
        if not crn:
            continue

        meeting_times = (course.get("meetingsFaculty") or [])
        # Prefer the first meeting that has actual times, fall back to any meeting block
        meeting = next(
            (
                (mt or {}).get("meetingTime") or {}
                for mt in meeting_times
                if (mt or {}).get("meetingTime", {}).get("beginTime")
            ),
            (meeting_times[0] or {}).get("meetingTime") or {} if meeting_times else {},
        )

        start_date = parse_mmddyyyy(meeting.get("startDate"))
        end_date = parse_mmddyyyy(meeting.get("endDate"))

        building = meeting.get("buildingDescription") or meeting.get("building")
        room = meeting.get("room")
        location = " ".join(part for part in (building, room) if part)

        metadata[crn] = {
            "start_date": start_date,
            "end_date": end_date,
            "location": location or None,
        }

    return metadata


def derive_term_bounds(schedules: Dict[str, dict], metadata: Dict[str, dict]) -> Tuple[date | None, date | None]:
    crns: set[str] = set()
    for schedule in schedules.values():
        for section in schedule.get("sections", []):
            crn = section.get("crn")
            if crn:
                crns.add(crn)

    starts = [meta["start_date"] for crn, meta in metadata.items() if crn in crns and meta.get("start_date")]
    ends = [meta["end_date"] for crn, meta in metadata.items() if crn in crns and meta.get("end_date")]

    return (min(starts) if starts else None, max(ends) if ends else None)


def next_weekday_on_or_after(start: date, target_weekday: int) -> date:
    delta = (target_weekday - start.weekday()) % 7
    return start + timedelta(days=delta)


def last_weekday_on_or_before(end: date, target_weekday: int) -> date:
    delta = (end.weekday() - target_weekday) % 7
    return end - timedelta(days=delta)


def sanitize_day(day_name: str) -> Tuple[int, str]:
    index = DAY_NAME_TO_INDEX.get(day_name.strip().lower())
    if index is None:
        raise ValueError(f"Unknown day name: {day_name}")
    return index, INDEX_TO_RRULE_DAY[index]


def format_dt(dt_value: datetime) -> str:
    return dt_value.strftime("%Y%m%dT%H%M%S")


def build_event_lines(
    schedule_name: str,
    section: dict,
    meeting: dict,
    term_start: date,
    term_end: date,
    timezone: str,
    metadata: Dict[str, dict],
) -> list[str]:
    weekday_index, rrule_day = sanitize_day(meeting["day"])
    begin_time = parse_hhmm(meeting["begin_time"])
    end_time = parse_hhmm(meeting["end_time"])

    first_date = next_weekday_on_or_after(term_start, weekday_index)
    last_date = last_weekday_on_or_before(term_end, weekday_index)
    if last_date < first_date:
        last_date = first_date

    dtstart = datetime.combine(first_date, begin_time)
    dtend = datetime.combine(first_date, end_time)
    until = datetime.combine(last_date, end_time)

    crn = section.get("crn", "").strip()
    uid_seed = f"{schedule_name}-{crn}-{meeting['day']}-{meeting['begin_time']}-{meeting['end_time']}"
    uid = uuid.uuid5(uuid.NAMESPACE_URL, uid_seed)

    location = (metadata.get(crn) or {}).get("location")
    description = f"CRN: {crn}" if crn else None

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"SUMMARY:{section.get('subject_course', '').strip()} {section.get('title', '').strip()}".strip(),
        f"DTSTAMP:{format_dt(datetime.now(UTC))}Z",
        f"DTSTART;TZID={timezone}:{format_dt(dtstart)}",
        f"DTEND;TZID={timezone}:{format_dt(dtend)}",
        f"RRULE:FREQ=WEEKLY;BYDAY={rrule_day};UNTIL={format_dt(until)}",
    ]
    if location:
        lines.append(f"LOCATION:{location}")
    if description:
        lines.append(f"DESCRIPTION:{description}")

    lines.append("END:VEVENT")
    return lines


def build_calendar(
    schedule_name: str,
    schedule: dict,
    term_start: date,
    term_end: date,
    timezone: str,
    metadata: Dict[str, dict],
) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//YACS//Schedule Export//EN",
        f"X-WR-CALNAME:{schedule_name}",
    ]

    for section in schedule.get("sections", []):
        for meeting in section.get("meeting_times", []):
            lines.extend(
                build_event_lines(
                    schedule_name=schedule_name,
                    section=section,
                    meeting=meeting,
                    term_start=term_start,
                    term_end=term_end,
                    timezone=timezone,
                    metadata=metadata,
                )
            )

    lines.append("END:VCALENDAR")
    # ICS prefers CRLF newlines
    return "\r\n".join(lines) + "\r\n"


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate .ics calendars from optimized course schedules.")
    parser.add_argument(
        "-i",
        "--input",
        default=Path(__file__).with_name("courses_optimized.json"),
        help="Path to optimizer output JSON.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="ics_out",
        help="Directory to write .ics files (defaults to the input file's directory).",
    )
    parser.add_argument(
        "--term-start",
        dest="term_start",
        help="ISO date (YYYY-MM-DD) for the first week of classes.",
    )
    parser.add_argument(
        "--term-end",
        dest="term_end",
        help="ISO date (YYYY-MM-DD) for the last week of classes.",
    )
    parser.add_argument(
        "-t",
        "--timezone",
        default=DEFAULT_TIMEZONE,
        help=f"Timezone identifier to use in the calendar (default: {DEFAULT_TIMEZONE}).",
    )
    parser.add_argument(
        "-r",
        "--raw-data",
        default=None,
        help="Optional path to the raw SIS9 course JSON to auto-derive dates/locations.",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    ensure_output_dir(output_dir)

    schedules = load_schedules(input_path)

    raw_data_path = Path(args.raw_data) if args.raw_data else DEFAULT_RAW_DATA
    metadata = load_section_metadata(raw_data_path)

    term_start = parse_iso_date(args.term_start) if args.term_start else None
    term_end = parse_iso_date(args.term_end) if args.term_end else None

    if not term_start or not term_end:
        derived_start, derived_end = derive_term_bounds(schedules, metadata)
        term_start = term_start or derived_start
        term_end = term_end or derived_end

    if not term_start or not term_end:
        raise SystemExit("Unable to determine term start/end. Provide --term-start and --term-end.")

    for schedule_name, schedule in schedules.items():
        calendar_text = build_calendar(
            schedule_name=schedule_name,
            schedule=schedule,
            term_start=term_start,
            term_end=term_end,
            timezone=args.timezone,
            metadata=metadata,
        )
        filename = schedule_name.lower().replace(" ", "_") + ".ics"
        output_path = output_dir / filename
        output_path.write_text(calendar_text)
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
