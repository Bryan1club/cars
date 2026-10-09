' net.inc -- email and text sending for the pages that need it (MAIL
' SETUP's TEST, EMAIL/TXT). build.py adds only the Subs/Functions a page
' uses, same as core.inc, so pages that don't send anything pay nothing.
'
' Settings live in the club folder:
'   mail.dat  server|port|email address|password (B64$)|send-test-to
'   sms.dat   phone IP|port|username|password (B64$)|test phone number
' The phone is the "SMS Gateway for Android" app in Local Server mode,
' the same one club.py used (POST /message, basic auth, JSON).
'
' Email goes over TLS from the first byte (port 465). club.py used 587
' with STARTTLS, which MMBasic's WEB OPEN TLS CLIENT can't do.

' a password box: like core's EditText$, but shows stars
Function EditPass$(x As integer, y As integer, w As integer, s$)
  Local string t$, k$
  t$ = s$
  TextBox x, y, w, String$(Len(t$), "*") + "_", 1
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
          If Len(t$) < 40 And k$ <> "|" Then t$ = t$ + k$
      End Select
      TextBox x, y, w, String$(Len(t$), "*") + "_", 1
    EndIf
    If ClickAt() Then Exit Do
    Pause 10
  Loop
  TextBox x, y, w, String$(Len(t$), "*"), 0
  EditPass$ = t$
End Function

' the settings line from a .dat file ("" if there isn't one)
Function NetLine$(f$)
  NetLine$ = ""
  On Error Skip
  Open f$ For Input As #3
  If MM.Errno Then Exit Function
  If Not Eof(#3) Then Line Input #3, NetLine$
  Close #3
End Function

Function B64$(s$)
  Local string t$, a$
  Local integer i, n, v
  a$ = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
  For i = 1 To Len(s$) Step 3
    n = Len(s$) - i + 1
    v = Asc(Mid$(s$, i, 1)) << 16
    If n > 1 Then v = v Or (Asc(Mid$(s$, i + 1, 1)) << 8)
    If n > 2 Then v = v Or Asc(Mid$(s$, i + 2, 1))
    t$ = t$ + Mid$(a$, ((v >> 18) And 63) + 1, 1) + Mid$(a$, ((v >> 12) And 63) + 1, 1)
    t$ = t$ + Choice(n > 1, Mid$(a$, ((v >> 6) And 63) + 1, 1), "=")
    t$ = t$ + Choice(n > 2, Mid$(a$, (v And 63) + 1, 1), "=")
  Next
  B64$ = t$
End Function

Function UnB64$(s$)
  Local string t$, a$
  Local integer i, k, v, c, bits
  a$ = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
  For i = 1 To Len(s$)
    c = Instr(a$, Mid$(s$, i, 1))
    If c > 0 Then
      v = ((v << 6) Or (c - 1)) And &HFFFFFF
      bits = bits + 6
      If bits >= 8 Then
        bits = bits - 8
        t$ = t$ + Chr$((v >> bits) And 255)
      EndIf
    EndIf
  Next
  UnB64$ = t$
End Function

' one SMTP command and its reply; "" if the reply starts with want$,
' otherwise what went wrong. buf%() holds the reply.
Function SmtpCmd$(c$, want$, buf%())
  If c$ = "" Then
    On Error Skip
    WEB TCP CLIENT READ buf%(), 15000
  Else
    On Error Skip
    WEB TCP CLIENT REQUEST c$ + Chr$(13) + Chr$(10), buf%(), 15000
  EndIf
  If MM.Errno Then
    SmtpCmd$ = MM.ErrMsg$
  ElseIf LGetStr$(buf%(), 1, 3) <> want$ Then
    SmtpCmd$ = LGetStr$(buf%(), 1, Min(60, LLen(buf%())))
  EndIf
End Function

' today as an email Date header wants it: Fri, 25 Sep 2026 10:15:00 +1000
Function MailDate$()
  Local string d$
  d$ = Date$
  MailDate$ = Left$(Day$(Now), 3) + ", " + Left$(d$, 2) + " " + Mid$("JanFebMarAprMayJunJulAugSepOctNovDec", Val(Mid$(d$, 4, 2)) * 3 - 2, 3) + " " + Right$(d$, 4) + " " + Time$ + " +1000"
End Function

' send one email with the MAIL SETUP settings; "" when it went, otherwise
' a short reason. mailText$ lines are split on "~" (MMBasic strings can't
' easily hold a typed newline).
Function SendMail$(to$, subj$, mailText$)
  Local buf%(256), msg%(512)
  Local string cfg$, srv$, usr$, pw$, e$, l$, b$
  Local integer port, p
  cfg$ = NetLine$(HOME_DIR$ + "/mail.dat")
  srv$ = Fld$(cfg$, 1)
  port = Val(Fld$(cfg$, 2))
  usr$ = Fld$(cfg$, 3)
  pw$ = UnB64$(Fld$(cfg$, 4))
  If srv$ = "" Or usr$ = "" Then
    SendMail$ = "MAIL SETUP isn't filled in"
    Exit Function
  EndIf
  If port = 0 Or port = 587 Then port = 465
  On Error Skip
  WEB OPEN TLS CLIENT srv$, port, 15000
  If MM.Errno Then
    SendMail$ = "Can't reach " + srv$ + ": " + MM.ErrMsg$
    Exit Function
  EndIf
  e$ = SmtpCmd$("", "220", buf%())
  If e$ = "" Then e$ = SmtpCmd$("EHLO carclub", "250", buf%())
  If e$ = "" Then e$ = SmtpCmd$("AUTH LOGIN", "334", buf%())
  If e$ = "" Then e$ = SmtpCmd$(B64$(usr$), "334", buf%())
  If e$ = "" Then
    e$ = SmtpCmd$(B64$(pw$), "235", buf%())
    If e$ <> "" Then e$ = "login refused - check the email address and password"
  EndIf
  If e$ = "" Then e$ = SmtpCmd$("MAIL FROM:<" + usr$ + ">", "250", buf%())
  If e$ = "" Then e$ = SmtpCmd$("RCPT TO:<" + to$ + ">", "250", buf%())
  If e$ = "" Then e$ = SmtpCmd$("DATA", "354", buf%())
  If e$ = "" Then
    LongString Clear msg%()
    MailLine msg%(), "From: " + usr$
    MailLine msg%(), "To: " + to$
    MailLine msg%(), "Subject: " + subj$
    MailLine msg%(), "Date: " + MailDate$()
    MailLine msg%(), "Content-Type: text/plain; charset=us-ascii"
    MailLine msg%(), ""
    b$ = mailText$
    Do
      p = Instr(b$, "~")
      If p = 0 Then
        l$ = b$
        b$ = ""
      Else
        l$ = Left$(b$, p - 1)
        b$ = Mid$(b$, p + 1)
      EndIf
      ' a line starting "." would end the message early (SMTP dot-stuffing)
      If Left$(l$, 1) = "." Then l$ = "." + l$
      MailLine msg%(), l$
    Loop Until b$ = ""
    On Error Skip
    WEB TCP CLIENT WRITE msg%()
    If MM.Errno Then e$ = MM.ErrMsg$
  EndIf
  If e$ = "" Then e$ = SmtpCmd$(".", "250", buf%())
  On Error Skip
  WEB TCP CLIENT REQUEST "QUIT" + Chr$(13) + Chr$(10), buf%(), 3000
  On Error Skip
  WEB CLOSE TCP CLIENT
  SendMail$ = e$
End Function

Sub MailLine(m%(), s$)
  LongString Append m%(), s$ + Chr$(13) + Chr$(10)
End Sub

' 0412 345 678 -> +61412345678; already +61... stays; "" if no digits
Function E164$(ph$)
  Local string d$, c$
  Local integer i
  For i = 1 To Len(ph$)
    c$ = Mid$(ph$, i, 1)
    If c$ >= "0" And c$ <= "9" Then d$ = d$ + c$
  Next
  If d$ = "" Then Exit Function
  If Left$(d$, 2) = "61" Then
    E164$ = "+" + d$
  ElseIf Left$(d$, 1) = "0" Then
    E164$ = "+61" + Mid$(d$, 2)
  Else
    E164$ = "+" + d$
  EndIf
End Function

' JSON-safe text: quotes and backslashes escaped, "~" becomes a newline
Function JsonStr$(s$)
  Local string t$, c$
  Local integer i
  For i = 1 To Len(s$)
    c$ = Mid$(s$, i, 1)
    If c$ = Chr$(34) Or c$ = "\" Then
      t$ = t$ + "\" + c$
    ElseIf c$ = "~" Then
      t$ = t$ + "\n"
    ElseIf c$ >= " " Then
      t$ = t$ + c$
    EndIf
  Next
  JsonStr$ = t$
End Function

' send one text through the phone gateway; "" when it went, otherwise why
Function SendSms$(phone$, text$)
  Local buf%(128), req%(128)
  Local string cfg$, ip$, usr$, pw$, to$, j$, r$
  Local integer port
  cfg$ = NetLine$(HOME_DIR$ + "/sms.dat")
  ip$ = Fld$(cfg$, 1)
  port = Val(Fld$(cfg$, 2))
  usr$ = Fld$(cfg$, 3)
  pw$ = UnB64$(Fld$(cfg$, 4))
  If ip$ = "" Or usr$ = "" Then
    SendSms$ = "SMS SETUP isn't filled in"
    Exit Function
  EndIf
  If port = 0 Then port = 8080
  to$ = E164$(phone$)
  If to$ = "" Then
    SendSms$ = "no phone number"
    Exit Function
  EndIf
  j$ = "{" + Chr$(34) + "textMessage" + Chr$(34) + ":{" + Chr$(34) + "text" + Chr$(34) + ":" + Chr$(34)
  LongString Clear req%()
  LongString Append req%(), j$
  LongString Append req%(), JsonStr$(text$)
  LongString Append req%(), Chr$(34) + "}," + Chr$(34) + "phoneNumbers" + Chr$(34) + ":[" + Chr$(34) + to$ + Chr$(34) + "]}"
  r$ = "POST /message HTTP/1.1" + Chr$(13) + Chr$(10) + "Host: " + ip$ + Chr$(13) + Chr$(10)
  r$ = r$ + "Authorization: Basic " + B64$(usr$ + ":" + pw$) + Chr$(13) + Chr$(10)
  r$ = r$ + "Content-Type: application/json" + Chr$(13) + Chr$(10) + "Connection: close" + Chr$(13) + Chr$(10)
  r$ = r$ + "Content-Length: " + Str$(LLen(req%())) + Chr$(13) + Chr$(10) + Chr$(13) + Chr$(10)
  On Error Skip
  WEB OPEN TCP CLIENT ip$, port, 10000
  If MM.Errno Then
    SendSms$ = "Can't reach the phone at " + ip$ + " - same WiFi?"
    Exit Function
  EndIf
  LongString Clear buf%()
  LongString Append buf%(), r$
  On Error Skip
  WEB TCP CLIENT WRITE buf%()
  If MM.Errno = 0 Then
    On Error Skip
    WEB TCP CLIENT WRITE req%()
  EndIf
  If MM.Errno = 0 Then
    On Error Skip
    WEB TCP CLIENT READ buf%(), 10000
  EndIf
  If MM.Errno Then
    SendSms$ = MM.ErrMsg$
  ElseIf Instr(LGetStr$(buf%(), 1, Min(20, LLen(buf%()))), " 20") = 0 Then
    SendSms$ = "phone said: " + LGetStr$(buf%(), 1, Min(40, LLen(buf%())))
  EndIf
  On Error Skip
  WEB CLOSE TCP CLIENT
End Function

' --- weather (the ticker on every page shows it; club.bas fetches it) ----
' where the weather is for: the last GPS fix (lastfix.dat, kept by the GPS
' page), else roughly where the board's internet connection is (ip-api.com,
' plain HTTP, no key). la/lo 0 = work it out. where$ says which it was.
' Returns "Clear sky, 21.5 C, wind 12 km/h" or "" and saves weather.txt
' (epoch|text|where) for every page's ticker.
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
  ' the club's own town (UNIT NAME > Town), before guessing by internet
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
  ' skip the units block, which also has a "temperature" key
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

' WMO codes, as used by open-meteo's "weathercode" (same list as club.py)
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

' a town's position from open-meteo's place search (plain HTTP, no key).
' It only knows plain place names, so: "Mt"/"Pt" become Mount/Port, a state
' on the end (South Australia, SA, Vic...) picks between same-named towns
' instead of being searched for, and with no match the last word is dropped
' and it tries again. Sets la, lo, where$; 0 if nothing was found.
Function TownLookup(t$, la As float, lo As float, where$) As integer
  Local string nm$, st$, w$
  Local integer i, tries
  nm$ = " " + Trim$(t$) + " "
  ' the state, if one's on the end (full name or short, as typed)
  For i = 1 To 8
    w$ = StateName$(i)
    If UCase$(Right$(nm$, Len(Fld$(w$, 1)) + 1)) = UCase$(Fld$(w$, 1) + " ") Then
      st$ = Fld$(w$, 1)
      nm$ = Left$(nm$, Len(nm$) - Len(Fld$(w$, 1)) - 1)
      Exit For
    ElseIf UCase$(Right$(nm$, Len(Fld$(w$, 2)) + 2)) = UCase$(" " + Fld$(w$, 2) + " ") Then
      st$ = Fld$(w$, 1)
      nm$ = Left$(nm$, Len(nm$) - Len(Fld$(w$, 2)) - 1)
      Exit For
    EndIf
  Next
  ' Mt -> Mount, Pt -> Port
  If UCase$(Left$(nm$, 4)) = " MT " Or UCase$(Left$(nm$, 4)) = " MT." Then nm$ = " Mount " + Mid$(nm$, 5)
  If UCase$(Left$(nm$, 4)) = " PT " Or UCase$(Left$(nm$, 4)) = " PT." Then nm$ = " Port " + Mid$(nm$, 5)
  nm$ = Trim$(nm$)
  For tries = 1 To 3
    If nm$ = "" Then Exit Function
    If TownAsk(nm$, st$, la, lo, where$) Then
      TownLookup = 1
      Exit Function
    EndIf
    ' no match: drop the last word and try again
    i = Instr(nm$ + " ", " ")
    If Instr(nm$, " ") = 0 Then Exit Function
    Do While Instr(i + 1, nm$, " ")
      i = Instr(i + 1, nm$, " ")
    Loop
    nm$ = Left$(nm$, i - 1)
  Next
End Function

' the states, full name|short (a Select, not one long line: MMBasic lines
' can be at most 255 characters)
Function StateName$(i As integer)
  Select Case i
    Case 1
      StateName$ = "South Australia|SA"
    Case 2
      StateName$ = "Victoria|Vic"
    Case 3
      StateName$ = "New South Wales|NSW"
    Case 4
      StateName$ = "Queensland|Qld"
    Case 5
      StateName$ = "Western Australia|WA"
    Case 6
      StateName$ = "Tasmania|Tas"
    Case 7
      StateName$ = "Northern Territory|NT"
    Case 8
      StateName$ = "Australian Capital Territory|ACT"
  End Select
End Function

' one place search: the first result in state st$ (any, if st$ is "")
Function TownAsk(nm$, st$, la As float, lo As float, where$) As integer
  Local integer b(1024), p, i
  Local string req$, u$, a$
  For i = 1 To Len(nm$)
    u$ = u$ + Choice(Mid$(nm$, i, 1) = " ", "%20", Mid$(nm$, i, 1))
  Next
  req$ = "GET /v1/search?name=" + u$ + "&count=10&country=AU HTTP/1.0" + Chr$(13) + Chr$(10)
  req$ = req$ + "Host: geocoding-api.open-meteo.com" + Chr$(13) + Chr$(10) + Chr$(13) + Chr$(10)
  On Error Skip
  WEB Open TCP Client "geocoding-api.open-meteo.com", 80
  If MM.Errno Then Exit Function
  On Error Skip
  WEB TCP Client Request req$, b(), 8000
  On Error Skip
  WEB Close TCP Client
  p = 1
  Do
    p = LInStr(b(), Chr$(34) + "latitude" + Chr$(34), p)
    If p = 0 Then Exit Function
    a$ = JsonText$(b(), "admin1", p)
    If st$ = "" Or UCase$(a$) = UCase$(st$) Then
      la = JsonNum(b(), "latitude", p)
      lo = JsonNum(b(), "longitude", p)
      where$ = nm$ + Choice(a$ = "", "", ", " + a$)
      TownAsk = 1
      Exit Function
    EndIf
    p = p + 10
  Loop
End Function

' a "key":"text" value from a JSON reply ("" if it isn't there)
Function JsonText$(b() As integer, k$, from As integer)
  Local integer p, q
  p = LInStr(b(), Chr$(34) + k$ + Chr$(34) + ":" + Chr$(34), from)
  If p = 0 Then Exit Function
  p = p + Len(k$) + 4
  q = LInStr(b(), Chr$(34), p)
  If q > p Then JsonText$ = LGetStr$(b(), p, Min(60, q - p))
End Function
