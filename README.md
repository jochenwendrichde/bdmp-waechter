# BDMP-Wächter Marsberg

Prüft alle 10 Minuten https://anmeldung.bdmp.de/index.php **eingeloggt** und
schickt eine Push-Nachricht (ntfy), sobald ein Wettkampf in Marsberg/Leitmar
auf **„Anmeldung offen"** springt. RO-Voranmeldung zählt nicht.

Eingeloggt, weil die öffentliche Ansicht teils „Anmeldung offen" zeigt,
obwohl erst die RO-Voranmeldung läuft.

## Einrichtung
- GitHub → Settings → Secrets and variables → Actions → *New repository secret*:
  `BDMP_KENNUNG` = deine BDMP-Zugangskennung.
- Handy: App **ntfy** → Topic `jw-bdmp-marsberg-42164d02ba` abonnieren.
- Test: Actions → „BDMP-Wächter Marsberg" → *Run workflow*.

## Verhalten
- Erster Lauf: einmal Überblick, was gerade offen ist. Danach nur Änderungen.
- Login-Problem oder geänderte Seite: eine Push-Warnung (nicht alle 10 Min).
- `state.json` löschen = Überblick erneut schicken.
