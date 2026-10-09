' music.bas -- MUSIC page for the car club (MMBasic), ported from
' club.py's music_player_page.py: the tracks in the music folder, a
' "now playing" line, big PREV / PLAY / PAUSE / STOP / NEXT buttons, and
' the top menu bar: PLAY, TRACK, VOLUME, MENU. Plays .mp3 .flac .wav
' through the board's own audio (OPTION AUDIO), and moves on to the next
' track when one finishes.
'
' The music folder is the USB stick's (C:/music, as club.py used) or,
' without a stick, the SD card's B:/music. Artists are folders in it:
' click a [folder] to open it, ".." goes back up. NEXT/PREV and the
' move-on after a track stay within the open folder's tracks.
'
' LIST: ADD SONG adds the picked song to the playlist (playlist.txt in the
' club folder), SHOW LIST plays from it (on down the list by itself),
' REMOVE SONG, SHOW FOLDERS, CLEAR LIST (twice).
'
' Build with: python mmbasic/build.py  (writes ../music.bas)

Option EXPLICIT
Option DEFAULT NONE

Const MAXT = 300, ROWS = 11

Dim string tn$(MAXT - 1), mdir$, rootDir$
' the playlist view: plMode = 1 shows playlist.txt (full paths in tp$)
Const PL_FILE$ = "playlist.txt"
Dim string tp$(MAXT - 1)
Dim integer plMode, clrArmed
Dim integer isdir(MAXT - 1)
Dim integer count, top, sel, playing, j, v, vol, ended
Dim integer lx, ly, lw, rh, ny
Dim integer bPrev, bPlay, bPause, bStop, bNext, bUp, bDn, bLUp, bLDn
Dim string cmd$

CoreInit
v = AddMenu("PLAY", "PLAY|PAUSE|RESUME|STOP")
v = AddMenu("TRACK", "NEXT|PREV")
v = AddMenu("VOLUME", "UP|DOWN")
v = AddMenu("LIST", "ADD SONG|REMOVE SONG|SHOW LIST|SHOW FOLDERS|CLEAR LIST")
v = AddMenu("MENU", "")
v = AddMenu("HELP", "")
DrawPage "MUSIC"
Layout
DrawAllBtns
StartCursor
vol = 70
FindRoot
playing = -1
LoadFolder
NowPlaying

Do
  j = PollInput()
  ' wheel, drag and keys on the list: arrows only highlight here (a folder
  ' opens on Enter or a click), Enter plays / opens
  v = ListNav(lx, ly, lw, rh, ROWS, count, top)
  If v = 1 Then DrawList
  If v = 2 Then
    sel = kbRow
    DrawList
  EndIf
  If v = 3 Then Clicked lx + 8, ly + 3 + (kbRow - top) * rh + rh \ 2
  If j = -2 Then GoBack
  If j = -3 Then Clicked clickX, clickY
  cmd$ = ""
  Select Case j
    Case bPrev
      cmd$ = "PREV"
    Case bPlay
      cmd$ = "PLAY"
    Case bPause
      cmd$ = "PAUSE"
    Case bStop
      cmd$ = "STOP"
    Case bNext
      cmd$ = "NEXT"
    Case bUp
      cmd$ = "UP"
    Case bDn
      cmd$ = "DOWN"
    Case bLUp
      cmd$ = "LIST UP"
    Case bLDn
      cmd$ = "LIST DOWN"
    Case Else
      cmd$ = Command$(j)
  End Select
  If cmd$ = "HELP" Then HelpFor "music", "music.bas"
  Select Case cmd$
    Case "MENU"
      GoBack
    Case "PLAY"
      If sel >= 0 Then PlayTrack sel
    Case "PAUSE"
      If playing >= 0 Then
        On Error Skip
        Play Pause
        TickerMsg "Paused"
      EndIf
    Case "RESUME"
      If playing >= 0 Then
        On Error Skip
        Play Resume
        TickerMsg "Playing " + tn$(playing)
      EndIf
    Case "STOP"
      StopTrack
    Case "NEXT"
      PlayTrack NextTrack(Max(playing, sel), 1)
    Case "PREV"
      PlayTrack NextTrack(Max(playing, sel), -1)
    Case "ADD SONG"
      AddSong
    Case "REMOVE SONG"
      RemoveSong
    Case "SHOW LIST"
      LoadPlaylist
    Case "SHOW FOLDERS"
      plMode = 0
      LoadFolder
    Case "CLEAR LIST"
      If clrArmed Then
        On Error Skip
        Kill PL_FILE$
        clrArmed = 0
        TickerMsg "Playlist cleared"
        If plMode Then LoadPlaylist
      Else
        clrArmed = 1
        TickerMsg "Press CLEAR LIST again to empty the playlist"
      EndIf
    Case "UP"
      SetVol vol + 10
    Case "DOWN"
      SetVol vol - 10
    Case "LIST UP"
      If top > 0 Then
        top = Max(0, top - ROWS)
        DrawList
      EndIf
    Case "LIST DOWN"
      If top + ROWS < count Then
        top = top + ROWS
        DrawList
      EndIf
  End Select
  ' the track that was playing finished: on to the next one
  If ended Then
    ended = 0
    If playing >= 0 Then PlayTrack NextTrack(playing, 1)
  EndIf
  Pause 10
Loop

Sub Layout
  Local integer m, bh2, bw2, y, i
  m = W \ 40
  rh = fh(0) + 5
  lx = m
  ' room on the right of the list for its UP/DOWN buttons
  lw = W - 3 * m - W \ 8
  ly = H * 13 \ 100
  ny = ly + ROWS * rh + 6 + m + fh(1) \ 2
  bh2 = H \ 11
  bw2 = (W - 8 * m) \ 7
  y = ny + fh(1) \ 2 + m
  bPrev = AddBtn("PREV", m, y, bw2, bh2, 0)
  bPlay = AddBtn("PLAY", m * 2 + bw2, y, bw2, bh2, 0)
  bPause = AddBtn("PAUSE", m * 3 + bw2 * 2, y, bw2, bh2, 0)
  bStop = AddBtn("STOP", m * 4 + bw2 * 3, y, bw2, bh2, 1)
  bNext = AddBtn("NEXT", m * 5 + bw2 * 4, y, bw2, bh2, 0)
  bDn = AddBtn("VOL -", m * 6 + bw2 * 5, y, bw2, bh2, 0)
  bUp = AddBtn("VOL +", m * 7 + bw2 * 6, y, bw2, bh2, 0)
  ' page the list up and down (153 artist folders don't fit on one screen)
  bLUp = AddBtn("UP", lx + lw + m, ly, W \ 8, bh2, 0)
  bLDn = AddBtn("DOWN", lx + lw + m, ly + ROWS * rh + 6 - bh2, W \ 8, bh2, 0)
  TickerAt m, H - fh(0) - 10 - m \ 2, W - 2 * m
End Sub

' the music folder: the USB stick's if it has one, else the SD card's
Sub FindRoot
  Local string f$
  Local integer i
  For i = 1 To 3
    rootDir$ = Choice(i = 1, "C:/music", Choice(i = 2, "B:/music", "B:/Music"))
    On Error Skip
    f$ = Dir$(rootDir$ + "/*", ALL)
    If MM.Errno = 0 And f$ <> "" Then Exit For
  Next
  mdir$ = rootDir$
End Sub

' the open folder: its sub-folders (with ".." below the top), then its
' .mp3 .flac .wav tracks, each A-Z
Sub LoadFolder
  Local string f$, u$
  Local integer nd
  count = 0
  If mdir$ <> rootDir$ Then
    tn$(0) = ".."
    isdir(0) = 1
    count = 1
  EndIf
  On Error Skip
  f$ = Dir$(mdir$ + "/*", DIR)
  Do While f$ <> "" And count < MAXT And MM.Errno = 0
    If f$ <> "." And f$ <> ".." Then
      tn$(count) = f$
      isdir(count) = 1
      count = count + 1
    EndIf
    f$ = Dir$()
  Loop
  nd = count
  If nd - (mdir$ <> rootDir$) > 1 Then Sort tn$(), , 2, (mdir$ <> rootDir$), nd - (mdir$ <> rootDir$)
  On Error Skip
  f$ = Dir$(mdir$ + "/*", FILE)
  Do While f$ <> "" And count < MAXT And MM.Errno = 0
    u$ = UCase$(f$)
    If Right$(u$, 4) = ".MP3" Or Right$(u$, 5) = ".FLAC" Or Right$(u$, 4) = ".WAV" Then
      tn$(count) = f$
      isdir(count) = 0
      count = count + 1
    EndIf
    f$ = Dir$()
  Loop
  If count - nd > 1 Then Sort tn$(), , 2, nd, count - nd
  top = 0
  sel = -1
  If playing >= 0 Then playing = -1
  DrawList
  TickerMsg mdir$ + "  -  " + Str$(nd) + " folders, " + Str$(count - nd) + " tracks"
End Sub

' the next (stp 1) or previous (stp -1) track in the folder after n,
' skipping folders; -1 if there are no tracks
Function NextTrack(n As integer, stp As integer) As integer
  Local integer i, t
  NextTrack = -1
  If count = 0 Then Exit Function
  t = n
  For i = 1 To count
    t = (t + stp + count) Mod count
    If Not isdir(t) Then
      NextTrack = t
      Exit Function
    EndIf
  Next
End Function

Sub DrawList
  Local integer r, y
  Local string t$
  CurHide
  RBox lx, ly, lw, ROWS * rh + 6, 4, C_DIM, C_BAR
  For r = 0 To ROWS - 1
    If top + r < count Then
      y = ly + 3 + r * rh
      If top + r = sel Then Box lx + 3, y, lw - 6, rh, 1, C_GRN_BASE, C_GRN_BASE
      t$ = tn$(top + r)
      If isdir(top + r) Then t$ = "[" + t$ + "]"
      If top + r = playing Then t$ = "> " + t$
      PText lx + 8, y + rh \ 2, Fit$(t$, lw - 16), "L", 0, C_INK
    EndIf
  Next
  CurShow
End Sub

Sub NowPlaying
  Local string t$
  If playing >= 0 Then
    t$ = "Now playing: " + tn$(playing)
  Else
    t$ = "Nothing playing"
  EndIf
  t$ = t$ + "    Volume " + Str$(vol) + "%"
  CurHide
  Box lx, ny - fh(1) \ 2, lw, fh(1), 1, C_PAGE, C_PAGE
  CurShow
  PText lx, ny, Fit$(t$, lw), "L", 0, C_INK
End Sub

Sub Clicked(x As integer, y As integer)
  Local integer r
  If x >= lx And x < lx + lw And y >= ly + 3 And y < ly + 3 + ROWS * rh Then
    r = top + (y - ly - 3) \ rh
    If r < count Then
      If isdir(r) Then
        If tn$(r) = ".." Then
          mdir$ = Left$(mdir$, RInstr(mdir$, "/") - 1)
        Else
          mdir$ = mdir$ + "/" + tn$(r)
        EndIf
        LoadFolder
      ElseIf r = sel Then
        PlayTrack r
      Else
        sel = r
        DrawList
        TickerMsg tn$(sel) + " - click again to play"
      EndIf
    EndIf
  EndIf
End Sub

' called by the firmware when a track reaches its end
Sub TrackDone
  ended = 1
End Sub

Sub PlayTrack(n As integer)
  Local string f$, u$
  If n < 0 Or n >= count Then Exit Sub
  If isdir(n) Then Exit Sub
  On Error Skip
  Play Stop
  f$ = Choice(plMode, tp$(n), mdir$ + "/" + tn$(n))
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
    TickerMsg "Can't play " + tn$(n) + ": " + MM.ErrMsg$
    playing = -1
  Else
    playing = n
    sel = n
    If sel < top Or sel >= top + ROWS Then top = (sel \ ROWS) * ROWS
    SetVol vol
    TickerMsg "Playing " + tn$(n)
  EndIf
  DrawList
  NowPlaying
End Sub

Sub StopTrack
  On Error Skip
  Play Stop
  playing = -1
  DrawList
  NowPlaying
  TickerMsg "Stopped"
End Sub

Sub SetVol(v2 As integer)
  vol = Max(0, Min(100, v2))
  On Error Skip
  Play Volume vol, vol
  NowPlaying
End Sub

' music stops when the page is left, as a new program closes the audio
Sub GoBack
  On Error Skip
  Play Stop
  GoPage "club.bas"
End Sub

Function RInstr(s$, c$) As integer
  Local integer i
  For i = Len(s$) To 1 Step -1
    If Mid$(s$, i, 1) = c$ Then
      RInstr = i
      Exit Function
    EndIf
  Next
End Function

' --- the playlist (playlist.txt in the club folder: a full path per line) ---
Sub AddSong
  If plMode Then
    TickerMsg "That's the playlist - SHOW FOLDERS to pick songs to add"
    Exit Sub
  EndIf
  If sel < 0 Or sel >= count Then
    TickerMsg "Pick a song first"
    Exit Sub
  EndIf
  If isdir(sel) Then
    TickerMsg "That's a folder - open it and pick a song"
    Exit Sub
  EndIf
  Open PL_FILE$ For Append As #1
  Print #1, mdir$ + "/" + tn$(sel)
  Close #1
  TickerMsg "Added " + tn$(sel) + " to the playlist (" + Str$(PlCount()) + " songs)"
End Sub

Function PlCount() As integer
  Local string l$
  On Error Skip
  Open PL_FILE$ For Input As #1
  If MM.Errno Then Exit Function
  Do While Not Eof(#1)
    Line Input #1, l$
    If l$ <> "" Then PlCount = PlCount + 1
  Loop
  Close #1
End Function

Sub LoadPlaylist
  Local string l$
  Local integer p
  On Error Skip
  Play Stop
  plMode = 1
  count = 0
  On Error Skip
  Open PL_FILE$ For Input As #1
  If MM.Errno = 0 Then
    Do While Not Eof(#1) And count < MAXT
      Line Input #1, l$
      If l$ <> "" Then
        tp$(count) = l$
        p = RInstr(l$, "/")
        tn$(count) = Mid$(l$, p + 1)
        isdir(count) = 0
        count = count + 1
      EndIf
    Loop
    Close #1
  EndIf
  top = 0
  sel = Choice(count > 0, 0, -1)
  playing = -1
  DrawList
  NowPlaying
  If count = 0 Then
    TickerMsg "The playlist is empty - SHOW FOLDERS, pick a song, LIST > ADD SONG"
  Else
    TickerMsg "Playlist: " + Str$(count) + " songs - click one (or Enter) to play, it carries on down the list"
  EndIf
End Sub

Sub RemoveSong
  Local integer i
  If Not plMode Then
    TickerMsg "SHOW LIST first, then pick the song to take out"
    Exit Sub
  EndIf
  If sel < 0 Or sel >= count Then
    TickerMsg "Pick a song in the playlist first"
    Exit Sub
  EndIf
  Open PL_FILE$ For Output As #1
  For i = 0 To count - 1
    If i <> sel Then Print #1, tp$(i)
  Next
  Close #1
  TickerMsg "Took out " + tn$(sel)
  LoadPlaylist
End Sub
