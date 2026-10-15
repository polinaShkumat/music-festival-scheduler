"""Tests for the scheduling rules, using a fresh in-memory database for every test."""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import festival as fest


@pytest.fixture
def cur():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    fest.create_tables(cursor)
    fest.add_artist(cursor, "Artist A", "Ukraine", "Rock")   # id 1
    fest.add_artist(cursor, "Artist B", "Netherlands", "Pop")  # id 2
    fest.add_stage(cursor, "Main Stage", 5000)                 # id 1
    fest.add_stage(cursor, "Forest Stage", 800)                # id 2
    fest.add_performance(cursor, 1, 1, "2026-07-10", "18:00", 60)  # 18:00-19:00
    yield cursor
    conn.close()


@pytest.mark.parametrize("start1, dur1, start2, dur2, expected", [
    ("18:00", 60, "18:30", 60, True),    # partly overlapping
    ("18:00", 60, "18:15", 15, True),    # one inside the other
    ("18:00", 60, "19:00", 60, False),   # back to back is allowed
    ("18:00", 60, "20:00", 30, False),   # clearly apart
])
def test_overlaps(start1, dur1, start2, dur2, expected):
    assert fest.overlaps(start1, dur1, start2, dur2) == expected


def test_same_stage_same_time_is_rejected(cur):
    ok, message = fest.add_performance(cur, 2, 1, "2026-07-10", "18:30", 60)
    assert not ok and "stage 1 is already busy" in message


def test_same_artist_on_two_stages_is_rejected(cur):
    ok, message = fest.add_performance(cur, 1, 2, "2026-07-10", "18:30", 60)
    assert not ok and "artist 1 already performs" in message


def test_other_stage_other_artist_is_allowed(cur):
    ok, _ = fest.add_performance(cur, 2, 2, "2026-07-10", "18:30", 60)
    assert ok


def test_same_slot_on_another_day_is_allowed(cur):
    ok, _ = fest.add_performance(cur, 1, 1, "2026-07-11", "18:00", 60)
    assert ok


@pytest.mark.parametrize("artist, stage, date, start, duration", [
    (99, 1, "2026-07-10", "12:00", 30),       # artist does not exist
    (1, 99, "2026-07-10", "12:00", 30),       # stage does not exist
    (1, 1, "10-07-2026", "12:00", 30),        # wrong date format
    (1, 1, "2026-07-10", "25:00", 30),        # impossible time
    (1, 1, "2026-07-10", "12:00", 0),         # zero duration
    (1, 1, "2026-07-10", "23:30", 60),        # ends after midnight
])
def test_invalid_performances_are_rejected(cur, artist, stage, date, start, duration):
    ok, _ = fest.add_performance(cur, artist, stage, date, start, duration)
    assert not ok


def test_duplicate_visitor_email_is_rejected(cur):
    assert fest.add_visitor(cur, "Anna", "anna@example.com", "VIP")[0]
    ok, message = fest.add_visitor(cur, "Anna 2", "ANNA@example.com", "VIP")
    assert not ok and "already exists" in message


def test_unknown_ticket_type_is_rejected(cur):
    ok, _ = fest.add_visitor(cur, "Bob", "bob@example.com", "Golden Ticket")
    assert not ok
