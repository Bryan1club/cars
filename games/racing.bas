LIBRARY LOAD "B:/Games/racing_quotes.bas", "B:/Games/racing_ui.bas", RAM
Option EXPLICIT
Option DEFAULT NONE
Const USE_MAP = 1
Const F_TEXT = 9, F_TITLE = 10
Const NBMAX = 16
Const BG_FILE$ = "page_bg_640.bmp"
Const CURSOR_FILE$ = "arrow.spr"
Const HOME_DIR$ = "B:/club"
Dim integer C_BLACK, C_GRN_TOP, C_GRN_BASE, C_RED_TOP, C_RED_BASE
Dim integer C_BAR, C_PAGE, C_INK, C_DIM, C_AMBER, C_FACE
Dim string lbl$(NBMAX - 1)
Dim integer bx(NBMAX - 1), by(NBMAX - 1), bw(NBMAX - 1), bh(NBMAX - 1)
Dim integer colA(NBMAX - 1), colB(NBMAX - 1)
Dim integer bstyle(NBMAX - 1)
Const MAXLA = 8
Dim string laN$(MAXLA - 1)
Dim integer laX(MAXLA - 1), laY(MAXLA - 1), laW(MAXLA - 1), laH(MAXLA - 1), nla
Dim integer nb, focus, W, H
Dim integer clickX, clickY
Dim string mitem$(NBMAX - 1)
Dim integer hasBar, barX
Const TICK_MS = 150
Dim integer tkx, tky, tkw, tkh, tkPos, lastTick
Dim integer tickerRaceMode
Dim string ip$, tkMsg$, tkWx$
Dim string tkSeg$(4)
Dim integer hasTouch, hasMouse, gmx, gmy, gml, prevML, curX, curY
Dim integer lastWheel, dragY
Dim integer kbRow, lsKey, lsOn
Dim integer pendClick
Dim integer nm, ach, mch(3), px(4), py(4), pl(4)
Dim integer adv(1, 94), fh(1)
Dim integer fText, fTitle
Dim integer forceBuiltinFont
Dim string gameDir$, PLAYERS_FILE$, CARS_FILE$
Const ENTRY_FEE = 200, STARTING_BUDGET = 20000, MAXPL = 20
Const NCARS = 30
Const POD_CASH1 = 30000, POD_CASH2 = 15000, POD_CASH3 = 10000
Dim integer EVENT_RACES = 1
Const NRAW = 50, NWP = 100, TRACK_W = 48, RACE_MS = 60
Const RAWW = 520, RAWH = 333, TRACK_MARGIN = 28
Const WX_EVERY = 60000, WX_PLACE_MS = 180000
Dim integer lastWx, wxStartT
Dim integer trackNo, nTracks
Dim string tName$
Const LAT_LIMIT = 16, LAT_DRIFT = 0.5, MIN_PROG_GAP = 20, MIN_LAT_GAP = 12, GRID_GAP = 22
Const SAND_R = 12
Const COLLIDE_BASE = 0.08, COLLIDE_SPD_K = 0.25, COLLIDE_CHANCE_MAX = 0.35
Const CRASH_SPD = 0.5, CRASH_CHANCE_K = 0.3, CRASH_DMG_MIN = 8, CRASH_DMG_RANGE = 8
Const BUMP_SPD_CUT = 0.9, CRASH_SPD_CUT = 0.55, CRASH_SPIN_TICKS = 20
Const S_GRASS = 7, S_ROAD = 8, S_PURPLE = 9, S_SAND = 11, S_BLUE = 12
Dim float wx(NWP), wy(NWP), cum(NWP), trackLen, rx(NRAW - 1), ry(NRAW - 1)
Dim integer sandX(3), sandY(3), carCol(NCARS - 1), CT, CB
Dim integer carCycle(7)
Dim integer introDone
Dim string carName$(NCARS - 1), pn$(MAXPL - 1), owner$(NCARS - 1)
Dim float carVal(NCARS - 1), pb(MAXPL - 1), dmg(NCARS - 1)
Dim float carMinVal, carMaxVal
Const NTEAM = 7
Dim integer pMain(MAXPL - 1), pShade(MAXPL - 1)
Dim integer np, lapsToWin, j, v
Dim string cmd$, statusMsg$
Dim integer ne, ep(NCARS - 1), ec(NCARS - 1), laps(NCARS - 1), fin(NCARS - 1), place(NCARS - 1), nfin, lastX(NCARS - 1), lastY(NCARS - 1), shown(NCARS - 1)
Dim integer wasNew(NCARS - 1)
Dim float prog(NCARS - 1), lat(NCARS - 1), spd(NCARS - 1)
Dim float latV(NCARS - 1)
Const HOT_PAR = 2.2, TOO_DAMAGED = 80, Q_STAGGER = 14
Dim integer hotTicks, hotPar, hotDone(NCARS - 1), carDX, carDY
Dim integer nextIdleChat
Dim integer garageBubbleX, garageBubbleY
Dim integer bulkJoin
Dim integer sceneChaining
Dim integer hotCar, hotPl, hotX, hotY, hotShown
Dim float hotProg
Dim float hotRoll
Dim integer phase, qIdx, qStart, qTime(NCARS - 1), lastMove
Dim integer qTicks, qDone(NCARS - 1)
Dim integer qShown(NCARS - 1), qRank(NCARS - 1), gridT0
Dim integer raceNum, wins(MAXPL - 1)
Dim float pot, startB(MAXPL - 1)
Dim integer lSeg
Dim float lT
Dim integer gBtn0, gGX(2), gGY(2), gGW(2), gDrawerH, gDrawerGap, gBenchH
Dim integer gPick
Const PANEL_W = 150
Const CAB_DX = 6, CAB_DY = -8
Dim integer panelX, panelY, pDragging, panelDX, panelDY
Dim integer raceTickerT0, raceRankIdx
Dim integer qualTickerT0, qualRotIdx
Dim integer entIdx, entT0, entLastNe
Dim integer panelLastX, panelLastY, panelLastH
gameDir$ = MM.Info(PATH)
If gameDir$ = "" Or Instr(gameDir$, "/") = 0 Then gameDir$ = "B:/Games/"
If Right$(gameDir$, 1) <> "/" Then gameDir$ = gameDir$ + "/"
PLAYERS_FILE$ = gameDir$ + "racing_players.dat"
CARS_FILE$ = gameDir$ + "racing_cars.dat"
forceBuiltinFont = 1
CoreInit
SetGamePalette
DrawPageOn "CIRCUIT RACE", ""
TickerAt W \ 40, H - fh(0) - 10 - W \ 80, W - W \ 20
CB = H - fh(0) - 14 - W \ 80
CT = W \ 40
AddGarageButtons
wxStartT = Timer
tickerRaceMode = 1
StartCursor
Restore CarData
For j = 0 To NCARS - 1
  Read carName$(j), carVal(j)
Next
carMinVal = carVal(0)
carMaxVal = carVal(0)
For j = 1 To NCARS - 1
  carMinVal = Min(carMinVal, carVal(j))
  carMaxVal = Max(carMaxVal, carVal(j))
Next
carCycle(0) = MAP(5) : carCycle(1) = MAP(S_BLUE) : carCycle(2) = MAP(3) : carCycle(3) = MAP(1)
carCycle(4) = MAP(S_PURPLE) : carCycle(5) = MAP(15) : carCycle(6) = MAP(2) : carCycle(7) = MAP(4)
For j = 0 To NCARS - 1
  carCol(j) = carCycle(j Mod 8)
Next j
BuildTrack
LoadPlayers
LoadCars
lapsToWin = 1
On Error Skip
FRAMEBUFFER CLOSE
On Error Skip
FRAMEBUFFER CREATE
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
  If phase = 0 And Timer > nextIdleChat Then IdleChat
  If j = -2 Then Quit
  cmd$ = Command$(j)
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
        gPick = PickList("LAPS PER RACE", "1 LAP|2 LAPS|3 LAPS|5 LAPS|8 LAPS|10 LAPS")
        If gPick >= 0 Then
          lapsToWin = Val(Field$("1|2|3|5|8|10", gPick + 1, "|"))
          Status "Races are " + Str$(lapsToWin) + " lap" + Choice(lapsToWin = 1, "", "s") + " each"
          RaceInfoTicker
        EndIf
      EndIf
    Case "RACES"
      If phase = 1 Or phase = 2 Or phase = 5 Or raceNum > 1 Then
        Status "This event is " + Str$(EVENT_RACES) + " races - set for the next one once this one's done"
      Else
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
Sub SetGamePalette
  MAP S_GRASS = RGB(30, 74, 30)
  MAP S_ROAD = RGB(96, 96, 96)
  MAP S_PURPLE = RGB(204, 102, 255)
  MAP S_SAND = RGB(210, 180, 140)
  MAP S_BLUE = RGB(51, 136, 255)
  MAP SET
End Sub
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
Sub Status(s$)
  statusMsg$ = s$
  If phase <> 1 And phase <> 5 And phase <> 2 Then TickerSeg 3, s$
End Sub
Sub BuildTrack
  Local float ax(NWP - 1), ay(NWP - 1), bx2(NWP - 1), by2(NWP - 1), d
  Local float sc, ox, oy
  Local integer i, n, it, k, x, y
  Restore Tracks
  Read nTracks
  trackNo = Max(0, Min(nTracks - 1, trackNo))
  For k = 1 To trackNo
    Read tName$
    For i = 1 To NRAW * 2
      Read x
    Next
  Next
  Read tName$
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
Sub DrawTrack
  Local integer i
  Local float t, x, y, sl
  CurHide
  FRAMEBUFFER WRITE F
  Box 0, CT, W, CB - CT, 1, MAP(S_GRASS), MAP(S_GRASS)
  For i = 0 To 3
    Circle sandX(i), sandY(i), SAND_R, 1, 1, MAP(S_SAND), MAP(S_SAND)
  Next
  For i = 0 To NWP - 1
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
  TrackAt 0
  x = wy(1) - wy(0)
  y = wx(0) - wx(1)
  sl = Max(0.001, Sqr(x * x + y * y))
  Line wx(0) - x / sl * TRACK_W / 2, wy(0) - y / sl * TRACK_W / 2, wx(0) + x / sl * TRACK_W / 2, wy(0) + y / sl * TRACK_W / 2, 2, C_INK
  FRAMEBUFFER WRITE N
  CurShow
End Sub
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
Sub HidePlaceAfter3Min
  Local integer p
  If Timer - wxStartT < WX_PLACE_MS Then Exit Sub
  p = Instr(tkWx$, " (")
  If p Then tkWx$ = Left$(tkWx$, p - 1)
End Sub
Sub ShowTrack
  Local integer i
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
Sub AddGarageButtons
  Local string lbl$(11)
  Local integer i, gi, lh, floorTop, backBottom, cabH, benchH, benchDW, bgap, totalW
  lbl$(0) = "ENTER PLAYER" : lbl$(1) = "LEAVE" : lbl$(2) = "CAR LIST" : lbl$(3) = "DRIVERS"
  lbl$(4) = "VISIT" : lbl$(5) = "REPAIR" : lbl$(6) = "HOT LAP" : lbl$(7) = "SELL CAR"
  lbl$(8) = "TRACK" : lbl$(9) = "LAPS" : lbl$(10) = "RACES" : lbl$(11) = "START RACE"
  gDrawerGap = 4
  lh = fh(0) + 8
  floorTop = CT + (CB - CT) * 35 \ 100
  backBottom = floorTop - (floorTop - CT) * 30 \ 100
  gGW(0) = W \ 7
  gGW(2) = W \ 7
  gGW(1) = W * 3 \ 10
  cabH = (CB - backBottom) * 45 \ 100
  benchH = cabH * 55 \ 100
  gBenchH = benchH
  gDrawerH = (cabH - lh - 3 * gDrawerGap) \ 4
  totalW = gGW(0) + 12 + gGW(1) + 12 + gGW(2)
  gGX(0) = (W - totalW) \ 2
  gGY(0) = backBottom - 94
  gGX(1) = gGX(0) + gGW(0) + 12 : gGY(1) = backBottom - 94
  gGX(2) = gGX(1) + gGW(1) + 12 : gGY(2) = backBottom - 94
  For gi = 0 To 3
    i = gi
    v = AddBtn(lbl$(i), gGX(0) + 2, gGY(0) + lh + gi * (gDrawerH + gDrawerGap), gGW(0) - 4, gDrawerH, Choice(lbl$(i) = "LEAVE", 1, 0))
    bstyle(v) = 4
    If i = 0 Then gBtn0 = v
  Next
  bgap = 4
  benchDW = (gGW(1) - 5 * bgap) \ 4
  For gi = 0 To 3
    i = 4 + gi
    v = AddBtn(lbl$(i), gGX(1) + bgap + gi * (benchDW + bgap), gGY(1) + lh, benchDW, benchH - lh, 0)
    bstyle(v) = 4
    If i = 0 Then gBtn0 = v
  Next
  For gi = 0 To 3
    i = 8 + gi
    v = AddBtn(lbl$(i), gGX(2) + 2, gGY(2) + lh + gi * (gDrawerH + gDrawerGap), gGW(2) - 4, gDrawerH, Choice(lbl$(i) = "LEAVE", 1, 0))
    bstyle(v) = 4
    If i = 0 Then gBtn0 = v
  Next
End Sub
Sub DrawDrawer(i As integer, shift As integer)
  Local integer x, y, w, h, face, p
  Local string l1$, l2$
  x = bx(i) + shift
  y = by(i)
  w = bw(i)
  h = bh(i)
  face = Choice(shift > 0, 5, 13)
  If shift > 0 Then Box bx(i) - 2, y - 2, shift + 4, h + 4, 0, 0, MAP(6)
  Box x, y, w, h, 0, 0, MAP(face)
  Line x, y, x + w - 1, y, 1, MAP(15)
  Line x, y, x, y + h - 1, 1, MAP(15)
  Line x, y + h - 1, x + w - 1, y + h - 1, 1, C_BLACK
  Line x + w - 1, y, x + w - 1, y + h - 1, 1, C_BLACK
  Box x + w \ 4, y + 3, w \ 2, 5, 0, 0, MAP(Choice(shift > 0, 15, 14))
  Line x + w \ 4, y + 3, x + w * 3 \ 4, y + 3, 1, MAP(15)
  Line x + w \ 4, y + 7, x + w * 3 \ 4, y + 7, 1, C_BLACK
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
Sub DrawerOpen(i As integer)
  Local integer k
  CurHide
  For k = 2 To 10 Step 4
    DrawDrawer i, k
  Next
  CurShow
  Pause 120
End Sub
Sub RaceInfoTicker
  TickerSeg 1, "Race " + Str$(raceNum) + " of " + Str$(EVENT_RACES) + " - pot $" + Str$(Int(pot)) + " - " + Str$(lapsToWin) + " lap" + Choice(lapsToWin = 1, "", "s") + " - " + tName$
End Sub
Sub DrawGarage
  Local integer i, g, mw, mh, mmx, mmy, mx, my, pose, t0, justIntroduced
  Local integer cabBottom
  Local integer cx, cy, cw, ch
  Local integer px(4), py(4)
  Local string r$
  CurHide
  DrawBay "GARAGE"
  Restore ArtInfo
  Read mw, mh, mmx, mmy
  mx = gGX(2) + gGW(2) + 12 + (W - (gGX(2) + gGW(2) + 12) - mw) \ 2
  mx = Min(mx, W - mw - 8)
  my = CB - mh - 8
  pose = Int(Rnd * 3)
  ArtAt Choice(pose = 0, 0, Choice(pose = 1, 11, 12)), mx, my
  If introDone = 0 Then
    introDone = 1
    justIntroduced = 1
  EndIf
  EntrantsTicker
  RaceInfoTicker
  TickerSeg 2, ""
  For g = 0 To 2
    cx = gGX(g) - 6
    cy = gGY(g) - 2
    cw = gGW(g) + 12
    cabBottom = gGY(g) + fh(0) + 8 + Choice(g = 1, gBenchH - fh(0) - 8, 4 * gDrawerH + 3 * gDrawerGap) + 8
    ch = cabBottom - cy
    px(0) = cx : py(0) = cy : px(1) = cx + cw : py(1) = cy
    px(2) = cx + cw + CAB_DX : py(2) = cy + CAB_DY : px(3) = cx + CAB_DX : py(3) = cy + CAB_DY
    px(4) = cx : py(4) = cy
    Polygon 5, px(), py(), MAP(15), MAP(15)
    px(0) = cx + cw : py(0) = cy : px(1) = cx + cw + CAB_DX : py(1) = cy + CAB_DY
    px(2) = cx + cw + CAB_DX : py(2) = cy + CAB_DY + ch : px(3) = cx + cw : py(3) = cy + ch
    px(4) = cx + cw : py(4) = cy
    Polygon 5, px(), py(), MAP(13), MAP(13)
    Box cx, cy, cw, ch, 1, C_BLACK, MAP(14)
    PText cx + cw \ 2, cy + fh(0) \ 2, Choice(g = 0, "PLAYERS", Choice(g = 1, "GARAGE", "RACE")), "C", 0, C_BLACK
    Box cx - 2, cy + ch, cw + 4, 3, 0, 0, MAP(6)
  Next
  For i = 0 To 11
    DrawDrawer gBtn0 + i, 0
  Next
  BLIT FRAMEBUFFER N, 2, 0, CT, 0, CT, W, CB - CT
  garageBubbleX = mx + mmx
  garageBubbleY = my + mmy
  If Not justIntroduced Then Talk Quote$("GARAGE"), garageBubbleX, garageBubbleY, 0, 1
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
  nextIdleChat = Timer + 4000
End Sub
Sub IdleChat
  CurHide
  BLIT FRAMEBUFFER 2, N, 0, CT, 0, CT, W, CB - CT
  Talk Quote$("GARAGE"), garageBubbleX, garageBubbleY, 0, 1
  CurShow
  nextIdleChat = Timer + 4000
End Sub
Sub DrawCar(i As integer)
  DrawCarAt prog(i), lat(i), carCol(ec(i))
  lastX(i) = carDX
  lastY(i) = carDY
  shown(i) = 1
End Sub
Sub DrawCarAt(p As float, l As float, c As integer)
  Local float x, y, tx, ty, d, ax, ay
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
Sub CarTop(x As float, y As float, tx As float, ty As float, c As integer)
  Local float nx, ny
  Local integer px(4), py(4)
  x = Int(x + 0.5)
  y = Int(y + 0.5)
  nx = -ty
  ny = tx
  Circle x + tx * 4.5 + nx * 4, y + ty * 4.5 + ny * 4, 1.5, 1, 1, C_BLACK, C_BLACK
  Circle x + tx * 4.5 - nx * 4, y + ty * 4.5 - ny * 4, 1.5, 1, 1, C_BLACK, C_BLACK
  Circle x - tx * 5 + nx * 4, y - ty * 5 + ny * 4, 1.8, 1, 1, C_BLACK, C_BLACK
  Circle x - tx * 5 - nx * 4, y - ty * 5 - ny * 4, 1.8, 1, 1, C_BLACK, C_BLACK
  px(0) = x + tx * 9 + nx * 2.5 : py(0) = y + ty * 9 + ny * 2.5
  px(1) = x + tx * 9 - nx * 2.5 : py(1) = y + ty * 9 - ny * 2.5
  px(2) = x - tx * 8 - nx * 4 : py(2) = y - ty * 8 - ny * 4
  px(3) = x - tx * 8 + nx * 4 : py(3) = y - ty * 8 + ny * 4
  px(4) = px(0) : py(4) = py(0)
  Polygon 5, px(), py(), C_BLACK, c
  Line x + tx * 8, y + ty * 8, x + tx * 3, y + ty * 3, 1, C_INK
  Circle x - tx * 2, y - ty * 2, 2, 1, 1, C_BLACK, C_BLACK
  Line x - tx * 8 + nx * 5, y - ty * 8 + ny * 5, x - tx * 8 - nx * 5, y - ty * 8 - ny * 5, 2, C_BLACK
End Sub
Sub EraseCar(i As integer)
  If Not shown(i) Then Exit Sub
  BLIT FRAMEBUFFER F, N, lastX(i) - 11, lastY(i) - 11, lastX(i) - 11, lastY(i) - 11, 23, 23
  shown(i) = 0
End Sub
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
Function PickList(t$, rows$) As integer
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
  boxH = 13 * rh + 10
  PickListRows = -1
  Do
    shown = Min(11, n - first)
    If n <= 12 Then shown = n
    more = Choice(n > 12, 1, 0)
    CurHide
    RBox x, y, wd, boxH, 6, C_INK, C_BAR
    RBox x, y, wd, rh + 4, 6, C_INK, C_GRN_BASE
    CurShow
    PText x + wd \ 2, y + rh \ 2 + 2, t$, "C", 0, C_INK
    sel = -1
    For i = 0 To shown - 1
      DrawPickRow x, y + rh, wd, rh, i, item$(first + i), i = sel
    Next
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
    first = Choice(first + 11 < n, first + 11, 0)
  Loop
  ShowTrack
End Function
Sub Owners
  Local string it$(NCARS)
  Local integer i
  For i = 0 To NCARS - 1
    it$(i) = carName$(i) + " $" + Str$(carVal(i)) + " " + Choice(owner$(i) = "", "-", owner$(i)) + " " + Str$(Int(dmg(i))) + "%"
  Next
  it$(NCARS) = "CLOSE"
  i = PickListRows("CAR OWNERS", it$(), NCARS + 1)
End Sub
Sub EnterPlayer
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
    k = PickList(pn$(np) + " - PRIMARY COLOUR", TeamNames$())
    If k < 0 Then Exit Sub
    pMain(np) = ColourSlot(k)
    k = PickList(pn$(np) + " - SECONDARY COLOUR", TeamNames$())
    If k < 0 Then Exit Sub
    pShade(np) = ColourSlot(k)
    np = np + 1
    needSave = 1
    isNew = 1
  EndIf
  JoinRace pl, isNew, needSave
End Sub
Sub JoinRace(pl As integer, isNew As integer, needSave As integer)
  Local integer i, c, k
  For i = 0 To ne - 1
    If ep(i) = pl Then
      If needSave Then SavePlayers
      Status pn$(pl) + " is already in this race"
      Exit Sub
    EndIf
  Next
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
  c = -1
  k = 0
  For i = 0 To NCARS - 1
    If owner$(i) = pn$(pl) Then
      c = i
      k = k + 1
    EndIf
  Next
  If k <> 1 Then
    Local string carIt$(NCARS - 1)
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
Sub AutoJoinSaved
  Local integer pl
  bulkJoin = 1
  For pl = 0 To np - 1
    JoinRace pl, 0, 0
  Next
  bulkJoin = 0
End Sub
Sub LeavePlayer
  Local integer pl, i, k
  Local string it$(MAXPL - 1)
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then
    Status "Wait for this race to finish"
    Exit Sub
  EndIf
  If ne = 0 Then
    Status "Nobody's racing yet"
    Exit Sub
  EndIf
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
  nfin = 0
  phase = 0
  ShowTrack
End Sub
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
Sub BeginRace(midEvent As integer)
  Local integer i
  For i = 0 To ne - 1
    laps(i) = 0
    fin(i) = 0
    place(i) = 0
    shown(i) = 0
  Next
  nfin = 0
  TickerSeg 0, ""
  TickerSeg 1, "Race " + Str$(raceNum) + " of " + Str$(EVENT_RACES) + " - " + tName$
  TickerSeg 3, ""
  TickerMsg ""
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
  hid = 0
  For i = 0 To ne - 1
    If Not qDone(i) And shown(i) And CurOver(lastX(i) - 11, lastY(i) - 11, 23, 23) Then hid = 1
  Next
  If hid Then CurHide
  For i = 0 To ne - 1
    If Not qDone(i) Then EraseCar i
  Next
  For i = 0 To ne - 1
    If Not qDone(i) And qTicks > i * Q_STAGGER Then
      prog(i) = prog(i) + spd(i)
      If prog(i) >= trackLen Then
        qDone(i) = 1
        qTime(i) = qTicks - i * Q_STAGGER
      EndIf
    EndIf
  Next
  For i = 0 To ne - 2
    For k = i + 1 To ne - 1
      If Not qDone(i) And Not qDone(k) And qTicks > k * Q_STAGGER Then
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
      If qTicks > i * Q_STAGGER Then DrawCar i
    EndIf
  Next
  If hid Then CurShow
  QualPanel
  If running = 0 Then FinishQualifying
End Sub
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
    If qTicks > i * Q_STAGGER Then away = away + 1
  Next
  ph = (n + 1) * rh + 8
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
Sub FinishQualifying
  Local integer i, k, rank
  For i = 0 To ne - 1
    rank = 0
    For k = 0 To ne - 1
      If qTime(k) < qTime(i) Or (qTime(k) = qTime(i) And k < i) Then rank = rank + 1
    Next
    qRank(i) = rank
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
      latV(i) = Max(-0.35, Min(0.35, latV(i) * 0.9 + (Rnd - 0.5) * LAT_DRIFT * 0.3))
      lat(i) = lat(i) + latV(i)
      If Abs(lat(i)) > LAT_LIMIT Then
        lat(i) = Max(-LAT_LIMIT, Min(LAT_LIMIT, lat(i)))
        latV(i) = -latV(i)
      EndIf
      If Int(prog(i) / trackLen) > oldLap Then
        laps(i) = laps(i) + 1
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
          latV(i) = 0.3 * dirn
          latV(k) = -0.3 * dirn
          If Abs(lat(i) - lat(k)) < MIN_LAT_GAP Then
            sd = prog(i) - prog(k)
            sd = sd - Int(sd / trackLen + 0.5) * trackLen
            closeSpd = Abs(spd(i) - spd(k))
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
  hid = 0
  For i = 0 To ne - 1
    If shown(i) And CurOver(lastX(i) - 11, lastY(i) - 11, 23, 23) Then hid = 1
  Next
  If hid Then CurHide
  For i = 0 To ne - 1
    EraseCar i
  Next
  For i = 0 To ne - 1
    If Not fin(i) Then DrawCar i
  Next
  If hid Then CurShow
  RaceTicker
  If nfin >= ne Then RaceOver
End Sub
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
    If dmg(victimCar) >= TOO_DAMAGED And Not fin(victimEntrant) Then
      fin(victimEntrant) = 1
      nfin = nfin + 1
      TickerMsg carName$(victimCar) + " (" + pn$(ep(victimEntrant)) + ") retires - too much damage to continue"
    EndIf
  EndIf
End Sub
Sub EntrantsTicker
  If phase <> 0 Then Exit Sub
  If ne = 0 Then
    tkSeg$(0) = "Nobody's entered yet"
    entIdx = 0
    entLastNe = 0
    Exit Sub
  EndIf
  If entIdx >= ne Then entIdx = 0
  If tkSeg$(0) = "" Or ne <> entLastNe Or Timer - entT0 >= 3000 Then
    tkSeg$(0) = Str$(entIdx + 1) + "/" + Str$(ne) + ": " + pn$(ep(entIdx)) + " (" + carName$(ec(entIdx)) + ")"
    entIdx = (entIdx + 1) Mod ne
    entT0 = Timer
    entLastNe = ne
  EndIf
End Sub
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
    continuing = 1
  Else
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
    If EVENT_RACES >= 3 Then RankPodium pod1, pod2, pod3
    NewEvent
  EndIf
  SavePlayers
  Status msg$ + Choice(dcount, " | " + Str$(dcount) + " damage", " | no damage")
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
  If continuing Then
    BeginRace 1
  Else
    SavePlayers
    NewRace
  EndIf
End Sub
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
  TickerMsg "Circuit Race at " + tName$ + " - " + Str$(EVENT_RACES) + "-race events, $" + Str$(ENTRY_FEE) + " entry. TRACK picks the circuit"
End Sub
Sub Visit
  Local integer c
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then
    Status "The garage is busy - after the race"
    Exit Sub
  EndIf
  c = PickOwned("GARAGE - WHOSE CAR?")
  If c < 0 Then
    ShowTrack
    Exit Sub
  EndIf
  Scene PlayerNum(owner$(c)), c, "PRE_" + Mechanic$(dmg(c)), Choice(dmg(c) >= TOO_DAMAGED, "VISITBADR", "VISITR")
End Sub
Sub SellCar
  Local integer c, pl, i, price, dismiss
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then
    Status "Sell between races"
    Exit Sub
  EndIf
  c = PickOwned("SELL - WHICH CAR?")
  If c < 0 Then
    ShowTrack
    Exit Sub
  EndIf
  For i = 0 To ne - 1
    If ec(i) = c And phase = 0 Then
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
Function PlayerNum(n$) As integer
  Local integer i
  PlayerNum = -1
  For i = 0 To np - 1
    If pn$(i) = n$ Then PlayerNum = i
  Next
End Function
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
Sub HotLap
  Local integer c, pl
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then
    Status "Hot laps are between races"
    Exit Sub
  EndIf
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
  hotPar = Int(trackLen / (HOT_PAR * (1 - dmg(c) / 100 * 0.4)))
  qX$ = Str$(hotPar * RACE_MS / 1000, 0, 1)
  Scene pl, c, "HOTGO", "HOTGOR"
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
Sub Repair
  Local integer c, pl, cost
  Local float fix
  If phase = 1 Or phase = 2 Or phase = 4 Or phase = 5 Then
    Status "Repairs are between races"
    Exit Sub
  EndIf
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
Sub MapGreys
  MAP 6 = RGB(17,18,19)
  MAP 7 = RGB(20,22,24)
  MAP 8 = RGB(23,25,27)
  MAP 9 = RGB(26,28,31)
  MAP 10 = RGB(30,32,35)
  MAP 11 = RGB(33,36,39)
  MAP 12 = RGB(42,44,47)
  MAP 13 = RGB(66,70,74)
  MAP 14 = RGB(117,121,125)
End Sub
FontWidths:
Data 18
Data 4,3,5,10,8,10,8,5,4,4,6,6,3,5,3,6,7,5,7,7,7,7,7,7
Data 7,7,4,4,5,6,5,6,11,9,8,7,9,8,7,8,9,7,8,7,7,11,10,10
Data 6,11,8,8,8,9,8,12,9,8,8,5,7,5,7,8,7,6,7,6,7,7,6,6
Data 7,3,5,6,3,9,6,6,6,6,6,6,6,6,6,8,7,6,6,4,5,4,7
Data 32
Data 5,4,8,15,12,15,12,7,7,7,10,9,5,8,4,9,11,8,11,11,11,11,11,11
Data 11,11,5,5,7,9,7,9,17,13,11,11,13,11,11,12,14,10,12,11,10,16,14,14
Data 9,16,11,12,12,13,12,19,13,11,12,7,10,7,10,11,10,9,11,9,11,10,9,10
Data 10,5,7,10,5,14,9,9,10,9,9,9,8,9,9,12,11,9,10,7,8,7,11
Sub CoreInit
  On Error Skip
  Option Web Messages Off
  On Error Skip
  Drive "B:"
  On Error Skip
  Chdir HOME_DIR$
  MODE 3
  CLS
  W = MM.HRES
  H = MM.VRES
  SetPalette
  ReadWidths
  ProbeInputs
  nb = 0
  focus = 0
  hasBar = 0
  kbRow = -1
  barX = W \ 40
End Sub
Sub SetPalette
  MAP 0 = RGB(0,0,0)
  MAP 1 = RGB(67,160,71)
  MAP 2 = RGB(46,125,50)
  MAP 3 = RGB(226,75,74)
  MAP 4 = RGB(168,40,40)
  MAP 5 = RGB(255,176,0)
  MAP 15 = RGB(232,234,237)
  MapGreys
  MAP SET
  C_BLACK = MAP(0)
  C_GRN_TOP = MAP(1)
  C_GRN_BASE = MAP(2)
  C_RED_TOP = MAP(3)
  C_RED_BASE = MAP(4)
  C_AMBER = MAP(5)
  C_BAR = MAP(6)
  C_PAGE = MAP(10)
  C_FACE = MAP(14)
  C_DIM = MAP(13)
  C_INK = MAP(15)
End Sub
Sub ReadWidths
  Local integer f, i
  Restore FontWidths
  For f = 0 To 1
    Read fh(f)
    For i = 0 To 94
      Read adv(f, i)
    Next
  Next
  fText = F_TEXT
  fTitle = F_TITLE
  If forceBuiltinFont = 0 Then
    On Error Skip
    Font F_TEXT
    If MM.Errno = 0 Then
      On Error Skip
      Font F_TITLE
    EndIf
  EndIf
  If forceBuiltinFont Or MM.Errno Then
    fText = 1
    fTitle = 1
    Font 1
    fh(0) = MM.Info(FONTHEIGHT)
    fh(1) = MM.Info(FONTHEIGHT)
    For f = 0 To 1
      For i = 0 To 94
        adv(f, i) = MM.Info(FONTWIDTH)
      Next
    Next
  EndIf
  Font 1
End Sub
Sub ProbeInputs
  Local integer v
  hasTouch = 0
  hasMouse = 0
  On Error Skip
  v = Touch(X)
  If MM.Errno = 0 Then hasTouch = 1
  nm = 0
  For v = 1 To 4
    If MM.Info(USB v) = 2 And nm < 4 Then
      mch(nm) = v
      px(v) = Device(MOUSE v, X)
      py(v) = Device(MOUSE v, Y)
      pl(v) = Device(MOUSE v, L)
      nm = nm + 1
    EndIf
  Next
  If nm > 0 Then
    hasMouse = 1
    ach = mch(0)
  EndIf
End Sub
Sub StartCursor
  If hasMouse = 0 Then Exit Sub
  ReadMouse
  curX = gmx
  curY = gmy
  GUI Cursor On 0, curX, curY, C_INK
  dragY = -1
  On Error Skip
  lastWheel = Device(MOUSE ach, W)
  On Error Skip
  GUI Cursor Load CURSOR_FILE$
End Sub
Function ListDelta(x As integer, y As integer, wd As integer, ht As integer, rh As integer) As integer
  Local integer wv, d, n
  If hasMouse = 0 Then Exit Function
  wv = lastWheel
  On Error Skip
  wv = Device(MOUSE ach, W)
  If wv <> lastWheel Then
    d = (lastWheel - wv) * 3
    lastWheel = wv
  EndIf
  If gml <> 0 And gmx >= x And gmx < x + wd And gmy >= y And gmy < y + ht Then
    If dragY < 0 Then
      dragY = gmy
    Else
      n = (dragY - gmy) \ rh
      If n <> 0 Then
        d = d + n
        dragY = dragY - n * rh
      EndIf
    EndIf
  Else
    dragY = -1
  EndIf
  ListDelta = d
End Function
Function ListNav(x As integer, y As integer, w As integer, rh As integer, rows As integer, n As integer, top As integer) As integer
  Local integer d, r, k
  lsOn = 1
  d = ListDelta(x, y, w, rows * rh + 6, rh)
  If d <> 0 And n > rows Then
    r = Max(0, Min(n - rows, top + d))
    If r <> top Then
      top = r
      ListNav = 1
    EndIf
  EndIf
  k = lsKey
  lsKey = 0
  If k = 0 Or n = 0 Then Exit Function
  If k = 13 Then
    If kbRow >= 0 And kbRow < n Then ListNav = 3
    Exit Function
  EndIf
  r = kbRow
  If r < 0 Then r = top - Choice(k = 129, 1, 0)
  Select Case k
    Case 128
      r = r - 1
    Case 129
      r = r + 1
    Case 136
      r = r - rows
    Case 137
      r = r + rows
  End Select
  kbRow = Max(0, Min(n - 1, r))
  If kbRow < top Then top = kbRow
  If kbRow >= top + rows Then top = kbRow - rows + 1
  ListNav = 2
End Function
Sub GoPage(f$)
  If hasMouse Then GUI Cursor Off
  If Instr(f$, ":") = 0 Then
    Run HOME_DIR$ + "/" + f$
  Else
    Run f$
  EndIf
End Sub
Sub DrawPage(title$)
  DrawPageOn title$, BG_FILE$
End Sub
Sub DrawPageOn(title$, bg$)
  CurHide
  Box 0, 0, W, H, 1, C_PAGE, C_PAGE
  On Error Skip
  Load Bmp bg$, 0, 0
  If title$ <> "" Then
    If hasBar Then
      PText W - W \ 40 + 1, H \ 16 + 1, title$, "R", 1, C_BLACK
      PText W - W \ 40, H \ 16, title$, "R", 1, C_INK
    Else
      PText W \ 2 + 1, H \ 16 + 1, title$, "C", 1, C_BLACK
      PText W \ 2, H \ 16, title$, "C", 1, C_INK
    EndIf
  EndIf
  CurShow
End Sub
Function AddBtn(t$, x As integer, y As integer, w As integer, h As integer, red As integer) As integer
  lbl$(nb) = t$
  mitem$(nb) = ""
  bstyle(nb) = 0
  bx(nb) = x
  by(nb) = y
  bw(nb) = w
  bh(nb) = h
  If red Then
    colA(nb) = C_RED_TOP
    colB(nb) = C_RED_BASE
  Else
    colA(nb) = C_GRN_TOP
    colB(nb) = C_GRN_BASE
  EndIf
  AddBtn = nb
  nb = nb + 1
End Function
Sub DrawBtn(i As integer, st As integer)
  Local integer x, y, w, h, r, top, bot, edge, nudge
  If bstyle(i) = 4 Then Exit Sub
  If bstyle(i) = 3 Then
    DrawArt i, st
    Exit Sub
  EndIf
  If bstyle(i) > 0 Then
    DrawPlate i, st
    Exit Sub
  EndIf
  x = bx(i)
  y = by(i)
  w = bw(i)
  h = bh(i)
  r = h \ 4
  If st = 2 Then
    top = colB(i)
    bot = colA(i)
    nudge = 1
  Else
    top = colA(i)
    bot = colB(i)
    nudge = 0
  EndIf
  If st = 0 Then
    edge = C_BLACK
  Else
    edge = C_INK
  EndIf
  CurHide
  RBox x, y, w, h, r, edge, bot
  RBox x + 3, y + 3, w - 6, h \ 2 - 2, r - 2, top, top
  If st <> 0 Then RBox x + 1, y + 1, w - 2, h - 2, r, edge
  PText x + w \ 2 + 1 + nudge, y + h \ 2 + 1 + nudge, lbl$(i), "C", 0, C_BLACK
  PText x + w \ 2 + nudge, y + h \ 2 + nudge, lbl$(i), "C", 0, C_INK
  CurShow
End Sub
Sub DrawPlate(i As integer, st As integer)
  Local integer x, y, w, h, cx
  x = bx(i)
  y = by(i)
  w = bw(i)
  h = bh(i)
  CurHide
  Blit Write 10 + i, x - 2, y - 2
  If st = 2 Then RBox x + 2, y + 2, w - 4, h - 4, 3, C_GRN_TOP, C_GRN_BASE
  If st <> 0 Then
    RBox x - 2, y - 2, w + 4, h + 4, 5, C_AMBER
    RBox x - 1, y - 1, w + 2, h + 2, 4, C_AMBER
  EndIf
  cx = x + w \ 2 + Choice(bstyle(i) = 1, 6, -6)
  PText cx + 1, y + h \ 2 + 1, lbl$(i), "C", 0, C_BLACK
  PText cx, y + h \ 2, lbl$(i), "C", 0, C_INK
  CurShow
End Sub
Function HitTest(x As integer, y As integer) As integer
  Local integer i
  HitTest = -1
  For i = 0 To nb - 1
    If x >= bx(i) And x < bx(i) + bw(i) And y >= by(i) And y < by(i) + bh(i) Then
      HitTest = i
      Exit Function
    EndIf
  Next
End Function
Sub SetFocus(n As integer)
  Local integer old
  old = focus
  focus = n
  If old <> n Then DrawBtn old, 0
  DrawBtn n, 1
End Sub
Sub MoveFocus(dx As integer, dy As integer)
  Local integer i, best, bestScore, ddx, ddy, along, across, score
  best = -1
  bestScore = 999999
  For i = 0 To nb - 1
    If i <> focus Then
      ddx = (bx(i) + bw(i) \ 2) - (bx(focus) + bw(focus) \ 2)
      ddy = (by(i) + bh(i) \ 2) - (by(focus) + bh(focus) \ 2)
      along = ddx * dx + ddy * dy
      across = Abs(ddx * dy) + Abs(ddy * dx)
      If along > 0 Then
        score = along + across * 2
        If score < bestScore Then
          best = i
          bestScore = score
        EndIf
      EndIf
    EndIf
  Next
  If best >= 0 Then SetFocus best
End Sub
Sub PressBtn(i As integer)
  DrawBtn i, 2
  Pause 150
  DrawBtn i, 1
End Sub
Function PollInput() As integer
  Local string k$
  Local integer j
  PollInput = -1
  TickerTick
  k$ = Inkey$
  If k$ = Chr$(27) Then
    PollInput = -2
    Exit Function
  EndIf
  If lsOn And k$ <> "" Then
    Select Case Asc(k$)
      Case 128, 129, 136, 137
        lsKey = Asc(k$)
        Exit Function
      Case 13
        If kbRow >= 0 Then
          lsKey = 13
          Exit Function
        EndIf
    End Select
  EndIf
  If k$ <> "" And nb > 0 Then
    Select Case Asc(k$)
      Case 128
        MoveFocus 0, -1
      Case 129
        MoveFocus 0, 1
      Case 130
        MoveFocus -1, 0
      Case 131
        MoveFocus 1, 0
    End Select
  EndIf
  If (k$ = Chr$(13) Or k$ = " ") And nb > 0 Then
    PressBtn focus
    PollInput = focus
    Exit Function
  EndIf
  If pendClick Or ClickAt() Then
    pendClick = 0
    j = HitTest(clickX, clickY)
    If j >= 0 Then
      SetFocus j
      PressBtn j
      PollInput = j
    Else
      PollInput = -3
    EndIf
    Exit Function
  EndIf
  If hasMouse Then
    j = HitTest(gmx, gmy)
    If j >= 0 And j <> focus Then SetFocus j
  EndIf
End Function
Sub TextBox(x As integer, y As integer, w As integer, s$, active As integer)
  Local string t$
  Local integer h
  h = fh(0) + 6
  t$ = s$
  Do While PWidth(t$, 0) > w - 10 And Len(t$) > 0
    t$ = Mid$(t$, 2)
  Loop
  CurHide
  If active Then
    RBox x, y, w, h, 4, C_INK, C_GRN_BASE
  Else
    RBox x, y, w, h, 4, C_DIM, C_BAR
  EndIf
  PText x + 5, y + h \ 2, t$, "L", 0, C_INK
  CurShow
End Sub
Function EditText$(x As integer, y As integer, w As integer, s$)
  Local string t$, k$
  t$ = s$
  TextBox x, y, w, t$ + "_", 1
  Do
    k$ = Inkey$
    If k$ <> "" Then
      Select Case Asc(k$)
        Case 13
          Exit Do
        Case 27
          t$ = s$
          Exit Do
        Case 8, 127
          If Len(t$) > 0 Then t$ = Left$(t$, Len(t$) - 1)
        Case 32 To 126
          If Len(t$) < 79 And k$ <> "|" Then t$ = t$ + k$
      End Select
      TextBox x, y, w, t$ + "_", 1
    EndIf
    If ClickAt() Then
      pendClick = 1
      Exit Do
    EndIf
    Pause 10
  Loop
  TextBox x, y, w, t$, 0
  EditText$ = t$
End Function
Function Fld$(l$, n As integer)
  Local integer i, p, q
  p = 1
  For i = 1 To n - 1
    q = Instr(p, l$, "|")
    If q = 0 Then Exit Function
    p = q + 1
  Next
  q = Instr(p, l$, "|")
  If q = 0 Then q = Len(l$) + 1
  Fld$ = Mid$(l$, p, q - p)
End Function
Function Fit$(s$, w As integer)
  Local string t$
  t$ = s$
  If PWidth(t$, 0) <= w Then
    Fit$ = t$
    Exit Function
  EndIf
  Do While Len(t$) > 0 And PWidth(t$ + "..", 0) > w
    t$ = Left$(t$, Len(t$) - 1)
  Loop
  Fit$ = t$ + ".."
End Function
Function Command$(j As integer)
  If j < 0 Then Exit Function
  If mitem$(j) = "" Then
    Command$ = lbl$(j)
  Else
    Command$ = Dropdown$(j)
  EndIf
End Function
Function Dropdown$(j As integer)
  Local string item$(15), k$
  Local integer n, i, x, y, lw, lh, rowH, hover, old, hit
  Do While n < 16
    item$(n) = Fld$(mitem$(j), n + 1)
    If item$(n) = "" Then Exit Do
    n = n + 1
  Loop
  rowH = fh(0) + 8
  For i = 0 To n - 1
    lw = Max(lw, PWidth(item$(i), 0))
  Next
  lw = Max(lw + 30, bw(j))
  lh = n * rowH + 8
  x = Max(4, Min(bx(j), W - lw - 4))
  y = by(j) + bh(j) + 2
  If y + lh > H - 4 Then y = H - lh - 4
  CurHide
  Blit Read 1, x, y, lw, lh
  RBox x, y, lw, lh, 5, C_INK, C_BAR
  For i = 0 To n - 1
    PText x + 12, y + 4 + i * rowH + rowH \ 2, item$(i), "L", 0, C_INK
  Next
  CurShow
  hover = -1
  hit = -1
  Do
    k$ = Inkey$
    If k$ = Chr$(27) Then Exit Do
    If ClickAt() Then
      If clickX >= x And clickX < x + lw And clickY >= y + 4 And clickY < y + 4 + n * rowH Then hit = (clickY - y - 4) \ rowH
      Exit Do
    EndIf
    old = hover
    hover = -1
    If gmx >= x And gmx < x + lw And gmy >= y + 4 And gmy < y + 4 + n * rowH Then hover = (gmy - y - 4) \ rowH
    If hover <> old Then
      CurHide
      If old >= 0 Then
        Box x + 3, y + 4 + old * rowH, lw - 6, rowH, 1, C_BAR, C_BAR
        PText x + 12, y + 4 + old * rowH + rowH \ 2, item$(old), "L", 0, C_INK
      EndIf
      If hover >= 0 Then
        Box x + 3, y + 4 + hover * rowH, lw - 6, rowH, 1, C_GRN_BASE, C_GRN_BASE
        PText x + 12, y + 4 + hover * rowH + rowH \ 2, item$(hover), "L", 0, C_INK
      EndIf
      CurShow
    EndIf
    Pause 10
  Loop
  CurHide
  Blit Write 1, x, y
  Blit Close 1
  CurShow
  If hit >= 0 Then Dropdown$ = item$(hit)
End Function
Sub TickerAt(x As integer, y As integer, w As integer)
  tkx = x
  tky = y
  tkw = w
  tkh = fh(0) + 10
  CurHide
  RBox tkx, tky, tkw, tkh, 5, C_INK, C_BAR
  CurShow
  WifiCheck
  WeatherLoad
  lastTick = Timer
End Sub
Sub TickerMsg(s$)
  tkMsg$ = Left$(s$, 100)
  tkPos = 0
End Sub
Sub TickerSeg(slot As integer, s$)
  tkSeg$(slot) = Left$(s$, 60)
End Sub
Sub DrawArt(i As integer, st As integer)
  CurHide
  Blit Write 10 + i, bx(i) - 2, by(i) - 2
  If st <> 0 Then
    RBox bx(i) - 2, by(i) - 2, bw(i) + 4, bh(i) + 4, 5, C_AMBER
    RBox bx(i) - 1, by(i) - 1, bw(i) + 2, bh(i) + 2, 4, C_AMBER
  EndIf
  If st = 2 Then RBox bx(i), by(i), bw(i), bh(i), 4, C_AMBER
  CurShow
End Sub
Function NetLine$(f$)
  NetLine$ = ""
  On Error Skip
  Open f$ For Input As #3
  If MM.Errno Then Exit Function
  If Not Eof(#3) Then Line Input #3, NetLine$
  Close #3
End Function
Function WeatherNow$(la As float, lo As float, where$)
  Local integer wb(1024), p, code
  Local float temp, wind
  Local string req$, l$, d$
  If la = 0 And lo = 0 Then
    l$ = NetLine$(HOME_DIR$ + "/lastfix.dat")
    la = Val(Fld$(l$, 1))
    lo = Val(Fld$(l$, 2))
    If la <> 0 Or lo <> 0 Then where$ = "last GPS fix"
  EndIf
  If la = 0 And lo = 0 Then
    l$ = NetLine$(HOME_DIR$ + "/home.dat")
    la = Val(Fld$(l$, 1))
    lo = Val(Fld$(l$, 2))
    If la <> 0 Or lo <> 0 Then where$ = Fld$(l$, 3)
  EndIf
  If la = 0 And lo = 0 Then IpLocate la, lo, where$
  If la = 0 And lo = 0 Then Exit Function
  req$ = "GET /v1/forecast?latitude=" + Str$(la, 0, 4) + "&longitude=" + Str$(lo, 0, 4)
  req$ = req$ + "&current_weather=true HTTP/1.0" + Chr$(13) + Chr$(10)
  req$ = req$ + "Host: api.open-meteo.com" + Chr$(13) + Chr$(10) + Chr$(13) + Chr$(10)
  On Error Skip
  WEB Open TCP Client "api.open-meteo.com", 80
  If MM.Errno Then Exit Function
  On Error Skip
  WEB TCP Client Request req$, wb(), 8000
  On Error Skip
  WEB Close TCP Client
  p = LInStr(wb(), Chr$(34) + "current_weather" + Chr$(34) + ":{")
  If p = 0 Then Exit Function
  temp = JsonNum(wb(), "temperature", p)
  wind = JsonNum(wb(), "windspeed", p)
  code = JsonNum(wb(), "weathercode", p)
  d$ = WeatherText$(code) + ", " + Str$(temp, 0, 1) + " C, wind " + Str$(wind, 0, 0) + " km/h"
  On Error Skip
  Open HOME_DIR$ + "/weather.txt" For Output As #3
  If MM.Errno = 0 Then
    Print #3, Str$(Epoch(Now)) + "|" + d$ + "|" + where$
    Close #3
  EndIf
  WeatherNow$ = d$
End Function
Sub IpLocate(la As float, lo As float, where$)
  Local integer b(512), p, q
  Local string req$, city$
  req$ = "GET /json/?fields=status,city,lat,lon HTTP/1.0" + Chr$(13) + Chr$(10)
  req$ = req$ + "Host: ip-api.com" + Chr$(13) + Chr$(10) + Chr$(13) + Chr$(10)
  On Error Skip
  WEB Open TCP Client "ip-api.com", 80
  If MM.Errno Then Exit Sub
  On Error Skip
  WEB TCP Client Request req$, b(), 8000
  On Error Skip
  WEB Close TCP Client
  If LInStr(b(), Chr$(34) + "success" + Chr$(34)) = 0 Then Exit Sub
  la = JsonNum(b(), "lat", 1)
  lo = JsonNum(b(), "lon", 1)
  p = LInStr(b(), Chr$(34) + "city" + Chr$(34) + ":" + Chr$(34))
  If p Then
    q = LInStr(b(), Chr$(34), p + 8)
    If q > p + 8 Then city$ = LGetStr$(b(), p + 8, Min(40, q - p - 8))
  EndIf
  where$ = "near " + Choice(city$ = "", "here", city$)
End Sub
Function JsonNum(b() As integer, k$, from As integer) As float
  Local integer p
  p = LInStr(b(), Chr$(34) + k$ + Chr$(34) + ":", from)
  If p = 0 Then Exit Function
  JsonNum = Val(LGetStr$(b(), p + Len(k$) + 3, 12))
End Function
Function WeatherText$(c As integer)
  Select Case c
    Case 0
      WeatherText$ = "Clear sky"
    Case 1
      WeatherText$ = "Mainly clear"
    Case 2
      WeatherText$ = "Partly cloudy"
    Case 3
      WeatherText$ = "Overcast"
    Case 45, 48
      WeatherText$ = "Fog"
    Case 51, 53, 55
      WeatherText$ = "Drizzle"
    Case 61
      WeatherText$ = "Slight rain"
    Case 63
      WeatherText$ = "Rain"
    Case 65
      WeatherText$ = "Heavy rain"
    Case 71, 73, 75, 77
      WeatherText$ = "Snow"
    Case 80, 81
      WeatherText$ = "Rain showers"
    Case 82
      WeatherText$ = "Violent showers"
    Case 85, 86
      WeatherText$ = "Snow showers"
    Case 95, 96, 99
      WeatherText$ = "Thunderstorm"
    Case Else
      WeatherText$ = "Weather code " + Str$(c)
  End Select
End Function
