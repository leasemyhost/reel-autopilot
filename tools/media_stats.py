"""Print stats of the latest N reels (views, reach, watch time...). python3 tools/media_stats.py [N]"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from post_instagram import HOST, VER, api
tok, uid = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
base = f"https://{HOST}/{VER}"
n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
acct = api("GET", f"{base}/{uid}", {"fields": "username,followers_count,media_count", "access_token": tok})
print("account:", acct)
media = api("GET", f"{base}/{uid}/media", {"fields": "id,timestamp,media_product_type,permalink,like_count,comments_count,caption", "limit": n, "access_token": tok})
for m in media.get("data", []):
    print("\n==", m["timestamp"], m.get("media_product_type"), m.get("permalink"))
    print("   likes", m.get("like_count"), "comments", m.get("comments_count"), "|", (m.get("caption") or "")[:70].replace("\n", " "))
    for metrics in ("views,reach,saved,shares,total_interactions,ig_reels_avg_watch_time,ig_reels_video_view_total_time",
                    "reach,saved,shares,total_interactions"):
        try:
            r = api("GET", f"{base}/{m['id']}/insights", {"metric": metrics, "access_token": tok})
            print("  ", {x["name"]: x["values"][0]["value"] for x in r.get("data", [])})
            break
        except Exception as e:
            print("   insights err:", str(e)[:250])
