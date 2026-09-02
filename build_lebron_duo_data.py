#!/usr/bin/env python3
"""
Builds lebron-duo-data.js for the "Beat LeBron" duo quiz.

Reads the public nba-player-data JSON (rsStats, poStats, awards, awardVotes) plus the
nba-headshots index, computes ~35 career metrics for every All-Star in the database
and LeBron's own marks, and writes a compact JS file the quiz loads with a <script> tag.

Usage (from the repo folder):
    python build_lebron_duo_data.py            # fetch from GitHub and write lebron-duo-data.js
    python build_lebron_duo_data.py --local D  # read the JSON files from folder D instead

Re-run it whenever the nba-player-data sheet changes (new season, new awards).
"""
import json, sys, os, re, unicodedata, collections, urllib.request, datetime

RAW = "https://raw.githubusercontent.com/jsierrahoopshype/nba-player-data/main/"
HEADSHOT_INDEX = "https://raw.githubusercontent.com/jsierrahoopshype/nba-headshots/main/players/metadata/players_all.json"
OUT = "lebron-duo-data.js"
LEBRON = "LeBron James"
MIN_ALLSTAR = 1  # players need at least this many All-Star selections to enter the pool


def load(name, local):
    if local:
        with open(os.path.join(local, name), encoding="utf-8") as f:
            return json.load(f)
    url = HEADSHOT_INDEX if name == "players_all.json" else RAW + name
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"\(.*?\)", "", s)                      # "Larry Johnson (1969)" -> "Larry Johnson"
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", s.lower())
    return " ".join(re.sub(r"[^a-z0-9 ]", "", s).split())


def num(x):
    try:
        return float(x)
    except Exception:
        return 0.0


# ---- metric definitions -------------------------------------------------------
# key, short label (used in the question sentence), long label, kind
# kind: "count" (small integers, exact) or "total" (big career totals)
METRICS = [
    ("asg",      "All-Star selections",                 "count"),
    ("allnba1",  "All-NBA First Team selections",       "count"),
    ("allnba",   "All-NBA selections",                  "count"),
    ("alldef1",  "All-Defensive First Team selections", "count"),
    ("alldef",   "All-Defensive selections",            "count"),
    ("pow",      "Player of the Week awards",           "count"),
    ("pom",      "Player of the Month awards",          "count"),
    ("olymed",   "Olympic medals",                      "count"),
    ("mvp",      "MVP awards",                          "count"),
    ("fmvp",     "Finals MVP awards",                   "count"),
    ("asmvp",    "All-Star Game MVP awards",            "count"),
    ("titles",   "NBA titles",                          "count"),
    ("mvpvotes", "seasons receiving MVP votes",         "count"),
    ("mvptop5",  "top-5 MVP finishes",                  "count"),
    ("dpoyvotes","seasons receiving DPOY votes",        "count"),
    ("seasons",  "NBA seasons",                         "count"),
    ("s20",      "seasons averaging 20+ points",        "count"),
    ("s25",      "seasons averaging 25+ points",        "count"),
    ("poapp",    "playoff appearances",                 "count"),
    ("posemis",  "trips to the conference semifinals",  "count"),
    ("poconf",   "trips to the conference finals",      "count"),
    ("pofinals", "NBA Finals appearances",              "count"),
    ("rsg",      "regular season games",                "total"),
    ("rsmin",    "regular season minutes",              "total"),
    ("rspts",    "regular season points",               "total"),
    ("rsfgm",    "regular season field goals made",     "total"),
    ("rs3pm",    "regular season three-pointers made",  "total"),
    ("rsftm",    "regular season free throws made",     "total"),
    ("rsreb",    "regular season rebounds",             "total"),
    ("rsast",    "regular season assists",              "total"),
    ("rsstl",    "regular season steals",               "total"),
    ("rsblk",    "regular season blocks",               "total"),
    ("pog",      "playoff games",                       "total"),
    ("pomin",    "playoff minutes",                     "total"),
    ("popts",    "playoff points",                      "total"),
    ("po3pm",    "playoff three-pointers made",         "total"),
    ("poreb",    "playoff rebounds",                    "total"),
    ("poast",    "playoff assists",                     "total"),
    ("postl",    "playoff steals",                      "total"),
    ("poblk",    "playoff blocks",                      "total"),
]

AWARD_MAP = {
    "asg":     ["All-Star"],
    "allnba1": ["All-NBA First Team"],
    "allnba":  ["All-NBA First Team", "All-NBA Second Team", "All-NBA Third Team"],
    "alldef1": ["All-Defensive First Team"],
    "alldef":  ["All-Defensive First Team", "All-Defensive Second Team"],
    "pow":     ["Player of the Week"],
    "pom":     ["Player of the Month"],
    "olymed":  ["Olympic Gold", "Olympic Silver", "Olympic Bronze"],
    "mvp":     ["Most Valuable Player"],
    "fmvp":    ["Finals MVP"],
    "asmvp":   ["All-Star MVP"],
    "titles":  ["NBA Champion"],
}
SEMIS_OR_BETTER = {"Conf Semis", "Conf Finalist", "Finalist", "Champion"}
CONF_OR_BETTER = {"Conf Finalist", "Finalist", "Champion"}
FINALS_OR_BETTER = {"Finalist", "Champion"}


def main():
    local = None
    if "--local" in sys.argv:
        local = sys.argv[sys.argv.index("--local") + 1]
    rs = load("rsStats.json", local)
    po = load("poStats.json", local)
    awards = load("awards.json", local)
    votes = load("awardVotes.json", local)
    try:
        heads = load("players_all.json", local)["players"]
    except Exception as e:  # headshots are optional
        print("headshot index unavailable:", e)
        heads = []

    # --- pool: every All-Star in the awards file (LeBron handled separately) ----
    asg = collections.Counter(a["PLAYER / COACH"] for a in awards if a["AWARD"] == "All-Star")
    pool = {p for p, n in asg.items() if n >= MIN_ALLSTAR}
    pool.add(LEBRON)

    # --- award counts ---------------------------------------------------------
    award_ct = collections.defaultdict(collections.Counter)
    for a in awards:
        p = a["PLAYER / COACH"]
        if p in pool:
            award_ct[p][a["AWARD"]] += 1

    # --- vote years ---------------------------------------------------------------
    mvp_years = collections.defaultdict(set)
    mvp5_years = collections.defaultdict(set)
    dpoy_years = collections.defaultdict(set)
    for v in votes:
        p = v["PLAYER"]
        if p not in pool:
            continue
        if v["AWARD"] == "MVP":
            mvp_years[p].add(v["YEAR"])
            if num(v["RNK"]) and num(v["RNK"]) <= 5:
                mvp5_years[p].add(v["YEAR"])
        elif v["AWARD"] == "DPOY":
            dpoy_years[p].add(v["YEAR"])

    # --- regular season totals (rows are per team, so plain sums are right) -------
    rs_tot = collections.defaultdict(lambda: collections.Counter())
    rs_years = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))  # year -> [gp, pts]
    for r in rs:
        p = r["PLAYER"]
        if p not in pool:
            continue
        t = rs_tot[p]
        t["g"] += num(r["GP"]); t["min"] += num(r["MIN"]); t["pts"] += num(r["PTS"])
        t["fgm"] += num(r["FGM"]); t["3pm"] += num(r["3P"]); t["ftm"] += num(r["FTM"])
        t["reb"] += num(r["REB"]); t["ast"] += num(r["AST"]); t["stl"] += num(r["STL"]); t["blk"] += num(r["BLK"])
        y = rs_years[p][r["YEAR"]]
        y[0] += num(r["GP"]); y[1] += num(r["PTS"])

    # --- playoff totals + runs -------------------------------------------------------
    po_tot = collections.defaultdict(lambda: collections.Counter())
    po_years = collections.defaultdict(dict)  # year -> best RESULT that year
    for r in po:
        p = r["PLAYER"]
        if p not in pool:
            continue
        t = po_tot[p]
        t["g"] += num(r["GP"]); t["min"] += num(r["MIN"]); t["pts"] += num(r["PTS"]); t["3pm"] += num(r["3P"])
        t["reb"] += num(r["REB"]); t["ast"] += num(r["AST"]); t["stl"] += num(r["STL"]); t["blk"] += num(r["BLK"])
        po_years[p][r["YEAR"]] = r.get("RESULT", "")

    # --- headshots (suffix/diacritic tolerant) ---------------------------------------
    head_idx = {}
    for h in heads:
        head_idx.setdefault(norm(h["full_name"]), h["headshot"]["filename"])

    def metrics_for(p):
        ac = award_ct[p]
        rt, pt = rs_tot[p], po_tot[p]
        yrs = rs_years[p]
        py = po_years[p]
        m = {}
        for k, names in AWARD_MAP.items():
            m[k] = sum(ac[n] for n in names)
        m["mvpvotes"] = len(mvp_years[p])
        m["mvptop5"] = len(mvp5_years[p])
        m["dpoyvotes"] = len(dpoy_years[p])
        m["seasons"] = len(yrs)
        m["s20"] = sum(1 for g, pts in yrs.values() if g > 0 and pts / g >= 20)
        m["s25"] = sum(1 for g, pts in yrs.values() if g > 0 and pts / g >= 25)
        m["poapp"] = len(py)
        m["posemis"] = sum(1 for r in py.values() if r in SEMIS_OR_BETTER)
        m["poconf"] = sum(1 for r in py.values() if r in CONF_OR_BETTER)
        m["pofinals"] = sum(1 for r in py.values() if r in FINALS_OR_BETTER)
        m["rsg"] = rt["g"]; m["rsmin"] = rt["min"]; m["rspts"] = rt["pts"]; m["rsfgm"] = rt["fgm"]
        m["rs3pm"] = rt["3pm"]; m["rsftm"] = rt["ftm"]; m["rsreb"] = rt["reb"]; m["rsast"] = rt["ast"]
        m["rsstl"] = rt["stl"]; m["rsblk"] = rt["blk"]
        m["pog"] = pt["g"]; m["pomin"] = pt["min"]; m["popts"] = pt["pts"]; m["po3pm"] = pt["3pm"]
        m["poreb"] = pt["reb"]; m["poast"] = pt["ast"]; m["postl"] = pt["stl"]; m["poblk"] = pt["blk"]
        return [int(round(m[k])) for k, _, _ in METRICS]

    keys = [k for k, _, _ in METRICS]
    lebron = dict(zip(keys, metrics_for(LEBRON)))

    players = []
    for p in sorted(pool):
        if p == LEBRON or p not in rs_years:
            continue
        yrs = sorted(int(y) for y in rs_years[p])
        vals = metrics_for(p)
        d = dict(zip(keys, vals))
        # recognizability weight: accolades + recency + a big bump for NBA Top-75 / HoopsHype Top-78 names
        top = 30 if (award_ct[p]["NBA Top-75"] or award_ct[p]["HoopsHype Top-78"]) else 0
        fame = d["asg"] * 3 + d["allnba"] * 2 + d["titles"] * 2 + d["mvp"] * 4 + (10 if yrs[-1] >= 2010 else 5 if yrs[-1] >= 1995 else 0) + top
        players.append({
            "n": re.sub(r"\s*\(.*?\)", "", p),      # display name
            "y": [yrs[0] - 1, yrs[-1]],             # career span as season start/end years, e.g. [1984, 2003]
            "f": fame,
            "h": head_idx.get(norm(p)),             # headshot filename or None
            "v": vals,
        })

    out = {
        "generated": datetime.date.today().isoformat(),
        "metrics": [{"k": k, "label": lab, "kind": kind} for k, lab, kind in METRICS],
        "lebron": {"name": LEBRON, "h": head_idx.get(norm(LEBRON)), "v": [lebron[k] for k in keys]},
        "players": players,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// Generated by build_lebron_duo_data.py on %s. Do not edit by hand.\n" % out["generated"])
        f.write("window.LEBRON_DUO_DATA = ")
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)
        f.write(";\n")
    print("wrote %s: %d players, %d metrics, %d with headshots" % (
        OUT, len(players), len(METRICS), sum(1 for p in players if p["h"])))
    for k, lab, _ in METRICS:
        print("  LeBron %-40s %s" % (lab, lebron[k]))


if __name__ == "__main__":
    main()
