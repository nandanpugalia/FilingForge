#!/usr/bin/env python3
"""Post a FilingForge metrics summary to Discord. Run by GitHub Actions (twice daily +
a weekly graph). Privacy-respecting by design: every number comes from GitHub (release
download counts, stars, issues) — there is NO app telemetry, nothing phones home.

Signals:
  • Downloads  — release-asset download_count for FilingForge.dmg / FilingForge-Setup.exe
  • Update pings (≈ active installs) — download_count of latest.json (the updater fetches
    it on launch, so GitHub counts it for us — no tracking added)
  • Stars / forks / open issues — repo stats

Modes:
  (default)   daily summary + deltas, append a snapshot to history
  --weekly    7/30-day trend graph (QuickChart) from the snapshot history

State lives in metrics/ in the repo: state.json (last snapshot) + history.jsonl (append-only).
"""
from __future__ import annotations
import json, os, sys, datetime, urllib.request, urllib.parse
from pathlib import Path

REPO = os.environ.get("GH_REPO") or "nandanpugalia/FilingForge"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
EMBER = 0xFF6A3D
MDIR = Path(os.environ.get("METRICS_DIR", "metrics"))
STATE, HISTORY = MDIR / "state.json", MDIR / "history.jsonl"


def gh(path: str):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
                 "User-Agent": "filingforge-metrics"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect() -> dict:
    repo = gh(f"/repos/{REPO}")
    dmg = exe = pings = 0
    try:
        for rel in gh(f"/repos/{REPO}/releases"):
            for a in rel.get("assets", []):
                n, c = a["name"].lower(), a.get("download_count", 0)
                if n.endswith(".dmg"):
                    dmg += c
                elif n.endswith(".exe"):
                    exe += c
                if n == "latest.json":
                    pings += c
    except Exception as e:  # no releases yet → zeros
        print(f"releases fetch note: {e}", file=sys.stderr)
    return {
        "ts": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "issues": repo.get("open_issues_count", 0),
        "downloads": dmg + exe, "dmg": dmg, "exe": exe, "pings": pings,
    }


def _post(payload: dict):
    if not WEBHOOK:
        print("no DISCORD_WEBHOOK set; would have posted:", json.dumps(payload)[:200]); return
    req = urllib.request.Request(WEBHOOK, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "FilingForge-Notifier/1.0"})  # Discord 403s default urllib UA
    urllib.request.urlopen(req, timeout=30).read()


def _delta(cur, prev, k):
    d = cur.get(k, 0) - prev.get(k, 0)
    return f"  `+{d}`" if d > 0 else ""


def daily():
    cur = collect()
    prev = {}
    try:
        prev = json.loads(STATE.read_text())
    except Exception:
        pass
    today = datetime.datetime.utcnow().strftime("%d %b %Y")
    desc = (
        f"⬇️ **Downloads** {cur['downloads']}{_delta(cur, prev, 'downloads')}"
        f"   ·  🍎 {cur['dmg']}   ·  ⊞ {cur['exe']}\n"
        f"🟢 **Active (update pings)** {cur['pings']}{_delta(cur, prev, 'pings')}\n"
        f"⭐ **Stars** {cur['stars']}{_delta(cur, prev, 'stars')}"
        f"   ·  🍴 {cur['forks']}   ·  🐞 open issues {cur['issues']}"
    )
    _post({"username": "FilingForge",
           "embeds": [{"title": f"📊 FilingForge — {today}", "description": desc, "color": EMBER}]})
    MDIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(cur, indent=2))
    # append one snapshot per day (replace same-day line so twice-daily runs don't double up)
    rows = [l for l in (HISTORY.read_text().splitlines() if HISTORY.exists() else [])
            if l.strip() and json.loads(l).get("ts") != cur["ts"]]
    rows.append(json.dumps(cur))
    HISTORY.write_text("\n".join(rows) + "\n")
    print("daily posted; state + history saved")


def _quickchart(labels, series) -> str:
    cfg = {"type": "line",
           "data": {"labels": labels,
                    "datasets": [{"label": k, "data": v, "fill": False, "tension": 0.3}
                                 for k, v in series.items()]},
           "options": {"title": {"display": True, "text": "FilingForge — 30-day trend"}}}
    return "https://quickchart.io/chart?w=640&h=320&bkg=white&c=" + urllib.parse.quote(json.dumps(cfg))


def weekly(days=30):
    if not HISTORY.exists():
        print("no history yet; skipping weekly"); return
    rows = [json.loads(l) for l in HISTORY.read_text().splitlines() if l.strip()][-days:]
    if len(rows) < 2:
        print("not enough history for a trend yet"); return
    labels = [r["ts"][5:] for r in rows]  # MM-DD
    series = {"Downloads": [r["downloads"] for r in rows],
              "Active": [r["pings"] for r in rows],
              "Stars": [r["stars"] for r in rows]}
    cur = rows[-1]
    _post({"username": "FilingForge",
           "embeds": [{"title": "📈 FilingForge — weekly trend",
                       "description": f"Last {len(rows)} days · {cur['downloads']} downloads · "
                                      f"{cur['pings']} active · ⭐ {cur['stars']}",
                       "color": EMBER, "image": {"url": _quickchart(labels, series)}}]})
    print("weekly graph posted")


if __name__ == "__main__":
    (weekly if "--weekly" in sys.argv else daily)()
