import json
import subprocess
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend import models
from backend.worker import aggregate_play_logs_sync

def main():
    adb = r"C:\Users\Roshan Raj\AppData\Local\Android\Sdk\platform-tools\adb.exe"
    out = subprocess.check_output([
        adb, "-s", "HNP06KSC", "shell",
        "run-as com.olrac.signage sqlite3 -json databases/signage_database 'SELECT * FROM play_events;'"
    ], text=True)
    
    events_raw = json.loads(out)
    print(f"Loaded {len(events_raw)} events from tablet")

    client = TestClient(app)
    # Upload in chunks of 500
    for i in range(0, len(events_raw), 500):
        chunk = events_raw[i:i+500]
        payload = {
            "device_id": "0bb269af-1e49-3067-bdc8-c85de92ee290",
            "events": [
                {
                    "event_id": e["eventId"],
                    "media_id": e["mediaId"],
                    "playlist_id": e["playlistId"],
                    "campaign_id": e["campaignId"],
                    "device_started_at": e["deviceStartedAt"],
                    "device_finished_at": e["deviceFinishedAt"],
                    "corrected_started_at": e["correctedStartedAt"],
                    "corrected_finished_at": e["correctedFinishedAt"],
                    "duration_ms": e["durationMs"],
                    "status": e["status"],
                    "error_message": e.get("errorMessage")
                }
                for e in chunk
            ]
        }
        res = client.post("/api/screens/play-logs/batch", json=payload)
        print(f"Uploaded batch {i//500 + 1}: status {res.status_code}, {res.json()}")

    # Now aggregate
    db = SessionLocal()
    res_agg = aggregate_play_logs_sync(db)
    print("Aggregate result:", res_agg)
    r = db.query(models.PlayLogHourlyRollup).filter(models.PlayLogHourlyRollup.media_id == 17).all()
    print("Rollups for 17:", [(x.date_hour, x.media_id, x.screen_id, x.total_plays, x.completed_plays) for x in r])
    db.close()

if __name__ == "__main__":
    main()
