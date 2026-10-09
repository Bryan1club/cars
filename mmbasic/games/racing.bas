' racing.bas -- CIRCUIT RACE, ported from club.py's assets/games/racing.py.
' A spectator/betting game: named players (hot-seat) each buy or pick one of
' five cars, pay the entry fee into the event pot, then every car runs a
' qualifying lap on its own (fastest gets pole), then they race. Pace is
' random and re-rolled every lap, damaged cars run slower. On track, a car
' boxed in with nowhere to pass can clip the one in front -- a scrape that
' costs a little damage and pace, or, if it was catching up fast, a real
' crash: heavy damage, a spin that costs it ground, and if that tips it
' past 80% damage mid-race it retires on the spot (see CarContact). After
' each race every entrant rolls a random cost event (tune-up, engine trouble, crash)
' that costs a share of the car's value and adds to its damage. An event is
' EVENT_RACES races; at the end the pot is split between the players who won
' a race -- two wins needed by anyone whose budget fell during the event.
'
' Menu bar: RACE (ENTER PLAYER / START RACE / NEW EVENT), LAPS (1-10),
' RACES (races per event, 1-10, set before the event's first race),
' GARAGE: VISIT (the mechanic's report on your car), REPAIR, HOT LAP,
' SELL CAR, CAR LIST. HOT LAP / REPAIR: a car at 80% damage or more can't race;
' its owner runs a solo hot lap against a target time for prize money,
' once per car between races, and pays the mechanic to REPAIR it,
' OWNERS (who owns which car, its damage and the mechanic's word), QUIT.
' Every player picks a team colour when they join. The pit garage scene
' (PitScene, art from games/gen_pitart.py) shows the player as a driver in
' their team's race suit, their car, and the mechanic in the team's colours:
' he talks, the driver answers, the words type out in speech bubbles while
' their mouths move, and they blink now and then. It plays when a player
' joins, before every race (how each car's running -- never who'll win,
' the race is random) and, after it, for each car that needs work.
' Players and cars are kept in B:/Games (racing_players.dat,
' racing_cars.dat -- "name,budget,team colour" / "owner,damage" lines; the
' colour is new, club.py's two-field lines read as team RED).
'
' The track is drawn once into framebuffer F; each tick the few pixels
' behind every car are copied back from F, so the road is never damaged.
'
' Stand-alone: one file, runs on any Pico Computer 3 (RP2350, MODE 3 + MAP)
' with or without the club -- the club pointer and weather are used if
' they're there, and it keeps its save files next to itself. It always
' draws in the board's built-in font, not the club's #9/#10 (members found
' that italic font hard to read on the race/garage screens).
' Build with: python mmbasic/build.py  (writes ../games/racing.bas, which
' goes in the SD card's Games folder)
' The quote bank (QuoteBank/Quote$/FillIn$) lives in racing_quotes.bas and
' the pit-garage presentation layer (DrawBay/Scene/PitScene/Talk/Blink/
' ArtAt and all its art DATA) in racing_ui.bas, not here -- the game's own
' code plus either no longer fits in the board's 128K program space, let
' alone both. LIBRARY LOAD, RAM must be the very first statement (no
' Option/Dim/Const before it -- MMBasic restarts the program to run the
' library's top level first) and puts them in a PSRAM-backed RAM library
' slot, not flash: it shadows whatever's flash-saved (the club's font
' library) without touching it, and none of it survives once this game
' exits or another program RUNs -- so nobody else's board session is ever
' affected by it. Several files here become ONE library (concatenated in
' the order given), which is how two unrelated halves (quotes, art) stay
' in their own source files instead of one growing blob
LIBRARY LOAD "B:/Games/racing_quotes.bas", "B:/Games/racing_ui.bas", RAM

Option EXPLICIT
Option DEFAULT NONE

' the players' and cars' files live next to the game itself, wherever
' it's run from (B:/Games on a club board)
Dim string gameDir$, PLAYERS_FILE$, CARS_FILE$
Const ENTRY_FEE = 200, STARTING_BUDGET = 20000, MAXPL = 20
' the garage: how many car models, and the most that can be in one race
Const NCARS = 30
' the event podium bonus (3+ race events only), on top of the normal pot
Const POD_CASH1 = 30000, POD_CASH2 = 15000, POD_CASH3 = 10000
' races in an event (the RACES menu; set before an event's first race).
' One race is the norm; RACES makes it a series
Dim integer EVENT_RACES = 1
Const NRAW = 50, NWP = 100, TRACK_W = 48, RACE_MS = 60
' BuildTrack fits the raw circuit (RAWW x RAWH, gen_tracks.py's BOX) to
' fill however much of the track band this board actually has, margin
' aside. Declared up here with the other top-level Consts, not down by
' BuildTrack: a Const only exists once the program's top-level flow has
' executed the line declaring it, and BuildTrack is CALLED (further down,
' during setup) before that flow would otherwise reach a Const sitting
' right next to the Sub itself -- "not declared" at runtime, not a typo
Const RAWW = 520, RAWH = 333, TRACK_MARGIN = 28
' the ticker's weather: refreshed every WX_EVERY once the game's running,
' but the "(near X)" place is only worth saying for the first WX_PLACE_MS
' -- after that it's dropped from weather.txt so the ticker just shows
' the weather itself, not where it's for, every time round
Const WX_EVERY = 60000, WX_PLACE_MS = 180000
Dim integer lastWx, wxStartT
' the circuit (TRACK menu; the layouts are games/gen_tracks.py's Tracks)
Dim integer trackNo, nTracks
Dim string tName$
' Q$'s fill-ins (qN$/qC$/qD$/qM$/qT$/qX$/qE$/qP$), qLast and qSaid are all
' declared in racing_quotes.bas now -- the LIBRARY LOAD above runs that
' before this line, so they already exist by the time anything here needs them
' gaps sized for the top-down cars (about 18 long, 11 wide). LAT_LIMIT is
' wide enough for 3 side by side on the road now (TRACK_W/2 minus half a
' car), not just 2 -- with 30-car fields a bunch of 3+ at the same pace
' is common, and only 2 lanes meant a 3rd car was always "boxed in" with
' nowhere to go (see the collision-damage branch in RaceTick/QualifyTick)
Const LAT_LIMIT = 16, LAT_DRIFT = 0.5, MIN_PROG_GAP = 20, MIN_LAT_GAP = 12, GRID_GAP = 22
Const SAND_R = 12
' collision physics (RaceTick's CarContact, boxed-in cars with nowhere to
' go). Severity scales with closing speed -- the gap between the two
' cars' current RandSpeed pace, which runs about 0.99 (100% damage, the
' cheapest car) to 2.92 (undamaged, priciest car, lucky roll) -- see
' PriceFactor. COLLIDE_* is the everyday scrape: chance rises
' with closing speed up to COLLIDE_CHANCE_MAX, capped so a huge field
' isn't pinging every tick. CRASH_SPD is the closing speed a hit has to
' clear before it can be a real crash rather than paint; CRASH_CHANCE_K
' scales how likely that is once past it. A crash costs a lot more
' damage and a real chunk of progress (a spin), not just next lap's pace
Const COLLIDE_BASE = 0.08, COLLIDE_SPD_K = 0.25, COLLIDE_CHANCE_MAX = 0.35
Const CRASH_SPD = 0.5, CRASH_CHANCE_K = 0.3, CRASH_DMG_MIN = 8, CRASH_DMG_RANGE = 8
Const BUMP_SPD_CUT = 0.9, CRASH_SPD_CUT = 0.55, CRASH_SPIN_TICKS = 20
' the game's own colour slots (the page greys it borrows aren't on show here)
Const S_GRASS = 7, S_ROAD = 8, S_PURPLE = 9, S_SAND = 11, S_BLUE = 12

Dim float wx(NWP), wy(NWP), cum(NWP), trackLen, rx(NRAW - 1), ry(NRAW - 1)
' CT/CB: the track area, between the menu bar + status line and the ticker
Dim integer sandX(3), sandY(3), carCol(NCARS - 1), CT, CB
' the 8 distinct liveries carCol cycles through once there are more cars
' than colours to give them (see where it's filled, below)
Dim integer carCycle(7)
' true once the one-off welcome/how-to-start message has been shown
Dim integer introDone
Dim string carName$(NCARS - 1), pn$(MAXPL - 1), owner$(NCARS - 1)
Dim float carVal(NCARS - 1), pb(MAXPL - 1), dmg(NCARS - 1)
' the cheapest/priciest car in the lineup (set once from CarData at boot)
' -- see PriceFactor
Dim float carMinVal, carMaxVal
' each player's own two-colour pick (a MAP slot each, from ColourSlot$/
' TeamColours -- see the DESIGN step in EnterPlayer): tmMain/tmShade for
' whichever driver is in the scene right now. The mechanic is his own guy,
' not the driver's twin -- fixed navy overalls, mechMain/mechShade, never
' changed by who's visiting
Const NTEAM = 7
Dim integer pMain(MAXPL - 1), pShade(MAXPL - 1)
' tmMain/tmShade (the current pit-scene team colour), drvOff, mechMain/
' mechShade, cMain/cShade, psMX/psMY/psDX/psDY and nextBlink all moved to
' racing_ui.bas with the Scene/PitScene/Talk/Blink/ArtAt they belong to
Dim integer np, lapsToWin, j, v
Dim string cmd$, statusMsg$
' this race: entrants (player, car), each car's state
Dim integer ne, ep(NCARS - 1), ec(NCARS - 1), laps(NCARS - 1), fin(NCARS - 1), place(NCARS - 1), nfin, lastX(NCARS - 1), lastY(NCARS - 1), shown(NCARS - 1)
' whether an entrant already had their condition covered when they
' joined this race via EnterPlayer (always true -- WELCOME for a new
' player, whose car is always fresh, or the damage-aware PRE_ chat
' itself for a returning one), so BeginRace's own PRE_ chat right before
' the race has nothing left to add and skips them. Used by its "new
' player" Scene pick too, hence the name
Dim integer wasNew(NCARS - 1)
Dim float prog(NCARS - 1), lat(NCARS - 1), spd(NCARS - 1)
' how fast each car is drifting sideways (it weaves smoothly, not jitters)
Dim float latV(NCARS - 1)
' hot lap: ticks so far, the target, the lap's pace roll, and which cars
' have had their hot lap since the last race
Const HOT_PAR = 2.2, TOO_DAMAGED = 80, Q_STAGGER = 14
Dim integer hotTicks, hotPar, hotDone(NCARS - 1), carDX, carDY
' when the garage home screen (phase 0) next redraws itself just to give
' the idling mechanic a fresh line -- set at the end of DrawGarage itself
Dim integer nextIdleChat
' the mechanic's mouth position in the last DrawGarage, for IdleChat to
' anchor a fresh bubble on without redrawing him to find it again
Dim integer garageBubbleX, garageBubbleY
' set around AutoJoinSaved's boot-time loop: every saved member who
' already owns one car and can afford the entry races straight away
' instead of everyone having to be re-entered by hand each session --
' JoinRace does the real work (car ownership, entry fee, the pot) exactly
' as it would for a manual join, this just skips its mechanic dialogue so
' a whole club's worth of returning drivers doesn't mean a whole club's
' worth of 8-second waits before anyone can race
Dim integer bulkJoin
' set around a run of several Scene() calls in a row (RaceOver's damage
' reports, ShowPodium's placings): PitScene (racing_ui.bas) checks this
' before its own ShowTrack, which normally restores the track view once a
' scene's done -- but back to back that was just a flash of the track
' between every single one, immediately covered by the next scene's own
' full-screen backdrop. The caller chaining them is responsible for
' whatever's shown once the whole run's over instead (it always was, via
' BeginRace/NewRace) -- this just skips the pointless flashes in between.
' Declared here, not in racing_ui.bas: a library can read or write a
' variable the main program declares, but not the other way round
Dim integer sceneChaining
' the hot-lap car: its own, so the race entries stay as they are
Dim integer hotCar, hotPl, hotX, hotY, hotShown
Dim float hotProg
Dim float hotRoll
Dim integer phase, qIdx, qStart, qTime(NCARS - 1), lastMove
' qualifying: every car's flying lap at once -- ticks so far, who's done
Dim integer qTicks, qDone(NCARS - 1)
' whether a car's time is already on the live qualifying panel, its grid
' rank once qualifying's done, and when phase 5 (grid shown, race pending)
' started
Dim integer qShown(NCARS - 1), qRank(NCARS - 1), gridT0
' the event: race number, pot, wins and starting budget per player
Dim integer raceNum, wins(MAXPL - 1)
Dim float pot, startB(MAXPL - 1)
' _locate's results
Dim integer lSeg
Dim float lT
' the garage home screen's buttons (drawn only while phase = 0): PLAYERS
' and RACE are filing cabinets (upper-left/right), GARAGE a tool bench
' (upper middle). gBtn0 is the first drawer's button index (the rest
' follow in fixed order); gGX/gGY/gGW each group's frame (top-left
' corner and width); gDrawerH/Gap the cabinets' stacked drawers;
' gBenchH the bench's own (much shorter) height
Dim integer gBtn0, gGX(2), gGY(2), gGW(2), gDrawerH, gDrawerGap, gBenchH
Dim integer gPick
' the live corner panel (qualifying times / race places / hot lap clock):
' its top-left, draggable clear of the action, and drag state
Const PANEL_W = 150
' the fake-3D offset for the garage's cabinet boxes (top face + side sliver)
Const CAB_DX = 6, CAB_DY = -8
Dim integer panelX, panelY, pDragging, panelDX, panelDY
' when the race ticker (running order + gaps) last updated, and which
' place it's currently showing (one at a time -- see RaceTicker)
Dim integer raceTickerT0, raceRankIdx
' same idea for QualPanel's ticker segment -- which qualifying time it's
' currently showing, and when it last rotated to the next one
Dim integer qualTickerT0, qualRotIdx
' the garage's entrant ticker: one entrant at a time rather than trying
' to fit them all on the line at once (see EntrantsTicker) -- which one
' is showing, when it last moved on to the next, and how many were
' entered last time it ran (so a join/leave refreshes it immediately
' instead of waiting out the rotation)
Dim integer entIdx, entT0, entLastNe
' where the panel was last drawn (0 height = never), so moving it can
' restore the track underneath instead of leaving a trail behind it
Dim integer panelLastX, panelLastY, panelLastH

gameDir$ = MM.Info(PATH)
If gameDir$ = "" Or Instr(gameDir$, "/") = 0 Then gameDir$ = "B:/Games/"
If Right$(gameDir$, 1) <> "/" Then gameDir$ = gameDir$ + "/"
PLAYERS_FILE$ = gameDir$ + "racing_players.dat"
CARS_FILE$ = gameDir$ + "racing_cars.dat"
' always the board's built-in font 1, never the club's #9/#10 -- ReadWidths
' (run by CoreInit) loads those when they're in the library, but members
' found them hard to read on this game's race/garage screens
forceBuiltinFont = 1
CoreInit
SetGamePalette
' every action lives as a button on the garage home screen now, not a
' menu bar -- QUIT's gone too (Esc still quits, via PollInput's own -2),
' so the scene gets the full page instead of a reserved top strip
DrawPageOn "CIRCUIT RACE", ""
TickerAt W \ 40, H - fh(0) - 10 - W \ 80, W - W \ 20
CB = H - fh(0) - 14 - W \ 80
CT = W \ 40
AddGarageButtons
wxStartT = Timer
' left out for now -- see FetchWeather's own comment: WEB Open TCP
' Client's no-timeout connect caused real board hangs/reboots during
' testing 2026-09-28, even called just once at start-up. Call it here
' again once that's sorted out (mmbasic_web_tcp_client_no_timeout memory)
' no date/time/weather/wifi at all, entering drivers or racing -- the
' ticker's for the task at hand (who's entered, the running order),
' never on for this game
tickerRaceMode = 1
StartCursor
Restore CarData
For j = 0 To NCARS - 1
  Read carName$(j), carVal(j)
Next
' the cheapest and priciest car in the lineup, whatever they happen to be
' -- PriceFactor scales pace between them, so this stays right even if
' the lineup (CarData) ever changes
carMinVal = carVal(0)
carMaxVal = carVal(0)
For j = 1 To NCARS - 1
  carMinVal = Min(carMinVal, carVal(j))
  carMaxVal = Max(carMaxVal, carVal(j))
Next
carCycle(0) = MAP(5) : carCycle(1) = MAP(S_BLUE) : carCycle(2) = MAP(3) : carCycle(3) = MAP(1)
carCycle(4) = MAP(S_PURPLE) : carCycle(5) = MAP(15) : carCycle(6) = MAP(2) : carCycle(7) = MAP(4)
' 8 distinct liveries don't stretch to NCARS cars, so they cycle -- no two
' adjacent in the garage list share one, and it matches CarColours' own
' repeating cycle below
For j = 0 To NCARS - 1
  carCol(j) = carCycle(j Mod 8)
Next j
BuildTrack
LoadPlayers
LoadCars
' one lap is the normal race (LAPS for longer ones)
lapsToWin = 1
' the track's framebuffer first: NewRace shows the track (ShowTrack
' copies it from F), so F has to exist before it -- the other way round was
' the "Same framebuffer" error at start-up. A crash earlier (this file has
' no catch-all handler) can leave F allocated from a previous run without
' ever reaching Quit's FRAMEBUFFER CLOSE, so close any stale one first --
' both guarded, since neither call is an error the second time round
On Error Skip
FRAMEBUFFER CLOSE
On Error Skip
FRAMEBUFFER CREATE
' a second, independent buffer (RP2350 only): a snapshot of the idle
' garage screen (bay/mechanic/cabinets/buttons, no speech bubble) so the
' mechanic's line can be refreshed there without redrawing any of that --
' a full DrawGarage while a button click was landing made choosing an
' option hit-and-miss. F can't do this job too: it's the current race
' track's own saved image and has to survive untouched between races
On Error Skip
FRAMEBUFFER CREATE 2
DrawTrack
NewEvent
NewRace
AutoJoinSaved
Status Choice(ne > 0, Str$(ne) + " driver" + Choice(ne = 1, "", "s") + " ready - START RACE when you are", "ENTER PLAYER to join, then START RACE")

Do
  j = PollInput()
  EntrantsTicker
  HidePlaceAfter3Min
  ' idle on the garage home screen: IdleChat gives the mechanic a fresh
  ' line without redrawing any of the rest of the screen (a full
  ' DrawGarage here once made choosing an option hit-and-miss -- see its
  ' own comment for why this is safe where that wasn't)
  If phase = 0 And Timer > nextIdleChat Then IdleChat
  If j = -2 Then Quit
  cmd$ = Command$(j)
  ' a garage drawer rolls out and opens before its action runs
  If j >= gBtn0 And phase = 0 Then DrawerOpen j
  Select Case cmd$
    Case "QUIT"
      Quit
    Case "ENTER PLAYER"
      EnterPlayer
    Case "LEAVE"
      LeavePlayer
    Case "START RACE"
      StartRace
    Case "HOT LAP"
      HotLap
    Case "REPAIR"
      Repair
    Case "TRACK"
      ChooseTrack
    Case "CAR LIST"
      Owners
    Case "DRIVERS"
      Drivers
    Case "VISIT"
      Visit
    Case "SELL CAR"
      SellCar
    Case "LAPS"
      If phase = 1 Or phase = 2 Or phase = 5 Then
        Status "Laps are locked in once a race is running"
      Else
        ' PickList already redraws the garage once, underneath it, as it
        ' closes -- a second ShowTrack here was just the same redraw done
        ' twice for nothing
        gPick = PickList("LAPS PER RACE", "1 LAP|2 LAPS|3 LAPS|5 LAPS|8 LAPS|10 LAPS")
        If gPick >= 0 Then
          lapsToWin = Val(Field$("1|2|3|5|8|10", gPick + 1, "|"))
          Status "Races are " + Str$(lapsToWin) + " lap" + Choice(lapsToWin = 1, "", "s") + " each"
          RaceInfoTicker
        EndIf
      EndIf
    Case "RACES"
      ' the event's length: only before its first race has started
      If phase = 1 Or phase = 2 Or phase = 5 Or raceNum > 1 Then
        Status "This event is " + Str$(EVENT_RACES) + " races - set for the next one once this one's done"
      Else
        ' PickList already redraws the garage once, underneath it, as it
        ' closes -- a second ShowTrack here was just the same redraw done
        ' twice for nothing
        gPick = PickList("RACES PER EVENT", "1 RACE|3 RACES|5 RACES|8 RACES|10 RACES")
        If gPick >= 0 Then
          EVENT_RACES = Val(Field$("1|3|5|8|10", gPick + 1, "|"))
          Status "Events are " + Str$(EVENT_RACES) + " race" + Choice(EVENT_RACES = 1, "", "s") + " - race 1 of " + Str$(EVENT_RACES)
          RaceInfoTicker
        EndIf
      EndIf
    Case ""
  End Select
  If Timer - lastMove >= RACE_MS Then
    lastMove = Timer
    If phase = 1 Then QualifyTick
    If phase = 2 Then RaceTick
    If phase = 4 Then HotTick
    If phase = 5 Then GridTick
  EndIf
  Pause 2
Loop

CarData:
Data "HOLDEN", 4000, "FORD", 6000, "HONDA", 9000, "SUBARU", 13000, "TOYOTA", 18000
Data "NISSAN", 7000, "HYUNDAI", 11500, "MAZDA", 16000
Data "KIA", 5000, "SUZUKI", 5500, "MITSUBISHI", 8000, "RENAULT", 8500
Data "PEUGEOT", 10000, "SKODA", 12000, "VOLKSWAGEN", 14000, "VOLVO", 22000
Data "AUDI", 32000, "BMW", 35000, "MERCEDES", 40000, "PORSCHE", 60000
Data "DAIHATSU", 4500, "CHERY", 5200, "ISUZU", 6500, "MG", 7500, "FIAT", 9500
Data "CITROEN", 11000, "JEEP", 17000, "JAGUAR", 38000, "LAND ROVER", 45000, "FERRARI", 90000

TrackCredit:
Data "Circuit layouts: github.com/bacinger/f1-circuits, MIT licence, (c) 2019-2025 Tomislav Bacinger"
' TRACKS BEGIN (written by games/gen_tracks.py -- don't edit by hand)
' circuit layouts from github.com/bacinger/f1-circuits (MIT licence,
' (c) 2019-2025 Tomislav Bacinger), written by games/gen_tracks.py:
' how many, then per circuit its name and 50 x,y points in race order
Tracks:
Data 24
Data "Albert Park"
Data 210,129, 235,114, 261,100, 286,85, 311,96, 339,91, 364,75, 390,62, 416,50, 444,42, 473,35, 476,62
Data 491,81, 520,87, 541,104, 551,131, 556,160, 560,188, 554,212, 538,235, 523,260, 497,273, 468,272, 439,270
Data 415,255, 393,236, 367,223, 340,214, 311,212, 282,219, 257,234, 234,251, 223,278, 206,300, 182,316, 157,331
Data 128,336, 99,337, 70,338, 47,330, 43,301, 40,272, 60,255, 88,248, 105,233, 91,207, 109,187, 134,172
Data 160,158, 185,144
Data "Shanghai"
Data 246,83, 258,36, 294,20, 325,42, 302,60, 284,66, 305,87, 345,79, 384,70, 424,68, 464,76, 501,88
Data 467,106, 427,108, 386,110, 351,126, 343,164, 362,199, 369,236, 335,253, 301,262, 320,295, 360,294, 401,294
Data 435,288, 466,282, 490,280, 503,285, 503,296, 490,311, 468,328, 428,330, 387,332, 347,334, 306,337, 266,340
Data 225,342, 186,348, 145,355, 104,350, 64,353, 64,335, 104,329, 144,316, 179,309, 192,274, 204,235, 215,196
Data 227,157, 239,119
Data "Suzuka"
Data 484,197, 504,221, 523,245, 543,269, 560,295, 551,324, 526,316, 509,290, 484,276, 462,259, 449,232, 418,227
Data 404,202, 412,172, 393,155, 367,158, 342,164, 320,187, 293,204, 258,212, 254,198, 242,140, 237,117, 247,88
Data 228,100, 206,123, 188,127, 163,124, 136,115, 108,96, 88,72, 70,49, 40,54, 41,82, 61,103, 80,125
Data 105,141, 136,155, 172,164, 206,164, 218,172, 274,163, 286,165, 308,145, 335,125, 364,118, 394,115, 423,127
Data 444,149, 464,173
Data "Bahrain"
Data 318,31, 363,32, 408,33, 452,35, 497,36, 542,38, 533,67, 538,109, 535,153, 527,197, 518,240, 510,284
Data 501,328, 477,353, 448,319, 418,286, 380,263, 379,220, 360,194, 351,172, 357,158, 379,152, 407,146, 426,139
Data 428,130, 413,120, 386,111, 343,107, 296,108, 251,107, 207,105, 179,128, 197,168, 236,189, 269,218, 266,261
Data 246,301, 211,313, 187,275, 165,236, 144,197, 122,157, 100,118, 78,79, 58,40, 95,20, 139,21, 184,23
Data 229,25, 274,28
Data "Jeddah"
Data 185,271, 201,260, 217,248, 236,233, 235,224, 248,209, 269,198, 296,183, 310,164, 314,150, 337,137, 358,122
Data 366,107, 380,97, 404,98, 426,95, 447,89, 472,78, 483,59, 488,44, 484,35, 474,33, 460,35, 445,48
Data 422,55, 403,58, 379,57, 355,64, 337,80, 328,95, 305,106, 283,122, 275,141, 266,156, 243,167, 220,180
Data 202,202, 187,222, 166,228, 144,237, 127,252, 111,270, 101,291, 94,313, 101,325, 110,331, 122,329, 137,322
Data 154,306, 170,289
Data "Miami"
Data 299,139, 331,160, 364,180, 355,206, 348,241, 323,258, 291,258, 256,244, 216,231, 183,214, 147,221, 112,224
Data 81,205, 45,217, 40,252, 77,255, 114,264, 152,265, 191,264, 221,270, 255,284, 299,298, 341,294, 377,283
Data 413,271, 449,257, 484,242, 518,224, 529,200, 517,169, 553,161, 560,133, 560,99, 522,97, 483,96, 445,95
Data 407,93, 369,92, 330,91, 292,89, 260,81, 221,73, 177,71, 139,82, 101,82, 123,109, 157,113, 190,109
Data 228,113, 266,121
Data "Imola"
Data 371,82, 343,78, 316,72, 288,68, 260,68, 232,70, 205,73, 178,81, 163,102, 138,115, 126,140, 116,166
Data 105,192, 95,218, 93,245, 83,267, 61,285, 40,304, 51,320, 79,316, 107,313, 135,309, 162,310, 190,315
Data 216,311, 228,286, 229,259, 223,231, 220,204, 236,181, 263,187, 291,187, 319,187, 347,186, 375,186, 397,190
Data 423,180, 448,167, 470,150, 490,131, 510,111, 534,97, 560,86, 555,61, 534,53, 507,63, 481,73, 455,81
Data 427,82, 399,82
Data "Monaco"
Data 406,80, 432,61, 463,47, 484,50, 501,54, 514,59, 525,64, 533,69, 538,79, 537,95, 531,117, 509,140
Data 481,160, 450,172, 416,179, 385,181, 348,178, 315,169, 285,161, 257,155, 225,145, 194,135, 162,123, 139,126
Data 119,149, 108,177, 99,208, 88,240, 75,262, 72,296, 78,326, 62,339, 40,320, 33,286, 37,251, 53,220
Data 64,188, 74,156, 88,123, 112,96, 139,82, 173,85, 205,96, 240,107, 267,117, 304,126, 337,135, 367,143
Data 400,142, 412,113
Data "Barcelona"
Data 414,219, 381,237, 348,254, 315,271, 283,290, 251,308, 217,324, 183,341, 150,342, 126,323, 87,322, 53,309
Data 40,275, 52,240, 79,215, 112,198, 139,193, 159,194, 167,205, 162,222, 148,241, 141,259, 146,274, 164,285
Data 190,293, 224,280, 256,262, 248,228, 251,191, 256,154, 272,123, 309,118, 346,120, 383,122, 420,124, 458,126
Data 495,126, 493,95, 470,82, 456,69, 457,55, 473,43, 498,31, 527,50, 545,83, 560,117, 546,150, 514,168
Data 481,185, 448,202
Data "Montreal"
Data 189,257, 166,269, 143,281, 119,292, 93,298, 67,301, 57,324, 40,311, 40,285, 48,260, 59,236, 77,221
Data 97,206, 111,185, 124,162, 147,151, 172,144, 189,129, 190,105, 212,91, 237,83, 262,75, 287,69, 313,65
Data 339,64, 365,64, 383,79, 409,83, 435,83, 460,81, 481,72, 499,65, 536,61, 560,49, 552,64, 541,77
Data 517,101, 489,111, 467,123, 446,139, 423,151, 399,163, 376,174, 352,186, 329,198, 306,210, 282,222, 259,233
Data 236,233, 213,245
Data "Red Bull Ring"
Data 386,322, 351,331, 315,341, 280,351, 247,351, 227,321, 205,291, 185,260, 166,229, 149,196, 133,163, 117,130
Data 95,101, 70,74, 44,48, 40,25, 77,22, 113,22, 150,26, 186,33, 222,40, 258,46, 295,49, 331,51
Data 367,56, 359,87, 330,110, 294,117, 258,113, 221,107, 187,115, 178,149, 195,181, 213,213, 246,226, 274,204
Data 303,182, 339,175, 375,174, 412,174, 449,173, 485,172, 522,171, 548,196, 558,231, 560,265, 528,282, 493,293
Data 457,303, 422,312
Data "Silverstone"
Data 521,102, 542,132, 560,163, 547,195, 521,221, 492,243, 461,262, 435,286, 408,306, 373,320, 354,348, 320,342
Data 286,333, 249,334, 213,335, 177,336, 140,337, 104,337, 68,335, 40,315, 49,282, 66,250, 77,215, 80,183
Data 69,157, 93,131, 130,134, 166,139, 202,144, 238,149, 264,170, 279,204, 307,224, 341,238, 349,262, 340,290
Data 376,280, 396,256, 404,220, 412,185, 419,149, 427,114, 419,90, 410,68, 405,52, 409,40, 424,32, 448,25
Data 478,43, 500,72
Data "Spa"
Data 483,52, 507,28, 528,20, 521,53, 509,85, 491,113, 472,141, 457,171, 431,191, 407,214, 384,239, 358,260
Data 329,277, 300,295, 271,312, 242,330, 213,347, 183,341, 152,353, 125,332, 100,310, 96,284, 123,300, 152,304
Data 180,285, 211,270, 241,256, 251,226, 235,197, 203,189, 170,185, 137,179, 132,148, 110,126, 78,116, 72,89
Data 90,61, 123,61, 154,74, 182,93, 205,118, 230,140, 262,151, 295,156, 325,142, 352,122, 382,107, 414,96
Data 436,100, 460,76
Data "Hungaroring"
Data 134,164, 130,132, 127,100, 123,68, 122,37, 148,48, 166,74, 174,105, 178,137, 182,169, 201,190, 221,169
Data 230,139, 258,125, 289,115, 319,104, 350,94, 381,87, 407,73, 423,45, 442,20, 470,28, 478,59, 478,91
Data 476,123, 452,141, 436,169, 438,198, 453,225, 433,249, 408,268, 393,296, 386,327, 362,345, 330,347, 298,349
Data 266,351, 234,353, 231,327, 226,294, 216,265, 195,280, 189,303, 181,318, 171,321, 160,311, 149,292, 145,260
Data 142,228, 138,196
Data "Zandvoort"
Data 144,171, 160,136, 178,109, 190,77, 205,45, 225,20, 241,43, 229,75, 218,108, 215,141, 191,160, 182,183
Data 210,177, 244,170, 277,169, 306,169, 339,164, 375,155, 408,147, 442,149, 476,155, 496,181, 491,214, 473,242
Data 454,272, 432,293, 398,287, 370,269, 378,243, 398,230, 409,217, 407,207, 392,199, 370,195, 335,204, 296,208
Data 264,213, 233,229, 207,217, 194,239, 200,273, 205,307, 206,341, 177,353, 142,351, 114,332, 104,300, 112,267
Data 125,236, 138,204
Data "Monza"
Data 155,187, 176,170, 196,153, 216,136, 236,119, 257,102, 277,96, 291,74, 310,56, 332,41, 357,35, 383,38
Data 407,49, 428,66, 448,83, 468,100, 489,114, 512,122, 535,134, 559,146, 560,170, 543,190, 526,211, 502,209
Data 476,202, 451,195, 425,189, 399,187, 372,185, 346,184, 320,182, 293,180, 271,190, 247,196, 225,210, 204,226
Data 184,243, 163,260, 143,276, 122,293, 102,310, 81,326, 58,338, 40,322, 42,296, 56,274, 74,255, 94,237
Data 114,220, 135,204
Data "Baku"
Data 497,101, 522,91, 531,72, 520,47, 509,23, 488,20, 463,30, 438,40, 413,50, 388,61, 364,72, 339,83
Data 326,101, 336,126, 327,137, 303,149, 280,161, 276,172, 259,186, 240,200, 210,217, 198,221, 185,201, 166,187
Data 142,190, 117,201, 94,214, 77,235, 70,260, 69,287, 71,314, 89,331, 113,343, 138,353, 155,335, 170,312
Data 190,294, 207,278, 206,265, 226,254, 247,239, 274,223, 305,200, 325,183, 351,168, 373,154, 398,143, 423,132
Data 447,122, 472,111
Data "Singapore"
Data 550,142, 555,178, 560,214, 554,248, 526,265, 490,263, 454,259, 430,239, 401,229, 364,227, 328,225, 292,223
Data 255,220, 225,201, 199,178, 168,181, 159,207, 152,243, 145,279, 138,315, 129,350, 105,331, 77,308, 71,275
Data 40,257, 42,224, 60,192, 78,161, 96,129, 121,108, 148,131, 174,141, 191,118, 210,87, 242,102, 273,120
Data 305,138, 338,152, 374,155, 411,157, 447,159, 483,160, 499,132, 492,96, 479,62, 479,26, 502,23, 536,34
Data 541,70, 545,106
Data "Austin COTA"
Data 141,282, 166,301, 192,321, 219,337, 215,308, 207,277, 223,251, 250,234, 274,213, 294,190, 309,165, 329,141
Data 359,144, 389,149, 411,126, 437,137, 468,134, 499,125, 519,101, 531,80, 537,64, 531,54, 515,52, 492,55
Data 461,63, 430,71, 398,77, 367,83, 335,88, 305,93, 280,100, 261,109, 249,121, 242,131, 234,139, 225,144
Data 217,151, 210,163, 204,181, 194,201, 182,221, 152,209, 134,183, 112,160, 82,171, 53,183, 40,202, 65,222
Data 90,242, 116,262
Data "Mexico City"
Data 149,26, 177,30, 205,34, 233,37, 260,41, 288,45, 316,48, 344,51, 372,54, 400,58, 428,62, 456,66
Data 484,70, 511,75, 523,94, 534,115, 531,142, 520,168, 506,192, 492,216, 477,240, 462,264, 450,288, 442,311
Data 448,330, 429,349, 405,353, 402,328, 405,295, 415,268, 411,244, 389,227, 374,204, 347,197, 319,192, 306,169
Data 285,151, 260,138, 233,131, 205,127, 177,123, 150,119, 125,110, 123,82, 116,59, 93,66, 66,61, 71,36
Data 93,20, 121,20
Data "Interlagos"
Data 164,107, 127,129, 89,150, 52,171, 40,206, 71,233, 65,275, 80,314, 115,338, 157,343, 200,343, 243,343
Data 286,342, 329,342, 372,342, 414,342, 456,338, 464,298, 455,256, 424,228, 384,212, 344,196, 304,181, 265,165
Data 249,126, 268,90, 297,89, 324,91, 348,93, 373,90, 398,79, 415,82, 426,93, 428,114, 424,143, 447,177
Data 488,191, 529,203, 557,185, 560,143, 544,103, 519,68, 487,40, 448,27, 402,29, 361,33, 318,33, 276,45
Data 237,65, 202,87
Data "Las Vegas"
Data 99,319, 125,339, 135,313, 116,286, 128,257, 160,250, 193,250, 227,250, 260,250, 294,249, 327,249, 361,249
Data 376,268, 376,302, 386,332, 416,345, 440,331, 468,335, 470,302, 471,268, 473,235, 486,205, 515,189, 544,174
Data 560,145, 559,116, 529,101, 500,85, 471,68, 440,55, 408,45, 375,38, 342,33, 309,32, 275,33, 242,33
Data 208,32, 175,30, 141,29, 108,29, 74,28, 52,43, 41,73, 40,107, 40,140, 41,174, 40,207, 42,241
Data 50,273, 74,296
Data "Lusail"
Data 319,23, 358,24, 396,25, 435,26, 474,26, 498,51, 471,76, 437,95, 428,128, 461,148, 490,172, 502,209
Data 514,246, 526,283, 512,315, 475,323, 455,292, 443,255, 421,230, 411,266, 400,294, 386,313, 370,318, 351,307
Data 332,286, 312,254, 323,217, 317,183, 280,191, 248,212, 224,242, 209,278, 193,313, 165,337, 126,337, 99,313
Data 81,278, 93,245, 119,215, 144,186, 137,151, 116,118, 95,85, 74,53, 86,21, 125,20, 163,21, 202,21
Data 241,22, 280,23
Data "Yas Marina"
Data 256,146, 270,179, 283,212, 309,225, 340,208, 368,186, 372,151, 390,122, 425,116, 460,113, 494,101, 515,87
Data 528,73, 526,62, 509,54, 484,48, 449,45, 413,43, 377,41, 342,39, 306,36, 270,36, 236,33, 198,26
Data 167,35, 153,58, 129,82, 106,110, 91,142, 72,170, 57,203, 49,240, 46,277, 54,297, 62,307, 71,304
Data 79,286, 84,261, 88,229, 101,197, 127,176, 145,203, 178,204, 184,174, 170,141, 159,107, 184,84, 207,65
Data 228,80, 242,113
' TRACKS END

Sub SetGamePalette
  MAP S_GRASS = RGB(30, 74, 30)
  MAP S_ROAD = RGB(96, 96, 96)
  MAP S_PURPLE = RGB(204, 102, 255)
  MAP S_SAND = RGB(210, 180, 140)
  MAP S_BLUE = RGB(51, 136, 255)
  MAP SET
End Sub

' back to the club's GAMES page if this board has the club, otherwise
' to the prompt with the screen the way it normally is
Sub Quit
  On Error Skip
  FRAMEBUFFER CLOSE
  If MM.Info(FILESIZE HOME_DIR$ + "/games.bas") > 0 Then GoPage "games.bas"
  If hasMouse Then GUI Cursor Off
  MAP RESET
  MODE 1
  Font 1
  CLS
  Print "CIRCUIT RACE closed."
  End
End Sub

' feedback messages go through the ticker now (slot 3), not a reserved
' strip at the top of the screen -- the whole page is the scene. Except
' once qualifying/the grid/the race itself is under way (phase 1, 5, 2)
' -- the ticker's for the running order then, not anything else
Sub Status(s$)
  statusMsg$ = s$
  If phase <> 1 And phase <> 5 And phase <> 2 Then TickerSeg 3, s$
End Sub

' --- the track --------------------------------------------------------------
' fitted to fill however much of the track band this board actually has
' (RAWW/RAWH is gen_tracks.py's BOX, the box every circuit was fitted into
' when it was generated -- offline, so it can't just read W/CT/CB itself),
' not a fixed 1.1x -- a bigger screen than this was tuned on used to leave
' real margin unused on every track, and a tight corner is that much
' tighter (relative to a car and to MIN_LAT_GAP) on a smaller drawn track.
' Smoothed twice after (Chaikin: every edge becomes points 1/4 and 3/4
' along it), then the running arc length
Sub BuildTrack
  Local float ax(NWP - 1), ay(NWP - 1), bx2(NWP - 1), by2(NWP - 1), d
  Local float sc, ox, oy
  Local integer i, n, it, k, x, y
  Restore Tracks
  Read nTracks
  trackNo = Max(0, Min(nTracks - 1, trackNo))
  ' skip the circuits before the one wanted
  For k = 1 To trackNo
    Read tName$
    For i = 1 To NRAW * 2
      Read x
    Next
  Next
  Read tName$
  ' whichever of width/height is tighter wins, so the track never runs off
  ' the band; centred in the other axis rather than pinned to one corner
  sc = Min((W - TRACK_MARGIN * 2) / RAWW, (CB - CT - TRACK_MARGIN * 2) / RAWH)
  ox = (W - RAWW * sc) / 2
  oy = CT + (CB - CT - RAWH * sc) / 2
  For i = 0 To NRAW - 1
    Read x, y
    rx(i) = ox + (x - 40) * sc
    ry(i) = oy + (y - 20) * sc
    ax(i) = rx(i)
    ay(i) = ry(i)
  Next
  n = NRAW
  For it = 1 To 1
    For i = 0 To n - 1
      k = (i + 1) Mod n
      bx2(2 * i) = 0.75 * ax(i) + 0.25 * ax(k)
      by2(2 * i) = 0.75 * ay(i) + 0.25 * ay(k)
      bx2(2 * i + 1) = 0.25 * ax(i) + 0.75 * ax(k)
      by2(2 * i + 1) = 0.25 * ay(i) + 0.75 * ay(k)
    Next
    n = n * 2
    For i = 0 To n - 1
      ax(i) = bx2(i)
      ay(i) = by2(i)
    Next
  Next
  For i = 0 To NWP - 1
    wx(i) = ax(i)
    wy(i) = ay(i)
  Next
  wx(NWP) = wx(0)
  wy(NWP) = wy(0)
  cum(0) = 0
  For i = 0 To NWP - 1
    d = Sqr((wx(i + 1) - wx(i)) ^ 2 + (wy(i + 1) - wy(i)) ^ 2)
    cum(i + 1) = cum(i) + d
  Next
  trackLen = cum(NWP)
  SandTraps
End Sub

' sand at the 4 sharpest corners, pushed outward from the loop's middle
Sub SandTraps
  Local float sh(NRAW - 1), cx, cy, v1x, v1y, v2x, v2y, l1, l2, dx, dy, dl
  Local integer i, k, best, used(NRAW - 1), a, b
  For i = 0 To NRAW - 1
    cx = cx + rx(i) / NRAW
    cy = cy + ry(i) / NRAW
    a = (i + NRAW - 1) Mod NRAW
    b = (i + 1) Mod NRAW
    v1x = rx(a) - rx(i)
    v1y = ry(a) - ry(i)
    v2x = rx(b) - rx(i)
    v2y = ry(b) - ry(i)
    l1 = Max(1, Sqr(v1x * v1x + v1y * v1y))
    l2 = Max(1, Sqr(v2x * v2x + v2y * v2y))
    sh(i) = (v1x * v2x + v1y * v2y) / (l1 * l2)
  Next
  For k = 0 To 3
    best = -1
    For i = 0 To NRAW - 1
      If Not used(i) Then
        If best < 0 Then
          best = i
        ElseIf sh(i) > sh(best) Then
          best = i
        EndIf
      EndIf
    Next
    used(best) = 1
    dx = rx(best) - cx
    dy = ry(best) - cy
    dl = Max(1, Sqr(dx * dx + dy * dy))
    sandX(k) = Max(SAND_R + 2, Min(W - SAND_R - 2, rx(best) + dx / dl * (TRACK_W / 2 + 10)))
    sandY(k) = Max(CT + SAND_R, Min(CB - SAND_R, ry(best) + dy / dl * (TRACK_W / 2 + 10)))
  Next
End Sub

' which segment progress p is on (lSeg) and how far along it (lT, 0-1)
Sub TrackAt(p As float)
  Local integer lo, hi, m
  Local float q
  q = p - Int(p / trackLen) * trackLen
  lo = 0
  hi = NWP - 1
  Do While lo < hi
    m = (lo + hi + 1) \ 2
    If cum(m) <= q Then
      lo = m
    Else
      hi = m - 1
    EndIf
  Loop
  lSeg = lo
  lT = (q - cum(lo)) / Max(0.001, cum(lo + 1) - cum(lo))
End Sub

' the grass, sand, road, centre line and start line, into framebuffer F
Sub DrawTrack
  Local integer i
  Local float t, x, y, sl
  ' hidden before this draws into F, unlike every other Sub here that
  ' draws straight to the screen -- otherwise the cursor is wherever the
  ' mouse happens to be when this runs, gets baked into the track's own
  ' framebuffer, and BLIT keeps reprinting that little box every tick for
  ' as long as this track image lasts (a whole race, since F is never
  ' rebuilt mid-race)
  CurHide
  FRAMEBUFFER WRITE F
  Box 0, CT, W, CB - CT, 1, MAP(S_GRASS), MAP(S_GRASS)
  For i = 0 To 3
    Circle sandX(i), sandY(i), SAND_R, 1, 1, MAP(S_SAND), MAP(S_SAND)
  Next
  ' the road: filled circles every 4px along the centre line
  For i = 0 To NWP - 1
    ' (two points on the same spot would divide by nought)
    sl = Max(0.001, cum(i + 1) - cum(i))
    For t = 0 To sl Step 4
      x = wx(i) + (wx(i + 1) - wx(i)) * t / sl
      y = wy(i) + (wy(i + 1) - wy(i)) * t / sl
      Circle x, y, TRACK_W \ 2, 1, 1, MAP(S_ROAD), MAP(S_ROAD)
    Next
  Next
  For i = 0 To NWP - 1
    Line wx(i), wy(i), wx(i + 1), wy(i + 1), 1, C_DIM
  Next
  ' start/finish line across the road at waypoint 0
  TrackAt 0
  x = wy(1) - wy(0)
  y = wx(0) - wx(1)
  sl = Max(0.001, Sqr(x * x + y * y))
  Line wx(0) - x / sl * TRACK_W / 2, wy(0) - y / sl * TRACK_W / 2, wx(0) + x / sl * TRACK_W / 2, wy(0) + y / sl * TRACK_W / 2, 2, C_INK
  FRAMEBUFFER WRITE N
  CurShow
End Sub

' local weather for the ticker, for whoever's playing wherever they are --
' WeatherNow$ (net.inc) guesses the location from the board's own internet
' connection (ip-api.com) when there's no GPS fix or home town set, so it
' needs no setup at all: any board, anywhere in the world, just works.
' Fetched once, at start-up, NOT repeatedly from the main loop. This was
' tried both ways during testing 2026-09-28: a DrawGarage self-recursion
' bug was one real cause of a full board hang, but re-enabling the
' repeat fetch after fixing that was followed by a watchdog-style soft
' reboot (WEB Open TCP Client has no visible timeout, so a slow/dead
' connection attempt can block the single-threaded interpreter long
' enough to trip it) -- so this stays a one-off boot-time fetch
Sub FetchWeather
  Local string w$, where$
  If ip$ = "" Then Exit Sub
  If lastWx <> 0 And Timer - lastWx < WX_EVERY Then Exit Sub
  lastWx = Timer
  w$ = WeatherNow$(0, 0, where$)
  If w$ = "" Then Exit Sub
  If Timer - wxStartT >= WX_PLACE_MS Then
    On Error Skip
    Open HOME_DIR$ + "/weather.txt" For Output As #4
    If MM.Errno = 0 Then
      Print #4, Str$(Epoch(Now)) + "|" + w$
      Close #4
    EndIf
  EndIf
  WeatherLoad
End Sub

' the "(near X)" place is only worth saying for the first WX_PLACE_MS --
' but with the weather fetched just once now (see FetchWeather), there's
' no later fetch left to rewrite weather.txt without it, the way this
' used to drop it. So instead: called every tick, and once the time's up,
' trims tkWx$ directly -- and keeps trimming it, since core.inc's own
' WeatherLoad re-reads the place straight back out of weather.txt on
' every ticker scroll (the file itself was never touched)
Sub HidePlaceAfter3Min
  Local integer p
  If Timer - wxStartT < WX_PLACE_MS Then Exit Sub
  p = Instr(tkWx$, " (")
  If p Then tkWx$ = Left$(tkWx$, p - 1)
End Sub

' the whole track area from F, then the cars on it
Sub ShowTrack
  Local integer i
  ' idle between races: the garage is the home screen, not an empty track
  If phase = 0 Then
    DrawGarage
    Exit Sub
  EndIf
  CurHide
  BLIT FRAMEBUFFER F, N, 0, CT, 0, CT, W, CB - CT
  For i = 0 To ne - 1
    shown(i) = 0
    If phase = 2 Or (phase = 1 And Not qDone(i)) Or phase = 3 Or phase = 5 Then DrawCar i
  Next
  hotShown = 0
  If phase = 4 Then DrawHot
  CurShow
End Sub

' registers every garage action as a button in a 4-across grid over the
' bottom of the track area; not drawn here -- DrawGarage draws them
' whenever phase = 0 (the garage is the home screen)
' PLAYERS and RACE are filing cabinets in the floor's upper-left and
' upper-right corners (drawers stacked); GARAGE is a tool bench across
' the upper middle (drawers side by side). All three sit up near the
' back wall, clear of the mechanic, driver and car who stand at the
' front when the pit-garage scenes use this same bay backdrop
Sub AddGarageButtons
  Local string lbl$(11)
  Local integer i, gi, lh, floorTop, backBottom, cabH, benchH, benchDW, bgap, totalW
  ' NEW EVENT used to live here -- gone now that a new event's lineup and
  ' entry fee are handled automatically (see RaceOver) and LAPS/RACES
  ' cover the rest from the RACE cabinet. DRIVERS took the slot instead:
  ' the membership list (see there), now that a driver's account (kitty,
  ' wins, car) persists across sessions and LEAVE only sits them out of
  ' the current race rather than deleting it
  lbl$(0) = "ENTER PLAYER" : lbl$(1) = "LEAVE" : lbl$(2) = "CAR LIST" : lbl$(3) = "DRIVERS"
  lbl$(4) = "VISIT" : lbl$(5) = "REPAIR" : lbl$(6) = "HOT LAP" : lbl$(7) = "SELL CAR"
  lbl$(8) = "TRACK" : lbl$(9) = "LAPS" : lbl$(10) = "RACES" : lbl$(11) = "START RACE"
  gDrawerGap = 4
  lh = fh(0) + 8
  ' the same back-wall geometry DrawBay works out, so the furniture sits
  ' properly on the FLOOR -- anchored on backBottom, the floor's own back
  ' edge. The wall's shrunk to 35% (was 55%) so the floor -- and the back
  ' wall's roller door -- starts higher, above the furniture, instead of
  ' the furniture sitting in front of (and hiding) the wall
  floorTop = CT + (CB - CT) * 35 \ 100
  backBottom = floorTop - (floorTop - CT) * 30 \ 100
  gGW(0) = W \ 7
  gGW(2) = W \ 7
  gGW(1) = W * 3 \ 10
  ' tall and narrow for the cabinets (the 4 stacked drawers make up
  ' nearly all their height); low and wide for the bench
  cabH = (CB - backBottom) * 45 \ 100
  benchH = cabH * 55 \ 100
  gBenchH = benchH
  gDrawerH = (cabH - lh - 3 * gDrawerGap) \ 4
  ' the whole connected run centred on the page itself -- the one thing
  ' fixed first; the mechanic (DrawGarage) is positioned from its actual
  ' right edge afterwards, not the other way around, so the two can't
  ' drift out of step the way independently-centred guesses just did
  totalW = gGW(0) + 12 + gGW(1) + 12 + gGW(2)
  gGX(0) = (W - totalW) \ 2
  gGY(0) = backBottom - 94
  gGX(1) = gGX(0) + gGW(0) + 12 : gGY(1) = backBottom - 94
  gGX(2) = gGX(1) + gGW(1) + 12 : gGY(2) = backBottom - 94
  ' PLAYERS: stacked drawers, as wide as the cabinet face allows.
  ' bstyle 4 opts every drawer out of core.inc's generic hover/press
  ' redraw helper (unused here on purpose -- naming it in this comment
  ' would make build.py's word-scan bundle it into the build for nothing)
  ' -- DrawDrawer is the only thing allowed to draw them, or hovering
  ' across them repaints each as a plain green button and never puts the
  ' steel drawer art back
  For gi = 0 To 3
    i = gi
    v = AddBtn(lbl$(i), gGX(0) + 2, gGY(0) + lh + gi * (gDrawerH + gDrawerGap), gGW(0) - 4, gDrawerH, Choice(lbl$(i) = "LEAVE", 1, 0))
    bstyle(v) = 4
    If i = 0 Then gBtn0 = v
  Next
  ' GARAGE: the tool bench's 4 drawers, side by side
  bgap = 4
  benchDW = (gGW(1) - 5 * bgap) \ 4
  For gi = 0 To 3
    i = 4 + gi
    v = AddBtn(lbl$(i), gGX(1) + bgap + gi * (benchDW + bgap), gGY(1) + lh, benchDW, benchH - lh, 0)
    bstyle(v) = 4
    If i = 0 Then gBtn0 = v
  Next
  ' RACE: stacked drawers
  For gi = 0 To 3
    i = 8 + gi
    v = AddBtn(lbl$(i), gGX(2) + 2, gGY(2) + lh + gi * (gDrawerH + gDrawerGap), gGW(2) - 4, gDrawerH, Choice(lbl$(i) = "LEAVE", 1, 0))
    bstyle(v) = 4
    If i = 0 Then gBtn0 = v
  Next
End Sub

' one drawer of a garage filing cabinet: shift > 0 slides it out (and
' lights it up) for the roll-out-and-open flourish on a click
Sub DrawDrawer(i As integer, shift As integer)
  Local integer x, y, w, h, face, p
  Local string l1$, l2$
  x = bx(i) + shift
  y = by(i)
  w = bw(i)
  h = bh(i)
  face = Choice(shift > 0, 5, 13)
  If shift > 0 Then Box bx(i) - 2, y - 2, shift + 4, h + 4, 0, 0, MAP(6)
  ' a bevelled steel drawer front -- lit top-left edge, shadowed
  ' bottom-right, so it reads as a raised panel, not a flat button
  Box x, y, w, h, 0, 0, MAP(face)
  Line x, y, x + w - 1, y, 1, MAP(15)
  Line x, y, x, y + h - 1, 1, MAP(15)
  Line x, y + h - 1, x + w - 1, y + h - 1, 1, C_BLACK
  Line x + w - 1, y, x + w - 1, y + h - 1, 1, C_BLACK
  ' the handle: a raised bar, same trick in miniature, kept small so a
  ' two-line label still has room
  Box x + w \ 4, y + 3, w \ 2, 5, 0, 0, MAP(Choice(shift > 0, 15, 14))
  Line x + w \ 4, y + 3, x + w * 3 \ 4, y + 3, 1, MAP(15)
  Line x + w \ 4, y + 7, x + w * 3 \ 4, y + 7, 1, C_BLACK
  ' the label, split at its last space onto two lines -- a narrow drawer
  ' front can't fit "ENTER PLAYER" etc. on one
  l1$ = lbl$(i)
  l2$ = ""
  p = Instr(l1$, " ")
  If p > 0 Then
    l2$ = Mid$(l1$, p + 1)
    l1$ = Left$(l1$, p - 1)
  EndIf
  If l2$ = "" Then
    PText x + w \ 2, y + h - fh(0) \ 2 - 2, l1$, "C", 0, C_BLACK
  Else
    PText x + w \ 2, y + h - fh(0) - 6, l1$, "C", 0, C_BLACK
    PText x + w \ 2, y + h - 6, l2$, "C", 0, C_BLACK
  EndIf
End Sub

' the click flourish: the drawer rolls out and lights up before its
' action runs, so a filing cabinet is what it looks like, not a button
Sub DrawerOpen(i As integer)
  Local integer k
  CurHide
  For k = 2 To 10 Step 4
    DrawDrawer i, k
  Next
  CurShow
  Pause 120
End Sub

' the garage ticker's own summary line: race/event, pot, laps, track.
' DrawGarage sets this as part of its own full redraw; LAPS/RACES/TRACK
' change one of these without wanting (or needing) a full garage redraw
' just to keep this one line current
Sub RaceInfoTicker
  TickerSeg 1, "Race " + Str$(raceNum) + " of " + Str$(EVENT_RACES) + " - pot $" + Str$(Int(pot)) + " - " + Str$(lapsToWin) + " lap" + Choice(lapsToWin = 1, "", "s") + " - " + tName$
End Sub

' the garage home screen: shown whenever phase = 0 (idle, between races),
' with the mechanic in it, and every action a filing-cabinet drawer in
' one of three groups (PLAYERS, GARAGE, RACE) instead of a menu bar to
' hunt through
Sub DrawGarage
  Local integer i, g, mw, mh, mmx, mmy, mx, my, pose, t0, justIntroduced
  Local integer cabBottom
  Local integer cx, cy, cw, ch
  Local integer px(4), py(4)
  Local string r$
  CurHide
  DrawBay "GARAGE"
  ' the mechanic, standing in the foreground, with a word for whoever's
  ' about (he opens up with a message, never who'll win a race that
  ' hasn't happened)
  Restore ArtInfo
  Read mw, mh, mmx, mmy
  ' centred in whatever's actually left to the right of the furniture's
  ' real edge, now that the furniture is centred on the page first --
  ' clamped so a narrow gap (or a wide mechanic sprite) never pushes him
  ' past the right edge of the screen
  mx = gGX(2) + gGW(2) + 12 + (W - (gGX(2) + gGW(2) + 12) - mw) \ 2
  mx = Min(mx, W - mw - 8)
  my = CB - mh - 8
  ' a different stance each visit -- holding that spanner all the time
  ' would be tiring
  pose = Int(Rnd * 3)
  ArtAt Choice(pose = 0, 0, Choice(pose = 1, 11, 12)), mx, my
  ' the very first time the garage is shown this run: a welcome and a
  ' quick word on how to start, instead of the usual one-line greeting.
  ' Just the flag here -- the bubble itself is drawn at the very end of
  ' this Sub (see there), after the cabinets, or they're drawn on top of
  ' it and cover part of it (they're drawn later in this Sub, so later
  ' in z-order too)
  If introDone = 0 Then
    introDone = 1
    justIntroduced = 1
  EndIf
  ' who's in and the event: the ticker's what that's for, not text on the
  ' screen that just gets hidden behind the furniture. EntrantsTicker
  ' owns segment 0 (one entrant at a time -- see there for why)
  EntrantsTicker
  RaceInfoTicker
  TickerSeg 2, ""
  ' PLAYERS and RACE: filing cabinets in the floor's upper corners.
  ' GARAGE: a tool bench across the upper middle. All three real steel
  ' boxes (front, top and a side sliver), up near the back wall, clear
  ' of the mechanic/driver/car in a pit-garage scene
  For g = 0 To 2
    cx = gGX(g) - 6
    cy = gGY(g) - 2
    cw = gGW(g) + 12
    cabBottom = gGY(g) + fh(0) + 8 + Choice(g = 1, gBenchH - fh(0) - 8, 4 * gDrawerH + 3 * gDrawerGap) + 8
    ch = cabBottom - cy
    ' the lit top, seen from above
    px(0) = cx : py(0) = cy : px(1) = cx + cw : py(1) = cy
    px(2) = cx + cw + CAB_DX : py(2) = cy + CAB_DY : px(3) = cx + CAB_DX : py(3) = cy + CAB_DY
    px(4) = cx : py(4) = cy
    Polygon 5, px(), py(), MAP(15), MAP(15)
    ' the shadowed side sliver
    px(0) = cx + cw : py(0) = cy : px(1) = cx + cw + CAB_DX : py(1) = cy + CAB_DY
    px(2) = cx + cw + CAB_DX : py(2) = cy + CAB_DY + ch : px(3) = cx + cw : py(3) = cy + ch
    px(4) = cx + cw : py(4) = cy
    Polygon 5, px(), py(), MAP(13), MAP(13)
    ' the front face and its label
    Box cx, cy, cw, ch, 1, C_BLACK, MAP(14)
    PText cx + cw \ 2, cy + fh(0) \ 2, Choice(g = 0, "PLAYERS", Choice(g = 1, "GARAGE", "RACE")), "C", 0, C_BLACK
    ' a thin dark line where it meets the floor -- grounds it without the
    ' heavy black shadow blob
    Box cx - 2, cy + ch, cw + 4, 3, 0, 0, MAP(6)
  Next
  For i = 0 To 11
    DrawDrawer gBtn0 + i, 0
  Next
  ' a clean snapshot of the screen right here -- bay, mechanic, cabinets,
  ' buttons, no speech bubble yet -- into the second framebuffer, so
  ' IdleChat can put a fresh line up later by restoring this and drawing
  ' straight over it, without redrawing (or so much as touching) any of
  ' the rest of it
  BLIT FRAMEBUFFER N, 2, 0, CT, 0, CT, W, CB - CT
  garageBubbleX = mx + mmx
  garageBubbleY = my + mmy
  ' a full bubble, not a single Fit$-truncated line -- a real welcome
  ' line was getting cut off ("Garage is open - what'll", never "it be?").
  ' Anchored on the mouth (mx + mmx, my + mmy, from ArtInfo) so the
  ' bubble's tail starts right where he's actually talking from -- the
  ' head itself is drawn the same in every pose (gen_pitart.py's mechanic()
  ' only branches on pose for the arms), so this holds even though he's in
  ' a random stance here. Skipped right after the welcome below -- Talk
  ' doesn't erase the last bubble before drawing a new one, so back to
  ' back they'd show as one on top of the other instead of a clean
  ' second message
  If Not justIntroduced Then Talk Quote$("GARAGE"), garageBubbleX, garageBubbleY, 0, 1
  ' the welcome bubble itself, now that the cabinets are drawn and can't
  ' end up on top of it
  If justIntroduced Then
    Talk "Welcome to F1 racing|ENTER PLAYER to join up, buy or pick a car, then START RACE when you're ready.", mx + mmx, my + mmy, 0, 1
    t0 = Timer
    Do
      TickerTick
      If Inkey$ <> "" Then Exit Do
      Pause 10
    Loop Until ClickAt() Or Timer - t0 > 12000
  EndIf
  CurShow
  ' the main loop calls IdleChat again once this long idle, so the
  ' mechanic keeps saying something new the whole time nobody's picked an
  ' option yet, not just on the one call when the screen first came up.
  ' Any real action gets back to DrawGarage anyway, which pushes the
  ' countdown out instead of double-triggering it
  nextIdleChat = Timer + 4000
End Sub

' a fresh mechanic line on the idle garage screen without redrawing any
' of it: restores the clean snapshot DrawGarage took (bay/mechanic/
' cabinets/buttons, no bubble) into the second framebuffer, then draws a
' new bubble straight over it. A full DrawGarage here instead once made
' choosing an option hit-and-miss -- the redraw could land between a
' click landing and PollInput picking it up; this never touches a button
' or a drawer, so there's nothing for a click to collide with
Sub IdleChat
  CurHide
  BLIT FRAMEBUFFER 2, N, 0, CT, 0, CT, W, CB - CT
  Talk Quote$("GARAGE"), garageBubbleX, garageBubbleY, 0, 1
  CurShow
  nextIdleChat = Timer + 4000
End Sub

' car i at its progress/lateral, facing along the track
Sub DrawCar(i As integer)
  DrawCarAt prog(i), lat(i), carCol(ec(i))
  lastX(i) = carDX
  lastY(i) = carDY
  shown(i) = 1
End Sub

' a car at distance p round the track, l to the side of the centre line,
' colour c; where it went is left in carDX, carDY (for erasing it)
Sub DrawCarAt(p As float, l As float, c As integer)
  Local float x, y, tx, ty, d, ax, ay
  ' the heading: from a little behind the car to a little ahead of it, so
  ' it turns smoothly through a bend instead of in a jump at every track
  ' point (that made the tyres jump about)
  TrackAt p - 6
  ax = wx(lSeg) + (wx(lSeg + 1) - wx(lSeg)) * lT
  ay = wy(lSeg) + (wy(lSeg + 1) - wy(lSeg)) * lT
  TrackAt p + 6
  tx = wx(lSeg) + (wx(lSeg + 1) - wx(lSeg)) * lT - ax
  ty = wy(lSeg) + (wy(lSeg + 1) - wy(lSeg)) * lT - ay
  d = Max(0.001, Sqr(tx * tx + ty * ty))
  tx = tx / d
  ty = ty / d
  TrackAt p
  x = wx(lSeg) + (wx(lSeg + 1) - wx(lSeg)) * lT - ty * l
  y = wy(lSeg) + (wy(lSeg + 1) - wy(lSeg)) * lT + tx * l
  CarTop x, y, tx, ty, c
  carDX = x
  carDY = y
End Sub

' a top-down race car centred on (x, y), pointing along (tx, ty) (a unit
' vector), body colour c: four tyres, a black-edged body tapered to the
' nose, a white stripe, black cockpit and rear wing. About 18 x 11 pixels.
Sub CarTop(x As float, y As float, tx As float, ty As float, c As integer)
  Local float nx, ny
  Local integer px(4), py(4)
  ' on whole pixels, so every part of the car moves together
  x = Int(x + 0.5)
  y = Int(y + 0.5)
  nx = -ty
  ny = tx
  ' tyres, front and back, both sides: solid dots, which look the same at
  ' any angle (thick angled lines flickered as the car moved). Thinner
  ' and closer-in than a real car's, so their reach (4 + radius) stays
  ' under half MIN_LAT_GAP -- wide tyres were visually overlapping on a
  ' pass or side by side even though the collision code had them at a
  ' legal gap
  Circle x + tx * 4.5 + nx * 4, y + ty * 4.5 + ny * 4, 1.5, 1, 1, C_BLACK, C_BLACK
  Circle x + tx * 4.5 - nx * 4, y + ty * 4.5 - ny * 4, 1.5, 1, 1, C_BLACK, C_BLACK
  Circle x - tx * 5 + nx * 4, y - ty * 5 + ny * 4, 1.8, 1, 1, C_BLACK, C_BLACK
  Circle x - tx * 5 - nx * 4, y - ty * 5 - ny * 4, 1.8, 1, 1, C_BLACK, C_BLACK
  ' the body: wide at the back, narrow at the nose, black edge
  px(0) = x + tx * 9 + nx * 2.5 : py(0) = y + ty * 9 + ny * 2.5
  px(1) = x + tx * 9 - nx * 2.5 : py(1) = y + ty * 9 - ny * 2.5
  px(2) = x - tx * 8 - nx * 4 : py(2) = y - ty * 8 - ny * 4
  px(3) = x - tx * 8 + nx * 4 : py(3) = y - ty * 8 + ny * 4
  px(4) = px(0) : py(4) = py(0)
  Polygon 5, px(), py(), C_BLACK, c
  ' stripe down the nose, cockpit, rear wing
  Line x + tx * 8, y + ty * 8, x + tx * 3, y + ty * 3, 1, C_INK
  Circle x - tx * 2, y - ty * 2, 2, 1, 1, C_BLACK, C_BLACK
  Line x - tx * 8 + nx * 5, y - ty * 8 + ny * 5, x - tx * 8 - nx * 5, y - ty * 8 - ny * 5, 2, C_BLACK
End Sub

' put back the road under where car i was drawn
Sub EraseCar(i As integer)
  If Not shown(i) Then Exit Sub
  BLIT FRAMEBUFFER F, N, lastX(i) - 11, lastY(i) - 11, lastX(i) - 11, lastY(i) - 11, 23, 23
  shown(i) = 0
End Sub

' --- players and cars (files) ------------------------------------------------
Sub LoadPlayers
  Local string l$, f4$
  np = 0
  On Error Skip
  Open PLAYERS_FILE$ For Input As #1
  If MM.Errno Then Exit Sub
  Do While Not Eof(#1) And np < MAXPL
    Line Input #1, l$
    If Instr(l$, ",") Then
      pn$(np) = Field$(l$, 1, ",")
      pb(np) = Val(Field$(l$, 2, ","))
      ' an older save (one team-colour field, not a primary+secondary
      ' pair) falls back to plain red
      f4$ = Field$(l$, 4, ",")
      If f4$ = "" Then
        pMain(np) = 3
        pShade(np) = 4
      Else
        pMain(np) = Val(Field$(l$, 3, ","))
        pShade(np) = Val(f4$)
      EndIf
      np = np + 1
    EndIf
  Loop
  Close #1
End Sub

Sub SavePlayers
  Local integer i
  On Error Skip
  Open PLAYERS_FILE$ For Output As #1
  If MM.Errno Then Exit Sub
  For i = 0 To np - 1
    Print #1, pn$(i) + "," + Str$(Int(pb(i))) + "," + Str$(pMain(i)) + "," + Str$(pShade(i))
  Next
  Close #1
End Sub

Sub LoadCars
  Local string l$
  Local integer i
  On Error Skip
  Open CARS_FILE$ For Input As #1
  If MM.Errno Then Exit Sub
  Do While Not Eof(#1) And i < NCARS
    Line Input #1, l$
    If Instr(l$, ",") Then
      owner$(i) = Field$(l$, 1, ",")
      dmg(i) = Val(Field$(l$, 2, ","))
      i = i + 1
    EndIf
  Loop
  Close #1
End Sub

Sub SaveCars
  Local integer i
  On Error Skip
  Open CARS_FILE$ For Output As #1
  If MM.Errno Then Exit Sub
  For i = 0 To NCARS - 1
    Print #1, owner$(i) + "," + Str$(dmg(i), 0, 1)
  Next
  Close #1
End Sub

Function Mechanic$(d As float)
  Mechanic$ = Choice(d < 20, "OK", Choice(d < 50, "WORN", Choice(d < 80, "BAD", "CRITICAL")))
End Function

' --- pop-up lists -------------------------------------------------------------
' a list over the track; returns the row clicked (0 up) or -1 (Esc / click
' outside). Rows are "|"-separated.
Function PickList(t$, rows$) As integer
  ' any number of rows (up to 40): 11 to a page, with MORE... to turn it
  Local string it$(39), r$
  Local integer n, p
  r$ = rows$
  Do While r$ <> "" And n < 40
    p = Instr(r$, "|")
    If p = 0 Then p = Len(r$) + 1
    it$(n) = Left$(r$, p - 1)
    r$ = Mid$(r$, p + 1)
    n = n + 1
  Loop
  PickList = PickListRows(t$, it$(), n)
End Function

' the list UI itself, working from an already-split array -- split out of
' PickList so a caller with more content than fits in one 255-char string
' (Owners, once there were 20 cars) can fill item$() a row at a time
' instead of ever joining the whole list into a single "|"-separated
' string first (that's what "String too long" crashed on)
' one row of a PickListRows popup, row 0 the first item below the title
' bar: highlighted (hi) for the keyboard's current row, plain otherwise
Sub DrawPickRow(x As integer, y As integer, wd As integer, rh As integer, row As integer, lbl$, hi As integer)
  CurHide
  Box x + 4, y + 6 + row * rh, wd - 8, rh, 0, 0, Choice(hi, C_AMBER, C_BAR)
  PText x + 14, y + 6 + row * rh + rh \ 2, Fit$(lbl$, wd - 28), "L", 0, Choice(hi, C_BLACK, C_INK)
  CurShow
End Sub

Function PickListRows(t$, item$() As string, n As integer) As integer
  Local integer i, x, y, wd, rh, p, first, shown, pick, more, sel, k, boxH
  Local string ky$
  rh = fh(0) + 10
  wd = W * 3 \ 5
  x = (W - wd) \ 2
  y = CT + 20
  ' fixed at the largest a page ever needs (11 items + header + a MORE
  ' row), so turning the page redraws just the box itself, at the same
  ' size every time, instead of a full ShowTrack -- the whole background
  ' and every cabinet behind a popup that's about to cover most of it
  ' anyway. Only the box moved; nothing underneath ever needed clearing
  boxH = 13 * rh + 10
  PickListRows = -1
  Do
    shown = Min(11, n - first)
    If n <= 12 Then shown = n
    ' MMBasic's relational operators return -1 for true: Choice(), not the
    ' raw comparison, or the box comes out two rows short of the "MORE..."
    ' label it draws, and a click on that label misses its own hit-test
    more = Choice(n > 12, 1, 0)
    CurHide
    RBox x, y, wd, boxH, 6, C_INK, C_BAR
    RBox x, y, wd, rh + 4, 6, C_INK, C_GRN_BASE
    CurShow
    PText x + wd \ 2, y + rh \ 2 + 2, t$, "C", 0, C_INK
    ' sel: the keyboard's current row, 0..shown-1 an item, shown itself
    ' the MORE... row when there is one -- Up/Down/Enter drive it, a
    ' click still works as before and doesn't need it set first. Starts
    ' at -1 (nobody highlighted) so a mouse-only click through never
    ' shows an unexplained box on row 0 -- only the first arrow key
    ' actually pressed turns the highlight on
    sel = -1
    For i = 0 To shown - 1
      DrawPickRow x, y + rh, wd, rh, i, item$(first + i), i = sel
    Next
    ' MORE... is just row "shown" of the same keyboard cursor, so Down
    ' off the last item reaches it and Enter pages on, the same as a click
    If more Then DrawPickRow x, y + rh, wd, rh, shown, "MORE...", sel = shown
    pick = -2
    Do
      ky$ = Inkey$
      If ky$ = Chr$(27) Then pick = -1
      If ky$ = Chr$(13) And sel >= 0 Then pick = sel
      k = Asc(ky$ + Chr$(0))
      If (k = 128 Or k = 129) And shown + more > 1 Then
        If sel >= 0 Then DrawPickRow x, y + rh, wd, rh, sel, Choice(sel = shown, "MORE...", item$(first + sel)), 0
        If sel < 0 Then
          ' the first press just turns the highlight on, at the natural
          ' end for that direction, rather than landing wherever -1+1
          ' or -1-1 would wrap to
          sel = Choice(k = 129, 0, shown + more - 1)
        Else
          sel = (sel + shown + more + Choice(k = 129, 1, -1)) Mod (shown + more)
        EndIf
        DrawPickRow x, y + rh, wd, rh, sel, Choice(sel = shown, "MORE...", item$(first + sel)), 1
      EndIf
      If ClickAt() Then
        pick = -1
        If clickX >= x And clickX < x + wd And clickY >= y + 6 + rh And clickY < y + 6 + (shown + 1 + more) * rh Then
          pick = (clickY - y - 6) \ rh - 1
        EndIf
      EndIf
      If pick = -2 Then
        TickerTick
        Pause 10
      EndIf
    Loop Until pick > -2
    If pick >= 0 And pick < shown Then
      PickListRows = first + pick
      Exit Do
    EndIf
    If pick < 0 Then Exit Do
    ' MORE...: the next page, round to the first
    first = Choice(first + 11 < n, first + 11, 0)
  Loop
  ShowTrack
End Function

Sub Owners
  ' PickListRows, not PickList -- with 20 cars now, joining every row into
  ' one "|"-separated string would run past MMBasic's 255-char limit and
  ' crash with "String too long" (exactly what happened at 8 cars once
  ' most were owned). Filling the array straight up has no such limit,
  ' since each row's still its own short string
  Local string it$(NCARS)
  Local integer i
  For i = 0 To NCARS - 1
    it$(i) = carName$(i) + " $" + Str$(carVal(i)) + " " + Choice(owner$(i) = "", "-", owner$(i)) + " " + Str$(Int(dmg(i))) + "%"
  Next
  it$(NCARS) = "CLOSE"
  i = PickListRows("CAR OWNERS", it$(), NCARS + 1)
End Sub

' a player joins this race: pick (or add) the player, then buy or pick a car
Sub EnterPlayer
  ' PickListRows, not PickList -- with MAXPL now 20, joining every row into
  ' one "|"-separated string would run past MMBasic's 255-char limit and
  ' crash with "String too long" (see Owners for where that first bit)
  Local string it$(MAXPL), nm$
  Local integer i, pl, c, x, y, wd, isNew, k, needSave
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then
    Status "Wait for this race to finish"
    Exit Sub
  EndIf
  If phase = 3 Then NewRace
  If ne >= NCARS Then
    Status "All the cars are in this race"
    Exit Sub
  EndIf
  For i = 0 To np - 1
    it$(i) = pn$(i) + "  $" + Str$(Int(pb(i)))
  Next
  it$(np) = "+ ADD PLAYER"
  pl = PickListRows("WHO'S RACING?", it$(), np + 1)
  If pl < 0 Then Exit Sub
  If pl = np Then
    If np >= MAXPL Then
      Status "No room for more players"
      Exit Sub
    EndIf
    wd = W \ 2
    x = (W - wd) \ 2
    y = CT + 60
    CurHide
    RBox x - 10, y - 30, wd + 20, 80, 6, C_INK, C_BAR
    CurShow
    PText x, y - 16, "New player's name, Enter:", "L", 0, C_INK
    nm$ = Trim$(EditText$(x, y, wd, ""))
    ShowTrack
    If nm$ = "" Then Exit Sub
    pn$(np) = Left$(nm$, 20)
    pb(np) = STARTING_BUDGET
    ' DESIGN: a custom livery, primary and secondary picked independently
    ' (not just the 7 fixed team combos). Esc on either cancels the join,
    ' same as Esc does one step earlier on WHO'S RACING? -- nothing's been
    ' counted into np yet, so there's nothing to unwind
    k = PickList(pn$(np) + " - PRIMARY COLOUR", TeamNames$())
    If k < 0 Then Exit Sub
    pMain(np) = ColourSlot(k)
    k = PickList(pn$(np) + " - SECONDARY COLOUR", TeamNames$())
    If k < 0 Then Exit Sub
    pShade(np) = ColourSlot(k)
    np = np + 1
    ' saved once, at whichever exit below this ends up being the last
    ' thing that changes this player's record -- not here as well, or a
    ' player who joins fine writes the same file to the SD card twice more
    ' than it needs to
    needSave = 1
    isNew = 1
  EndIf
  JoinRace pl, isNew, needSave
End Sub

' the shared back half of joining a race: already-in-this-race / broke /
' car-ownership checks, charging the entry fee, and the mechanic scene --
' used by EnterPlayer (after picking or creating a player above) and by
' Drivers (picking an existing member straight off the membership list,
' with no new-player creation to do first)
' isNew: 1 shows the WELCOME scene instead of the usual PRE_ chat -- only
' ever true from EnterPlayer's own new-player branch, never from Drivers
' needSave: 1 if the caller already changed a player record that hasn't
' been flushed to disk yet, so an early exit below still saves it
Sub JoinRace(pl As integer, isNew As integer, needSave As integer)
  Local integer i, c, k
  For i = 0 To ne - 1
    If ep(i) = pl Then
      If needSave Then SavePlayers
      Status pn$(pl) + " is already in this race"
      Exit Sub
    EndIf
  Next
  ' broke: with a car, the mechanic points at a HOT LAP; with no car at
  ' all, a sponsor puts up enough for the cheapest car and the entry, so
  ' nobody is locked out of the game for good
  If pb(pl) < ENTRY_FEE Then
    c = -1
    For i = 0 To NCARS - 1
      If owner$(i) = pn$(pl) Then c = i
    Next
    If c >= 0 Then
      If needSave Then SavePlayers
      Status pn$(pl) + ": $" + Str$(Int(pb(pl))) + ", below the $" + Str$(ENTRY_FEE) + " entry - try HOT LAP"
      qM$ = Str$(Int(pb(pl)))
      If Not bulkJoin Then Scene pl, c, "BROKE", "BROKER"
      Exit Sub
    EndIf
    k = -1
    For i = 0 To NCARS - 1
      If owner$(i) = "" And (k < 0 Or carVal(i) < carVal(k)) Then k = i
    Next
    If k < 0 Then
      If needSave Then SavePlayers
      Status pn$(pl) + ": every car's owned - wait for one to be sold"
      Exit Sub
    EndIf
    pb(pl) = carVal(k) + ENTRY_FEE
    needSave = 1
    Status "A sponsor backs " + pn$(pl) + ": $" + Str$(Int(pb(pl))) + " - enough for the " + carName$(k) + " and the entry"
  EndIf
  ' a player who owns just one car races it -- no list. The list is for
  ' buying a first car, or choosing between two owned ones
  c = -1
  k = 0
  For i = 0 To NCARS - 1
    If owner$(i) = pn$(pl) Then
      c = i
      k = k + 1
    EndIf
  Next
  If k <> 1 Then
    ' PickListRows (an array), not PickList (one joined string) -- with 20
    ' cars in the line-up, joining every priced row into one string runs
    ' well past MMBasic's 255-char limit ("String too long"). carIt$, not
    ' it$ -- this Sub already declares it$(MAXPL) up top for WHO'S
    ' RACING?, and MMBasic errors ("already declared") on a second Local
    ' of the same name even nested inside an If, a real bug that sat
    ' undetected until a player who didn't already own exactly one car
    ' actually reached this branch
    Local string carIt$(NCARS - 1)
    ' the full line-up, priced -- and what's still short of it, so a new
    ' player can see what they're saving up for
    For i = 0 To NCARS - 1
      If owner$(i) = "" Then
        If pb(pl) >= carVal(i) + ENTRY_FEE Then
          carIt$(i) = carName$(i) + "  $" + Str$(carVal(i)) + " (buy)"
        Else
          carIt$(i) = carName$(i) + "  $" + Str$(carVal(i)) + " (need $" + Str$(Int(carVal(i) + ENTRY_FEE - pb(pl))) + " more)"
        EndIf
      Else
        carIt$(i) = carName$(i) + "  owned: " + owner$(i)
      EndIf
    Next
    c = PickListRows(pn$(pl) + " - BUY / PICK CAR", carIt$(), NCARS)
    If c < 0 Then
      If needSave Then SavePlayers
      Exit Sub
    EndIf
  EndIf
  For i = 0 To ne - 1
    If ec(i) = c Then
      If needSave Then SavePlayers
      Status carName$(c) + " is already in this race"
      Exit Sub
    EndIf
  Next
  If owner$(c) <> "" And owner$(c) <> pn$(pl) Then
    If needSave Then SavePlayers
    Status carName$(c) + " is owned by " + owner$(c) + " - pick another"
    Exit Sub
  EndIf
  If owner$(c) = pn$(pl) And dmg(c) >= TOO_DAMAGED Then
    If needSave Then SavePlayers
    Status carName$(c) + " is too damaged to race (" + Str$(Int(dmg(c))) + "%) - HOT LAP, then REPAIR"
    If Not bulkJoin Then Scene pl, c, "TOODMG", "TOODMGR"
    Exit Sub
  EndIf
  ' the budget this player started the event with, before any spending
  If startB(pl) < 0 Then startB(pl) = pb(pl)
  If owner$(c) = "" Then
    If pb(pl) < carVal(c) + ENTRY_FEE Then
      If needSave Then SavePlayers
      Status "Can't afford the " + carName$(c) + " ($" + Str$(carVal(c)) + " + entry)"
      Exit Sub
    EndIf
    pb(pl) = pb(pl) - carVal(c)
    owner$(c) = pn$(pl)
    SaveCars
  EndIf
  pb(pl) = pb(pl) - ENTRY_FEE
  pot = pot + ENTRY_FEE
  ep(ne) = pl
  ec(ne) = c
  ' both branches below cover the car's condition (PRE_ is damage-aware,
  ' WELCOME's car is always fresh) -- so BeginRace's PRE_ chat right
  ' before the race, which exists for exactly that, has nothing left to
  ' add for anyone entered this way and always skips them (see there)
  wasNew(ne) = 1
  ne = ne + 1
  SavePlayers
  Status pn$(pl) + " races the " + carName$(c) + " - " + Str$(ne) + " in, pot $" + Str$(Int(pot)) + ". START RACE when ready"
  If Not bulkJoin Then
    If isNew Then
      WelcomeScene pl, c
    Else
      Scene pl, c, "PRE_" + Mechanic$(dmg(c)), "PRER"
    EndIf
  EndIf
End Sub

' every saved club member who already owns exactly one car and can
' afford the entry races from the moment the game starts -- called once
' at boot, right after LoadPlayers/LoadCars. Anyone broke, owning none or
' 2+ cars, or whose one car's too damaged just doesn't get auto-added
' (JoinRace's own checks, same as a manual join); they still show up fine
' in ENTER PLAYER/DRIVERS to sort out by hand
Sub AutoJoinSaved
  Local integer pl
  bulkJoin = 1
  For pl = 0 To np - 1
    JoinRace pl, 0, 0
  Next
  bulkJoin = 0
End Sub

' a player leaves for good: a farewell in the garage, their car(s) go
' back to the lot (repaired, unowned, ready for the next driver), any
' entry in a race that hasn't started yet is scratched, and everyone
' below them shuffles up a slot
' sits someone out of the CURRENT RACE only -- their account (kitty,
' wins, whatever car they own) is a club membership now, not a per-race
' thing, and is left completely alone. See DRIVERS for the membership
' list itself, and its own way to actually retire a driver for good
Sub LeavePlayer
  Local integer pl, i, k
  ' PickListRows, not PickList -- see EnterPlayer for why (255-char limit)
  Local string it$(MAXPL - 1)
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then
    Status "Wait for this race to finish"
    Exit Sub
  EndIf
  If ne = 0 Then
    Status "Nobody's racing yet"
    Exit Sub
  EndIf
  ' who's actually IN this race -- not the whole membership, only they
  ' can leave a race they're not even in
  For i = 0 To ne - 1
    it$(i) = pn$(ep(i)) + "  $" + Str$(Int(pb(ep(i))))
  Next
  k = PickListRows("WHO'S LEAVING?", it$(), ne)
  If k < 0 Then Exit Sub
  pl = ep(k)
  For i = k To ne - 2
    ep(i) = ep(i + 1)
    ec(i) = ec(i + 1)
    wasNew(i) = wasNew(i + 1)
  Next
  ne = ne - 1
  Status pn$(pl) + " sits this one out - the account's still there next time"
End Sub

' the membership list: every driver who's ever joined, their kitty and
' wins -- not just who's in the current race (that's ENTER PLAYER's own
' list) or who can leave it (LeavePlayer's)
Sub Drivers
  Local string it$(MAXPL - 1)
  Local integer i, pl
  If np = 0 Then
    i = PickList("DRIVERS", "Nobody's signed up yet|CLOSE")
    ShowTrack
    Exit Sub
  EndIf
  For i = 0 To np - 1
    it$(i) = pn$(i) + "  $" + Str$(Int(pb(i))) + "  " + Str$(wins(i)) + " win" + Choice(wins(i) = 1, "", "s")
  Next
  ' PickListRows already redraws the track once, underneath the popup, as
  ' it closes -- a second ShowTrack here would just be the same redraw
  ' done twice for nothing
  pl = PickListRows("DRIVERS - PICK TO JOIN THE RACE", it$(), np)
  If pl < 0 Then Exit Sub
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then
    Status "Wait for this race to finish"
    Exit Sub
  EndIf
  If phase = 3 Then NewRace
  If ne >= NCARS Then
    Status "All the cars are in this race"
    Exit Sub
  EndIf
  JoinRace pl, 0, 0
End Sub

' --- racing -------------------------------------------------------------------
Sub NewEvent
  Local integer i
  raceNum = 1
  pot = 0
  For i = 0 To MAXPL - 1
    wins(i) = 0
    startB(i) = -1
  Next
End Sub

Sub NewRace
  ' entrants are NOT cleared here -- LEAVE is the only way out once
  ' you're in (or going broke when a new event's entry fee comes due,
  ' see RaceOver), so nobody has to re-enter every single race
  nfin = 0
  phase = 0
  ShowTrack
End Sub

' base pace 1.8-2.7 px a tick, up to 40% slower for a fully damaged car
' a pricier car is a genuinely quicker one, not just a status symbol --
' log-scaled (price spans 22x across the lineup, HOLDEN to FERRARI;
' linear would make the priciest car absurdly dominant), and modest
' (0.92-1.08, an 8% swing either side of the middle) so the per-lap random
' roll below stays the biggest factor and a cheap car can still win
Function PriceFactor(c As integer) As float
  If carMaxVal <= carMinVal Then
    PriceFactor = 1
  Else
    PriceFactor = 0.92 + 0.16 * (Log(carVal(c)) - Log(carMinVal)) / (Log(carMaxVal) - Log(carMinVal))
  EndIf
End Function

Function RandSpeed(i As integer) As float
  RandSpeed = (1.8 + Rnd * 0.9) * (1 - dmg(ec(i)) / 100 * 0.4) * PriceFactor(ec(i))
End Function

Sub StartRace
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then Exit Sub
  If phase = 3 Then NewRace
  If ne = 0 Then
    Status "Nobody's entered yet - ENTER PLAYER"
    Exit Sub
  EndIf
  BeginRace 0
End Sub

' the actual race start: lap/finish state reset, the pre-race word, then
' qualifying. Called by StartRace (fresh entrants, checked above), and by
' RaceOver to carry the same line-up straight into an event's next race
' without making everyone re-join
' midEvent: 1 when this is the next race of an event already under way
' (called from RaceOver), 0 for a fresh start (StartRace). The pre-race
' garage chat is skipped when midEvent, or every player gets TWO mechanic
' meets back to back between races -- the BILL/CLEAN scene RaceOver just
' showed them already covers the car's condition
Sub BeginRace(midEvent As integer)
  Local integer i
  For i = 0 To ne - 1
    laps(i) = 0
    fin(i) = 0
    place(i) = 0
    shown(i) = 0
  Next
  nfin = 0
  ' the garage's "Entered:" segment, and whatever status or one-off
  ' message was last showing, are all done their job now -- but which
  ' race and which track stays useful the whole way through qualifying/
  ' grid/racing, so slot 1 gets its own short version instead of going
  ' blank (segment 2 is still the running order once racing starts, see
  ' RaceTicker; Status stops writing slot 3 for the same reason once
  ' phase says qualifying/grid/racing)
  TickerSeg 0, ""
  TickerSeg 1, "Race " + Str$(raceNum) + " of " + Str$(EVENT_RACES) + " - " + tName$
  TickerSeg 3, ""
  TickerMsg ""
  ' the pre-race word in the garage, one entrant at a time (nothing about
  ' who'll win -- the race is random). Skipped for a brand-new player --
  ' they just had their WELCOME scene, and a second garage visit straight
  ' after feels like a double-up
  If Not midEvent Then
    For i = 0 To ne - 1
      If Not wasNew(i) Then Scene ep(i), ec(i), "PRE_" + Mechanic$(dmg(ec(i))), "PRER"
    Next
  EndIf
  phase = 1
  qIdx = 0
  ShowTrack
  StartQualifier
End Sub

' qualifying: every car does one flying lap, all on track together. They
' leave the line one after another (Q_STAGGER ticks apart) so they don't
' start on top of each other, and each is timed from its own start, in
' ticks, so a slow board can't make it unfair. Cars that meet go side by
' side (nobody is held back -- that would cost them time). The times set
' the grid.
Sub StartQualifier
  Local integer i
  For i = 0 To ne - 1
    prog(i) = 0
    lat(i) = Choice(i Mod 2 = 0, -5, 5)
    latV(i) = 0
    spd(i) = RandSpeed(i)
    qDone(i) = 0
    qTime(i) = 0
    shown(i) = 0
  Next
  qTicks = 0
  Status "QUALIFYING: " + Str$(ne) + " car" + Choice(ne = 1, "", "s") + ", one flying lap each - fastest gets pole"
End Sub

Sub QualifyTick
  Local integer i, k, running, hid
  Local float dp, dl, shove, dirn
  qTicks = qTicks + 1
  ' only hidden if it's actually where a car is -- see RaceTick/Talk for
  ' the same fix and why (the whole track was tried first, but the track
  ' is most of the screen, so that barely helped)
  hid = 0
  For i = 0 To ne - 1
    If Not qDone(i) And shown(i) And CurOver(lastX(i) - 11, lastY(i) - 11, 23, 23) Then hid = 1
  Next
  If hid Then CurHide
  For i = 0 To ne - 1
    If Not qDone(i) Then EraseCar i
  Next
  For i = 0 To ne - 1
    ' car i leaves the line i * Q_STAGGER ticks after the first
    If Not qDone(i) And qTicks > i * Q_STAGGER Then
      prog(i) = prog(i) + spd(i)
      If prog(i) >= trackLen Then
        qDone(i) = 1
        qTime(i) = qTicks - i * Q_STAGGER
      EndIf
    EndIf
  Next
  ' cars on the road together move over to pass
  For i = 0 To ne - 2
    For k = i + 1 To ne - 1
      If Not qDone(i) And Not qDone(k) And qTicks > k * Q_STAGGER Then
        ' wrap the gap around the loop, the same as RaceTick -- otherwise a
        ' car finishing its lap (prog near trackLen) and one still staggered
        ' at the start (prog near 0) look almost a lap apart instead of
        ' side by side at the line
        dp = Abs(prog(i) - prog(k))
        dp = dp - Int(dp / trackLen) * trackLen
        dp = Min(dp, trackLen - dp)
        dl = lat(i) - lat(k)
        If dp <= MIN_PROG_GAP And Abs(dl) < MIN_LAT_GAP Then
          shove = (MIN_LAT_GAP - Abs(dl)) / 2
          dirn = Choice(dl >= 0, 1, -1)
          lat(i) = Max(-LAT_LIMIT, Min(LAT_LIMIT, lat(i) + shove * dirn))
          lat(k) = Max(-LAT_LIMIT, Min(LAT_LIMIT, lat(k) - shove * dirn))
        EndIf
      EndIf
    Next
  Next
  For i = 0 To ne - 1
    If Not qDone(i) Then
      running = running + 1
      ' a car still waiting its turn isn't on the road yet
      If qTicks > i * Q_STAGGER Then DrawCar i
    EndIf
  Next
  If hid Then CurShow
  ' drawn every tick (not just when someone finishes) so it's draggable
  ' clear of the action at any time
  QualPanel
  If running = 0 Then FinishQualifying
End Sub

' the live corner panel: every car's time so far, in finishing order, as
' they cross the line one by one
' the corner panel's default spot (top-right of the track area), and
' dragging it clear of the action by its title bar -- one shared position
' for whichever of QualPanel/HotPanel is showing (the race's own running
' order lives in the ticker instead, see RaceTicker)
Sub PanelDrag
  Local integer rh
  rh = fh(0) + 4
  If panelX = 0 And panelY = 0 Then
    panelX = W - PANEL_W - 8
    panelY = CT + 6
  EndIf
  If Not hasMouse Then Exit Sub
  If gml Then
    If Not pDragging Then
      If gmx >= panelX And gmx < panelX + PANEL_W And gmy >= panelY And gmy < panelY + rh + 8 Then
        pDragging = 1
        panelDX = gmx - panelX
        panelDY = gmy - panelY
      EndIf
    Else
      panelX = Max(0, Min(W - PANEL_W, gmx - panelDX))
      panelY = Max(CT, Min(CB - rh - 8, gmy - panelDY))
    EndIf
  Else
    pDragging = 0
  EndIf
End Sub

' restores the track under wherever the panel was last drawn -- called
' before it's drawn again, so dragging it moves it instead of leaving a
' trail of copies behind (it's redrawn every tick, and its own size
' changes as rows are added, so a plain redraw at the new spot isn't enough)
Sub PanelErase
  If panelLastH > 0 Then BLIT FRAMEBUFFER F, N, panelLastX - 2, panelLastY - 2, panelLastX - 2, panelLastY - 2, PANEL_W + 4, panelLastH + 4
End Sub

Sub QualPanel
  Local integer i, n, rh, x, y, ph, away, row
  Local string qt$(NCARS - 1)
  PanelDrag
  rh = fh(0) + 4
  x = panelX
  y = panelY
  For i = 0 To ne - 1
    If qDone(i) Then n = n + 1
    ' left the line already, per StartQualifier's stagger -- while nobody's
    ' finished yet, this is the only thing that changes tick to tick, so
    ' the ticker's fallback text below reads as counting up, not stuck
    If qTicks > i * Q_STAGGER Then away = away + 1
  Next
  ph = (n + 1) * rh + 8
  ' the box itself only actually changes when it's dragged or another row
  ' finishes -- erasing and redrawing an unchanged box every tick (this
  ' runs every RACE_MS) flickered badly once a bigger field meant more
  ' rows to erase and redraw for nothing. The ticker segment below still
  ' updates every tick regardless (it needs to, for the "X away" count)
  If ph <> panelLastH Or x <> panelLastX Or y <> panelLastY Then
    PanelErase
    CurHide
    RBox x, y, PANEL_W, ph, 6, C_INK, C_BAR
    CurShow
    PText x + PANEL_W \ 2, y + 4 + rh \ 2, "TIMES", "C", 0, C_AMBER
    row = 0
    For i = 0 To ne - 1
      If qDone(i) Then
        PText x + 8, y + 4 + (row + 1) * rh + rh \ 2, pn$(ep(i)) + " " + Str$(qTime(i) * RACE_MS / 1000, 0, 1) + "s", "L", 0, C_INK
        row = row + 1
      EndIf
    Next
    panelLastX = x : panelLastY = y : panelLastH = ph
  EndIf
  ' one time at a time, not all of them joined into a single line --
  ' TickerSeg cuts a segment to 60 characters, so with a full field the
  ' joined line filled that up after just the first two or three finished
  ' and every later time was silently cut off -- it looked frozen, not
  ' just cluttered. Before anyone's finished, "X away" counts up as cars
  ' leave the line (Q_STAGGER ticks apart) every tick instead of sitting
  ' on a static "Qualifying...", the whole time a big field's staggering
  ' out; once times start coming in, one rotates into view every couple
  ' of seconds -- the same live segment RaceTicker uses once the race
  ' itself is running (qualifying and racing never overlap, so no clash)
  If n = 0 Then
    TickerSeg 2, "QUALIFYING: " + Str$(away) + "/" + Str$(ne) + " away"
  ElseIf Timer - qualTickerT0 >= 2000 Or qualRotIdx >= n Then
    qualTickerT0 = Timer
    If qualRotIdx >= n Then qualRotIdx = 0
    row = 0
    For i = 0 To ne - 1
      If qDone(i) Then
        qt$(row) = pn$(ep(i)) + " " + Str$(qTime(i) * RACE_MS / 1000, 0, 1) + "s"
        row = row + 1
      EndIf
    Next
    TickerSeg 2, "TIME " + Str$(qualRotIdx + 1) + "/" + Str$(n) + ": " + qt$(qualRotIdx)
    qualRotIdx = qualRotIdx + 1
  EndIf
End Sub

' fastest lap starts furthest ahead, GRID_GAP px per grid place. The grid
' and every time are shown for a few seconds (phase 5, GridTick) before
' the race starts itself
Sub FinishQualifying
  Local integer i, k, rank
  For i = 0 To ne - 1
    rank = 0
    For k = 0 To ne - 1
      If qTime(k) < qTime(i) Or (qTime(k) = qTime(i) And k < i) Then rank = rank + 1
    Next
    qRank(i) = rank
    ' two to a row, pole on the left, rows GRID_GAP apart
    prog(i) = ((ne - 1) \ 2 - rank \ 2) * GRID_GAP
    lat(i) = Choice(rank Mod 2 = 0, -7, 7)
    latV(i) = 0
    spd(i) = RandSpeed(i)
  Next
  phase = 5
  gridT0 = Timer
  ShowGrid
  Status "Qualifying's set the grid - race starts in a few seconds"
End Sub

' the qualifying results: grid order and every lap time, over the track
Sub ShowGrid
  Local integer i, k, rh, x, y, gw
  rh = fh(0) + 10
  gw = W * 3 \ 5
  x = (W - gw) \ 2
  y = CT + 20
  CurHide
  ShowTrack
  CurHide
  RBox x, y, gw, (ne + 1) * rh + 10, 6, C_INK, C_BAR
  RBox x, y, gw, rh + 4, 6, C_INK, C_GRN_BASE
  CurShow
  PText x + gw \ 2, y + rh \ 2 + 2, "GRID - QUALIFYING TIMES", "C", 0, C_INK
  For k = 0 To ne - 1
    For i = 0 To ne - 1
      If qRank(i) = k Then
        PText x + 14, y + 6 + (k + 1) * rh + rh \ 2, Str$(k + 1) + ". " + pn$(ep(i)) + " - " + carName$(ec(i)) + "  " + Str$(qTime(i) * RACE_MS / 1000, 0, 1) + "s", "L", 0, C_INK
      EndIf
    Next
  Next
End Sub

' phase 5: the grid's up for a few seconds, then the race gets going
' on its own, same as a PitScene's timeout
Sub GridTick
  If Timer - gridT0 > 4000 Then
    phase = 2
    ShowTrack
    Status "Race " + Str$(raceNum) + " of " + Str$(EVENT_RACES) + ", " + Str$(lapsToWin) + " lap" + Choice(lapsToWin = 1, "", "s") + " - " + Str$(ne) + " car" + Choice(ne = 1, "", "s") + ", event pot $" + Str$(Int(pot))
  EndIf
End Sub

Sub RaceTick
  Local integer i, k, oldLap, hid
  Local float dp, dl, shove, dirn, sd, closeSpd
  For i = 0 To ne - 1
    If Not fin(i) Then
      oldLap = Int(prog(i) / trackLen)
      prog(i) = prog(i) + spd(i)
      ' the random nudge changes the sideways speed, not the position, so
      ' a car weaves gently across the road (a nudge to the position every
      ' tick made the whole car shiver and its tyres jump a pixel)
      latV(i) = Max(-0.35, Min(0.35, latV(i) * 0.9 + (Rnd - 0.5) * LAT_DRIFT * 0.3))
      lat(i) = lat(i) + latV(i)
      If Abs(lat(i)) > LAT_LIMIT Then
        lat(i) = Max(-LAT_LIMIT, Min(LAT_LIMIT, lat(i)))
        latV(i) = -latV(i)
      EndIf
      If Int(prog(i) / trackLen) > oldLap Then
        laps(i) = laps(i) + 1
        ' pace re-rolled every lap, so places can change all race
        spd(i) = RandSpeed(i)
        If laps(i) >= lapsToWin Then
          fin(i) = 1
          nfin = nfin + 1
          place(i) = nfin
          TickerMsg Ordinal$(place(i)) + ": " + pn$(ep(i)) + " (" + carName$(ec(i)) + ") past the post!"
        EndIf
      EndIf
    EndIf
  Next
  ' shove apart cars that are close along the track and side by side
  For i = 0 To ne - 2
    For k = i + 1 To ne - 1
      If Not fin(i) And Not fin(k) Then
        dp = Abs(prog(i) - prog(k))
        dp = dp - Int(dp / trackLen) * trackLen
        dp = Min(dp, trackLen - dp)
        dl = lat(i) - lat(k)
        If dp <= MIN_PROG_GAP And Abs(dl) < MIN_LAT_GAP Then
          shove = (MIN_LAT_GAP - Abs(dl)) / 2
          dirn = Choice(dl >= 0, 1, -1)
          lat(i) = Max(-LAT_LIMIT, Min(LAT_LIMIT, lat(i) + shove * dirn))
          lat(k) = Max(-LAT_LIMIT, Min(LAT_LIMIT, lat(k) - shove * dirn))
          ' and steer apart, so they go side by side to pass
          latV(i) = 0.3 * dirn
          latV(k) = -0.3 * dirn
          ' no room to go side by side (the edge of the road): the car
          ' behind tucks in behind instead of driving through -- a bump,
          ' not a clean pass, so it can pick up damage (a small chance
          ' each tick it's boxed in, not every tick, or a long queue
          ' behind a slow car would wreck it in seconds). How hard depends
          ' on the closing speed between them -- see CarContact
          If Abs(lat(i) - lat(k)) < MIN_LAT_GAP Then
            sd = prog(i) - prog(k)
            sd = sd - Int(sd / trackLen + 0.5) * trackLen
            closeSpd = Abs(spd(i) - spd(k))
            ' (never back over the line it just crossed, or that lap would
            ' count twice)
            ' silent before this -- a bump mid-race left no sign of itself
            ' until the mechanic's bill after the finish. Called out on the
            ' ticker now, same as a finish ("past the post!"), and flagged
            ' LAPPING when it's the leader going through backmarker traffic
            ' rather than two cars on the same lap racing for position
            If sd >= 0 Then
              prog(k) = Max(Int(prog(k) / trackLen) * trackLen + 0.01, prog(k) - (MIN_PROG_GAP - dp))
              CarContact ec(i), k, closeSpd, laps(i) <> laps(k)
            Else
              prog(i) = Max(Int(prog(i) / trackLen) * trackLen + 0.01, prog(i) - (MIN_PROG_GAP - dp))
              CarContact ec(k), i, closeSpd, laps(k) <> laps(i)
            EndIf
          EndIf
        EndIf
      EndIf
    Next
  Next
  ' all the old spots first, then all the new ones, so one car's erase
  ' can't wipe another's fresh drawing. Only hidden at all if it's
  ' actually sitting where a car is -- the whole track was tried first,
  ' but the track IS most of the screen, so a cursor resting anywhere on
  ' it still hid/showed every tick; checking each car's own small erase
  ' box instead means it only blinks when a car is genuinely about to
  ' pass under it (see Talk for the same fix on the bubbles, and why)
  hid = 0
  For i = 0 To ne - 1
    If shown(i) And CurOver(lastX(i) - 11, lastY(i) - 11, 23, 23) Then hid = 1
  Next
  If hid Then CurHide
  ' every car on screen is wiped (EraseCar skips ones that aren't); only
  ' those still racing are drawn again -- a finished car leaves the track
  ' instead of being left frozen on it
  For i = 0 To ne - 1
    EraseCar i
  Next
  For i = 0 To ne - 1
    If Not fin(i) Then DrawCar i
  Next
  If hid Then CurShow
  ' the running order scrolls through the ticker instead of sitting in a
  ' box over the track -- that's what the ticker's for, and it leaves the
  ' whole screen free for the race
  RaceTicker
  If nfin >= ne Then RaceOver
End Sub

' one car boxed in behind another with nowhere to go (see RaceTick).
' passerCar is the ec() index of the car it's stuck behind; victimEntrant
' is the entrant index (into ep()/ec()/spd()/prog()) of the one taking
' the knock. closeSpd is the gap between their current RandSpeed pace --
' see the COLLIDE_*/CRASH_* consts for what that buys: worse odds and a
' harder hit the faster the passing car was catching up
Sub CarContact(passerCar As integer, victimEntrant As integer, closeSpd As float, lapping As integer)
  Local integer victimCar
  Local string lp$
  victimCar = ec(victimEntrant)
  lp$ = Choice(lapping, "LAPPING! ", "")
  If Rnd < Min(COLLIDE_CHANCE_MAX, COLLIDE_BASE + closeSpd * COLLIDE_SPD_K) Then
    If closeSpd > CRASH_SPD And Rnd < (closeSpd - CRASH_SPD) * CRASH_CHANCE_K Then
      dmg(victimCar) = Min(100, dmg(victimCar) + CRASH_DMG_MIN + Rnd * CRASH_DMG_RANGE)
      spd(victimEntrant) = Max(0.5, spd(victimEntrant) * CRASH_SPD_CUT)
      prog(victimEntrant) = Max(Int(prog(victimEntrant) / trackLen) * trackLen + 0.01, prog(victimEntrant) - spd(victimEntrant) * CRASH_SPIN_TICKS)
      TickerMsg lp$ + "CRASH! " + carName$(victimCar) + " spins out avoiding " + carName$(passerCar) + " - heavy damage"
    Else
      dmg(victimCar) = Min(100, dmg(victimCar) + 1 + Rnd * 2)
      spd(victimEntrant) = Max(0.5, spd(victimEntrant) * BUMP_SPD_CUT)
      TickerMsg lp$ + carName$(passerCar) + " squeezes past " + carName$(victimCar) + " - contact, a little paint"
    EndIf
    ' terminal damage mid-race: the same TOO_DAMAGED lockout that keeps a
    ' wrecked car out of the NEXT race, but reached during this one -- it
    ' pulls in now instead of trundling round at walking pace for the
    ' rest of the field to lap. No place is set, same as never crossing
    ' the line, so it can't win this race and RaceOver's placings skip
    ' straight over it
    If dmg(victimCar) >= TOO_DAMAGED And Not fin(victimEntrant) Then
      fin(victimEntrant) = 1
      nfin = nfin + 1
      TickerMsg carName$(victimCar) + " (" + pn$(ep(victimEntrant)) + ") retires - too much damage to continue"
    EndIf
  EndIf
End Sub

' the garage's entrant list, in the ticker: one entrant at a time ("2/6:
' Dave (Ford)"), rotating every few seconds, rather than trying to join
' them all onto one line -- with more than a handful entered that either
' clipped names short (a plain 60-char TickerSeg) or, worse, risked
' "String too long" building the joined line in the first place (see
' DrawGarage's own history of both). Called every time DrawGarage draws
' (so a fresh entry shows straight away) and needs no other driver
Sub EntrantsTicker
  ' the garage's own segment -- once a race is under way BeginRace hands
  ' slot 0 to something else, and this must not fight it for it
  If phase <> 0 Then Exit Sub
  If ne = 0 Then
    tkSeg$(0) = "Nobody's entered yet"
    entIdx = 0
    entLastNe = 0
    Exit Sub
  EndIf
  If entIdx >= ne Then entIdx = 0
  ' a join or a LEAVE changes who's showing straight away, not up to
  ' 3 seconds later
  If tkSeg$(0) = "" Or ne <> entLastNe Or Timer - entT0 >= 3000 Then
    tkSeg$(0) = Str$(entIdx + 1) + "/" + Str$(ne) + ": " + pn$(ep(entIdx)) + " (" + carName$(ec(entIdx)) + ")"
    entIdx = (entIdx + 1) Mod ne
    entT0 = Timer
    entLastNe = ne
  EndIf
End Sub

' the live running order, in the ticker: 1st|2nd|3rd together on one
' line, ranked by total distance covered (laps * lap length + this lap's
' progress), with each's gap to the leader in (rough, pace-based) whole
' seconds. A finished car keeps its real finishing place() rather than
' being ranked by its frozen, since-crossed-the-line progress. Names cut
' to 8 characters here -- TickerSeg cuts the whole segment to 60, and 3
' places plus a two-digit gap each already uses 44 of those, so a long
' name can't be let through uncapped without risking the field itself
' silently losing data at 60. Top 3 only, not the whole field: with up to
' NCARS in a race there's no way to fit everyone in 60 characters at all,
' and the leaders are what a ticker's actually for. Updated every couple
' of seconds, not every tick, or it'd never scroll -- TickerMsg restarts it
Sub RaceTicker
  Local integer i, k, leadI, r, top
  Local float tp(NCARS - 1), key(NCARS - 1), leadDist, gap
  Local integer rk(NCARS - 1)
  Local string s$
  If Timer - raceTickerT0 < 2000 Then Exit Sub
  raceTickerT0 = Timer
  leadDist = -1
  leadI = -1
  For i = 0 To ne - 1
    tp(i) = laps(i) * trackLen + (prog(i) Mod trackLen)
    key(i) = Choice(fin(i), place(i), 1000000 - tp(i))
    If Not fin(i) And tp(i) > leadDist Then
      leadDist = tp(i)
      leadI = i
    EndIf
  Next
  For i = 0 To ne - 1
    rk(i) = 0
    For k = 0 To ne - 1
      If key(k) < key(i) Or (key(k) = key(i) And k < i) Then rk(i) = rk(i) + 1
    Next
  Next
  top = Min(3, ne) - 1
  For r = 0 To top
    For i = 0 To ne - 1
      If rk(i) = r Then
        gap = 0
        If Not fin(i) And leadI >= 0 And i <> leadI Then gap = (leadDist - tp(i)) / Max(0.3, spd(leadI)) * RACE_MS / 1000
        s$ = s$ + Str$(r + 1) + "." + Left$(pn$(ep(i)), 8) + Choice(gap > 0, " +" + Str$(gap, 0, 0) + "s", "") + Choice(r < top, " | ", "")
        Exit For
      EndIf
    Next
  Next
  TickerSeg 2, s$
End Sub

Sub RaceOver
  Local integer i, k, win, second, third, c, dcount, need, nq, continuing
  Local integer pod1, pod2, pod3
  Local float fr, share
  Local string d$, msg$, dm$(NCARS - 1)
  Local integer dmM(NCARS - 1)
  phase = 3
  pod1 = -1
  second = -1
  third = -1
  For i = 0 To ne - 1
    If place(i) = 1 Then win = i
    If place(i) = 2 Then second = i
    If place(i) = 3 Then third = i
  Next
  wins(ep(win)) = wins(ep(win)) + 1
  ' a random cost event for every entrant, win or lose
  For i = 0 To ne - 1
    RollEvent fr, d$
    If d$ <> "" Then
      c = ec(i)
      pb(ep(i)) = pb(ep(i)) - carVal(c) * fr
      dmg(c) = Min(100, dmg(c) + fr * 60)
      dcount = dcount + 1
      TickerMsg carName$(c) + ": " + d$ + " -$" + Str$(Int(carVal(c) * fr))
      dm$(i) = d$
      dmM(i) = Int(carVal(c) * fr)
    EndIf
  Next
  SaveCars
  For i = 0 To NCARS - 1
    hotDone(i) = 0
  Next
  If raceNum < EVENT_RACES Then
    msg$ = carName$(ec(win)) + " (" + pn$(ep(win)) + ") wins race " + Str$(raceNum) + " of " + Str$(EVENT_RACES) + " - pot $" + Str$(Int(pot))
    If ne >= 4 And third >= 0 Then msg$ = msg$ + " | 2nd " + pn$(ep(second)) + ", 3rd " + pn$(ep(third))
    raceNum = raceNum + 1
    ' same line-up straight into the next race -- no re-joining mid-event
    continuing = 1
  Else
    ' cash up: one race win qualifies, two if your budget fell this event
    For i = 0 To np - 1
      need = Choice(startB(i) >= 0 And pb(i) < startB(i), 2, 1)
      If wins(i) >= need Then nq = nq + 1
    Next
    If nq > 0 And pot > 0 Then
      share = pot / nq
      For i = 0 To np - 1
        need = Choice(startB(i) >= 0 And pb(i) < startB(i), 2, 1)
        If wins(i) >= need Then pb(i) = pb(i) + share
      Next
      msg$ = "EVENT OVER! " + carName$(ec(win)) + " wins. $" + Str$(Int(pot)) + " split " + Str$(nq) + " way" + Choice(nq = 1, "", "s")
    Else
      msg$ = "EVENT OVER! " + carName$(ec(win)) + " wins. Nobody cashed up"
    EndIf
    ' the event podium (3+ race events only): ranked on race wins, a cash
    ' bonus on top of the pot -- read before NewEvent clears the win count
    If EVENT_RACES >= 3 Then RankPodium pod1, pod2, pod3
    NewEvent
  EndIf
  SavePlayers
  Status msg$ + Choice(dcount, " | " + Str$(dcount) + " damage", " | no damage")
  ' several Scene()s in a row here (one per damaged car, then up to 3 for
  ' the podium) -- sceneChaining stops each one's PitScene flashing the
  ' bare track before the next one's backdrop covers it again; BeginRace/
  ' NewRace below draw whatever's actually next once the run's done, same
  ' as always
  sceneChaining = 1
  If dcount Then
    For i = 0 To ne - 1
      If dm$(i) <> "" Then
        qE$ = dm$(i)
        qM$ = Str$(dmM(i))
        Scene ep(i), ec(i), "BILL", "BILLR"
      EndIf
    Next
  Else
    Scene ep(win), ec(win), "CLEAN", "CLEANR"
  EndIf
  If pod1 >= 0 Then ShowPodium pod1, pod2, pod3
  sceneChaining = 0
  ' the lineup always carries straight into whatever's next, race or new
  ' event -- LEAVE is the only way out. A new event used to re-charge
  ' the entry fee here and scratch anyone who couldn't cover it, but
  ' with EVENT_RACES defaulting to 1, that ran after literally every
  ' single race and could empty the whole lineup the moment someone's
  ' budget dipped -- exactly the "reload every race" problem this was
  ' meant to avoid. One entry fee, paid at EnterPlayer, now covers a
  ' player for as long as they stay in
  If continuing Then
    BeginRace 1
  Else
    SavePlayers
    NewRace
  EndIf
End Sub

' the event's top 3 by race wins (ties keep the earlier player), -1 for a
' place nobody's filled -- then the cash bonus on top of the pot
Sub RankPodium(p1 As integer, p2 As integer, p3 As integer)
  Local integer i, w1, w2, w3
  p1 = -1
  p2 = -1
  p3 = -1
  For i = 0 To np - 1
    If wins(i) > w1 Then
      p3 = p2 : w3 = w2
      p2 = p1 : w2 = w1
      p1 = i : w1 = wins(i)
    ElseIf wins(i) > w2 Then
      p3 = p2 : w3 = w2
      p2 = i : w2 = wins(i)
    ElseIf wins(i) > w3 Then
      p3 = i : w3 = wins(i)
    EndIf
  Next
  pb(p1) = pb(p1) + POD_CASH1
  TickerMsg "EVENT PODIUM! 1st " + pn$(p1) + " +$" + Str$(POD_CASH1)
  If p2 >= 0 Then
    pb(p2) = pb(p2) + POD_CASH2
    TickerMsg "2nd " + pn$(p2) + " +$" + Str$(POD_CASH2)
  EndIf
  If p3 >= 0 Then
    pb(p3) = pb(p3) + POD_CASH3
    TickerMsg "3rd " + pn$(p3) + " +$" + Str$(POD_CASH3)
  EndIf
End Sub

' the podium celebration: the mechanic and each place-getter, one at a
' time, same as the damage-bill loop after an ordinary race
Sub ShowPodium(p1 As integer, p2 As integer, p3 As integer)
  ShowPodiumPlace p1, 1
  If p2 >= 0 Then ShowPodiumPlace p2, 2
  If p3 >= 0 Then ShowPodiumPlace p3, 3
End Sub

Sub ShowPodiumPlace(pl As integer, rank As integer)
  Local integer c, i
  c = -1
  For i = 0 To NCARS - 1
    If owner$(i) = pn$(pl) Then c = i
  Next
  If c < 0 Then c = 0
  qP$ = Ordinal$(rank)
  qM$ = Str$(Int(Choice(rank = 1, POD_CASH1, Choice(rank = 2, POD_CASH2, POD_CASH3))))
  Scene pl, c, "PODIUM", "PODIUMR"
End Sub

' "1st".."8th" (and beyond) -- used for the podium (always 1-3) and now
' the race-finish ticker too (up to NCARS)
Function Ordinal$(n As integer) As string
  Local string s$
  s$ = Str$(n)
  If n Mod 100 >= 11 And n Mod 100 <= 13 Then
    Ordinal$ = s$ + "th"
  ElseIf n Mod 10 = 1 Then
    Ordinal$ = s$ + "st"
  ElseIf n Mod 10 = 2 Then
    Ordinal$ = s$ + "nd"
  ElseIf n Mod 10 = 3 Then
    Ordinal$ = s$ + "rd"
  Else
    Ordinal$ = s$ + "th"
  EndIf
End Function

' --- the circuits --------------------------------------------------------------
' pick a circuit, 11 to a page; the track is rebuilt and redrawn (entries
' for the next race stay entered)
Sub ChooseTrack
  Local string r$, n$
  Local integer i, k, first, pick, x
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then
    Status "Change the track between races"
    Exit Sub
  EndIf
  first = 0
  Do
    r$ = ""
    Restore Tracks
    Read nTracks
    For i = 0 To nTracks - 1
      Read n$
      For k = 1 To NRAW * 2
        Read x
      Next
      If i >= first And i < first + 11 Then r$ = r$ + Choice(i = trackNo, "* ", "  ") + n$ + "|"
    Next
    r$ = r$ + Choice(first + 11 < nTracks, "MORE TRACKS...", "BACK TO THE START...")
    ' PickList already redraws the garage once, underneath it, as it
    ' closes -- a second ShowTrack on the way out here was just the same
    ' redraw done twice for nothing
    pick = PickList("TRACK - PICK A CIRCUIT", r$)
    If pick < 0 Then Exit Sub
    If pick < Min(11, nTracks - first) Then Exit Do
    first = Choice(first + 11 < nTracks, first + 11, 0)
  Loop
  trackNo = first + pick
  If phase = 3 Then NewRace
  BuildTrack
  DrawTrack
  RaceInfoTicker
  Status "Track: " + tName$ + " - ENTER PLAYER, then START RACE"
  ' the ticker still had the old venue in it otherwise
  TickerMsg "Circuit Race at " + tName$ + " - " + Str$(EVENT_RACES) + "-race events, $" + Str$(ENTRY_FEE) + " entry. TRACK picks the circuit"
End Sub

' --- the garage ---------------------------------------------------------------
' drop in on the mechanic: his word on how your car's running
Sub Visit
  Local integer c
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then
    Status "The garage is busy - after the race"
    Exit Sub
  EndIf
  ' ShowTrack only on the way out without a scene to follow it -- see
  ' HotLap for why
  c = PickOwned("GARAGE - WHOSE CAR?")
  If c < 0 Then
    ShowTrack
    Exit Sub
  EndIf
  Scene PlayerNum(owner$(c)), c, "PRE_" + Mechanic$(dmg(c)), Choice(dmg(c) >= TOO_DAMAGED, "VISITBADR", "VISITR")
End Sub

' sell a car back to the garage for its value less half its damage (the
' garage fixes her up for the next buyer)
Sub SellCar
  Local integer c, pl, i, price, dismiss
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then
    Status "Sell between races"
    Exit Sub
  EndIf
  ' ShowTrack only on the way out without another popup to follow it --
  ' see HotLap for why
  c = PickOwned("SELL - WHICH CAR?")
  If c < 0 Then
    ShowTrack
    Exit Sub
  EndIf
  For i = 0 To ne - 1
    If ec(i) = c And phase = 0 Then
      ' a plain Status here is easy to miss (it's just a ticker line now,
      ' not a big on-screen band) -- this is a hard "no", so it needs a
      ' box the player has to dismiss, or it looks like SELL CAR just did
      ' nothing at all
      dismiss = PickList(carName$(c) + " is entered in the next race - can't sell her now", "OK")
      ShowTrack
      Exit Sub
    EndIf
  Next
  pl = PlayerNum(owner$(c))
  price = Int(carVal(c) * (1 - dmg(c) / 100 * 0.5))
  If PickList("SELL THE " + carName$(c) + " FOR $" + Str$(price) + "?", "YES, SELL HER|NO, KEEP HER") <> 0 Then Exit Sub
  pb(pl) = pb(pl) + price
  owner$(c) = ""
  dmg(c) = 0
  SavePlayers
  SaveCars
  Status pn$(pl) + " sold the " + carName$(c) + " for $" + Str$(price) + " - now has $" + Str$(Int(pb(pl)))
  qM$ = Str$(price)
  Scene pl, c, "SELL", "SELLR"
End Sub

' --- hot laps and repairs ---------------------------------------------------
' the player called n$ (-1 if there isn't one)
Function PlayerNum(n$) As integer
  Local integer i
  PlayerNum = -1
  For i = 0 To np - 1
    If pn$(i) = n$ Then PlayerNum = i
  Next
End Function

' pick an owned car: its number, or -1. PickListRows (an array), not
' PickList (one joined string) -- 20 cars' worth of names/owners/damage
' joined into a single string runs well past MMBasic's 255-char limit
Function PickOwned(t$) As integer
  Local string it$(NCARS - 1)
  Local integer i, c
  For i = 0 To NCARS - 1
    it$(i) = carName$(i) + "  " + Choice(owner$(i) = "", "unowned", owner$(i)) + "  dmg " + Str$(Int(dmg(i))) + "%"
  Next
  c = PickListRows(t$, it$(), NCARS)
  PickOwned = -1
  If c < 0 Then Exit Function
  If owner$(c) = "" Then
    i = PickList(carName$(c) + " has no owner yet - buy it with ENTER PLAYER", "OK")
    ShowTrack
    Exit Function
  EndIf
  If PlayerNum(owner$(c)) < 0 Then
    i = PickList(carName$(c) + "'s owner isn't a player any more", "OK")
    ShowTrack
    Exit Function
  EndIf
  PickOwned = c
End Function

' one car alone, one flying lap against a target: beat it for prize money.
' Damage slows the car the same as in a race, so the target is set for the
' car's damage -- a wrecked car can still earn its repairs.
Sub HotLap
  Local integer c, pl
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then
    Status "Hot laps are between races"
    Exit Sub
  EndIf
  ' ShowTrack only on the way out without a scene to follow it -- PitScene
  ' (via Scene, below) redraws everything itself, so a ShowTrack right
  ' before it just flashed the plain track up for a moment before the
  ' scene painted straight over it
  c = PickOwned("HOT LAP - WHICH CAR?")
  If c < 0 Then
    ShowTrack
    Exit Sub
  EndIf
  pl = PlayerNum(owner$(c))
  If hotDone(c) Then
    ShowTrack
    Status carName$(c) + " has had its hot lap - race again first"
    Exit Sub
  EndIf
  ' the lap's ticks at the target pace, for this car's damage
  hotPar = Int(trackLen / (HOT_PAR * (1 - dmg(c) / 100 * 0.4)))
  qX$ = Str$(hotPar * RACE_MS / 1000, 0, 1)
  Scene pl, c, "HOTGO", "HOTGOR"
  ' a finished race's cars leave the track (the entries for the next one
  ' stay entered)
  If phase = 3 Then NewRace
  hotCar = c
  hotPl = pl
  hotProg = 0
  hotRoll = 1.8 + Rnd * 0.9
  hotTicks = 0
  hotDone(c) = 1
  phase = 4
  ShowTrack
  Status "HOT LAP: " + carName$(c) + " - target " + Str$(hotPar * RACE_MS / 1000, 0, 1) + "s"
End Sub

Sub DrawHot
  DrawCarAt hotProg, 0, carCol(hotCar)
  hotX = carDX
  hotY = carDY
  hotShown = 1
End Sub

' the live corner clock during a hot lap -- no CurHide/CurShow of its own,
' the caller (HotTick) is already mid-redraw when it's drawn
Sub HotPanel
  Local integer rh, x, y, ph
  PanelErase
  PanelDrag
  rh = fh(0) + 4
  x = panelX
  y = panelY
  ph = rh * 2 + 8
  RBox x, y, PANEL_W, ph, 6, C_INK, C_BAR
  PText x + PANEL_W \ 2, y + 4 + rh \ 2, "HOT LAP", "C", 0, C_AMBER
  PText x + PANEL_W \ 2, y + 4 + rh + rh \ 2, Str$(hotTicks * RACE_MS / 1000, 0, 1) + "s / " + Str$(hotPar * RACE_MS / 1000, 0, 1) + "s", "C", 0, C_INK
  panelLastX = x : panelLastY = y : panelLastH = ph
End Sub

Sub HotTick
  Local integer prize
  Local float t
  CurHide
  If hotShown Then BLIT FRAMEBUFFER F, N, hotX - 11, hotY - 11, hotX - 11, hotY - 11, 23, 23
  hotShown = 0
  hotProg = hotProg + hotRoll * (1 - dmg(hotCar) / 100 * 0.4)
  hotTicks = hotTicks + 1
  HotPanel
  If hotProg < trackLen Then
    DrawHot
    CurShow
    Exit Sub
  EndIf
  CurShow
  phase = 0
  t = hotTicks * RACE_MS / 1000
  If hotTicks < hotPar Then
    ' the bigger the margin, the bigger the cheque: $500 to $2000
    prize = 500 + Int(1500 * Min(1, (hotPar - hotTicks) / (hotPar * 0.25)))
    pb(hotPl) = pb(hotPl) + prize
    SavePlayers
    Status "HOT LAP " + Str$(t, 0, 1) + "s - beat the target! +$" + Str$(prize)
    qT$ = Str$(t, 0, 1)
    qM$ = Str$(prize)
    Scene hotPl, hotCar, "HOTWIN", "HOTWINR"
  Else
    Status "HOT LAP " + Str$(t, 0, 1) + "s - target was " + Str$(hotPar * RACE_MS / 1000, 0, 1) + "s, no money"
    qT$ = Str$(t, 0, 1)
    qX$ = Str$(hotPar * RACE_MS / 1000, 0, 1)
    Scene hotPl, hotCar, "HOTLOSE", "HOTLOSER"
  EndIf
End Sub

' the mechanic fixes a car: 0.5% of its value per 1% of damage, as much as
' the owner's budget covers
Sub Repair
  Local integer c, pl, cost
  Local float fix
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then
    Status "Repairs are between races"
    Exit Sub
  EndIf
  ' ShowTrack only on the way out without a scene to follow it -- see
  ' HotLap for why
  c = PickOwned("REPAIR - WHICH CAR?")
  If c < 0 Then
    ShowTrack
    Exit Sub
  EndIf
  pl = PlayerNum(owner$(c))
  If dmg(c) < 1 Then
    Scene pl, c, "FIXNONE", "FIXNONER"
    Exit Sub
  EndIf
  cost = Int(dmg(c) * carVal(c) * 0.005)
  If pb(pl) <= 0 Then
    qM$ = Str$(cost)
    Scene pl, c, "SKINT", "SKINTR"
    Exit Sub
  EndIf
  If pb(pl) >= cost Then
    pb(pl) = pb(pl) - cost
    dmg(c) = 0
    qM$ = Str$(cost)
    Scene pl, c, "FIXED", "FIXEDR"
  Else
    ' part of it: what the budget pays for
    fix = pb(pl) / (carVal(c) * 0.005)
    cost = Int(pb(pl))
    pb(pl) = 0
    dmg(c) = Max(0, dmg(c) - fix)
    qM$ = Str$(cost)
    Scene pl, c, "PART", "PARTR"
  EndIf
  SavePlayers
  SaveCars
  Status carName$(c) + " repaired to " + Str$(Int(dmg(c))) + "% - " + pn$(pl) + " has $" + Str$(Int(pb(pl)))
End Sub

' 50% nothing, 30% tune-up (5% of the car's value), 15% engine (15%),
' 5% crash (35%)
Sub RollEvent(fr As float, d$)
  Local integer r
  r = Int(Rnd * 100)
  fr = 0
  d$ = ""
  If r >= 50 And r < 80 Then
    fr = 0.05
    d$ = "minor tune-up"
  ElseIf r >= 80 And r < 95 Then
    fr = 0.15
    d$ = "engine trouble"
  ElseIf r >= 95 Then
    fr = 0.35
    d$ = "crash damage"
  EndIf
End Sub
