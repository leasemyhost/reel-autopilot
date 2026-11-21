"""Pull insights for posted reels into data/insights.json (Claude reads this to improve topics/hooks).
Env: IG_USER_ID, IG_ACCESS_TOKEN, IG_GRAPH_HOST, IG_API_VERSION"""
import json
import os
from pathlib import Path

from post_instagram import HOST, VER, api

ROOT = Path(__file__).resolve().parents[1]


def main():
    tok, uid = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
    base = f"https://{HOST}/{VER}"
    out = {"account": {}, "reels": []}
    try:
        out["account"] = api("GET", f"{base}/{uid}", {"fields": "username,followers_count,media_count", "access_token": tok})
    except Exception as e:
        out["account"] = {"error": str(e)}
    for meta in sorted((ROOT / "posted").glob("*/meta.json")):
        m = json.load(open(meta))
        if not m.get("media_id"):
            continue
        row = {"id": meta.parent.name, "title": m.get("title"), "hook": m.get("hook"), "topic": m.get("topic"),
               "posted_at": m.get("posted_at"), "permalink": m.get("permalink")}
        try:
            r = api("GET", f"{base}/{m['media_id']}/insights",
                    {"metric": "views,reach,likes,comments,shares,saved,ig_reels_avg_watch_time,total_interactions", "access_token": tok})
            for d in r.get("data", []):
                row[d["name"]] = (d.get("values") or [{}])[0].get("value", d.get("total_value", {}).get("value"))
        except Exception as e:
            row["error"] = str(e)[:200]
        out["reels"].append(row)
    (ROOT / "data").mkdir(exist_ok=True)
    json.dump(out, open(ROOT / "data/insights.json", "w"), indent=2, ensure_ascii=False)
    print("insights:", len(out["reels"]), "reels")


if __name__ == "__main__":
    main()
