# OLRAC Signage — 80-TV Rollout Deployment Guide

This document covers the end-to-end deployment process for a new production environment, from standing up the server stack to provisioning physical Android TVs in the field.

## 1. Server Environment Setup

Before starting the stack, ensure the following mandatory environment variables are set in your `.env` file (see `.env.example` for reference):

- `SECRET_KEY`: A cryptographically secure random string used for JWT signing.
- `PUBLIC_BASE_URL`: The public-facing URL of the backend (e.g., `https://api.olracsignage.com`). This must be correct, as it is used to generate absolute URLs for media assets and APK downloads.
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`, `S3_ENDPOINT_URL`: R2/S3 credentials for media storage.
- `PLAY_LOG_RETENTION_DAYS`: Number of days to keep proof-of-play billing logs (default is 180).

## 2. Storage Configuration

You must explicitly configure your storage backend depending on your deployment scale:

- **Default Local Storage (`AWS_ACCESS_KEY_ID=mock`)**: Media is saved to the local disk. This requires the shared `uploads_data` volume in Docker so both the `backend` and `worker` containers can see the files. **Warning:** Local storage is single-host only. Moving to a second backend host or scaling horizontally will cause media to be lost or become inaccessible.
- **Production Cloud Storage (R2/S3)**: Set real Cloudflare R2 (or AWS S3) credentials in your `.env`. Media is uploaded directly to the object storage bucket, and TVs download assets directly via signed URLs. The backend API never proxies large files. **This is strictly required to scale past one backend instance.**

## 3. Start the Stack

The entire application runs via Docker Compose.

```bash
# Start Postgres, Redis, Backend, Worker, and Frontend
docker compose up -d
```

Verify all 5 containers (`olrac_db`, `olrac_redis`, `olrac_backend`, `olrac_worker`, `olrac_frontend`) are healthy:
```bash
docker compose ps
```

## 4. Database Migration

The database schema is managed by Alembic. Once the database container is healthy, run the migrations to create all tables:

```bash
docker compose exec backend alembic -c backend/alembic.ini upgrade head
```

## 5. Create the Platform Owner

Before anyone can log into the dashboard, you must seed the initial owner account. Provide the desired username as an argument.

```bash
docker compose exec backend python -m backend.seed_admin <username>
```
*Note: This script will prompt you for a password interactively. It does not store credentials in any file.*

## 6. TV Enrollment & Provisioning

Instead of manually typing a 6-digit code with a remote control 80 times, use the zero-touch enrollment flow.

1. Log into the dashboard (`http://localhost:3000` or your production domain) using the owner account created above.
2. Navigate to **Dashboard > Enrollment**.
3. Generate a new **Enrollment Token**. Set an expiry and max uses (e.g., 100 uses). 
4. Copy the token. **This is a one-time view credential.**
5. Build the Android TV APK with this token baked in, or provide it during the installer wizard on the TV.

## 7. Watchdog Setup (Crucial for Budget TVs)

Budget Android TVs (like the Realtek 2K D5STV) aggressively kill background processes and ignore standard boot receivers. To ensure the signage app recovers from power cuts automatically, you must install the **Watchdog Accessibility Service**.

### Build the Watchdog
Before compiling the watchdog APK in `android-watchdog/`, you **must** update the target package constant in `WatchdogAccessibilityService.java`:
```java
// Change this from tv.ablesign.app to com.olrac.signage
public static final String ABLESIGN = "com.olrac.signage";
```

### Install via ADB on the TV
Connect to the TV via ADB and install both the main player APK and the Watchdog APK.

```bash
# Disable Play Protect blocking
adb shell settings put global verifier_verify_adb_installs 0
adb shell settings put global package_verifier_enable 0

# Install APKs
adb install -r signage-player.apk
adb install -r watchdog.apk

# Enable the Watchdog Accessibility Service (Survives Reboot)
adb shell settings put secure enabled_accessibility_services com.ablesign.bootlauncher/.WatchdogAccessibilityService
adb shell settings put secure accessibility_enabled 1

# Whitelist both apps from battery optimization
adb shell dumpsys deviceidle whitelist +com.olrac.signage
adb shell dumpsys deviceidle whitelist +com.ablesign.bootlauncher
```

### Verification
Reboot the TV (`adb shell reboot`). The Android OS will start, wait ~12 seconds to settle, and the Watchdog will automatically bring `com.olrac.signage` to the foreground.
