from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, stdev
from typing import Callable, Dict, FrozenSet, Iterable, List, Sequence

logger = logging.getLogger(__name__)

# Constants
MEETING_KEYS = ("monday", "tuesday", "wednesday", "thursday", "friday")
DAY_NAMES_SHORT = ("Mon", "Tue", "Wed", "Thu", "Fri")
DAY_NAMES_LONG = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")

DEFAULT_REQUIREMENTS_SPEC: Dict[str, list[list[str]]] = {
    "cs_requirement": [["CSCI1200"]],
    "math_requirement": [["MATH1020"]],
    "biol_requirement": [["BIOL1010", "BIOL1015"], ["BIOL1010", "BIOL1016"]],
}
DEFAULT_HASS_SUBJECT = "INQR"
DEFAULT_MAX_SCHEDULES = 25

EARLY_CLASS_THRESHOLD = 10 * 60  # 10:00
LATE_CLASS_THRESHOLD = 18 * 60   # 18:00
EARLY_LATE_PENALTY_PER_MIN = 0.2
ACTIVE_DAY_IDEAL_RANGE = (3, 4)
ACTIVE_DAY_BONUS = 100
ACTIVE_DAY_PENALTY_PER_DAY = 50
DISTRIBUTION_WEIGHT = 20
IDLE_TIME_PENALTY = 0.05
SPAN_PENALTY = 0.05


@dataclass(frozen=True, slots=True)
class ScoringWeights:
    early_class_threshold: int = EARLY_CLASS_THRESHOLD
    late_class_threshold: int = LATE_CLASS_THRESHOLD
    early_late_penalty_per_min: float = EARLY_LATE_PENALTY_PER_MIN
    active_day_ideal_range: tuple[int, int] = (ACTIVE_DAY_IDEAL_RANGE[0], ACTIVE_DAY_IDEAL_RANGE[1])
    active_day_bonus: float = ACTIVE_DAY_BONUS
    active_day_penalty_per_day: float = ACTIVE_DAY_PENALTY_PER_DAY
    distribution_weight: float = DISTRIBUTION_WEIGHT
    idle_time_penalty: float = IDLE_TIME_PENALTY
    span_penalty: float = SPAN_PENALTY


@dataclass(frozen=True, slots=True)
class OptimizationOptions:
    requirements_spec: Dict[str, list[list[str]]] = field(
        default_factory=lambda: {k: [list(g) for g in v] for k, v in DEFAULT_REQUIREMENTS_SPEC.items()}
    )
    hass_subject: str = DEFAULT_HASS_SUBJECT
    max_schedules: int = DEFAULT_MAX_SCHEDULES
    scoring: ScoringWeights = field(default_factory=ScoringWeights)
    min_seats_available: int = 1
    include_subjects: FrozenSet[str] | None = None
    exclude_subjects: FrozenSet[str] | None = None
    penalties: tuple[Callable[[Iterable["Section"]], float], ...] = field(default_factory=tuple)


def hhmm_to_minutes(hhmm: str) -> int:
    """Convert 'HHMM' (e.g., '0930') to minutes since midnight."""
    return int(hhmm[:2]) * 60 + int(hhmm[2:])


def minutes_to_hhmm(minutes: int) -> str:
    """Convert minutes since midnight to 'HHMM'."""
    return f"{minutes // 60:02d}{minutes % 60:02d}"


def minutes_to_hh_colon_mm(minutes: int) -> str:
    """Convert minutes since midnight to 'HH:MM'."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@dataclass(frozen=True, slots=True)
class MeetingTime:
    """Normalized meeting time for a single day."""

    # Day index: 0=Mon ... 4=Fri
    day: int
    begin_time: int  # minutes since midnight
    end_time: int    # minutes since midnight

    @classmethod
    def from_strings(cls, day: int, begin_time: str, end_time: str) -> "MeetingTime":
        return cls(day=day, begin_time=hhmm_to_minutes(begin_time), end_time=hhmm_to_minutes(end_time))

    def overlaps_with(self, other: "MeetingTime") -> bool:
        if self.day != other.day:
            return False
        return not (self.end_time <= other.begin_time or self.begin_time >= other.end_time)

    def __repr__(self) -> str:
        return (
            f"{DAY_NAMES_SHORT[self.day]} "
            f"{minutes_to_hh_colon_mm(self.begin_time)}–{minutes_to_hh_colon_mm(self.end_time)}"
        )


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def extract_meeting_times(section: dict) -> List[MeetingTime]:
    """
    Extract and validate meeting times from a Banner section payload.

    Sections missing meeting info are skipped to avoid silently creating
    schedules with unknown times.
    """
    meeting_times: List[MeetingTime] = []

    for faculty_block in section.get("meetingsFaculty", []):
        mt = (faculty_block or {}).get("meetingTime") or {}
        begin = mt.get("beginTime")
        end = mt.get("endTime")
        if not begin or not end:
            continue

        try:
            begin_minutes = hhmm_to_minutes(begin)
            end_minutes = hhmm_to_minutes(end)
        except ValueError:
            logger.debug("Skipping meeting with invalid time format: %s–%s", begin, end)
            continue

        if begin_minutes >= end_minutes:
            logger.debug("Skipping meeting with non-positive duration: %s–%s", begin, end)
            continue

        for day_index, key in enumerate(MEETING_KEYS):
            if mt.get(key):
                meeting_times.append(
                    MeetingTime(day=day_index, begin_time=begin_minutes, end_time=end_minutes)
                )

    return meeting_times


def compute_section_credits(section: dict) -> float:
    """Prefer section creditHours, otherwise fall back to meeting creditHourSession sum."""
    credits = _safe_float(section.get("creditHours"))
    if credits:
        return credits

    return float(
        sum(
            _safe_float((meeting or {}).get("meetingTime", {}).get("creditHourSession"))
            for meeting in section.get("meetingsFaculty", [])
        )
    )


def _clone_requirements_spec(spec: Dict[str, list[list[str]]]) -> Dict[str, list[list[str]]]:
    """Copy requirements spec to avoid caller mutation affecting internal state."""
    return {key: [list(group) for group in groups] for key, groups in spec.items()}


def _resolve_options(
    *,
    options: OptimizationOptions | None,
    requirements_spec: Dict[str, list[list[str]]] | None,
    hass_subject: str | None,
    max_schedules: int | None,
    scoring: ScoringWeights | None,
    min_seats_available: int | None,
    include_subjects: Sequence[str] | FrozenSet[str] | None,
    exclude_subjects: Sequence[str] | FrozenSet[str] | None,
    penalties: Sequence[Callable[[Iterable["Section"]], float]] | None,
) -> OptimizationOptions:
    base = options or OptimizationOptions()

    resolved_requirements = _clone_requirements_spec(requirements_spec or base.requirements_spec)
    resolved_include = (
        frozenset(include_subjects) if include_subjects is not None else base.include_subjects
    )
    resolved_exclude = (
        frozenset(exclude_subjects) if exclude_subjects is not None else base.exclude_subjects
    )
    resolved_penalties = tuple(penalties) if penalties is not None else base.penalties

    return OptimizationOptions(
        requirements_spec=resolved_requirements,
        hass_subject=hass_subject or base.hass_subject,
        max_schedules=max_schedules if max_schedules is not None else base.max_schedules,
        scoring=scoring or base.scoring,
        min_seats_available=min_seats_available if min_seats_available is not None else base.min_seats_available,
        include_subjects=resolved_include,
        exclude_subjects=resolved_exclude,
        penalties=resolved_penalties,
    )


@dataclass(slots=True)
class Course:
    subject_course: str
    title: str
    credits: float
    sections: List["Section"] = field(default_factory=list)

    def add_section(self, section: dict) -> None:
        meeting_times = extract_meeting_times(section)
        if not meeting_times:
            logger.debug(
                "Skipping section %s for %s due to missing meeting times",
                section.get("courseReferenceNumber"),
                self.subject_course,
            )
            return

        crn = str(section.get("courseReferenceNumber", "")).strip()
        self.sections.append(Section(meeting_times=meeting_times, course=self, crn=crn))

    def __repr__(self) -> str:
        return f"Course(course={self.subject_course}, title={self.title}, credits={self.credits})"


@dataclass(frozen=True, slots=True)
class Section:
    meeting_times: List[MeetingTime]
    course: Course
    crn: str

    def conflicts_with(self, other: "Section") -> bool:
        return any(mt1.overlaps_with(mt2) for mt1 in self.meeting_times for mt2 in other.meeting_times)

    def __repr__(self) -> str:
        return f"Section({self.crn}, times={self.meeting_times}, course={self.course.subject_course})"


@dataclass(slots=True)
class CourseRequirement:
    # Each inner list is a "group" (choose exactly one group per requirement).
    # A group is the set of courses that must be taken together.
    subject_course_groups: List[List[Course]]


@dataclass(slots=True)
class CourseCombo:
    courses: List[Course]

    def generate_section_combinations(self) -> List[List[Section]]:
        """
        Generate all possible combinations of sections for the courses in this combo,
        pruning time conflicts incrementally (much faster than post-filtering).
        """
        combos: List[List[Section]] = [[]]
        for course in self.courses:
            if not course.sections:
                return []  # no valid sections for this required course
            new_combos: List[List[Section]] = []
            for sect in course.sections:
                for combo in combos:
                    if all(not sect.conflicts_with(existing) for existing in combo):
                        new_combos.append(combo + [sect])
            combos = new_combos
            if not combos:
                return []  # early exit if no valid partial schedules remain
        return combos


def evaluate_schedule(
    schedule: Iterable[Section],
    weights: ScoringWeights,
    penalties: Sequence[Callable[[Iterable[Section]], float]] | None = None,
) -> float:
    """
    Returns a numeric score for how 'good' a schedule is. Higher is better.

    Factors:
    - Penalize classes before 10:00 or after 18:00
    - Reward 3–4 active days; penalize too many/few
    - Reward even distribution (low stdev of class counts across active days)
    - Penalize long idle gaps; small penalty for large daily spans
    """
    schedule = list(schedule)
    if not schedule:
        return float("-inf")

    score = 0.0
    days: List[List[tuple[int, int]]] = [[] for _ in range(5)]  # Mon..Fri

    # Early/late penalties + collect per-day windows
    for section in schedule:
        for mt in section.meeting_times:
            days[mt.day].append((mt.begin_time, mt.end_time))
            if mt.begin_time < weights.early_class_threshold:
                score -= (weights.early_class_threshold - mt.begin_time) * weights.early_late_penalty_per_min
            if mt.end_time > weights.late_class_threshold:
                score -= (mt.end_time - weights.late_class_threshold) * weights.early_late_penalty_per_min

    # Active days and distribution
    day_counts = [len(d) for d in days if d]
    active_days = len(day_counts)

    if weights.active_day_ideal_range[0] <= active_days <= weights.active_day_ideal_range[1]:
        score += weights.active_day_bonus
    else:
        score -= abs(active_days - weights.active_day_ideal_range[1]) * weights.active_day_penalty_per_day

    if len(day_counts) > 1:
        score -= stdev(day_counts) * weights.distribution_weight

    # Compactness (idle time) and span
    spans: List[int] = []
    for day_times in days:
        if not day_times:
            continue
        start = min(t[0] for t in day_times)
        end = max(t[1] for t in day_times)
        total_class_time = sum(t[1] - t[0] for t in day_times)
        idle_time = (end - start) - total_class_time
        spans.append(end - start)
        score -= idle_time * weights.idle_time_penalty

    if spans:
        score -= mean(spans) * weights.span_penalty

    for penalty in penalties or ():
        try:
            score += penalty(schedule)
        except Exception:  # pragma: no cover - defensive for external hooks
            logger.exception("Custom penalty function failed; ignoring.")

    return round(score, 2)


def optimize_courses(
    courses_data: Sequence[dict],
    *,
    options: OptimizationOptions | None = None,
    requirements_spec: Dict[str, list[list[str]]] | None = None,
    hass_subject: str | None = None,
    max_schedules: int | None = None,
    scoring: ScoringWeights | None = None,
    min_seats_available: int | None = None,
    include_subjects: Sequence[str] | FrozenSet[str] | None = None,
    exclude_subjects: Sequence[str] | FrozenSet[str] | None = None,
    penalties: Sequence[Callable[[Iterable["Section"]], float]] | None = None,
) -> Dict[str, dict]:
    """
    Build requirements, enumerate course/section combinations without conflicts,
    score schedules, and return the top N as JSON-serializable data.

    requirements_spec: mapping of requirement name -> list of course groups
    (each group is taken together); overrides OptimizationOptions if provided.
    hass_subject: subject code to treat as HASS/INQR electives.
    max_schedules: truncate results to the top N schedules by score.
    scoring: override scoring weights.
    min_seats_available: minimum seats to consider a section.
    include_subjects / exclude_subjects: optional subject filters.
    penalties: optional sequence of callables that return score deltas (negative for penalties).
    """
    opts = _resolve_options(
        options=options,
        requirements_spec=requirements_spec,
        hass_subject=hass_subject,
        max_schedules=max_schedules,
        scoring=scoring,
        min_seats_available=min_seats_available,
        include_subjects=include_subjects,
        exclude_subjects=exclude_subjects,
        penalties=penalties,
    )
    if opts.max_schedules <= 0:
        raise ValueError("max_schedules must be positive")

    # Prepare course containers for required + HASS/INQR
    hass_dict: Dict[str, Course] = {}
    courses_dict: Dict[str, Course | None] = {
        course_code: None
        for groups in opts.requirements_spec.values()
        for course_code in (c for group in groups for c in group)
    }

    # Build Course objects from sections with seats
    for section in courses_data:
        if section.get("seatsAvailable", 0) < opts.min_seats_available:
            continue

        subject_course = section.get("subjectCourse")
        subject = section.get("subject")
        title = section.get("courseTitle", "")
        credits = compute_section_credits(section)

        if opts.include_subjects and subject not in opts.include_subjects:
            continue
        if opts.exclude_subjects and subject in opts.exclude_subjects:
            continue

        if subject_course in courses_dict:
            if courses_dict[subject_course] is None:
                courses_dict[subject_course] = Course(
                    subject_course=subject_course, title=title, credits=credits
                )
            courses_dict[subject_course].add_section(section)

        if subject == opts.hass_subject:
            if subject_course not in hass_dict:
                hass_dict[subject_course] = Course(
                    subject_course=subject_course, title=title, credits=credits
                )
            hass_dict[subject_course].add_section(section)

    # Convert requirement specs into concrete CourseRequirement objects,
    # dropping groups where any course is missing or has no sections.
    requirements: Dict[str, CourseRequirement] = {}
    for name, groups in opts.requirements_spec.items():
        concrete_groups: List[List[Course]] = []
        for group in groups:
            concrete = []
            missing = False
            for code in group:
                course = courses_dict.get(code)
                if course is None or not course.sections:
                    missing = True
                    break
                concrete.append(course)
            if not missing:
                concrete_groups.append(concrete)
        # If no concrete groups remain, this requirement cannot be satisfied.
        if not concrete_groups:
            # Keep an empty requirement to ensure we produce zero schedules gracefully.
            concrete_groups = []
        requirements[name] = CourseRequirement(subject_course_groups=concrete_groups)

    # HASS/INQR electives: treat each available INQR course as its own group
    hass_groups = [[c] for c in hass_dict.values() if c.sections]
    requirements["hass_electives"] = CourseRequirement(subject_course_groups=hass_groups)

    # Build course combinations (choose one group per requirement)
    course_combinations: List[List[Course]] = [[]]
    for req in requirements.values():
        if not req.subject_course_groups:
            # Requirement not fulfillable -> zero schedules overall
            return {}
        new_combos: List[List[Course]] = []
        for group in req.subject_course_groups:
            for combo in course_combinations:
                new_combos.append(combo + group)
        course_combinations = new_combos

    course_combos = [CourseCombo(courses=c) for c in course_combinations]
    # print(f"Total combinations of courses to evaluate: {len(course_combos)}")

    # Generate all valid, non-conflicting schedules across sections
    valid_schedules: List[List[Section]] = []
    for combo in course_combos:
        valid_schedules.extend(combo.generate_section_combinations())
    # print(f"Total possible valid schedules: {len(valid_schedules)}")

    if not valid_schedules:
        return {}

    # Score and sort
    scored = [{"schedule": s, "score": evaluate_schedule(s, opts.scoring, opts.penalties)} for s in valid_schedules]
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Format output (top max_schedules)
    output: Dict[str, dict] = {}
    for i, entry in enumerate(scored[: opts.max_schedules], start=1):
        schedule = entry["schedule"]
        output[f"Schedule {i}"] = {
            "score": entry["score"],
            "sections": [
                {
                    "crn": sec.crn,
                    "subject_course": sec.course.subject_course,
                    "title": sec.course.title,
                    "meeting_times": [
                        {
                            "day": DAY_NAMES_LONG[mt.day],
                            "begin_time": minutes_to_hhmm(mt.begin_time),
                            "end_time": minutes_to_hhmm(mt.end_time),
                        }
                        for mt in sec.meeting_times
                    ],
                }
                for sec in schedule
            ],
        }
    return output


if __name__ == "__main__":
    here = Path(__file__).parent
    with open(here / "data" / "sis9_courses_202601.json", "r") as infile:
        courses_data = json.load(infile)

    optimized_data = optimize_courses(courses_data)

    with open(here / "courses_optimized.json", "w") as outfile:
        json.dump(optimized_data, outfile, indent=4)
