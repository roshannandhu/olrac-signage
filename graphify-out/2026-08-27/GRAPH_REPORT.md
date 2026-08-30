# Graph Report - OLRAC SIGNAGE  (2026-08-27)

## Corpus Check
- 275 files · ~351,444 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2171 nodes · 4814 edges · 185 communities (140 shown, 45 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 162 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a0e8b3f0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- cn
- schemas.py
- PlaylistItemEntity
- ApiService.kt
- MainActivity
- team/page.tsx
- PlaybackService
- auth.py
- MainActivity
- AbleSign Auto-Launch — Full Documentation
- compilerOptions
- models.py
- ValueError
- test_screen_approval.py
- api.ts
- components.json
- OLRAC Signage — Work Order for Antigravity (Gemini Pro)
- PlaybackTelemetry
- HTTPException
- resolve_rotation
- AppDatabase
- acknowledge_alert
- dependencies
- devDependencies
- TenantScope
- OLRAC Signage
- TransitionType
- _post
- app/layout.tsx
- google_device.py
- StorageManagerTest
- conftest.py
- ProofOfPlayWorker
- scripts
- delete
- files/page.tsx
- test_alerting.py
- OLRAC Signage — Build Goal & Agent Work Order
- OLRAC Watchdog — build and TV setup
- test_quotas.py
- BootReceiver
- InstallReceiver
- ApiClientTest
- preflight.py
- SyncBackoffPolicy
- compute
- HeartbeatWorker
- LaunchStateResolverTest
- TransitionSpecResolverTest
- test_ws_connection_pool.py
- worker.py
- playlists.py
- SyncBackoffPolicyTest
- gradlew
- .onCreate
- test_media_storage.py
- model_validator
- @dnd-kit/utilities
- eslint.config.mjs
- next.config.ts
- DeviceState
- OLRAC Signage — 80-TV Rollout Deployment Guide
- PlayerScreen.kt
- test_google_signin.py
- health_check
- parse
- P9 — Zero-touch provisioning for 80+ TVs (no ADB)
- postcss.config.mjs
- backup_db.sh
- validation_script.sh
- content/[id]/page.tsx
- Player
- playlist-builder.tsx
- P8 — Per-TV capability detection and rendition selection
- Tests
- PlayerViewModel
- test_release_rollout.py
- ScheduleEvaluatorTest
- DeviceOwnerManagerTest
- test_p6_websockets.py
- Part B — Operations home page
- ScheduleEvaluator
- screen-map.tsx
- LaunchState
- UtcDateTime
- verify_device_token
- frontend/README.md
- Google Maps setup
- ContentResponse
- rules/graphify.md
- workflows/graphify.md
- create_token
- PlayEventDao
- AGENTS.md
- lucide-react
- check-maps-keys.py
- .downloadAndInstallUpdate
- SignageDeviceAdminReceiver
- recharts
- select_rendition
- start-dev.ps1
- useAuthStore
- approvals.py
- cleanup_orphans.py
- vercel.json
- provision-tv.sh
- build.sh
- upload_content
- HeartbeatRequest
- env.py
- @types/qrcode.react
- content/page.tsx
- test_rollout_policy.py
- booking_report.py
- MaintenanceGesture
- utcnow
- screens.py
- ensure_billing_catalog
- PlayCompletionTest
- @dnd-kit/sortable
- PlayEndReason
- UpdateGateTest
- GoogleDevicePollResponse
- theme-toggle.tsx
- PlaylistBase
- @dnd-kit/core
- UpdateGate
- a1b4e7c92f38_play_log_campaign_attribution.py
- leaflet
- next-themes
- react
- tw-animate-css
- @types/leaflet
- ScreenBase
- run
- Organization
- GoogleDeviceStartResponse
- GoogleWebSignInRequest
- PlacementSplit
- ProfileUpdate
- ScheduleBase
- ScreenSignInRequest
- shadcn

## God Nodes (most connected - your core abstractions)
1. `TenantScope` - 104 edges
2. `cn()` - 74 edges
3. `utcnow()` - 49 edges
4. `_post()` - 46 edges
5. `useAuthStore` - 42 edges
6. `get_password_hash()` - 40 edges
7. `Organization` - 31 edges
8. `Button()` - 31 edges
9. `screen()` - 31 edges
10. `api` - 29 edges

## Surprising Connections (you probably didn't know these)
- `test_s3_delete()` --calls--> `delete()`  [EXTRACTED]
  tests/test_media_storage.py → backend/media_storage.py
- `run()` --calls--> `Screen`  [EXTRACTED]
  tests/test_sqlite_utc.py → backend/models.py
- `run()` --calls--> `is_configured()`  [EXTRACTED]
  tests/test_google_signin.py → backend/google_device.py
- `run()` --calls--> `_claims()`  [EXTRACTED]
  tests/test_google_signin.py → backend/google_device.py
- `test_a_genuine_google_subdomain_is_still_accepted()` --calls--> `parse()`  [EXTRACTED]
  tests/test_maps_link.py → backend/maps_link.py

## Import Cycles
- None detected.

## Communities (185 total, 45 thin omitted)

### Community 0 - "cn"
Cohesion: 0.17
Nodes (23): AssignTarget, CardAction(), CardFooter(), DialogOverlay(), SelectContent(), SelectGroup(), SelectItem(), SelectLabel() (+15 more)

### Community 1 - "schemas.py"
Cohesion: 0.09
Nodes (41): AlertResponse, AlertSummaryResponse, AppReleasePatch, AppVersionResponse, BillingSummaryResponse, CheckoutRequest, CheckoutResponse, DeviceAuthRequest (+33 more)

### Community 2 - "PlaylistItemEntity"
Cohesion: 0.24
Nodes (3): PlaylistDao, PlaylistItemEntity, Flow

### Community 3 - "ApiService.kt"
Cohesion: 0.09
Nodes (21): ApiClient, Context, ApiService, AuthMethodsResponse, ContentDto, EnrollResponse, GooglePollResponse, GoogleStartRequest (+13 more)

### Community 4 - "MainActivity"
Cohesion: 0.15
Nodes (5): Intent, MainActivity, GooglePollRequest, ComponentActivity, KeyEvent

### Community 5 - "team/page.tsx"
Cohesion: 0.16
Nodes (19): BillingPage(), percent(), exportFormats, targetLabels, asTenantRole(), roleDescription, TeamPage(), TENANT_ROLES (+11 more)

### Community 6 - "PlaybackService"
Cohesion: 0.06
Nodes (22): ConnectivityWatcher, Response, WebSocket, RealtimeClient, WebSocketListener, Context, Intent, Job (+14 more)

### Community 7 - "auth.py"
Cohesion: 0.09
Nodes (33): auth_methods(), change_own_password(), ensure_initial_owner(), get_current_user(), get_current_user_ws(), get_or_create_default_organization(), get_password_hash(), get_secret_key() (+25 more)

### Community 8 - "MainActivity"
Cohesion: 0.06
Nodes (27): android.accessibilityservice.AccessibilityService, android.app.Activity, android.content.BroadcastReceiver, android.content.ComponentName, android.content.Context, android.content.Intent, android.content.SharedPreferences, android.os.Bundle (+19 more)

### Community 9 - "AbleSign Auto-Launch — Full Documentation"
Cohesion: 0.07
Nodes (28): AbleSign Auto-Launch — Full Documentation, AbleSign not launching after reboot, Build commands, Check if watchdog is running, Files in This Folder, How to Install on ANY Android TV, How to Rebuild the APK (if you change the code), If Something Goes Wrong (+20 more)

### Community 10 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 11 - "models.py"
Cohesion: 0.13
Nodes (18): OLRAC Signage backend package. Explicit package marker. Without it `backend` is…, _ensure_schema(), Build the schema on a brand-new database, and stamp it so Alembic can take…, datetime, timestamp_to_datetime(), get_tenant_scope(), Session, User (+10 more)

### Community 12 - "ValueError"
Cohesion: 0.14
Nodes (11): AppReleaseCreate, AppReleaseResponse, PasswordChange, PlaylistItemUpdate, Partial screen update: only the fields actually present are written. The PUT…, Each day maps to exactly [start, end] as HH:MM. Validated here rather than in…, ScreenPatch, UserCreate (+3 more)

### Community 13 - "test_screen_approval.py"
Cohesion: 0.29
Nodes (12): auth_header(), A self-enrolled screen waits for an operator: python…, sign_in(), test_a_pending_screen_syncs_nothing(), test_approval_admits_the_screen(), test_approving_twice_keeps_the_first_timestamp(), test_enrolment_token_admits_immediately(), test_only_an_owner_can_approve() (+4 more)

### Community 14 - "api.ts"
Cohesion: 0.07
Nodes (38): MediaThumbnail(), API_HOST, ApiError, authFetch(), configuredUrl, fetchWithAuth(), resolveMediaUrl(), WS_BASE (+30 more)

### Community 15 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 16 - "OLRAC Signage — Work Order for Antigravity (Gemini Pro)"
Cohesion: 0.08
Nodes (23): 0. Ground rules, 1. Device knowledge — the most important section, 2. What already exists and is verified, 3. Gap analysis — what the new goal needs, 4. Phases, 5. Infrastructure, 6. Regression suite — run after every phase, 7. Definition of done for the whole programme (+15 more)

### Community 17 - "PlaybackTelemetry"
Cohesion: 0.08
Nodes (17): ExoPlayer, Job, PlaybackException, onPlayerError(), PlayerSupervisor, HeartbeatReporter, Context, PlaybackSnapshot (+9 more)

### Community 18 - "HTTPException"
Cohesion: 0.13
Nodes (24): export_campaign_report(), get_campaign_info(), get_campaign_stats(), get_campaign_timeseries(), get_media_report(), list_campaigns(), get, Session (+16 more)

### Community 19 - "resolve_rotation"
Cohesion: 0.23
Nodes (12): normalise(), Resolve the rotation a screen should apply to one playlist item. The player…, Coerce anything to one of 0/90/180/270, defaulting to 0., Degrees the player should rotate this item on this screen., resolve_rotation(), Rotation precedence — pure logic, no database, no device. Run directly: python…, A screen mounted portrait with one item deliberately pinned to landscape., test_defaults_when_nothing_is_set() (+4 more)

### Community 20 - "AppDatabase"
Cohesion: 0.29
Nodes (6): AppDatabase, getDatabase(), Context, migrate(), RoomDatabase, SupportSQLiteDatabase

### Community 21 - "acknowledge_alert"
Cohesion: 0.25
Nodes (9): Alert, acknowledge_alert(), alert_summary(), list_alerts(), get, Open alerts, newest first. Resolved ones only when asked for. The default is…, Mark an alert as picked up, without claiming the underlying fault is fixed.…, Counts for the navigation badge, so the header does not fetch the whole list. (+1 more)

### Community 22 - "dependencies"
Cohesion: 0.10
Nodes (21): @base-ui/react, class-variance-authority, clsx, dependencies, @base-ui/react, class-variance-authority, clsx, next (+13 more)

### Community 23 - "devDependencies"
Cohesion: 0.09
Nodes (23): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, @opennextjs/cloudflare, tailwindcss, @tailwindcss/postcss (+15 more)

### Community 24 - "TenantScope"
Cohesion: 0.11
Nodes (37): AdPlacement, An advert sold to a client: what runs, for whom, when, and for how much.…, add_target(), _booking_screen_ids(), build_booking_report(), create_placement(), delete_placement(), download_booking_report() (+29 more)

### Community 25 - "OLRAC Signage"
Cohesion: 0.11
Nodes (16): Acceptance checks, Build-time server configuration, Install and pair, Kiosk and boot provisioning, OLRAC Android TV player, Supported devices, 1. Configure the backend, 2. Apply database migrations (+8 more)

### Community 26 - "TransitionType"
Cohesion: 0.19
Nodes (11): fromWire(), TransitionSpec, TransitionSpecResolver, TransitionType, FADE, NONE, SLIDE_DOWN, SLIDE_LEFT (+3 more)

### Community 27 - "_post"
Cohesion: 0.10
Nodes (26): _post(), Form-post to Google and return (status, parsed body). A 4xx is returned rather…, verify_password(), Request, razorpay_webhook(), BroadcastRequest, cancel_emergency_broadcast(), get_active_broadcasts() (+18 more)

### Community 28 - "app/layout.tsx"
Cohesion: 0.19
Nodes (8): geistMono, geistSans, metadata, Providers(), Toaster(), TransitionClass, ViewTransition(), ViewTransitionProps

### Community 29 - "google_device.py"
Cohesion: 0.10
Nodes (28): _claims(), client_id(), client_secret(), exchange_code(), GoogleError, is_configured(), is_web_configured(), poll() (+20 more)

### Community 30 - "StorageManagerTest"
Cohesion: 0.22
Nodes (4): OkHttpClient, StorageManager, Context, StorageManagerTest

### Community 31 - "conftest.py"
Cohesion: 0.16
Nodes (10): _postgres_reachable(), pytest_collect_file(), pytest_collection_finish(), pytest_collection_modifyitems(), Run each backend test script in its own process. `backend/database.py` builds…, Fail loudly if a script also got imported as a module. pytest.ini restricts…, Fail if any tests/test_*.py is collected by neither mechanism. A file that is…, Whether a server is listening on the port the scripts create their databases… (+2 more)

### Community 32 - "ProofOfPlayWorker"
Cohesion: 0.17
Nodes (12): BatchOutcome, ACCEPTED, DISCARD, RETRY_LATER, enqueueNow(), isoFormatter(), Context, CoroutineWorker (+4 more)

### Community 33 - "scripts"
Cohesion: 0.17
Nodes (11): name, private, scripts, build, cf:build, cf:deploy, cf:preview, dev (+3 more)

### Community 34 - "delete"
Cohesion: 0.18
Nodes (13): delete(), Remove a stored object. Best effort -- a missing object is not an error. Local…, delete_content(), get_all_content(), get, put, retry_content_processing(), serialize_content() (+5 more)

### Community 35 - "files/page.tsx"
Cohesion: 0.09
Nodes (35): FileSort, SORTS, LoginPage(), AdBookings(), asDate(), runState(), rupees(), SortOption (+27 more)

### Community 36 - "test_alerting.py"
Cohesion: 0.09
Nodes (57): AlertCondition, _as_utc(), evaluate_all(), evaluate_content(), evaluate_screen(), is_scheduled_off(), _minutes(), datetime (+49 more)

### Community 37 - "OLRAC Signage — Build Goal & Agent Work Order"
Cohesion: 0.12
Nodes (15): 10. Phase P7 — Remote player updates (R9), 11. Regression suite — run after every phase, 12. Definition of done, 13. Rules for the implementing agent, 1. Product requirements (the contract), 1a. Verified status — audit of 2026-08-07, 2. Current state — audit (original, pre-implementation), 3. Phase P0 — Offline-first playback (fix D1) (+7 more)

### Community 38 - "OLRAC Watchdog — build and TV setup"
Cohesion: 0.22
Nodes (8): Build, Checking a TV, How recovery actually works, Known issue in the player (not the watchdog), OLRAC Watchdog — build and TV setup, Provision a TV, Retargeting, The three things that silently break this

### Community 39 - "test_quotas.py"
Cohesion: 0.48
Nodes (6): auth_header(), pair_one_screen(), TestClient, Plan-limit enforcement check: python tests/test_quotas.py Covers GOAL.md T6.1…, Register a TV then pair it as the admin. Returns the pair response., run()

### Community 40 - "BootReceiver"
Cohesion: 0.33
Nodes (4): BootReceiver, BroadcastReceiver, Context, Intent

### Community 41 - "InstallReceiver"
Cohesion: 0.33
Nodes (4): InstallReceiver, BroadcastReceiver, Context, Intent

### Community 43 - "preflight.py"
Cohesion: 0.53
Nodes (5): fail(), main(), ok(), Pre-deployment environment check. backend\\venv\\Scripts\\python.exe…, warn()

### Community 45 - "compute"
Cohesion: 0.80
Nodes (4): compute(), DeviceCapabilities, get(), Context

### Community 46 - "HeartbeatWorker"
Cohesion: 0.40
Nodes (3): HeartbeatWorker, CoroutineWorker, Result

### Community 49 - "test_ws_connection_pool.py"
Cohesion: 0.32
Nodes (6): _database_url(), A websocket must not hold a database connection open for its whole life. Both…, Postgres when a server is there, SQLite otherwise -- as the other scripts do., redis_reachable(), run(), setup_db()

### Community 50 - "worker.py"
Cohesion: 0.09
Nodes (31): Reading and writing media wherever it happens to live. The transcoder needs a…, delete_stored_file(), Remove the local file a stored location points at. Returns True if it went.…, Alert, MediaRendition, Something wrong with the fleet, recorded so it can be delivered and reviewed.…, compute_sha256(), probe_file() (+23 more)

### Community 51 - "playlists.py"
Cohesion: 0.27
Nodes (16): add_item_to_playlist(), bump_playlist(), create_playlist(), delete_playlist(), get_playlist(), get_playlists(), get, Playlist (+8 more)

### Community 53 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 72 - ".onCreate"
Cohesion: 0.32
Nodes (13): BrandedMessage(), GoogleLogo(), GoogleSignInScreen(), Bundle, Modifier, PairingScreen(), PinPromptScreen(), secondaryButtonColors() (+5 more)

### Community 74 - "test_media_storage.py"
Cohesion: 0.11
Nodes (26): _client(), fetch_to(), is_remote(), Path, The backend-relative key inside a stored location. Both schemes carry the same…, Put the bytes of `stored_url` at `destination` and return it. A local file is…, Persist `local_path` under `key` and return the location to save on the row.…, storage_key_for() (+18 more)

### Community 75 - "model_validator"
Cohesion: 0.17
Nodes (7): MediaRenditionResponse, PlacementCreate, PlaylistItemBase, PlaylistItemCreate, PlaylistItemResponse, PlaylistUpdate, model_validator

### Community 79 - "DeviceState"
Cohesion: 0.21
Nodes (5): DeviceState, Activity, ScreenshotManager, Bitmap, WeakReference

### Community 80 - "OLRAC Signage — 80-TV Rollout Deployment Guide"
Cohesion: 0.11
Nodes (17): 1. Server Environment Setup, 2. Storage Configuration, 3. Start the Stack, 4. Database Migration, 5. Create the Platform Owner, 6. TV Enrollment & Provisioning, 7. Watchdog Setup (Crucial for Budget TVs), Build the Watchdog (+9 more)

### Community 81 - "PlayerScreen.kt"
Cohesion: 0.23
Nodes (14): android, awaitPlayerReady(), clearPlayCheckpoint(), DualSurfacePlayer(), com, ExoPlayer, Modifier, PlaybackSurface() (+6 more)

### Community 82 - "test_google_signin.py"
Cohesion: 0.17
Nodes (13): client_key(), Request, Who to count this request against. slowapi's get_remote_address returns…, approved(), _database_url(), poll(), Signing a TV in with a Google account: who it lets in, and who it must not.…, Postgres when a server is there, SQLite otherwise -- as test_release_rollout… (+5 more)

### Community 83 - "health_check"
Cohesion: 0.18
Nodes (11): health_check(), login_page(), get, Request, Session, Liveness, plus WHICH database is actually behind it. This used to answer…, read_root(), _redact() (+3 more)

### Community 84 - "parse"
Cohesion: 0.08
Nodes (44): _expand(), geocode(), _is_error_page(), MapsLinkError, _name_from(), _name_from_search(), parse(), Turn a shared Google Maps link into coordinates. This exists so setting a… (+36 more)

### Community 85 - "P9 — Zero-touch provisioning for 80+ TVs (no ADB)"
Cohesion: 0.20
Nodes (9): 1. Make the app a working Device Policy Controller, 2. Silent updates (finishes P7), 3. Generate the provisioning QR, 4. Auto-enrol on first boot, 5. Retire the accessibility watchdog on provisioned devices, Definition of done, Deployment paths, in order of preference, P9 — Zero-touch provisioning for 80+ TVs (no ADB) (+1 more)

### Community 89 - "content/[id]/page.tsx"
Cohesion: 0.16
Nodes (20): Alert, AlertsPage(), buildAlerts(), hoursSince(), Severity, FileManagementPage(), ReleasesPage(), orientationLabel() (+12 more)

### Community 90 - "Player"
Cohesion: 0.25
Nodes (5): Player, DecoderSnapshot, Player, PlaybackException, Player

### Community 91 - "playlist-builder.tsx"
Cohesion: 0.13
Nodes (21): AdDetailPage(), dayLabels, dayNames, DefaultTransitionPanel(), ItemRow(), PlaylistBuilder(), previewStyle(), rotationLabel() (+13 more)

### Community 92 - "P8 — Per-TV capability detection and rendition selection"
Cohesion: 0.25
Nodes (7): 1. Device reports its capabilities (Android), 2. Backend stores the profile, 3. Backend picks the rendition, 4. Dashboard, Definition of done, P8 — Per-TV capability detection and rendition selection, Tests

### Community 93 - "Tests"
Cohesion: 0.22
Nodes (8): Feature parity check, Live E2E test, Quota enforcement, Run everything, Storage and failure-path validation, Tenant isolation probe, Tests, What the suite needs

### Community 94 - "PlayerViewModel"
Cohesion: 0.38
Nodes (3): PlayerViewModel, AndroidViewModel, StateFlow

### Community 95 - "test_release_rollout.py"
Cohesion: 0.24
Nodes (10): AppRelease, bearer(), _database_url(), device_headers(), publish(), Player releases: who may publish one, and who it reaches. Covers the defect…, Read the screen straight from the database. There is no GET /api/screens/{id};…, Postgres when a server is there, SQLite otherwise. Production is Postgres and… (+2 more)

### Community 98 - "test_p6_websockets.py"
Cohesion: 0.20
Nodes (14): ScreenGroup, create_access_token(), P6 realtime checks: python tests/test_p6_websockets.py Covers hierarchical…, /api/ws/dashboard/ws must reach the dashboard handler, not the device one. Both…, Push must never be the only path. The spec is explicit: if the socket is down…, _redis_available(), run(), setup_db() (+6 more)

### Community 99 - "Part B — Operations home page"
Cohesion: 0.12
Nodes (16): Backend, Dashboard, Definition of done, Definition of done, Every panel below uses data that already exists, Layout, Order of work, P10 — Display rotation, and an operations home page (+8 more)

### Community 101 - "screen-map.tsx"
Cohesion: 0.16
Nodes (12): MapPoint, TILES, listeners, loadSdk(), MAPS_KEY, MapsWindow, publish(), serverSnapshot() (+4 more)

### Community 102 - "LaunchState"
Cohesion: 0.29
Nodes (8): CheckingLocalState, GoogleSignIn, LaunchState, LaunchStateResolver, Pairing, Playing, RegistrationSnapshot, SignIn

### Community 106 - "UtcDateTime"
Cohesion: 0.40
Nodes (3): A DateTime that always reads back as timezone-aware UTC. Postgres with…, UtcDateTime, TypeDecorator

### Community 107 - "verify_device_token"
Cohesion: 0.25
Nodes (8): dashboard_websocket(), Screen, Session, websocket, Push channel for one screen. Held open for the life of the device. The session…, Live fleet events for one dashboard user. The database session is opened, used…, screen_websocket(), verify_device_token()

### Community 108 - "frontend/README.md"
Cohesion: 0.50
Nodes (3): Deploy on Vercel, Getting Started, Learn More

### Community 109 - "Google Maps setup"
Cohesion: 0.20
Nodes (9): 1. Create a project and enable billing, 2. Enable the three APIs, 3. Create the browser key, 4. Create the server key, 5. Check the keys, 6. Restart, Google Maps setup, If the map does not appear (+1 more)

### Community 110 - "ContentResponse"
Cohesion: 0.40
Nodes (4): ContentBase, ContentResponse, ContentUpdate, Make stored locations fetchable, wherever this response is embedded. Doing it…

### Community 113 - "create_token"
Cohesion: 0.29
Nodes (8): create_token(), list_tokens(), get, _token_to_dict(), generate_provisioning_qr(), ProvisioningRequest, BaseModel, EnrollmentToken

### Community 118 - "check-maps-keys.py"
Cohesion: 0.32
Nodes (7): check_server_key(), main(), Path, Check the Google Maps keys and say plainly what is wrong with them. Run this…, Value of `name` in a .env file, or '' when absent - no dependency on dotenv., Ask Static Maps for a real image; its rejection text is the diagnosis., read_env()

### Community 119 - ".downloadAndInstallUpdate"
Cohesion: 0.36
Nodes (4): AppVersionDto, Context, OkHttpClient, UpdateManager

### Community 120 - "SignageDeviceAdminReceiver"
Cohesion: 0.33
Nodes (5): EnrollRequest, Context, Intent, SignageDeviceAdminReceiver, DeviceAdminReceiver

### Community 122 - "select_rendition"
Cohesion: 0.25
Nodes (16): Screen, Selects the most appropriate media rendition for a screen based on its hardware…, select_rendition(), Rendition selection, against the set the transcoder actually produces.…, Content carrying exactly what the transcoder produces today., real_content(), rendition(), screen() (+8 more)

### Community 128 - "useAuthStore"
Cohesion: 0.11
Nodes (21): AccountPage(), ApprovalsPage(), PendingOrg, EmergencyPage(), GroupDetailPage(), accountLinks, adminLinks, DashboardLayout() (+13 more)

### Community 130 - "approvals.py"
Cohesion: 0.19
Nodes (17): ApprovalRequest, approve_organization(), DemoVideoPayload, get_universal_demo_video(), list_pending_organizations(), PendingOrgOut, BaseModel, get (+9 more)

### Community 131 - "cleanup_orphans.py"
Cohesion: 0.43
Nodes (6): find_orphans(), main(), Path, Find upload files that no database row points at. Reports by default and…, Every upload path any row still points at, relative to the uploads root., referenced_paths()

### Community 132 - "vercel.json"
Cohesion: 0.29
Nodes (6): framework, root, rewrites, $schema, services, frontend

### Community 137 - "upload_content"
Cohesion: 0.29
Nodes (7): generate_video_thumbnail(), public_upload_url(), UploadFile, queue_processing(), Hand a video to the transcode worker, or mark it failed if we cannot. The…, Where an asset lives, stored as a path rather than a full URL. This used to…, upload_content()

### Community 140 - "env.py"
Cohesion: 0.40
Nodes (4): Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 143 - "content/page.tsx"
Cohesion: 0.16
Nodes (25): ContentPage(), isSupported(), QueuedUpload, stripExtension(), GroupsPage(), ScreensPage(), StatusFilter, useStoredView() (+17 more)

### Community 144 - "test_rollout_policy.py"
Cohesion: 0.18
Nodes (18): apply_update_status(), eligible_for_fallback(), Staged player rollout: which build a screen is offered, and when to give up on…, Point a screen at a build, clearing any state from the previous attempt.…, Restrict an AppRelease query to builds that unpinned screens may be offered., Fold one device-reported update result into `screen`. Returns a short human-…, repin(), Staged-rollout decisions — pure logic, no database, no device. Run directly:… (+10 more)

### Community 145 - "booking_report.py"
Cohesion: 0.22
Nodes (14): api_key(), fetch_static_map(), is_enabled(), Map imagery for reports, behind a single switch. Everything map-related…, URL for an image pinning every point, or None when maps are not configured.…, The map image itself, or None if unavailable. A report must never fail because…, static_map_url(), build_pdf() (+6 more)

### Community 147 - "utcnow"
Cohesion: 0.16
Nodes (18): datetime, Return a timezone-aware UTC timestamp., utcnow(), create_checkout(), assign_group_playlist(), create_group(), delete_group(), list_groups() (+10 more)

### Community 148 - "screens.py"
Cohesion: 0.07
Nodes (55): AppRelease, get_redis(), _detect_lan_host(), is_s3_enabled(), media_base_url(), Turning a stored media location into something a browser or a TV can fetch.…, Best-effort LAN address of this machine, so devices on the network can reach…, Origin that players and browsers should fetch media from. Defaults to this… (+47 more)

### Community 149 - "ensure_billing_catalog"
Cohesion: 0.14
Nodes (15): ensure_billing_catalog(), plan_features(), Plan, Session, lifespan(), Whether this API process should also run the arq worker. Off by default:…, _run_worker_in_process(), Subscription (+7 more)

### Community 152 - "PlayEndReason"
Cohesion: 0.22
Nodes (6): PlayCompletion, PlayEndReason, FAILED, INTERRUPTED, PLAYED_TO_END, SKIPPED

### Community 155 - "theme-toggle.tsx"
Cohesion: 0.83
Nodes (3): subscribe(), ThemeToggle(), useHydrated()

### Community 156 - "PlaylistBase"
Cohesion: 0.67
Nodes (3): PlaylistBase, PlaylistCreate, PlaylistResponse

### Community 175 - "ScreenBase"
Cohesion: 0.67
Nodes (3): ScreenBase, ScreenCreate, ScreenResponse

### Community 176 - "run"
Cohesion: 0.53
Nodes (5): auth_header(), main(), TestClient, Runnable backend parity check: python tests/test_feature_parity.py, run()

### Community 177 - "Organization"
Cohesion: 0.08
Nodes (42): get_db(), AdPlacementTarget, Campaign, Content, EmergencyBroadcast, EnrollmentToken, Organization, Plan (+34 more)

## Knowledge Gaps
- **301 isolated node(s):** `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END`, `SKIPPED`, `FAILED` (+296 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **45 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TenantScope` connect `TenantScope` to `approvals.py`, `delete`, `upload_content`, `models.py`, `create_token`, `HTTPException`, `utcnow`, `playlists.py`, `acknowledge_alert`, `ensure_billing_catalog`, `screens.py`, `Organization`, `_post`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `build_pdf()` connect `booking_report.py` to `TenantScope`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `approvals.py`, `test_p6_websockets.py`, `delete`, `test_alerting.py`, `auth.py`, `upload_content`, `models.py`, `run`, `Organization`, `worker.py`, `playlists.py`, `screens.py`, `acknowledge_alert`, `test_ws_connection_pool.py`, `TenantScope`, `_post`, `test_release_rollout.py`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Are the 59 inferred relationships involving `HTTPException` (e.g. with `health_check()` and `acknowledge_alert()`) actually correct?**
  _`HTTPException` has 59 INFERRED edges - model-reasoned connections that need verification._
- **What connects `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END` to the rest of the system?**
  _301 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `schemas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08710801393728224 - nodes in this community are weakly interconnected._
- **Should `ApiService.kt` be split into smaller, more focused modules?**
  _Cohesion score 0.09388335704125178 - nodes in this community are weakly interconnected._