# Car Club System

MicroPython app for a Pico Computer 3, used to manage car club member
records and run event check-ins on a single board (no networking).

## Files

- **club.py** — main app. SQLite-backed (`/sd/club.db`), with pages for
  the menu, member records, member cars, and events (create an event,
  start/stop it, check members in, see who's attended).
- **members.py** — standalone member record editor. Stores each member
  as a JSON file under `/sd/members/`. Simpler than `club.py` and does
  not handle cars or events.
- **menu.py** — launcher screen listing tools (`club.py`, `members.py`,
  plus `import.py`, `export.py`, `upload.py`, `settings.py`, which
  aren't present in this repo yet) and dimming any that aren't
  installed on the board.

Roles and membership statuses are configurable per-board via
`/sd/roles.txt` and `/sd/status.txt` (one value per line, `-` for a
blank entry); both files are created with sensible defaults on first
run if missing.

## Running

Copy the script you want as `/main.py` on the board so it runs at
boot, or run it directly from the MicroPython REPL.
