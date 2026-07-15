"""Public application boundary for essay rendering and derived feeds."""

from backend.ssg import (
    calculate_read_time,
    generate_feeds,
    parse_date,
    sync_essay_html,
)


class EssayWorkflow:
    """Expose SSG capabilities without leaking private helpers into routes."""

    def __init__(self, sync_essay, generate_feeds, parse_date, calculate_read_time):
        self._sync_essay = sync_essay
        self._generate_feeds = generate_feeds
        self._parse_date = parse_date
        self._calculate_read_time = calculate_read_time

    def format_date(self, value, include_time=False):
        return self._parse_date(value, include_time=include_time)

    def read_time(self, value):
        return self._calculate_read_time(value)

    def sync(self, essay, raw_md_memory=None, essays=None):
        return self._sync_essay(
            essay,
            raw_md_memory=raw_md_memory,
            essays=essays,
        )

    def regenerate_feeds(self):
        return self._generate_feeds()


ESSAY_WORKFLOW = EssayWorkflow(
    sync_essay=sync_essay_html,
    generate_feeds=generate_feeds,
    parse_date=parse_date,
    calculate_read_time=calculate_read_time,
)
