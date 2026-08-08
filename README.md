# Car Club System

MicroPython app for a Pico Computer 3, used to manage car club member
records and run event check-ins on a board. Can run standalone or join
WiFi to sync its clock, send emails, and forward uploads to other
boards.

## Files

- **main.py** — runs at boot. Starts the board as its own WiFi access
  point, tries to join a home/venue network to sync the clock, then
  launches `club.py`. **Fill in your own AP/WiFi credentials before
  deploying** — the placeholders in this repo are not real ones.
- **club.py** — the app itself. SQLite-backed (`/sd/club.db`), with
  pages for members, their cars, events (create, start/stop, check
  members in, see who attended), WiFi setup, email, and forwarding
  uploads to other boards.
- **menu.py**, **members.py** — an earlier, simpler version of this
  system (standalone member editor + tool launcher). Not used by
  `main.py` / `club.py` anymore; kept here for reference.

Roles and membership statuses are configurable per-board via
`/sd/roles.txt` and `/sd/status.txt` (one value per line, `-` for a
blank entry); both files are created with sensible defaults on first
run if missing.

## Running

Copy `main.py` and `club.py` onto the board's SD card, fill in your
own WiFi credentials in `main.py`, and it runs automatically at boot.

## A note on syncing from the board

The board's SD card mixes code with live data — member records
(`club.db`), saved WiFi passwords (`wifi.txt`), exported CSVs, member
photos, and upload logs. None of that belongs in this repo. Only copy
`.py` files across deliberately, and check them for hardcoded secrets
or personal details first (see `.gitignore` for what's excluded).
