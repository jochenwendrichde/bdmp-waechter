#!/usr/bin/env python3
"""BDMP-Wächter: meldet Marsberg-Wettkämpfe, sobald die Anmeldung offen ist.

Loggt sich mit der Zugangskennung ein, weil nur die eingeloggte Ansicht den
echten Status zeigt (öffentlich steht teils "Anmeldung offen", obwohl erst
RO-Voranmeldung läuft).
"""
import html, http.cookiejar, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

URL = "https://anmeldung.bdmp.de/index.php"
OPEN = "Anmeldung offen"
STATE = Path(__file__).with_name("state.json")
KENNUNG = os.environ.get("BDMP_KENNUNG", "")
TOPIC = os.environ.get("NTFY_TOPIC", "")

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
opener.addheaders = [("User-Agent", "Mozilla/5.0 (BDMP-Waechter)")]


def clean(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def is_marsberg(text):
    """Marsberg/Leitmar, tolerant gegen Tippfehler wie 'Marsbegrer'."""
    return bool(re.search(r"\b(mars|maa?res)b|leitmar", text, re.I))


def get(data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    with opener.open(URL, body, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def parse(page):
    events = {}
    for block in re.split(r'<a id="(?=[^"]+"></a>)', page)[1:]:
        eid = block.split('"', 1)[0]
        title = re.search(r'class="fav-title">(.*?)</span>', block, re.S)
        if not title:
            continue
        fields = {clean(k).rstrip(":"): clean(v) for k, v in
                  re.findall(r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>', block, re.S)}
        events[eid] = {"titel": clean(title.group(1)), "datum": fields.get("Datum", ""),
                       "ort": fields.get("Ort", ""), "disziplinen": fields.get("Disziplinen", ""),
                       "status": fields.get("Status", ""), "felder": fields}
        # Nur-RO-Phase: eingeloggt steht dann eine Zeile "RO-Bereitschaft melden"
        if any(name.startswith("RO-") for name in fields):
            events[eid]["status"] += " (nur RO)"
    return events


def notify(title, body):
    print(f"== {title}\n{body}\n")
    if TOPIC:
        req = urllib.request.Request(
            f"https://ntfy.sh/{TOPIC}", data=body.encode(), method="POST",
            headers={"Title": title.encode(), "Priority": "high", "Tags": "dart", "Click": URL})
        urllib.request.urlopen(req, timeout=30)


def describe(k, v):
    return f"{v['titel']}\nDatum: {v['datum']}\nOrt: {v['ort'] or '-'}\n{URL}#{k}"


def fail(state, msg):
    """Meldet ein Problem nur beim ersten Auftreten, nicht alle 10 Minuten."""
    print(msg)
    if state.get("fehler"):
        sys.exit(0)
    notify("BDMP-Waechter: Problem", msg)
    state["fehler"] = True
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    sys.exit(1)


def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    if not KENNUNG:
        fail(state, "Keine BDMP-Zugangskennung hinterlegt (GitHub-Secret BDMP_KENNUNG).")
    get()  # Session-Cookie holen
    page = get({"op": "1", "Kennwort": KENNUNG})
    if 'name="login"' in page:
        page = get()
    if 'name="login"' in page:
        fail(state, "Login bei BDMP fehlgeschlagen - Zugangskennung pruefen.")

    events = parse(page)
    if len(events) < 5:
        fail(state, f"Nur {len(events)} Wettkaempfe gelesen - hat sich die BDMP-Seite geaendert?")
    hits = {k: v for k, v in events.items() if is_marsberg(v["ort"] + " " + v["titel"])}
    old = state.get("events")

    if old is None:  # erster Lauf: einmal Überblick, danach nur Änderungen
        offen = [describe(k, v) for k, v in hits.items() if v["status"] == OPEN]
        notify("BDMP-Waechter aktiv: Marsberg",
               ("Jetzt schon offen:\n\n" + "\n\n".join(offen)) if offen else
               "Aktuell ist kein Marsberg-Wettkampf zur Anmeldung offen. Ich melde mich, sobald einer aufgeht.")
    else:
        for k, v in hits.items():
            if v["status"] == OPEN and old.get(k, {}).get("status") != OPEN:
                notify(f"Marsberg offen: {v['titel']}"[:200], describe(k, v) + f"\n\n{v['disziplinen']}")
    if state.get("fehler"):
        notify("BDMP-Waechter laeuft wieder", "Das Problem ist behoben, ich ueberwache wieder.")

    for k, v in hits.items():
        print(f"{v['datum']:>16}  {v['status']:<32} {v['titel']}")
        del v["felder"]
    STATE.write_text(json.dumps({"events": hits}, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
