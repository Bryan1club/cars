# What club.py had that the MMBasic pages don't (yet)

Made 2026-09-25 by going through every club.py page's menus and actions
(`*_page.py` and club.py itself) against the MMBasic pages in `mmbasic/`.
Tick things off here as they're done.

## Everywhere (shared -- fix once in core.inc, every page gets it)

- [x] Keyboard control of every list (Up/Down, PgUp/PgDn, Enter) -- core ListNav, 2026-09-25
- [x] Mouse wheel + click-and-drag scrolling on every list -- core ListNav, 2026-09-25
- [x] HELP in every page's menu -- help.bas + help.txt (not the main menu or the editor yet)
- [ ] Login / lock screen (LoginPage) and USERS actually used to log in
- [ ] Screensaver (screensaver_page.py) with unlock
- [ ] Ticker items club.py had: last GPS fix, last file received, transfer status (weather + WiFi done)
- [ ] Board-to-board: each board broadcasts name + IP + GPS fix every 15 s; boards list each other
- [ ] Phone GPS web page (board serves /gps, phone sends its position) -- needs `OPTION TCP SERVER PORT 80`
- [ ] WiFi file upload server (club.py port 8080 POST /upload) -- TFTP does this job for now
- [~] Pages shipped without comments (20-25% smaller, error line numbers match the file). LIBRARY not used: LIBRARY SAVE is refused inside a program, so every core change would mean typing at each board.

## Page by page

| Page | club.py had | MMBasic has | Missing |
|---|---|---|---|
| MEMBERS | NEW SAVE CLEAR DELETE UPDATE; LINKS: CARS PHOTO EMAIL CLUB CARS; LIST: SEARCH REFRESH SHOW ALL CHECK IN; HELP | NEW SAVE CLEAR DELETE; LINKS: CARS PHOTO EMAIL; SEARCH, SHOW ALL | UPDATE (push to other boards), CLUB CARS link -- (CHECK IN, REFRESH, HELP done 2026-09-25) |
| CARS | ADD SAVE DELETE; LINKS: PHOTO, ECU SCAN; paging; HELP | NEW SAVE DELETE, SHOW PIC, SHOW ALL | ECU SCAN link, HELP |
| CLUB CARS | photo tiles of every car, open/rename/attach photo to a member | -- | **whole page** |
| EVENTS | new/save/delete, start/stop an event, who's attending, GPS for the event, import toggle, message attendees, show photo | list/form, attendance | import -- (GET GPS, SHOW/SET PHOTO, MESSAGE the ones who came: done 2026-09-25; START/STOP/WHO CAME were already there) |
| FINANCIAL | NEW SAVE DELETE; EXPORT CSV; EDIT CATEGORIES (add/rename/delete); category cycle | list/form, EXPORT CSV | **EDIT CATEGORIES**, category picker |
| PHOTOS | show, rename, delete, refresh, send to board, WiFi upload, source toggle (SD/USB), import toggle, "use" for member/car | SHOW PIC, RENAME, DELETE, REFRESH | send to board, WiFi upload -- (USB STICK source, USE FOR CAR, COPY TO SD done 2026-09-25) |
| MUSIC | play/pause/stop/next/prev, **playlists** (add/remove/save/load), audio setup, mode toggle | play/pause/resume/stop, list | audio setup -- (playlists done 2026-09-25; NEXT/PREV and play-on were already there) |
| GAMES | run, refresh, paging | run, list | (fine) |
| GPS | get fix, weather | get fix (reads NMEA itself), weather in ticker | phone GPS, fix sharing (see Everywhere) |
| EXPORT/IMPORT | export, import, email CSV, send to board, pick/delete CSV, toggle SD/USB, help | export/import | **email CSV**, send to board, delete CSV, USB toggle, HELP |
| EMAIL/TXT (mass) | send to all/ticked, edit message, edit SMS gateways | send to all/ticked, paid only, email/SMS | edit gateways (email-to-SMS carriers) |
| EMAIL MEMBER | one member: templates (save/load), attach a file/doc, HTML body, size, save as txt | -- | **whole page** |
| MAIL SETUP | email + SMS gateway, save, test | email + SMS gateway, save, test | (fine -- not yet tried for real) |
| WIFI | saved networks list, connect/disconnect, board name, forward list (add/delete), links to BT/music | status + scan | saved networks, connect (firmware refuses from a program), board name, forward list |
| USERS | save/delete/clear, paging | save/delete/clear | nothing uses it yet (no login) |
| UNIT NAME | name | name + town for weather | (fine) |
| FILE TRANSFER | import, delete, send to board, edit, refresh, drive toggle, target folder box | import (+ .pak unpack), edit, delete, drives, keys, wheel/drag | send to board, target folder box |
| CALCULATOR | full calculator, degrees/radians, modes | -- | **whole page** |
| HELP | help pages per page | -- | **whole page** |
| ECU SCAN | OBD scan, save, paging | -- | **whole page** (needs the K-line/CAN hardware) |
| 3D MODEL | the whole 3D editor | -- | **whole page** (biggest job by far) |
| BLUETOOTH PAIR / SPEAKER | BLE keyboard pairing, BT speaker | -- | not possible in MMBasic without firmware work (the owner: drop BLE; speaker = firmware job) |

## Suggested order

1. Shared pieces (keys/wheel/drag on every list, HELP, library + small pages) -- every page improves at once
2. The pages members will actually touch at a demo: MEMBERS (check in), EVENTS, PHOTOS, MUSIC playlists
3. Whole missing pages: EMAIL MEMBER, CLUB CARS, CALCULATOR, HELP
4. Networking: board-to-board sharing, phone GPS, send-to-board
5. Big ones: 3D MODEL, ECU SCAN
