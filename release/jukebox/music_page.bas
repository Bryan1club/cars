' jukebox.bas -- a standalone jukebox for the car club's Pico Computer 3
' boards. This one file is the whole jukebox -- no other files, no pictures,
' no fonts to load: it draws its own background and uses the firmware's
' built-in fonts, and it does not use club.bas or core.inc, so it can be
' copied to any board and run on its own. Later club.bas can offer it as a
' page. It looks like the club pages: brushed-gunmetal panel with rivets,
' the club's colours and glossy buttons.
'
' WHAT IT DOES
'   Browses the whole file tree (the top level lists the drives: A: flash,
'   B: SD card, C: USB stick), plays .mp3 .flac .wav through whatever
'   OPTION AUDIO is set to -- on a Bluetooth build that is the paired
'   speaker -- and moves on to the next track by itself. It opens straight
'   into C:/music, B:/music or B:/Music if one exists.
'
'   RANDOM plays a random mix of the songs in the open folder, as many as
'   you pick, and never a song that has already been played this session.
'
' DISPLAY MODES
'   It starts in MODE 2 (320 x 240, 16 colours) and the MODE button at the
'   top, or the D key, switches to MODE 3 (640 x 480, like the club pages)
'   and back while the music plays. If a mode is refused the jukebox goes
'   back to the one it was in. (Bigger resolutions are not laid out.)
'
' CONTROLS  (keyboard, USB mouse and USB touch screen all work)
'   Click / tap      a folder opens it, a track plays it, a button works it.
'                    The mouse wheel scrolls the list. EXIT (top right)
'                    quits, so no keyboard is needed.
'   Keyboard         Up / Down / PgUp / PgDn move the highlight,
'                    Enter plays or opens, Backspace goes up a folder,
'                    Space pauses / resumes, N next, P previous,
'                    + / - volume, M or S random mix, R repeat,
'                    D display mode, Esc quits.
'
' THE QUEUE
'   The list on screen is the folder being browsed. The tracks that play
'   are a separate QUEUE (qn$, in qdir$), filled from a folder when you
'   start a track in it. That way you can browse other folders while the
'   music carries on, and NEXT / PREV stay in the folder that started.
'
' Run it with:  RUN "C:/jukebox.bas"   (or from wherever it is saved)

Option EXPLICIT
Option DEFAULT NONE

Const MAXT = 640          ' most entries in one folder (a flat music folder
                          ' of ~600 songs is normal here)
Const NAMELEN = 90        ' longest file name kept; a string array element
                          ' otherwise costs 256 bytes, and the heap is small
Const HSIZE = 2053        ' slots in the played-this-session table (prime)
Const NBTN = 8
' 1 when this file is installed as the club's music page (B:/club/music.bas):
' leaving the jukebox then returns to the club menu. 0 for a standalone run.
Const CLUB_MODE = 1
Const START_MODE = 2      ' 2 = 320 x 240 (safe), 3 = 640 x 480

' --- the layout: set for the current mode by Layout ----------------------
' (positions are pixels; every one of these differs between MODE 3 and 2)
Dim integer gmode              ' 3 = 640 x 480, 2 = 320 x 240
Dim integer ready              ' 0 if no usable display mode was found
Dim integer ROWS, ROWH, LISTX, LISTY, LISTW, ROW0
Dim integer STRIPY, STATX, MAXPATH, MAXSTAT
Dim integer BANDY, BANDH, TITX, TITY, INFOY, MAXTITLE
Dim integer BTNY, BTNH, BTNW, BTNGAP
Dim integer EXITX, EXITY, EXITW, EXITH, MODEX
Dim integer HEADY, HINTY
Dim integer RECX, RECR, EQX, EQGAP, EQBW, EQMAX, EQBASE
Dim integer TXTPAD, TXTPADY, MAXLIST
Dim integer fb, fbh, ft, fhd   ' fonts: body, track title, heading; body height
Dim integer pkX0, pkGAP, pkW, pkH, pkY1, pkY2, pkTitleY, pkHintY

' --- what is on screen ---------------------------------------------------
' the folder being browsed: names, whether each is a sub-folder
Dim string tn$(MAXT - 1) Length NAMELEN
Dim string mdir$, startDir$
Dim integer isdir(MAXT - 1)
Dim integer count, top, sel
Dim string status$             ' a message shown at the right of the strip

' --- what is playing -----------------------------------------------------
' the queue: the file names of the tracks in one folder (qdir$), and where
' we are in them
Dim string qn$(MAXT - 1) Length NAMELEN
Dim string qdir$
Dim integer qcount, qi, playing
Dim integer vol, repeatOn
Dim integer mixOn              ' 1 while the queue is a random mix
Dim integer ended              ' set by the firmware when a track finishes
Dim integer paused
Dim float startMs, pausedMs, pauseStart   ' for the elapsed-time clock
Dim integer lastSec

' what has been played this session (see PathHash): 0 = empty slot
Dim integer seen(HSIZE - 1), nseen

' --- animation: the spinning record and the equalizer --------------------
Dim integer eqh(7)             ' height of each equalizer bar
Dim float spin                 ' angle of the record, in radians
Dim float lastAnim

' --- colours (the club's palette slots, set in SetPalette) ---------------
Dim integer C_BLACK, C_GRN_TOP, C_GRN_BASE, C_RED_TOP, C_RED_BASE
Dim integer C_AMBER, C_BAR, C_PAGE, C_DIM, C_FACE, C_INK

' --- buttons -------------------------------------------------------------
Dim string bl$(NBTN - 1)
Dim integer btnx(NBTN - 1)

' --- input ---------------------------------------------------------------
' a popup is open: clicks go to it instead of the screen behind
Dim integer modal, mGot, mX, mY
Dim integer hasMouse, hasTouch, nm, mch(3), ach
Dim integer curX, curY, prevL, lastWheel

Dim integer running, logOn, logMouse, lastLogX, lastLogY, beat

Main

End

' =========================================================================
' progress log: when the file B:/jbdebug exists every stage writes a line to
' B:/jblog.txt (opened and closed each time so it survives a reset)
Sub JbLog(m$)
  If Not logOn Then Exit Sub
  On Error Skip
  Open "B:/jblog.txt" For Append As #7
  On Error Skip
  Print #7, Str$(Int(Timer)) + " " + m$
  On Error Skip
  Close #7
End Sub

Sub Main
  On Error Skip
  logOn = (Dir$("B:/jbdebug", FILE) <> "")
  If logOn Then
    On Error Skip
    Kill "B:/jblog.txt"
  EndIf
  JbLog "start"
  Setup
  JbLog "setup done ready=" + Str$(ready) + " gmode=" + Str$(gmode) + " hasMouse=" + Str$(hasMouse) + " nm=" + Str$(nm) + " hasTouch=" + Str$(hasTouch) + " HRES=" + Str$(MM.HRES)
  If Not ready Then Exit Sub
  vol = 70
  playing = -1
  qi = -1
  running = 1
  ' paint the screen first: reading a big folder (hundreds of files on a USB
  ' stick) can take a while, and a blank screen looks like a hang
  count = 0
  sel = -1
  status$ = "Reading the folder..."
  JbLog "drawing screen"
  DrawScreen
  JbLog "screen drawn; reading folder"
  FindStart
  LoadFolder
  JbLog "folder read: " + mdir$ + " count=" + Str$(count)
  status$ = ""
  DrawList
  DrawStrip
  JbLog "list drawn; entering loop"

  ' test hook: if the file B:/jbdebug exists, save a screenshot and quit
  On Error Skip
  If Dir$("B:/jbshot", FILE) <> "" Then
    Pause 1500
    On Error Skip
    Save Image "B:/jbshot.bmp"
    running = 0
  EndIf
  Do While running
    beat = beat + 1
    If beat = 1 Or beat = 200 Or beat = 2000 Then JbLog "main loop alive, pass " + Str$(beat)
    HandleKeys
    HandleMouse
    If ended Then
      ended = 0
      AdvanceAfterEnd
    EndIf
    UpdateClock
    Animate
    Pause 10
  Loop
  Shutdown
End Sub

' start in START_MODE. MODE 2 is the safe one: some firmware builds refuse
' MODE 3 at their current resolution, and a refused mode change can leave the
' video output blank, so MODE 3 is only tried when the MODE button or the D
' key asks for it (and SwitchMode puts MODE 2 back if it fails).
Sub Setup
  ready = 0
  On Error Skip
  Drive "B:"
  gmode = START_MODE
  On Error Skip
  MODE START_MODE
  If MM.Errno Then
    Print "Jukebox: MODE " + Str$(START_MODE) + " is not available on this display."
    Print "Check OPTION RESOLUTION (the jukebox wants 640x480)."
    Exit Sub
  EndIf
  ready = 1
  CLS
  SetPalette
  Layout
  PaintBox 0, 0, MM.HRES, MM.VRES, C_PAGE
  ProbeInputs
  StartCursor
  BuildButtons
End Sub

Sub Shutdown
  On Error Skip
  Play Stop
  If hasMouse Then GUI Cursor Off
  CLS
  If CLUB_MODE Then
    Run "B:/club/club.bas"
  EndIf
  Print "Jukebox stopped."
End Sub

' the club's 16 palette slots: 0-5 and 15 are the club colours, 6-14 the
' greys of the page background. Slot 0 (black) and 15 (near-white) are also
' the mouse pointer's colours, so they are kept as they are.
Sub SetPalette
  MAP 0 = RGB(0, 0, 0)
  MAP 1 = RGB(67, 160, 71)
  MAP 2 = RGB(46, 125, 50)
  MAP 3 = RGB(226, 75, 74)
  MAP 4 = RGB(168, 40, 40)
  MAP 5 = RGB(255, 176, 0)
  MAP 6 = RGB(17, 18, 19)
  MAP 7 = RGB(20, 22, 24)
  MAP 8 = RGB(23, 25, 27)
  MAP 9 = RGB(26, 28, 31)
  MAP 10 = RGB(30, 32, 35)
  MAP 11 = RGB(33, 36, 39)
  MAP 12 = RGB(42, 44, 47)
  MAP 13 = RGB(66, 70, 74)
  MAP 14 = RGB(117, 121, 125)
  MAP 15 = RGB(232, 234, 237)
  MAP SET
  C_BLACK = MAP(0)
  C_GRN_TOP = MAP(1)
  C_GRN_BASE = MAP(2)
  C_RED_TOP = MAP(3)
  C_RED_BASE = MAP(4)
  C_AMBER = MAP(5)
  C_BAR = MAP(6)
  C_PAGE = MAP(10)
  C_DIM = MAP(13)
  C_FACE = MAP(14)
  C_INK = MAP(15)
End Sub

' every position and font for the current mode. MODE 3 is the club's
' 640 x 480 layout; MODE 2 is the same screen at half the size, with the
' built-in 8 x 12 font, nine list rows and four-letter button labels.
Sub Layout
  If gmode = 3 Then
    fb = 4          ' 10 x 16, very clear
    fbh = 16
    ft = 2          ' 12 x 20, the track title
    fhd = 3         ' 16 x 24, the heading
    ROWS = 11
    ROWH = 22
    LISTX = 20
    LISTY = 62
    LISTW = 600
    TXTPAD = 10
    TXTPADY = 3
    MAXLIST = 56
    STRIPY = 316
    STATX = 320
    MAXPATH = 28
    MAXSTAT = 28
    BANDY = 340
    BANDH = 58
    TITX = 92
    TITY = 6
    INFOY = 34
    MAXTITLE = 36
    BTNY = 406
    BTNH = 34
    BTNW = 70
    BTNGAP = 5
    EXITX = 548
    EXITY = 10
    EXITW = 76
    EXITH = 32
    MODEX = 458
    HEADY = 14
    HINTY = 458
    RECX = 36
    RECR = 24
    EQX = 544
    EQGAP = 8
    EQBW = 6
    EQMAX = 40
    EQBASE = 50
    pkX0 = 40
    pkGAP = 140
    pkW = 120
    pkH = 50
    pkY1 = 112
    pkY2 = 178
    pkTitleY = 78
    pkHintY = 252
  Else
    fb = 1          ' 8 x 12
    fbh = 12
    ft = 1
    fhd = 4         ' 10 x 16
    ROWS = 9
    ROWH = 14
    LISTX = 10
    LISTY = 31
    LISTW = 300
    TXTPAD = 6
    TXTPADY = 1
    MAXLIST = 36
    STRIPY = 166
    STATX = 150
    MAXPATH = 17
    MAXSTAT = 18
    BANDY = 181
    BANDH = 34
    TITX = 50
    TITY = 4
    INFOY = 19
    MAXTITLE = 26
    BTNY = 219
    BTNH = 15
    BTNW = 35
    BTNGAP = 2
    EXITX = 262
    EXITY = 4
    EXITW = 48
    EXITH = 18
    MODEX = 208
    HEADY = 4
    HINTY = 0
    RECX = 20
    RECR = 12
    EQX = 266
    EQGAP = 4
    EQBW = 3
    EQMAX = 20
    EQBASE = 26
    pkX0 = 20
    pkGAP = 70
    pkW = 60
    pkH = 25
    pkY1 = 56
    pkY2 = 89
    pkTitleY = 39
    pkHintY = 126
  EndIf
  ROW0 = LISTY + 3
End Sub

' --- drawing helpers -----------------------------------------------------
Sub PaintBox(x As integer, y As integer, w As integer, h As integer, c As integer)
  Box x, y, w, h, 1, c, c
End Sub

' text in a built-in font (all of them are fixed width); transparent
' behind the letters
Sub Txt(x As integer, y As integer, s$, f As integer, c As integer)
  Text x, y, s$, "LT", f, 1, c, -1
End Sub

' width in pixels of s$ in font f, for centring
Function TW(s$, f As integer) As integer
  TW = Len(s$) * Choice(f = 1, 8, Choice(f = 2, 12, Choice(f = 3, 16, 10)))
End Function

' a glossy club button: a deeper shade for the body and a lighter one for
' the top band, a black drop shadow under the white label (like club.bas)
Sub Glossy(x As integer, y As integer, w As integer, h As integer, topc As integer, botc As integer, t$, tc As integer)
  Local integer r, tx, ty
  r = h \ 4
  RBox x, y, w, h, r, C_BLACK, botc
  RBox x + 3, y + 3, w - 6, h \ 2 - 2, r - 2, topc, topc
  tx = x + (w - TW(t$, fb)) \ 2
  ty = y + (h - fbh) \ 2
  If tc = C_INK Then Txt tx + 1, ty + 1, t$, fb, C_BLACK
  Txt tx, ty, t$, fb, tc
End Sub

' --- finding the music ---------------------------------------------------
' open the first likely music folder; if none exists start at the drive list
' (mdir$ = "" means the drive list)
Sub FindStart
  Local string f$
  Local integer i
  mdir$ = ""
  For i = 1 To 3
    startDir$ = Choice(i = 1, "C:/music", Choice(i = 2, "B:/music", "B:/Music"))
    On Error Skip
    f$ = Dir$(startDir$ + "/*", ALL)
    If MM.Errno = 0 And f$ <> "" Then
      mdir$ = startDir$
      Exit For
    EndIf
  Next
End Sub

' the drives that answer, as the entries of the top-level list
Sub LoadDrives
  Local string d$, f$
  Local integer i
  count = 0
  For i = 1 To 3
    d$ = Choice(i = 1, "A:", Choice(i = 2, "B:", "C:"))
    On Error Skip
    f$ = Dir$(d$ + "/*", ALL)
    If MM.Errno = 0 Then
      tn$(count) = d$
      isdir(count) = 1
      count = count + 1
    EndIf
  Next
  top = 0
  sel = Choice(count > 0, 0, -1)
End Sub

Function DriveLabel$(d$)
  DriveLabel$ = Choice(d$ = "A:", "flash", Choice(d$ = "B:", "SD card", "USB stick"))
End Function

' the open folder: ".." first, then sub-folders, then the tracks, each
' group A-Z. (".." from a drive's top returns to the drive list.)
Sub LoadFolder
  Local string f$, u$
  Local integer nd, first
  If mdir$ = "" Then
    LoadDrives
    Exit Sub
  EndIf
  first = 1
  tn$(0) = ".."
  isdir(0) = 1
  count = 1
  On Error Skip
  f$ = Dir$(mdir$ + "/*", DIR)
  Do While f$ <> "" And count < MAXT And MM.Errno = 0
    If f$ <> "." And f$ <> ".." And Len(f$) <= NAMELEN Then
      tn$(count) = f$
      isdir(count) = 1
      count = count + 1
    EndIf
    f$ = Dir$()
  Loop
  nd = count
  If nd - first > 1 Then Sort tn$(), , 2, first, nd - first
  On Error Skip
  f$ = Dir$(mdir$ + "/*", FILE)
  Do While f$ <> "" And count < MAXT And MM.Errno = 0
    u$ = UCase$(f$)
    If IsTrack(u$) And Len(f$) <= NAMELEN Then
      tn$(count) = f$
      isdir(count) = 0
      count = count + 1
    EndIf
    f$ = Dir$()
  Loop
  If count - nd > 1 Then Sort tn$(), , 2, nd, count - nd
  top = 0
  sel = Choice(count > 1, 1, 0)
End Sub

' a file name as a title: no extension, and no leading track number
' ("001 - Led Zeppelin - Stairway To Heaven.mp3" -> "Led Zeppelin - Stairway
' To Heaven")
Function Pretty$(f$)
  Local string t$
  Local integer p
  t$ = f$
  p = Len(t$)
  Do While p > 0 And Mid$(t$, p, 1) <> "."
    p = p - 1
  Loop
  If p > 1 And Len(t$) - p <= 4 Then t$ = Left$(t$, p - 1)
  p = 1
  Do While p <= Len(t$) And Mid$(t$, p, 1) >= "0" And Mid$(t$, p, 1) <= "9"
    p = p + 1
  Loop
  If p > 1 And Mid$(t$, p, 3) = " - " Then t$ = Mid$(t$, p + 3)
  Pretty$ = t$
End Function

Function IsTrack(u$) As integer
  IsTrack = (Right$(u$, 4) = ".MP3" Or Right$(u$, 5) = ".FLAC" Or Right$(u$, 4) = ".WAV")
End Function

' --- what has been played this session -----------------------------------
' Every track that starts playing is remembered, so a random mix never plays
' one twice in a session. Remembering whole paths would cost too much of the
' small heap, so each path becomes one big number (two checksums joined, so
' two different paths almost never match) kept in a hash table: seen() holds
' the numbers, 0 means an empty slot.
Function PathHash(p$) As integer
  Local integer i, a, b, c
  a = 7
  b = 11
  For i = 1 To Len(p$)
    c = Asc(Mid$(p$, i, 1))
    a = (a * 131 + c) Mod 1000000007
    b = (b * 137 + c) Mod 998244353
  Next
  PathHash = a * 1000000000 + b + 1     ' never 0
End Function

' the table slot holding h, or the empty slot where h belongs
Function SeenSlot(h As integer) As integer
  Local integer k
  k = h Mod HSIZE
  Do While seen(k) <> 0 And seen(k) <> h
    k = (k + 1) Mod HSIZE
  Loop
  SeenSlot = k
End Function

Sub MarkPlayed(p$)
  Local integer h, k
  h = PathHash(p$)
  k = SeenSlot(h)
  If seen(k) = 0 Then
    ' a nearly full table gets slow, so start the history again
    If nseen >= 1400 Then
      ForgetPlayed
      k = SeenSlot(h)
    EndIf
    seen(k) = h
    nseen = nseen + 1
  EndIf
End Sub

Function WasPlayed(p$) As integer
  WasPlayed = (seen(SeenSlot(PathHash(p$))) <> 0)
End Function

Sub ForgetPlayed
  Local integer i
  For i = 0 To HSIZE - 1
    seen(i) = 0
  Next
  nseen = 0
End Sub

' --- the queue -----------------------------------------------------------
' every track in the open folder becomes the queue; qi is the one chosen
Sub FillQueue(chosen As integer)
  Local integer i
  qcount = 0
  qdir$ = mdir$
  mixOn = 0
  For i = 0 To count - 1
    If Not isdir(i) Then
      qn$(qcount) = tn$(i)
      If i = chosen Then qi = qcount
      qcount = qcount + 1
    EndIf
  Next
End Sub

' A random mix: the tracks of the open folder that have not been played this
' session, in random order, nWanted of them (0 = all of them). They become the
' queue and play through once -- no wrapping, so nothing is played twice.
Sub RandomMix(nWanted As integer)
  Local integer cand(MAXT - 1)
  Local integer nc, i, j, t, take
  nc = 0
  For i = 0 To count - 1
    If Not isdir(i) Then
      If Not WasPlayed(mdir$ + "/" + tn$(i)) Then
        cand(nc) = i
        nc = nc + 1
      EndIf
    EndIf
  Next
  If nc = 0 Then
    status$ = "All played - FORGET"
    DrawStrip
    Exit Sub
  EndIf
  ' shuffle the candidates (Fisher-Yates)
  For i = nc - 1 To 1 Step -1
    j = Int(Rnd * (i + 1))
    t = cand(i)
    cand(i) = cand(j)
    cand(j) = t
  Next
  take = nc
  If nWanted > 0 And nWanted < nc Then take = nWanted
  qdir$ = mdir$
  qcount = take
  For i = 0 To take - 1
    qn$(i) = tn$(cand(i))
  Next
  mixOn = 1
  PlayQueue 0
  If playing >= 0 Then
    status$ = "Mix " + Str$(take) + ", " + Str$(nc - take) + " left"
    DrawStrip
  EndIf
End Sub

' --- playing -------------------------------------------------------------
Sub PlayQueue(n As integer)
  Local string f$, u$
  If n < 0 Or n >= qcount Then Exit Sub
  On Error Skip
  Play Stop
  f$ = qdir$ + "/" + qn$(n)
  u$ = UCase$(f$)
  ' On Error Skip only covers the next line, so one before each PLAY
  If Right$(u$, 4) = ".MP3" Then
    On Error Skip
    Play Mp3 f$, TrackDone
  ElseIf Right$(u$, 5) = ".FLAC" Then
    On Error Skip
    Play Flac f$, TrackDone
  Else
    On Error Skip
    Play Wav f$, TrackDone
  EndIf
  If MM.Errno Then
    playing = -1
    status$ = "Can't play: " + MM.ErrMsg$
  Else
    qi = n
    playing = n
    MarkPlayed qdir$ + "/" + qn$(n)
    paused = 0
    startMs = Timer
    pausedMs = 0
    lastSec = -1
    status$ = ""
    SetVolume vol
  EndIf
  DrawNowPlaying
  DrawButtons
  DrawStrip
End Sub

' called by the firmware when a track reaches its end; it only sets a flag
' because drawing and starting the next track belong in the main loop
Sub TrackDone
  ended = 1
End Sub

Sub AdvanceAfterEnd
  Local integer n
  n = PickNext(1)
  If n < 0 Then
    playing = -1
    If mixOn Then status$ = "Mix finished"
    DrawNowPlaying
    DrawButtons
    DrawStrip
  Else
    PlayQueue n
  EndIf
End Sub

' the next (d = 1) or previous (d = -1) queue entry; at the end of the queue
' it wraps if repeat is on (never in a random mix), else -1
Function PickNext(d As integer) As integer
  Local integer n
  PickNext = -1
  If qcount = 0 Then Exit Function
  n = qi + d
  If n >= qcount Or n < 0 Then
    If repeatOn And Not mixOn Then
      n = (n + qcount) Mod qcount
    Else
      Exit Function
    EndIf
  EndIf
  PickNext = n
End Function

Sub TogglePause
  If playing < 0 Then Exit Sub
  If paused Then
    On Error Skip
    Play Resume
    pausedMs = pausedMs + (Timer - pauseStart)
    paused = 0
  Else
    On Error Skip
    Play Pause
    pauseStart = Timer
    paused = 1
  EndIf
  DrawNowPlaying
  DrawButtons
End Sub

Sub StopTrack
  On Error Skip
  Play Stop
  playing = -1
  paused = 0
  DrawNowPlaying
  DrawButtons
  DrawStrip
End Sub

Sub SetVolume(v As integer)
  vol = Max(0, Min(100, v))
  On Error Skip
  Play Volume vol, vol
  DrawBandInfo
End Sub

' --- list actions --------------------------------------------------------
' Enter / click on a list row: open a folder or start a track
Sub ActivateRow(r As integer)
  If r < 0 Or r >= count Then Exit Sub
  If isdir(r) Then
    If tn$(r) = ".." Then
      GoUp
    Else
      mdir$ = Choice(mdir$ = "", tn$(r), mdir$ + "/" + tn$(r))
      LoadFolder
      DrawList
      DrawStrip
    EndIf
  Else
    FillQueue r
    sel = r
    PlayQueue qi
    DrawList
  EndIf
End Sub

Sub GoUp
  Local integer i, p
  If mdir$ = "" Then Exit Sub
  ' from a drive's top ("C:") step back to the drive list
  If Len(mdir$) <= 2 Then
    mdir$ = ""
  Else
    p = 0
    For i = Len(mdir$) To 1 Step -1
      If Mid$(mdir$, i, 1) = "/" Then
        p = i
        Exit For
      EndIf
    Next
    If p > 1 Then
      mdir$ = Left$(mdir$, p - 1)
    Else
      mdir$ = Left$(mdir$, 2)
    EndIf
  EndIf
  LoadFolder
  DrawList
  DrawStrip
End Sub

Sub MoveSel(d As integer)
  If count = 0 Then Exit Sub
  sel = Max(0, Min(count - 1, sel + d))
  If sel < top Then top = sel
  If sel >= top + ROWS Then top = sel - ROWS + 1
  DrawList
End Sub

Sub ScrollList(d As integer)
  top = Max(0, Min(Max(0, count - ROWS), top + d))
  DrawList
End Sub

' --- switching the display mode ------------------------------------------
' MODE 3 <-> MODE 2 while the music carries on. If the other mode is not
' available the screen is left as it is and a message says so.
Sub SwitchMode
  Local integer newm
  newm = Choice(gmode = 3, 2, 3)
  If hasMouse Then GUI Cursor Off
  On Error Skip
  MODE newm
  If MM.Errno Then
    ' refused: put the old mode back, and redraw it all, because a refused
    ' change can leave the screen blank
    On Error Skip
    MODE gmode
    CLS
    SetPalette
    Layout
    StartCursor
    status$ = "MODE " + Str$(newm) + " not available"
    DrawScreen
    Exit Sub
  EndIf
  gmode = newm
  CLS
  SetPalette
  Layout
  BuildButtons
  StartCursor
  ' keep the highlighted row on screen with the new row count
  top = Max(0, Min(top, Max(0, count - ROWS)))
  If sel >= top + ROWS Then top = sel - ROWS + 1
  If sel >= 0 And sel < top Then top = sel
  DrawScreen
End Sub

' --- buttons -------------------------------------------------------------
' four-letter labels in MODE 2, where a button is only 35 pixels wide
Sub BuildButtons
  Local integer i
  bl$(0) = "PREV"
  bl$(1) = "PLAY"
  bl$(2) = "STOP"
  bl$(3) = "NEXT"
  bl$(4) = Choice(gmode = 3, "VOL -", "VOL-")
  bl$(5) = Choice(gmode = 3, "VOL +", "VOL+")
  bl$(6) = Choice(gmode = 3, "RANDOM", "RAND")
  bl$(7) = Choice(gmode = 3, "REPEAT", "REPT")
  For i = 0 To NBTN - 1
    btnx(i) = LISTX + i * (BTNW + BTNGAP)
  Next
End Sub

Function ButtonAt(x As integer, y As integer) As integer
  Local integer i
  ButtonAt = -1
  If y < BTNY Or y >= BTNY + BTNH Then Exit Function
  For i = 0 To NBTN - 1
    If x >= btnx(i) And x < btnx(i) + BTNW Then
      ButtonAt = i
      Exit Function
    EndIf
  Next
End Function

Sub PressButton(i As integer)
  Local integer n
  Select Case i
    Case 0
      PlayQueue PickNextOrWrap(-1)
    Case 1
      If playing >= 0 Then
        TogglePause
      ElseIf sel >= 0 Then
        ActivateRow sel
      EndIf
    Case 2
      StopTrack
    Case 3
      PlayQueue PickNextOrWrap(1)
    Case 4
      SetVolume vol - 10
    Case 5
      SetVolume vol + 10
    Case 6
      n = PickMixSize()
      If n = -2 Then
        ForgetPlayed
        status$ = "History cleared"
        DrawList
        DrawStrip
      ElseIf n >= 0 Then
        RandomMix n
        DrawList
      EndIf
    Case 7
      repeatOn = 1 - repeatOn
      DrawButtons
  End Select
End Sub

' PREV / NEXT by hand always wrap, so there is always somewhere to go
Function PickNextOrWrap(d As integer) As integer
  Local integer keep
  keep = repeatOn
  repeatOn = 1
  PickNextOrWrap = PickNext(d)
  repeatOn = keep
End Function

' --- the random-mix picker -----------------------------------------------
' A popup over the list: how many songs? Returns the number (0 = all of
' them), -2 for FORGET PLAYED, or -1 if cancelled (Esc).
' Click or tap a box, or press 1 to 7.
Function PickMixSize() As integer
  Local integer ox(6), oy(6), ow(6), ov(6)
  Local string ol$(6), k$
  Local integer i, done, tx
  ol$(0) = "5"
  ol$(1) = "10"
  ol$(2) = "20"
  ol$(3) = "50"
  ol$(4) = "100"
  ol$(5) = "ALL"
  ol$(6) = Choice(gmode = 3, "FORGET PLAYED", "FORGET")
  ov(0) = 5
  ov(1) = 10
  ov(2) = 20
  ov(3) = 50
  ov(4) = 100
  ov(5) = 0
  ov(6) = -2
  For i = 0 To 3
    ox(i) = pkX0 + i * pkGAP
    oy(i) = pkY1
    ow(i) = pkW
  Next
  ox(4) = pkX0
  ox(5) = pkX0 + pkGAP
  ox(6) = pkX0 + 2 * pkGAP
  For i = 4 To 6
    oy(i) = pkY2
    ow(i) = pkW
  Next
  ow(6) = Choice(gmode = 3, 2 * pkW + 20, pkW + 10)
  CurHide
  RBox LISTX, LISTY, LISTW, ROWS * ROWH + 6, 4, C_DIM, C_BAR
  tx = (LISTX * 2 + LISTW - TW("RANDOM MIX - HOW MANY?", ft)) \ 2
  Txt tx, pkTitleY, "RANDOM MIX - HOW MANY?", ft, C_INK
  For i = 0 To 6
    Glossy ox(i), oy(i), ow(i), pkH, C_GRN_TOP, C_GRN_BASE, ol$(i), C_INK
  Next
  Txt LISTX + 20, pkHintY, "Keys 1-7, or click.  Esc cancels", fb, C_FACE
  CurShow
  PickMixSize = -1
  modal = 1
  mGot = 0
  done = 0
  Do While Not done
    k$ = Inkey$
    If k$ <> "" Then
      If Asc(k$) = 27 Then done = 1
      If k$ >= "1" And k$ <= "7" Then
        PickMixSize = ov(Val(k$) - 1)
        done = 1
      EndIf
    EndIf
    HandleMouse
    If mGot Then
      mGot = 0
      For i = 0 To 6
        If mX >= ox(i) And mX < ox(i) + ow(i) And mY >= oy(i) And mY < oy(i) + pkH Then
          PickMixSize = ov(i)
          done = 1
        EndIf
      Next
    EndIf
    Pause 10
  Loop
  modal = 0
  DrawList
End Function

' --- drawing -------------------------------------------------------------
Sub DrawScreen
  Local integer hx
  CurHide
  DrawBackground
  hx = (MM.HRES - TW("JUKEBOX", fhd)) \ 2
  Txt hx + 1, HEADY + 1, "JUKEBOX", fhd, C_BLACK
  Txt hx, HEADY, "JUKEBOX", fhd, C_INK
  Glossy MODEX, EXITY, EXITW, EXITH, C_GRN_TOP, C_GRN_BASE, "MODE", C_INK
  Glossy EXITX, EXITY, EXITW, EXITH, C_RED_TOP, C_RED_BASE, "EXIT", C_INK
  If gmode = 3 Then
    Txt 16, HINTY, "Enter play  Space pause  N/P track  +/- vol  M random  R repeat  D mode  Esc quit", 1, C_FACE
  EndIf
  CurShow
  DrawList
  DrawNowPlaying
  DrawButtons
  DrawStrip
End Sub

' The page background, drawn in code like the club's picture: a dark panel
' with fine horizontal "brushed" streaks, and a seam with a row of rivets
' near the top and the bottom. (It is deterministic: the same streaks every
' time, from its own little random-number generator, so the RANDOM mix's
' Rnd is not disturbed.)
Sub DrawBackground
  Local integer i, n, x, y, w, k, seed, y1, y2
  k = Choice(gmode = 3, 2, 1)         ' 2 in MODE 3, 1 in MODE 2
  PaintBox 0, 0, MM.HRES, MM.VRES, C_PAGE
  seed = 7
  n = MM.HRES * MM.VRES \ 1200
  For i = 1 To n
    seed = (seed * 1103515245 + 12345) And &H7FFFFFFF
    x = seed Mod MM.HRES
    seed = (seed * 1103515245 + 12345) And &H7FFFFFFF
    y = seed Mod MM.VRES
    seed = (seed * 1103515245 + 12345) And &H7FFFFFFF
    w = 12 * k + seed Mod (50 * k)
    ' the dim grey slots 7 to 12 of the club palette
    Line x, y, Min(MM.HRES - 1, x + w), y, 1, MAP(7 + (seed \ 7) Mod 6)
  Next
  y1 = 26 * k
  y2 = 224 * k
  PaintBox 0, y1 + 3 * k, MM.HRES, 1, C_BLACK
  PaintBox 0, y1 + 3 * k + 1, MM.HRES, 1, C_DIM
  PaintBox 0, y2 + 3 * k, MM.HRES, 1, C_BLACK
  PaintBox 0, y2 + 3 * k + 1, MM.HRES, 1, C_DIM
  For x = 10 * k To MM.HRES - 1 Step 20 * k
    Circle x, y1, k, 1, 1, C_FACE, C_FACE
    Circle x, y2, k, 1, 1, C_FACE, C_FACE
  Next
End Sub

Sub DrawList
  Local integer r, y, c
  Local string t$
  CurHide
  RBox LISTX, LISTY, LISTW, ROWS * ROWH + 6, 4, C_DIM, C_BAR
  For r = 0 To ROWS - 1
    If top + r < count Then
      y = ROW0 + r * ROWH
      If top + r = sel Then PaintBox LISTX + 3, y, LISTW - 6, ROWH, C_AMBER
      t$ = tn$(top + r)
      If isdir(top + r) Then
        t$ = "[" + t$ + "]"
      Else
        t$ = Pretty$(t$)
      EndIf
      If mdir$ = "" Then t$ = t$ + "   " + DriveLabel$(tn$(top + r))
      c = C_INK
      ' tracks already played this session are dimmed
      If Not isdir(top + r) Then
        If WasPlayed(mdir$ + "/" + tn$(top + r)) Then c = C_FACE
      EndIf
      ' black on the amber selection bar
      If top + r = sel Then c = C_BLACK
      Txt LISTX + TXTPAD, y + TXTPADY, Left$(t$, MAXLIST), fb, c
    EndIf
  Next
  CurShow
End Sub

' the folder on the left of the strip under the list, a message on the right
Sub DrawStrip
  Local string p$
  CurHide
  PaintBox LISTX, STRIPY, LISTW, fbh + 2, C_PAGE
  p$ = Choice(mdir$ = "", "Drives", mdir$)
  If Len(p$) > MAXPATH Then p$ = "~" + Right$(p$, MAXPATH - 1)
  Txt LISTX + 4, STRIPY + 1, p$, fb, C_FACE
  Txt LISTX + STATX, STRIPY + 1, Left$(status$, MAXSTAT), fb, C_AMBER
  CurShow
End Sub

' the now-playing band: the record on the left, the equalizer on the right
' (both drawn by Animate), the title and the volume and time between
Sub DrawNowPlaying
  Local string t$
  CurHide
  RBox LISTX, BANDY, LISTW, BANDH, 4, C_DIM, C_BAR
  If playing >= 0 Then
    t$ = Choice(paused, "(paused) ", "") + Pretty$(qn$(playing))
  Else
    t$ = "Nothing playing"
  EndIf
  Txt TITX, BANDY + TITY, Left$(t$, MAXTITLE), ft, C_INK
  CurShow
  DrawBandInfo
  DrawRecord
End Sub

' volume and the time into the track, under the title
Sub DrawBandInfo
  Local string r$
  Local integer s
  CurHide
  PaintBox TITX, BANDY + INFOY - 1, EQX - TITX - 8, fbh + 2, C_BAR
  r$ = "VOL " + Str$(vol) + "%"
  If playing >= 0 Then
    s = Int((Timer - startMs - pausedMs) / 1000)
    r$ = r$ + "  " + Str$(s \ 60) + ":" + Right$("0" + Str$(s Mod 60), 2)
  EndIf
  If mixOn Then r$ = r$ + "  MIX"
  If repeatOn Then r$ = r$ + "  REPEAT"
  Txt TITX, BANDY + INFOY, r$, fb, C_AMBER
  CurShow
End Sub

Sub DrawButtons
  Local integer i, topc, botc, tc
  Local string t$
  CurHide
  For i = 0 To NBTN - 1
    topc = C_GRN_TOP
    botc = C_GRN_BASE
    tc = C_INK
    If i = 2 Then
      topc = C_RED_TOP
      botc = C_RED_BASE
    EndIf
    ' switches that are on turn amber, with black lettering
    If i = 6 And mixOn Then
      topc = C_AMBER
      botc = C_AMBER
      tc = C_BLACK
    EndIf
    If i = 7 And repeatOn Then
      topc = C_AMBER
      botc = C_AMBER
      tc = C_BLACK
    EndIf
    t$ = bl$(i)
    If i = 1 Then
      If playing >= 0 And Not paused Then
        t$ = Choice(gmode = 3, "PAUSE", "PAUS")
      Else
        t$ = "PLAY"
      EndIf
    EndIf
    Glossy btnx(i), BTNY, BTNW, BTNH, topc, botc, t$, tc
  Next
  CurShow
End Sub

' once a second while playing, so the clock under the title counts up
Sub UpdateClock
  Local integer s
  If playing < 0 Or paused Then Exit Sub
  s = Int((Timer - startMs - pausedMs) / 1000)
  If s = lastSec Then Exit Sub
  lastSec = s
  DrawBandInfo
End Sub

' --- the record and the equalizer ----------------------------------------
' the record sits at the left of the band; a bright mark on it turns while
' a track plays
Sub DrawRecord
  Local integer cx, cy, r
  Local float a
  cx = LISTX + RECX
  cy = BANDY + BANDH \ 2
  r = RECR
  CurHide
  Circle cx, cy, r, 1, 1, C_FACE, C_BLACK
  Circle cx, cy, r * 2 \ 3, 1, 1, C_DIM
  Circle cx, cy, Max(2, r \ 3), 1, 1, C_AMBER, C_AMBER
  Circle cx, cy, 1, 1, 1, C_BAR, C_BAR
  a = spin
  Line cx + Int(Cos(a) * r * 0.6), cy + Int(Sin(a) * r * 0.6), cx + Int(Cos(a) * r * 0.92), cy + Int(Sin(a) * r * 0.92), 2, C_INK
  a = spin + Pi
  Line cx + Int(Cos(a) * r * 0.6), cy + Int(Sin(a) * r * 0.6), cx + Int(Cos(a) * r * 0.92), cy + Int(Sin(a) * r * 0.92), 2, C_INK
  CurShow
End Sub

' about eight times a second while a track plays: turn the record and move
' the equalizer bars; when nothing plays the bars settle to the floor
Sub Animate
  Local integer i, h, moving, x
  If Timer - lastAnim < 120 Then Exit Sub
  lastAnim = Timer
  moving = 0
  If playing >= 0 And Not paused Then
    spin = spin + 0.5
    For i = 0 To 7
      eqh(i) = (eqh(i) * 2 + Int(Rnd * EQMAX)) \ 3
    Next
    moving = 1
  Else
    For i = 0 To 7
      If eqh(i) > 0 Then
        eqh(i) = Max(0, eqh(i) - Max(1, EQMAX \ 7))
        moving = 1
      EndIf
    Next
  EndIf
  If Not moving Then Exit Sub
  CurHide
  PaintBox EQX - 4, BANDY + 4, 8 * EQGAP + 4, BANDH - 8, C_BAR
  For i = 0 To 7
    h = eqh(i)
    If h > 0 Then
      x = EQX + i * EQGAP
      PaintBox x, BANDY + EQBASE - h, EQBW, h, C_GRN_TOP
      If h > 4 Then PaintBox x, BANDY + EQBASE - h, EQBW, Max(2, EQBW \ 2), C_AMBER
    EndIf
  Next
  CurShow
  DrawRecord
End Sub

' --- input ---------------------------------------------------------------
Sub ProbeInputs
  Local integer v
  hasTouch = 0
  hasMouse = 0
  On Error Skip
  v = Touch(X)
  ' a USB monitor can report a touch position even when nothing touches it, and
  ' then waiting for the touch to end would wait forever: only trust touch if
  ' it says "no touch" (-1) right now
  If MM.Errno = 0 And v = -1 Then hasTouch = 1
  JbLog "probe: Touch(X)=" + Str$(v) + " errno=" + Str$(MM.Errno) + " -> hasTouch=" + Str$(hasTouch)
  nm = 0
  For v = 1 To 4
    If MM.Info(USB v) = 2 And nm < 4 Then
      mch(nm) = v
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
  curX = MM.HRES \ 2
  curY = MM.VRES \ 2
  GUI Cursor On 0, curX, curY, C_INK
  JbLog "GUI Cursor On done at " + Str$(curX) + "," + Str$(curY) + " errno=" + Str$(MM.Errno)
  On Error Skip
  lastWheel = Device(MOUSE ach, W)
End Sub

' the firmware's pointer saves what is under it, so hide it while drawing
Sub CurHide
  If hasMouse Then GUI Cursor Hide
End Sub

Sub CurShow
  If hasMouse Then GUI Cursor Show
End Sub

Sub HandleKeys
  Local string k$
  k$ = Inkey$
  If k$ = "" Then Exit Sub
  Select Case Asc(k$)
    Case 27
      running = 0
    Case 128
      MoveSel -1
    Case 129
      MoveSel 1
    Case 136
      MoveSel -ROWS
    Case 137
      MoveSel ROWS
    Case 13
      ActivateRow sel
    Case 8, 127
      GoUp
    Case 32
      PressButton 1
    Case 43, 61
      PressButton 5
    Case 45
      PressButton 4
    Case Else
      Select Case UCase$(k$)
        Case "N"
          PressButton 3
        Case "P"
          PressButton 0
        Case "S", "M"
          PressButton 6
        Case "R"
          PressButton 7
        Case "D"
          SwitchMode
      End Select
  End Select
End Sub

' mouse (and touch): a click is the left button going down. Every USB
' mouse is read and whichever moved last becomes the active one.
Sub HandleMouse
  Local integer i, c, x, y, l, wheel, d
  If hasTouch Then
    x = Touch(X)
    If x >= 0 Then
      y = Touch(Y)
      d = 0
      Do While Touch(X) >= 0 And d < 200
        Pause 10
        d = d + 1
      Loop
      Clicked x, y
    EndIf
  EndIf
  If hasMouse = 0 Then Exit Sub
  l = 0
  For i = 0 To nm - 1
    c = mch(i)
    x = Device(MOUSE c, X)
    y = Device(MOUSE c, Y)
    If x <> curX Or y <> curY Then ach = c
    If c = ach Then
      curX = x
      curY = y
      l = Device(MOUSE c, L)
    EndIf
  Next
  GUI Cursor curX, curY
  If logOn And logMouse < 6 And (curX <> lastLogX Or curY <> lastLogY) Then
    logMouse = logMouse + 1
    lastLogX = curX
    lastLogY = curY
    JbLog "mouse moved to " + Str$(curX) + "," + Str$(curY) + " ach=" + Str$(ach)
  EndIf
  If l <> 0 And prevL = 0 Then Clicked curX, curY
  prevL = l
  ' the wheel scrolls the list three rows a notch
  On Error Skip
  wheel = Device(MOUSE ach, W)
  If wheel <> lastWheel Then
    d = (lastWheel - wheel) * 3
    ScrollList d
    lastWheel = wheel
  EndIf
End Sub

' x, y are screen pixels
Sub Clicked(x As integer, y As integer)
  Local integer b, r
  If modal Then
    mX = x
    mY = y
    mGot = 1
    Exit Sub
  EndIf
  If y >= EXITY And y < EXITY + EXITH Then
    If x >= EXITX And x < EXITX + EXITW Then
      running = 0
      Exit Sub
    EndIf
    If x >= MODEX And x < MODEX + EXITW Then
      SwitchMode
      Exit Sub
    EndIf
  EndIf
  b = ButtonAt(x, y)
  If b >= 0 Then
    PressButton b
    Exit Sub
  EndIf
  If x >= LISTX And x < LISTX + LISTW And y >= ROW0 And y < ROW0 + ROWS * ROWH Then
    r = top + (y - ROW0) \ ROWH
    If r < count Then
      sel = r
      ActivateRow r
      DrawList
    EndIf
  EndIf
End Sub

' NOTES FOR LATER (club.bas)
'   Everything above is one program. To offer it as a club.bas page, the
'   page would RUN this file and this file would RUN club.bas again on Esc or
'   EXIT (Shutdown prints "Jukebox stopped." where that call would go). The
'   routines are kept separate (queue, drawing, input) so a page version
'   can reuse FillQueue / PlayQueue / PickNext unchanged.
