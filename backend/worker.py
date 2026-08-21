import asyncio
import hashlib
import json
import os
import subprocess
from pathlib import Path

from arq import cron
from arq.connections import RedisSettings
from dotenv import load_dotenv

from .database import SessionLocal, REDIS_SETTINGS
from . import models
from .models import Content, MediaRendition
from .media_urls import delete_stored_file
from .routers.content import UPLOAD_DIR, public_upload_url

import shutil
from sqlalchemy import or_

project_root = Path(__file__).parent.parent
if not shutil.which("ffmpeg"):
    ffmpeg_bin = project_root / "ffmpeg_build" / "ffmpeg-master-latest-win64-gpl" / "bin"
    if ffmpeg_bin.exists():
        os.environ["PATH"] += os.pathsep + str(ffmpeg_bin)


def run_command_sync(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def probe_file(file_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,codec_name,duration",
        "-show_entries", "stream_tags=rotate",
        "-of", "json",
        str(file_path)
    ]
    stdout = run_command_sync(cmd)
    data = json.loads(stdout)
    if "streams" not in data or not data["streams"]:
        raise ValueError("No video stream found")
    stream = data["streams"][0]
    
    width = int(stream.get("width", 0))
    height = int(stream.get("height", 0))
    codec = stream.get("codec_name", "")
    duration_s = float(stream.get("duration", 0))
    rotation_tag = stream.get("tags", {}).get("rotate", "0")
    rotation = int(rotation_tag)
    
    return {
        "width": width,
        "height": height,
        "codec": codec,
        "duration_ms": int(duration_s * 1000),
        "rotation": rotation
    }


def compute_sha256(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def process_media_sync(content_id: int):
    db = SessionLocal()
    try:
        content = db.query(Content).filter(Content.id == content_id).first()
        if not content:
            return
        
        # Only process video
        if content.type != "video":
            content.status = "ready"
            db.commit()
            return
        
        if content.file_url.startswith("s3://"):
            storage_key = content.file_url[5:]
            raise NotImplementedError("S3 transcoding is not implemented in this local script yet")
        else:
            storage_key = content.file_url.split("/uploads/")[1]

        file_path = Path(UPLOAD_DIR) / storage_key
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # A retry re-transcodes every resolution, so anything from a previous attempt is
        # stale. Without this each retry stacked another full set of renditions on the
        # row — three attempts left twelve where there should be four.
        db.query(MediaRendition).filter(MediaRendition.content_id == content.id).delete(
            synchronize_session=False
        )

        info = probe_file(file_path)
        # Persist the true length so a playlist item can default to it rather than a
        # flat 10 seconds, which truncates every advert longer than that.
        content.duration_ms = info.get("duration_ms") or None
        
        resolutions = {
            "1080p": (1920, 1080),
            "720p": (1280, 720),
            "540p": (960, 540),
            "360p": (640, 360)
        }
        
        output_dir = file_path.parent
        
        # Transcode renditions
        for name, (w_max, h_max) in resolutions.items():
            out_filename = f"{file_path.stem}_{name}.mp4"
            out_filepath = output_dir / out_filename
            
            # Use force_original_aspect_ratio=decrease so we don't upscale or break aspect ratio
            # Then use a second scale to ensure both width and height are divisible by 2 for libx264
            scale_filter = f"scale={w_max}:{h_max}:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p"
            
            cmd = [
                "ffmpeg",
                "-y",
                "-i", str(file_path),
                "-vf", scale_filter,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                str(out_filepath)
            ]
            run_command_sync(cmd)
            
            rend_info = probe_file(out_filepath)
            rend_size = out_filepath.stat().st_size
            rend_sha = compute_sha256(out_filepath)
            
            rendition = MediaRendition(
                content_id=content.id,
                resolution=name,
                width=rend_info["width"],
                height=rend_info["height"],
                rotation=rend_info["rotation"],
                duration_ms=rend_info["duration_ms"],
                codec=rend_info["codec"],
                sha256=rend_sha,
                file_size_bytes=rend_size,
                file_url=public_upload_url(f"{content.organization_id}/{out_filename}")
            )
            db.add(rendition)
            
        # extract thumbnail if missing
        if not content.thumbnail:
            thumb_filename = f"{file_path.stem}_thumb.jpg"
            thumb_filepath = output_dir / thumb_filename
            cmd = [
                "ffmpeg", "-y",
                "-ss", "00:00:01",
                "-i", str(file_path),
                "-vf", "scale=320:-2",
                "-frames:v", "1",
                str(thumb_filepath)
            ]
            try:
                run_command_sync(cmd)
                content.thumbnail = public_upload_url(f"{content.organization_id}/{thumb_filename}")
            except Exception:
                # Not fatal — the asset still plays without a thumbnail — but silence here
                # is why "thumbnail not showing" was impossible to diagnose: the item was
                # marked ready and nothing anywhere recorded that this step had failed.
                logger.exception("thumbnail generation failed for content %s", content.id)
        
        content.status = "ready"
        db.commit()
            
    except Exception as e:
        db.rollback()
        content = db.query(Content).filter(Content.id == content_id).first()
        if content:
            content.status = "failed"
            content.failed_reason = str(e)
            db.commit()
    finally:
        db.close()


async def process_media(ctx, content_id: int):
    print(f"Starting process_media task for Content ID: {content_id}")
    await asyncio.to_thread(process_media_sync, content_id)
    print(f"Finished process_media task for Content ID: {content_id}")


async def recover_stuck_processing(ctx):
    db = SessionLocal()
    try:
        from datetime import timedelta
        redis = ctx.get("redis")
        if not redis:
            return
        
        threshold = models.utcnow() - timedelta(minutes=10)
        # Times the current attempt, not the upload. The previous version reset the timer
        # by overwriting uploaded_at, which silently rewrote the "added 3 months ago" date
        # shown in the library and broke sorting by date added.
        stuck_content = db.query(Content).filter(
            Content.status == "processing",
            or_(
                Content.processing_started_at < threshold,
                Content.processing_started_at.is_(None),
            ),
        ).all()

        for c in stuck_content:
            c.processing_retries = (c.processing_retries or 0) + 1
            if c.processing_retries > 3:
                c.status = "failed"
                c.failed_reason = "Transcoding timed out and exceeded retry limit."
                print(f"Content {c.id} failed after {c.processing_retries} attempts")
            else:
                c.processing_started_at = models.utcnow()
                await redis.enqueue_job("process_media", c.id)
                print(f"Re-queued stuck content {c.id} (attempt {c.processing_retries})")

        db.commit()
    finally:
        db.close()


async def aggregate_play_logs(ctx):
    db = SessionLocal()
    try:
        from sqlalchemy import text
        # Atomic aggregation: 
        # 1. Update unaggregated rows and return them
        # 2. Group them by org/campaign/screen/media/hour
        # 3. Update existing rollups
        # 4. Insert new rollups for those that didn't exist
        
        db.execute(text("""
            WITH to_aggregate AS (
                UPDATE play_logs
                SET aggregated = TRUE
                WHERE aggregated = FALSE
                RETURNING *
            ),
            agg AS (
                SELECT 
                    organization_id, campaign_id, screen_id, media_id, 
                    date_trunc('hour', corrected_started_at) AS date_hour,
                    COUNT(*) AS total_plays,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_plays,
                    SUM(CASE WHEN status = 'partial' THEN 1 ELSE 0 END) AS partial_plays,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS error_plays,
                    SUM(duration_ms) AS duration_ms
                FROM to_aggregate
                GROUP BY organization_id, campaign_id, screen_id, media_id, date_trunc('hour', corrected_started_at)
            ),
            updated AS (
                UPDATE play_log_hourly_rollups p
                SET 
                    total_plays = p.total_plays + agg.total_plays,
                    completed_plays = p.completed_plays + agg.completed_plays,
                    partial_plays = p.partial_plays + agg.partial_plays,
                    error_plays = p.error_plays + agg.error_plays,
                    duration_ms = p.duration_ms + agg.duration_ms
                FROM agg
                WHERE p.organization_id = agg.organization_id
                  AND p.screen_id = agg.screen_id
                  AND p.date_hour = agg.date_hour
                  AND p.campaign_id IS NOT DISTINCT FROM agg.campaign_id
                  AND p.media_id IS NOT DISTINCT FROM agg.media_id
                RETURNING p.organization_id, p.campaign_id, p.screen_id, p.media_id, p.date_hour
            )
            INSERT INTO play_log_hourly_rollups (
                organization_id, campaign_id, screen_id, media_id, date_hour, 
                total_plays, completed_plays, partial_plays, error_plays, duration_ms
            )
            SELECT 
                agg.organization_id, agg.campaign_id, agg.screen_id, agg.media_id, agg.date_hour,
                agg.total_plays, agg.completed_plays, agg.partial_plays, agg.error_plays, agg.duration_ms
            FROM agg
            LEFT JOIN updated u
            ON agg.organization_id = u.organization_id
              AND agg.screen_id = u.screen_id
              AND agg.date_hour = u.date_hour
              AND agg.campaign_id IS NOT DISTINCT FROM u.campaign_id
              AND agg.media_id IS NOT DISTINCT FROM u.media_id
            WHERE u.organization_id IS NULL;
        """))
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error aggregating play logs: {e}")
    finally:
        db.close()


async def prune_play_logs(ctx):
    db = SessionLocal()
    try:
        retention_days = int(os.getenv("PLAY_LOG_RETENTION_DAYS", "180"))
        result = db.execute(text("""
            DELETE FROM play_logs WHERE aggregated = TRUE AND received_at < NOW() - CAST(:days || ' days' AS INTERVAL);
        """).bindparams(days=str(retention_days)))
        deleted_count = result.rowcount
        print(f"Pruned {deleted_count} aggregated play logs older than {retention_days} days.")
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error pruning play logs: {e}")
    finally:
        db.close()



async def prune_screenshots(ctx):
    """Keep only the newest captures per screen, and delete their files too.

    Nothing removed these before. The UI only ever shows the newest ten, so the rest were
    invisible while still consuming a row and an image file each — unbounded growth across
    a fleet that captures regularly.
    """
    keep = int(os.getenv("SCREENSHOT_KEEP_PER_SCREEN", "10"))
    db = SessionLocal()
    removed = 0
    try:
        screen_ids = [row[0] for row in db.query(models.ScreenshotLog.screen_id).distinct()]
        for screen_id in screen_ids:
            stale = (
                db.query(models.ScreenshotLog)
                .filter(models.ScreenshotLog.screen_id == screen_id)
                .order_by(models.ScreenshotLog.created_at.desc())
                .offset(keep)
                .all()
            )
            for shot in stale:
                # File first: if the row goes and the unlink fails we lose the only
                # pointer to it and it becomes an orphan.
                delete_stored_file(shot.file_url, UPLOAD_DIR)
                db.delete(shot)
                removed += 1
        db.commit()
        if removed:
            print(f"Pruned {removed} screenshots beyond the newest {keep} per screen.")
    except Exception as e:
        db.rollback()
        print(f"Error pruning screenshots: {e}")
    finally:
        db.close()


class WorkerSettings:
    functions = [process_media]
    cron_jobs = [
        cron(recover_stuck_processing, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
        cron(aggregate_play_logs, minute={0, 15, 30, 45}),
        cron(prune_play_logs, hour=3, minute=0),
        cron(prune_screenshots, hour=3, minute=30),
    ]
    redis_settings = REDIS_SETTINGS
