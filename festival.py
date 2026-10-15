"""Music Festival Scheduler.

A SQLite database for a music festival (artists, stages, performances, visitors
and their favourite artists) with a scheduler that refuses double bookings:
a stage cannot host two shows at once, and an artist cannot be on two stages at once.
"""
import random
import sqlite3
from datetime import datetime
from pathlib import Path

DB_NAME = Path(__file__).resolve().parent / "music_festival.db"
TICKET_TYPES = ["Day Pass", "Weekend Pass", "VIP", "Backstage"]


# ------------------------------------------------------------------
# 1. Tables
# ------------------------------------------------------------------
def create_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Artists (
        artist_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        country TEXT NOT NULL,
        genre TEXT NOT NULL
    );""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Stages (
        stage_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        capacity INTEGER NOT NULL
    );""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Performances (
        performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        artist_id INTEGER NOT NULL,
        stage_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        duration INTEGER NOT NULL,
        FOREIGN KEY (artist_id) REFERENCES Artists(artist_id),
        FOREIGN KEY (stage_id) REFERENCES Stages(stage_id)
    );""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Visitors (
        visitor_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        ticket_type TEXT NOT NULL
    );""")

    # junction table (many-to-many: visitors <-> artists)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS FavoriteArtists (
        visitor_id INTEGER NOT NULL,
        artist_id INTEGER NOT NULL,
        PRIMARY KEY (visitor_id, artist_id),
        FOREIGN KEY (visitor_id) REFERENCES Visitors(visitor_id),
        FOREIGN KEY (artist_id) REFERENCES Artists(artist_id)
    );""")


# ------------------------------------------------------------------
# 2. Validation helpers
# ------------------------------------------------------------------
def to_minutes(hhmm):
    """'18:30' -> 1110 (minutes after midnight)."""
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def overlaps(start1, dur1, start2, dur2):
    """Two time slots overlap if each one starts before the other ends."""
    s1, s2 = to_minutes(start1), to_minutes(start2)
    return s1 < s2 + dur2 and s2 < s1 + dur1


def find_conflict(cur, artist_id, stage_id, date, start_time, duration):
    """Return an error text if the new performance clashes, else None."""
    cur.execute("""
        SELECT artist_id, stage_id, start_time, duration
        FROM Performances
        WHERE date = ? AND (artist_id = ? OR stage_id = ?);
    """, (date, artist_id, stage_id))

    for other_artist, other_stage, other_start, other_dur in cur.fetchall():
        if overlaps(start_time, duration, other_start, other_dur):
            if other_stage == stage_id:
                return f"stage {stage_id} is already busy at {other_start} on {date}"
            if other_artist == artist_id:
                return f"artist {artist_id} already performs at {other_start} on {date}"
    return None


def exists(cur, table, id_column, value):
    cur.execute(f"SELECT 1 FROM {table} WHERE {id_column} = ?;", (value,))
    return cur.fetchone() is not None


# ------------------------------------------------------------------
# 3. Add functions - return (True/False, message), never crash
# ------------------------------------------------------------------
def add_artist(cur, name, country, genre):
    if not name.strip() or not country.strip() or not genre.strip():
        return False, "Name, country and genre may not be empty."
    cur.execute("INSERT INTO Artists (name, country, genre) VALUES (?, ?, ?);",
                (name.strip(), country.strip(), genre.strip()))
    return True, f"Artist '{name}' added with id {cur.lastrowid}."


def add_stage(cur, name, capacity):
    if not name.strip():
        return False, "Stage name may not be empty."
    if not isinstance(capacity, int) or capacity <= 0:
        return False, "Capacity must be a positive whole number."
    cur.execute("INSERT INTO Stages (name, capacity) VALUES (?, ?);", (name.strip(), capacity))
    return True, f"Stage '{name}' added with id {cur.lastrowid}."


def add_visitor(cur, name, email, ticket_type):
    if not name.strip():
        return False, "Name may not be empty."
    if "@" not in email or "." not in email.split("@")[-1]:
        return False, "That is not a valid email address."
    if ticket_type not in TICKET_TYPES:
        return False, f"Ticket type must be one of: {', '.join(TICKET_TYPES)}."
    try:
        cur.execute("INSERT INTO Visitors (name, email, ticket_type) VALUES (?, ?, ?);",
                    (name.strip(), email.strip().lower(), ticket_type))
    except sqlite3.IntegrityError:
        return False, "A visitor with this email already exists."
    return True, f"Visitor '{name}' added with id {cur.lastrowid}."


def add_performance(cur, artist_id, stage_id, date, start_time, duration):
    if not exists(cur, "Artists", "artist_id", artist_id):
        return False, f"Artist {artist_id} does not exist."
    if not exists(cur, "Stages", "stage_id", stage_id):
        return False, f"Stage {stage_id} does not exist."
    try:
        datetime.strptime(date, "%Y-%m-%d")
        datetime.strptime(start_time, "%H:%M")
    except ValueError:
        return False, "Date must be YYYY-MM-DD and time HH:MM."
    if duration <= 0:
        return False, "Duration must be positive."
    if to_minutes(start_time) + duration > 24 * 60:
        return False, "A performance must end before midnight."

    conflict = find_conflict(cur, artist_id, stage_id, date, start_time, duration)
    if conflict:
        return False, "Not scheduled: " + conflict + "."

    cur.execute("""
        INSERT INTO Performances (artist_id, stage_id, date, start_time, duration)
        VALUES (?, ?, ?, ?, ?);
    """, (artist_id, stage_id, date, start_time, duration))
    return True, "Performance added."


# ------------------------------------------------------------------
# 4. Random test data
# ------------------------------------------------------------------
def populate_stages(cur):
    for name in ["Main Stage", "Forest Stage", "Electro Tent", "Acoustic Garden", "Sunset Arena"]:
        add_stage(cur, name, random.randint(500, 10000))


def populate_artists(cur):
    genres = ["Rock", "Pop", "Electronic", "Jazz", "Hip-Hop", "Classical", "Reggae"]
    countries = ["Ukraine", "Netherlands", "USA", "Germany", "France", "Spain", "UK"]
    for i in range(1, 26):
        add_artist(cur, f"Artist {i}", random.choice(countries), random.choice(genres))


def populate_visitors(cur):
    first_names = ["Anna", "Mark", "Olena", "Dmytro", "Sofia", "Lucas", "Emma", "Noah", "Mia", "Liam"]
    last_names = ["Smith", "Johnson", "Kovalenko", "Brown", "Taylor", "Petrov", "Garcia", "Muller"]
    for i in range(1, 101):
        first, last = random.choice(first_names), random.choice(last_names)
        add_visitor(cur, f"{first} {last}", f"{first.lower()}.{last.lower()}{i}@gmail.com",
                    random.choice(TICKET_TYPES))


def populate_performances(cur, wanted=40):
    """Random performances, but only VALID ones are stored."""
    artist_ids = [row[0] for row in cur.execute("SELECT artist_id FROM Artists;").fetchall()]
    stage_ids = [row[0] for row in cur.execute("SELECT stage_id FROM Stages;").fetchall()]
    dates = ["2026-07-10", "2026-07-11", "2026-07-12"]
    start_times = ["14:00", "16:00", "18:00", "20:00", "22:00"]

    added, attempts = 0, 0
    while added < wanted and attempts < 1000:  # limit -> no endless loop
        attempts += 1
        ok, _ = add_performance(cur, random.choice(artist_ids), random.choice(stage_ids),
                                random.choice(dates), random.choice(start_times),
                                random.randint(30, 90))
        if ok:
            added += 1
    print(f"{added} performances scheduled ({attempts - added} random clashes rejected).")


def populate_favorites(cur):
    visitor_ids = [row[0] for row in cur.execute("SELECT visitor_id FROM Visitors;").fetchall()]
    artist_ids = [row[0] for row in cur.execute("SELECT artist_id FROM Artists;").fetchall()]
    rows = []
    for visitor_id in visitor_ids:
        for artist_id in random.sample(artist_ids, random.randint(1, 5)):  # no repeats
            rows.append((visitor_id, artist_id))
    cur.executemany("INSERT INTO FavoriteArtists (visitor_id, artist_id) VALUES (?, ?);", rows)


# ------------------------------------------------------------------
# 5. Check the whole schedule (proof that the data is valid)
# ------------------------------------------------------------------
def verify_schedule(cur):
    rows = cur.execute("""
        SELECT performance_id, artist_id, stage_id, date, start_time, duration
        FROM Performances;
    """).fetchall()

    problems = 0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):          # every pair once
            a, b = rows[i], rows[j]
            if a[3] == b[3] and overlaps(a[4], a[5], b[4], b[5]):
                if a[2] == b[2]:
                    print(f"  Stage clash: performances {a[0]} and {b[0]}")
                    problems += 1
                if a[1] == b[1]:
                    print(f"  Artist clash: performances {a[0]} and {b[0]}")
                    problems += 1

    if problems == 0:
        print(f"Schedule is valid: {len(rows)} performances, no overlaps.")
    else:
        print(f"{problems} problem(s) found.")


# ------------------------------------------------------------------
# 6. Menu (wrong input never crashes the program)
# ------------------------------------------------------------------
def ask_int(text):
    answer = input(text).strip()
    if answer.isdigit():
        return int(answer)
    print("Please enter a whole number.")
    return None


def menu(conn, cur):
    while True:
        print("\n1) Add artist  2) Add stage  3) Add visitor  4) Add performance  "
              "5) Verify schedule  6) Quit")
        choice = input("Choice: ").strip()

        result = None
        if choice == "1":
            result = add_artist(cur, input("Name: "), input("Country: "), input("Genre: "))
        elif choice == "2":
            name = input("Stage name: ")
            capacity = ask_int("Capacity: ")
            if capacity is not None:
                result = add_stage(cur, name, capacity)
        elif choice == "3":
            print("Ticket types:", ", ".join(TICKET_TYPES))
            result = add_visitor(cur, input("Name: "), input("Email: "), input("Ticket type: "))
        elif choice == "4":
            artist_id = ask_int("Artist id: ")
            stage_id = ask_int("Stage id: ")
            date = input("Date (YYYY-MM-DD): ").strip()
            start_time = input("Start time (HH:MM): ").strip()
            duration = ask_int("Duration in minutes: ")
            if None not in (artist_id, stage_id, duration):
                result = add_performance(cur, artist_id, stage_id, date, start_time, duration)
        elif choice == "5":
            verify_schedule(cur)
        elif choice == "6":
            break
        else:
            print("Invalid choice.")

        if result is not None:
            ok, message = result
            print(message)
            if ok:
                conn.commit()  # save only successful changes


def main():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")  # SQLite does not check FKs without this
    create_tables(cur)

    # fill with test data only the first time -> running again makes no duplicates
    if cur.execute("SELECT COUNT(*) FROM Stages;").fetchone()[0] == 0:
        populate_stages(cur)
        populate_artists(cur)
        populate_visitors(cur)
        populate_performances(cur)
        populate_favorites(cur)
        conn.commit()
        print(f"{DB_NAME.name} created and filled with test data.")
    else:
        print(f"{DB_NAME.name} already has data, nothing generated.")

    try:
        menu(conn, cur)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
