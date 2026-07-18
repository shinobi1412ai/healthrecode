"""Postet das naechste ungepostete Reel aus reel_queue.json zu IG + FB.
Re-hostet kurz zu Cloudinary (HTTPS, IG-Pflicht), postet, loescht Cloudinary-Temp.
Nutzt die vorhandenen post_reel_to_instagram / post_reel_to_facebook Funktionen.
Laeuft in GitHub Actions mit den Repo-Secrets."""
import os, json, sys, datetime
import cloudinary, cloudinary.uploader
from post_from_queue import post_reel_to_instagram, post_reel_to_facebook

Q = "reel_queue.json"
q = json.load(open(Q, encoding="utf-8"))
nxt = next((x for x in q if not x.get("posted")), None)
if not nxt:
    print("ALL REELS POSTED — nothing to do."); sys.exit(0)

cloudinary.config(
    cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
    api_key=os.environ["CLOUDINARY_API_KEY"],
    api_secret=os.environ["CLOUDINARY_API_SECRET"],
)
print(f"Next reel: idx={nxt['idx']}  {nxt['file']}")
print(f"Topic: {nxt['topic']}")

# 1) Re-host VPS-HTTP -> Cloudinary HTTPS
up = cloudinary.uploader.upload(nxt["url"], resource_type="video",
                                folder="reels_tmp", public_id=f"reel_{nxt['idx']:02d}", overwrite=True)
https_url = up["secure_url"]; pub_id = up["public_id"]
print("Cloudinary:", https_url)

# 2) Post
ig = post_reel_to_instagram(https_url, nxt["caption"])
print("IG:", ig)
fb = post_reel_to_facebook(https_url, nxt["caption"])
print("FB:", fb)

# 3) Cloudinary-Temp loeschen
try:
    cloudinary.uploader.destroy(pub_id, resource_type="video")
    print("Cloudinary temp deleted.")
except Exception as e:
    print("Cloudinary cleanup warn:", e)

# 4) Nur bei IG-Erfolg als gepostet markieren
if str(ig).startswith("posted"):
    nxt["posted"] = True
    nxt["posted_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    nxt["ig_result"] = ig; nxt["fb_result"] = fb
    json.dump(q, open(Q, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    remaining = sum(1 for x in q if not x.get("posted"))
    print(f"MARKED POSTED idx={nxt['idx']}. Remaining: {remaining}/72")
else:
    print("IG FAILED — queue not advanced.")
    sys.exit(1)
