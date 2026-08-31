# Graph Report - OLRAC SIGNAGE  (2026-08-31)

## Corpus Check
- 310 files · ~336,232 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2508 nodes · 5734 edges · 199 communities (160 shown, 39 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 202 edges (avg confidence: 0.78)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cdb54bc4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_tv_deep_link.py
- schemas.py
- PlaylistItemEntity
- ApiService.kt
- MainActivity
- team/page.tsx
- PlaybackService
- models.py
- MainActivity
- AbleSign Auto-Launch — Full Documentation
- compilerOptions
- ScheduleEvaluator
- ValueError
- test_screen_approval.py
- api.ts
- components.json
- OLRAC Signage — Work Order for Antigravity (Gemini Pro)
- PlaybackTelemetry
- tenancy.py
- resolve_rotation
- get_password_hash
- resolve_media_url
- dependencies
- devDependencies
- TenantScope
- OLRAC Signage
- TransitionType
- admin.py
- app/layout.tsx
- _post
- StorageManagerTest
- conftest.py
- ProofOfPlayWorker.kt
- scripts
- cn
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
- websockets.py
- test_media_storage.py
- get_redis
- SyncBackoffPolicyTest
- gradlew
- .onCreate
- storage_prefix
- model_validator
- process_media_sync
- eslint.config.mjs
- next.config.ts
- DeviceState
- OLRAC Signage — 80-TV Rollout Deployment Guide
- PlayerScreen.kt
- admin-ui.tsx
- parse
- P9 — Zero-touch provisioning for 80+ TVs (no ADB)
- postcss.config.mjs
- backup_db.sh
- validation_script.sh
- content/[id]/page.tsx
- Player
- AppDatabase
- P8 — Per-TV capability detection and rendition selection
- Tests
- PlayerViewModel
- test_release_rollout.py
- ScheduleEvaluatorTest
- DeviceOwnerManagerTest
- HTTPException
- Part B — Operations home page
- test_platform_admin.py
- screen-map.tsx
- LaunchState
- UtcDateTime
- test_role_separation.py
- frontend/README.md
- Google Maps setup
- ContentResponse
- rules/graphify.md
- workflows/graphify.md
- Deploying to Render + Cloudflare (or Vercel)
- playlist-builder.tsx
- AGENTS.md
- lucide-react
- check-maps-keys.py
- .downloadAndInstallUpdate
- SignageDeviceAdminReceiver
- PlayEventDao
- select_rendition
- start-dev.ps1
- useAuthStore
- get_payment_provider
- cleanup_orphans.py
- create_access_token
- provision-tv.sh
- build.sh
- ApiClient
- booking_report.py
- utcnow
- @types/qrcode.react
- content/page.tsx
- test_rollout_policy.py
- button.tsx
- MaintenanceGesture
- recharts
- screens.py
- main.py
- PlayCompletionTest
- check_r2.py
- PlayEndReason
- UpdateGateTest
- sign_in_with_google
- theme-toggle.tsx
- get_media_report
- UpdateGate
- a1b4e7c92f38_play_log_campaign_attribution.py
- env.py
- next-themes
- react
- tw-animate-css
- @types/leaflet
- update_user
- SessionLocal
- Organization
- test_reinstall_reconnect.py
- get
- content.py
- test_google_signin.py
- @dnd-kit/sortable
- shadcn
- emergency/page.tsx
- @dnd-kit/core
- routers/billing.py
- @dnd-kit/utilities
- groups.py
- ProfileUpdate
- test_signup_lifecycle.py
- PlaylistBase
- acknowledge_alert
- ScreenBase
- .query
- resolve_location_link
- promote_release
- leaflet

## God Nodes (most connected - your core abstractions)
1. `TenantScope` - 121 edges
2. `cn()` - 74 edges
3. `utcnow()` - 56 edges
4. `get_password_hash()` - 55 edges
5. `Organization` - 51 edges
6. `_post()` - 48 edges
7. `useAuthStore` - 44 edges
8. `User` - 43 edges
9. `create_access_token()` - 41 edges
10. `Screen` - 35 edges

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

## Communities (199 total, 39 thin omitted)

### Community 0 - "test_tv_deep_link.py"
Cohesion: 0.16
Nodes (16): _android_intent_url(), Rewrite an "olrac://" deep link into the intent: form a browser will actually…, The TV's Custom Tab landing page, which then hands back to the player app.…, _tv_result_page(), HTMLResponse, The TV hand-back link must be openable by a browser: python…, The whole bug in one assertion: a raw custom scheme is what Chrome rejects., No APK change: the intent's data must still be the olrac:// URL already… (+8 more)

### Community 1 - "schemas.py"
Cohesion: 0.08
Nodes (45): create_checkout(), AlertResponse, AlertSummaryResponse, AppVersionResponse, BillingSummaryResponse, CheckoutRequest, CheckoutResponse, DeviceAuthRequest (+37 more)

### Community 2 - "PlaylistItemEntity"
Cohesion: 0.24
Nodes (3): PlaylistDao, PlaylistItemEntity, Flow

### Community 3 - "ApiService.kt"
Cohesion: 0.10
Nodes (21): ApiService, AuthMethodsResponse, ContentDto, DeviceAuthRequest, DeviceTokenResponse, EnrollResponse, GoogleOAuthUrlResponse, GooglePollResponse (+13 more)

### Community 4 - "MainActivity"
Cohesion: 0.14
Nodes (7): RegistrationSnapshot, Intent, MainActivity, GooglePollRequest, SignInRequest, ComponentActivity, KeyEvent

### Community 5 - "team/page.tsx"
Cohesion: 0.12
Nodes (36): asTenantRole(), roleDescription, TeamPage(), TENANT_ROLES, AdBookings(), asDate(), runState(), rupees() (+28 more)

### Community 6 - "PlaybackService"
Cohesion: 0.06
Nodes (22): ConnectivityWatcher, Response, WebSocket, RealtimeClient, WebSocketListener, Context, Intent, Job (+14 more)

### Community 7 - "models.py"
Cohesion: 0.15
Nodes (20): AdPlacementTarget, Alert, Campaign, EmergencyBroadcast, Plan, PlayLog, PlayLogHourlyRollup, One place a booked advert runs, and the playlist item it put there. Exactly one… (+12 more)

### Community 8 - "MainActivity"
Cohesion: 0.05
Nodes (32): android.accessibilityservice.AccessibilityService, android.app.Activity, android.app.PendingIntent, android.content.BroadcastReceiver, android.content.ComponentName, android.content.Context, android.content.Intent, android.content.SharedPreferences (+24 more)

### Community 9 - "AbleSign Auto-Launch — Full Documentation"
Cohesion: 0.07
Nodes (28): AbleSign Auto-Launch — Full Documentation, AbleSign not launching after reboot, Build commands, Check if watchdog is running, Files in This Folder, How to Install on ANY Android TV, How to Rebuild the APK (if you change the code), If Something Goes Wrong (+20 more)

### Community 10 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 12 - "ValueError"
Cohesion: 0.12
Nodes (14): AppReleaseCreate, AppReleaseResponse, HeartbeatRequest, PasswordChange, PlaylistItemUpdate, Partial screen update: only the fields actually present are written. The PUT…, Each day maps to exactly [start, end] as HH:MM. Validated here rather than in…, ScheduleBase (+6 more)

### Community 13 - "test_screen_approval.py"
Cohesion: 0.26
Nodes (11): auth_header(), Screen pairing is instant: python tests/test_screen_approval.py This file used…, sign_in(), test_a_secret_does_not_authenticate_a_different_screen(), test_a_signed_in_screen_syncs_straight_away(), test_enrolment_token_admits_immediately(), test_pairing_admits_immediately(), test_re_signing_in_keeps_the_screen_admitted() (+3 more)

### Community 14 - "api.ts"
Cohesion: 0.06
Nodes (48): MediaThumbnail(), API_HOST, ApiError, authFetch(), configuredUrl, fetchWithAuth(), resolveMediaUrl(), AlertSeverity (+40 more)

### Community 15 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 16 - "OLRAC Signage — Work Order for Antigravity (Gemini Pro)"
Cohesion: 0.08
Nodes (23): 0. Ground rules, 1. Device knowledge — the most important section, 2. What already exists and is verified, 3. Gap analysis — what the new goal needs, 4. Phases, 5. Infrastructure, 6. Regression suite — run after every phase, 7. Definition of done for the whole programme (+15 more)

### Community 17 - "PlaybackTelemetry"
Cohesion: 0.08
Nodes (17): ExoPlayer, Job, PlaybackException, onPlayerError(), PlayerSupervisor, HeartbeatReporter, Context, PlaybackSnapshot (+9 more)

### Community 18 - "tenancy.py"
Cohesion: 0.12
Nodes (25): OLRAC Signage backend package. Explicit package marker. Without it `backend` is…, BroadcastRequest, cancel_emergency_broadcast(), get_active_broadcasts(), BaseModel, get, Session, create_token() (+17 more)

### Community 19 - "resolve_rotation"
Cohesion: 0.23
Nodes (12): normalise(), Resolve the rotation a screen should apply to one playlist item. The player…, Coerce anything to one of 0/90/180/270, defaulting to 0., Degrees the player should rotate this item on this screen., resolve_rotation(), Rotation precedence — pure logic, no database, no device. Run directly: python…, A screen mounted portrait with one item deliberately pinned to landscape., test_defaults_when_nothing_is_set() (+4 more)

### Community 20 - "get_password_hash"
Cohesion: 0.09
Nodes (21): ensure_initial_owner(), get_or_create_default_organization(), get_password_hash(), Create the first real owner only when explicit bootstrap credentials are…, main(), Self-service account endpoints behind the dashboard's profile menu. Covers the…, run(), _token() (+13 more)

### Community 21 - "resolve_media_url"
Cohesion: 0.16
Nodes (19): _client(), Reading and writing media wherever it happens to live. The transcoder needs a…, Persist `local_path` under `key` and return the location to save on the row.…, store(), delete_stored_file(), _detect_lan_host(), get_s3_config(), is_s3_enabled() (+11 more)

### Community 22 - "dependencies"
Cohesion: 0.10
Nodes (21): @base-ui/react, class-variance-authority, clsx, dependencies, @base-ui/react, class-variance-authority, clsx, next (+13 more)

### Community 23 - "devDependencies"
Cohesion: 0.09
Nodes (23): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, @opennextjs/cloudflare, tailwindcss, @tailwindcss/postcss (+15 more)

### Community 24 - "TenantScope"
Cohesion: 0.14
Nodes (35): AdPlacement, An advert sold to a client: what runs, for whom, when, and for how much.…, add_target(), _booking_screen_ids(), build_booking_report(), create_placement(), delete_placement(), download_booking_report() (+27 more)

### Community 25 - "OLRAC Signage"
Cohesion: 0.11
Nodes (16): Acceptance checks, Build-time server configuration, Install and pair, Kiosk and boot provisioning, OLRAC Android TV player, Supported devices, 1. Configure the backend, 2. Apply database migrations (+8 more)

### Community 26 - "TransitionType"
Cohesion: 0.19
Nodes (11): fromWire(), TransitionSpec, TransitionSpecResolver, TransitionType, FADE, NONE, SLIDE_DOWN, SLIDE_LEFT (+3 more)

### Community 27 - "admin.py"
Cohesion: 0.09
Nodes (55): _apply_plan(), ApprovalRequest, approve_tenant(), create_plan(), delete_plan(), DemoVideoPayload, _get_org(), get_tenant() (+47 more)

### Community 28 - "app/layout.tsx"
Cohesion: 0.19
Nodes (8): geistMono, geistSans, metadata, Providers(), Toaster(), TransitionClass, ViewTransition(), ViewTransitionProps

### Community 29 - "_post"
Cohesion: 0.12
Nodes (30): build_oauth_url(), _claims(), client_id(), client_secret(), exchange_code(), GoogleError, is_configured(), is_web_configured() (+22 more)

### Community 30 - "StorageManagerTest"
Cohesion: 0.22
Nodes (4): OkHttpClient, StorageManager, Context, StorageManagerTest

### Community 31 - "conftest.py"
Cohesion: 0.16
Nodes (10): _postgres_reachable(), pytest_collect_file(), pytest_collection_finish(), pytest_collection_modifyitems(), Run each backend test script in its own process. `backend/database.py` builds…, Whether a server is listening on the port the scripts create their databases…, Fail loudly if a script also got imported as a module. pytest.ini restricts…, Fail if any tests/test_*.py is collected by neither mechanism. A file that is… (+2 more)

### Community 32 - "ProofOfPlayWorker.kt"
Cohesion: 0.13
Nodes (16): Context, ProofOfPlayReporter, BatchOutcome, ACCEPTED, DISCARD, RETRY_LATER, enqueueNow(), isoFormatter() (+8 more)

### Community 33 - "scripts"
Cohesion: 0.17
Nodes (11): name, private, scripts, build, cf:build, cf:deploy, cf:preview, dev (+3 more)

### Community 35 - "cn"
Cohesion: 0.12
Nodes (28): StatusFilter, useStoredView(), ViewMode, AssetCard(), AssetGrid(), OverlayBadge(), StatusIndicator(), CardAction() (+20 more)

### Community 36 - "test_alerting.py"
Cohesion: 0.08
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

### Community 49 - "websockets.py"
Cohesion: 0.29
Nodes (11): dashboard_websocket(), Screen, Session, WebSocket, Live fleet events for one dashboard user., Identity check for a screen's push socket. Kept deliberately identical to…, Push channel for one screen. Held open for the life of the device., register_ws() (+3 more)

### Community 50 - "test_media_storage.py"
Cohesion: 0.12
Nodes (23): fetch_to(), is_remote(), Path, The backend-relative key inside a stored location. Both schemes carry the same…, Put the bytes of `stored_url` at `destination` and return it. A local file is…, storage_key_for(), local_mode(), fixture (+15 more)

### Community 51 - "get_redis"
Cohesion: 0.08
Nodes (31): Any, get_redis(), _pool_for_current_loop(), health_check(), Session, Liveness, plus WHICH database is actually behind it. This used to answer…, bring_to_front(), _command_key() (+23 more)

### Community 53 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 72 - ".onCreate"
Cohesion: 0.32
Nodes (13): BrandedMessage(), GoogleLogo(), GoogleSignInScreen(), Bundle, Modifier, PairingScreen(), PinPromptScreen(), secondaryButtonColors() (+5 more)

### Community 74 - "storage_prefix"
Cohesion: 0.14
Nodes (20): Safe, alphanumeric bucket key prefix for an organization., storage_prefix(), FakeOrg, FakeUser, Tenant storage folders are named, unique and stable: python…, Local disk and R2 must file a capture under the same key, or the folder layout…, Stands in for models.Organization; owner_email is a property over .users., The address itself, unmangled -- that is the point of naming rather than… (+12 more)

### Community 75 - "model_validator"
Cohesion: 0.15
Nodes (7): MediaRenditionResponse, PlacementCreate, PlaylistItemBase, PlaylistItemCreate, PlaylistItemResponse, PlaylistUpdate, model_validator

### Community 76 - "process_media_sync"
Cohesion: 0.18
Nodes (19): compute_sha256(), probe_file(), process_media(), process_media_sync(), run_command_sync(), skipif, cleanup_tempdir(), _do_not_process_on_upload() (+11 more)

### Community 79 - "DeviceState"
Cohesion: 0.15
Nodes (5): DeviceState, Activity, ScreenshotManager, Bitmap, WeakReference

### Community 80 - "OLRAC Signage — 80-TV Rollout Deployment Guide"
Cohesion: 0.10
Nodes (18): 1. Server Environment Setup, 2. Storage Configuration, 3. Start the Stack, 4. Database Migration, 5. Create the Platform Owner, 6. TV Enrollment & Provisioning, 7. Watchdog Setup (Crucial for Budget TVs), Build the Watchdog (+10 more)

### Community 81 - "PlayerScreen.kt"
Cohesion: 0.23
Nodes (13): android, clearPlayCheckpoint(), DualSurfacePlayer(), com, Modifier, PlaybackSurface(), PlayerScreen(), preparePlayer() (+5 more)

### Community 83 - "admin-ui.tsx"
Cohesion: 0.15
Nodes (18): AdminApprovalsPage(), AdminPackagesPage(), blank, AdminTenantDetailPage(), Tab, AdminTenantsPage(), Accent, accents (+10 more)

### Community 84 - "parse"
Cohesion: 0.08
Nodes (44): _expand(), geocode(), _is_error_page(), MapsLinkError, _name_from(), _name_from_search(), parse(), Turn a shared Google Maps link into coordinates. This exists so setting a… (+36 more)

### Community 85 - "P9 — Zero-touch provisioning for 80+ TVs (no ADB)"
Cohesion: 0.20
Nodes (9): 1. Make the app a working Device Policy Controller, 2. Silent updates (finishes P7), 3. Generate the provisioning QR, 4. Auto-enrol on first boot, 5. Retire the accessibility watchdog on provisioned devices, Definition of done, Deployment paths, in order of preference, P9 — Zero-touch provisioning for 80+ TVs (no ADB) (+1 more)

### Community 89 - "content/[id]/page.tsx"
Cohesion: 0.26
Nodes (9): dateTime(), ScreenDetailsDrawer(), ScreenMap(), Tabs(), TabsIndicator(), TabsList(), TabsPanel(), TabsTrigger() (+1 more)

### Community 90 - "Player"
Cohesion: 0.20
Nodes (7): awaitPlayerReady(), Player, DecoderSnapshot, Player, ExoPlayer, PlaybackException, Player

### Community 91 - "AppDatabase"
Cohesion: 0.25
Nodes (6): AppDatabase, getDatabase(), Context, migrate(), RoomDatabase, SupportSQLiteDatabase

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
Cohesion: 0.23
Nodes (11): AppRelease, bearer(), _database_url(), device_headers(), publish(), Player releases: who may publish one, and who it reaches. Covers the defect…, Read the screen straight from the database. There is no GET /api/screens/{id};…, Postgres when a server is there, SQLite otherwise. Production is Postgres and… (+3 more)

### Community 98 - "HTTPException"
Cohesion: 0.18
Nodes (27): delete(), Remove a stored object. Best effort -- a missing object is not an error. Local…, revoke_token(), add_item_to_playlist(), bump_playlist(), create_playlist(), delete_playlist(), get_playlist() (+19 more)

### Community 99 - "Part B — Operations home page"
Cohesion: 0.12
Nodes (16): Backend, Dashboard, Definition of done, Definition of done, Every panel below uses data that already exists, Layout, Order of work, P10 — Display rotation, and an operations home page (+8 more)

### Community 100 - "test_platform_admin.py"
Cohesion: 0.23
Nodes (10): client_key(), Request, Who to count this request against. slowapi's get_remote_address returns…, auth(), check(), Super Admin boundary and the auth holes it closed: python…, One platform operator, and one ordinary tenant owner in a separate organisation., run() (+2 more)

### Community 101 - "screen-map.tsx"
Cohesion: 0.16
Nodes (12): MapPoint, TILES, listeners, loadSdk(), MAPS_KEY, MapsWindow, publish(), serverSnapshot() (+4 more)

### Community 102 - "LaunchState"
Cohesion: 0.33
Nodes (7): CheckingLocalState, GoogleSignIn, LaunchState, LaunchStateResolver, Pairing, Playing, SignIn

### Community 106 - "UtcDateTime"
Cohesion: 0.40
Nodes (3): A DateTime that always reads back as timezone-aware UTC. Postgres with…, UtcDateTime, TypeDecorator

### Community 107 - "test_role_separation.py"
Cohesion: 0.14
Nodes (25): check(), cross_tenant_is_refused(), denied(), hdr(), invisible(), Every feature, exercised as the role that owns it: python…, Everything the platform operator owns, driven for real., The platform operator is not a tenant, and the dashboard must not pretend… (+17 more)

### Community 108 - "frontend/README.md"
Cohesion: 0.50
Nodes (3): Deploy on Vercel, Getting Started, Learn More

### Community 109 - "Google Maps setup"
Cohesion: 0.20
Nodes (9): 1. Create a project and enable billing, 2. Enable the three APIs, 3. Create the browser key, 4. Create the server key, 5. Check the keys, 6. Restart, Google Maps setup, If the map does not appear (+1 more)

### Community 110 - "ContentResponse"
Cohesion: 0.40
Nodes (4): ContentBase, ContentResponse, ContentUpdate, Make stored locations fetchable, wherever this response is embedded. Doing it…

### Community 113 - "Deploying to Render + Cloudflare (or Vercel)"
Cohesion: 0.12
Nodes (16): 0. Before either dashboard, 1. Render: the API and worker, 2. The dashboard: Cloudflare Workers, or Vercel, 2a. Cloudflare Workers (via OpenNext), 2b. Vercel, 3. Back to Render, 4. Create the platform operator, 5. Verify before provisioning a screen (+8 more)

### Community 114 - "playlist-builder.tsx"
Cohesion: 0.17
Nodes (13): dayLabels, dayNames, DefaultTransitionPanel(), ItemRow(), previewStyle(), rotationLabel(), rotationOptions, Selection (+5 more)

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
Cohesion: 0.13
Nodes (24): AdminLayout(), navItems, AccountPage(), EmergencyPage(), GroupsPage(), accountLinks, DashboardLayout(), primaryLinks (+16 more)

### Community 130 - "get_payment_provider"
Cohesion: 0.23
Nodes (9): CheckoutSession, get_payment_provider(), MockPaymentProvider, PaymentProvider, RazorpayProvider, Protocol, RuntimeError, auth_headers() (+1 more)

### Community 131 - "cleanup_orphans.py"
Cohesion: 0.43
Nodes (6): find_orphans(), main(), Path, Find upload files that no database row points at. Reports by default and…, Every upload path any row still points at, relative to the uploads root., referenced_paths()

### Community 132 - "create_access_token"
Cohesion: 0.17
Nodes (16): ScreenGroup, create_access_token(), capture_screenshot(), main(), P6 realtime checks: python tests/test_p6_websockets.py Covers hierarchical…, /api/ws/dashboard/ws must reach the dashboard handler, not the device one. Both…, Push must never be the only path. The spec is explicit: if the socket is down…, _redis_available() (+8 more)

### Community 137 - "ApiClient"
Cohesion: 0.38
Nodes (3): ApiClient, Context, okhttp3

### Community 139 - "booking_report.py"
Cohesion: 0.22
Nodes (14): api_key(), fetch_static_map(), is_enabled(), Map imagery for reports, behind a single switch. Everything map-related…, URL for an image pinning every point, or None when maps are not configured.…, The map image itself, or None if unavailable. A report must never fail because…, static_map_url(), build_pdf() (+6 more)

### Community 140 - "utcnow"
Cohesion: 0.15
Nodes (15): datetime, Return a timezone-aware UTC timestamp., utcnow(), recover_stuck_processing(), auth_header(), main(), TestClient, Runnable backend parity check: python tests/test_feature_parity.py (+7 more)

### Community 143 - "content/page.tsx"
Cohesion: 0.11
Nodes (31): AdminReleasesPage(), Alert, AlertsPage(), buildAlerts(), hoursSince(), Severity, AdDetailPage(), ContentPage() (+23 more)

### Community 144 - "test_rollout_policy.py"
Cohesion: 0.18
Nodes (18): apply_update_status(), eligible_for_fallback(), Staged player rollout: which build a screen is offered, and when to give up on…, Point a screen at a build, clearing any state from the previous attempt.…, Restrict an AppRelease query to builds that unpinned screens may be offered., Fold one device-reported update result into `screen`. Returns a short human-…, repin(), Staged-rollout decisions — pure logic, no database, no device. Run directly:… (+10 more)

### Community 145 - "button.tsx"
Cohesion: 0.24
Nodes (7): BulkActionBar(), SelectAllCheckbox(), looksLikeLink(), Place, PlaceSearch(), Button(), buttonVariants

### Community 148 - "screens.py"
Cohesion: 0.13
Nodes (33): AppRelease, as_aware_utc(), batch_upload_play_logs(), collect_device_secret(), current_app_version(), enroll_device(), ensure_screen_quota(), generate_pair_code() (+25 more)

### Community 149 - "main.py"
Cohesion: 0.07
Nodes (22): get_db(), _ensure_schema(), lifespan(), login_page(), get, Request, Build the schema on a brand-new database, and stamp it so Alembic can take…, Whether this API process should also run the arq worker. Off by default:… (+14 more)

### Community 152 - "PlayEndReason"
Cohesion: 0.22
Nodes (6): PlayCompletion, PlayEndReason, FAILED, INTERRUPTED, PLAYED_TO_END, SKIPPED

### Community 154 - "sign_in_with_google"
Cohesion: 0.16
Nodes (21): auth_methods(), change_own_password(), get_current_user(), get_current_user_ws(), get_secret_key(), login_for_access_token(), get, limit (+13 more)

### Community 155 - "theme-toggle.tsx"
Cohesion: 0.83
Nodes (3): subscribe(), ThemeToggle(), useHydrated()

### Community 156 - "get_media_report"
Cohesion: 0.36
Nodes (9): export_campaign_report(), get_campaign_info(), get_campaign_stats(), get_campaign_timeseries(), get_media_report(), list_campaigns(), get, Session (+1 more)

### Community 166 - "env.py"
Cohesion: 0.40
Nodes (4): Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 175 - "update_user"
Cohesion: 0.24
Nodes (10): active_owner_count(), create_user(), delete_user(), deny_platform_account(), list_users(), get, put, User (+2 more)

### Community 176 - "SessionLocal"
Cohesion: 0.09
Nodes (30): MediaRendition, aggregate_play_logs_sync(), prune_play_log_rollups(), prune_play_logs(), prune_screenshots(), _publish_alert(), Notice what is wrong with the fleet, and what has stopped being wrong. Runs…, Tell any connected dashboard, best effort. Wrapped: Redis being unavailable… (+22 more)

### Community 177 - "Organization"
Cohesion: 0.13
Nodes (31): Content, EnrollmentToken, Organization, Playlist, PlaylistItem, Exposed so UserResponse can show the tenant by name instead of a bare id., Address that names this tenant's storage folder. See media_urls.storage_prefix.…, Screen (+23 more)

### Community 178 - "test_reinstall_reconnect.py"
Cohesion: 0.30
Nodes (13): check(), dashboard_token(), fleet(), One account on the TV and the dashboard, and a screen that survives a…, What the player sends when the installer types their account on the TV., What the player sends on every cold start, before it knows anything., A wipe on a panel whose serial is unreadable CANNOT be auto-recovered. Pinned…, A caller holding only the device id must not be handed a device secret.… (+5 more)

### Community 179 - "get"
Cohesion: 0.14
Nodes (20): auth_device(), bind_screen_to_org(), get_tv_google_oauth_url(), google_device_poll(), public_base_url(), get, limit, put (+12 more)

### Community 180 - "content.py"
Cohesion: 0.21
Nodes (16): delete_content(), generate_video_thumbnail(), get_all_content(), get_s3_client(), public_upload_url(), get, put, UploadFile (+8 more)

### Community 184 - "test_google_signin.py"
Cohesion: 0.24
Nodes (10): approved(), _database_url(), poll(), Signing a TV in with a Google account: who it lets in, and who it must not.…, Postgres when a server is there, SQLite otherwise -- as test_release_rollout…, Point the module's two network calls at canned answers., run(), setup_db() (+2 more)

### Community 189 - "emergency/page.tsx"
Cohesion: 0.16
Nodes (16): BillingPage(), percent(), exportFormats, targetLabels, GroupDetailPage(), ErrorState(), AssignScreensDialog(), GroupSettingsDialog() (+8 more)

### Community 192 - "routers/billing.py"
Cohesion: 0.21
Nodes (15): ensure_billing_catalog(), plan_features(), Plan, Session, billing_summary(), list_plans(), datetime, get (+7 more)

### Community 195 - "groups.py"
Cohesion: 0.33
Nodes (12): assign_group_playlist(), create_group(), delete_group(), list_groups(), get, put, Reject a parent that is not ours, is the group itself, or would close a loop.…, serialize_group() (+4 more)

### Community 196 - "ProfileUpdate"
Cohesion: 0.33
Nodes (4): ProfileUpdate, Deliberately narrow: /screens/register is unauthenticated, so it must not reuse…, Self-service profile edit. Deliberately excludes role, is_active and password…, RegisterResponse

### Community 197 - "test_signup_lifecycle.py"
Cohesion: 0.31
Nodes (9): check(), hdr(), promote_platform_operator(), A company from signup to paying customer: python tests/test_signup_lifecycle.py…, Stand in for Google's token endpoint. Only the exchange is replaced. Everything…, The bootstrap account is created as an ordinary owner; make it the operator.…, run(), stub_google() (+1 more)

### Community 198 - "PlaylistBase"
Cohesion: 0.67
Nodes (3): PlaylistBase, PlaylistCreate, PlaylistResponse

### Community 199 - "acknowledge_alert"
Cohesion: 0.25
Nodes (9): Alert, acknowledge_alert(), alert_summary(), list_alerts(), get, Open alerts, newest first. Resolved ones only when asked for. The default is…, Mark an alert as picked up, without claiming the underlying fault is fixed.…, Counts for the navigation badge, so the header does not fetch the whole list. (+1 more)

### Community 200 - "ScreenBase"
Cohesion: 0.50
Nodes (3): ScreenBase, ScreenCreate, ScreenResponse

### Community 202 - "resolve_location_link"
Cohesion: 0.40
Nodes (5): Coordinates for a pasted Google Maps link. Deliberately not a Google API call:…, resolve_location_link(), A Google Maps share link, pasted by an operator., ResolveLinkRequest, ResolveLinkResponse

### Community 203 - "promote_release"
Cohesion: 0.40
Nodes (5): promote_release(), patch, Move a build along the rollout ring: draft -> canary -> released. Promoting to…, AppReleasePatch, Promote (or demote) a build. The only mutable field: version_code, apk_url and…

## Knowledge Gaps
- **316 isolated node(s):** `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END`, `SKIPPED`, `FAILED` (+311 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TenantScope` connect `TenantScope` to `schemas.py`, `tenancy.py`, `screens.py`, `main.py`, `admin.py`, `get_media_report`, `_post`, `update_user`, `Organization`, `get_redis`, `content.py`, `get`, `routers/billing.py`, `groups.py`, `acknowledge_alert`, `.query`, `resolve_location_link`, `promote_release`, `HTTPException`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `react` connect `react` to `button.tsx`, `dependencies`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Why does `SelectAllCheckbox()` connect `button.tsx` to `react`, `cn`, `content/page.tsx`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Are the 69 inferred relationships involving `HTTPException` (e.g. with `health_check()` and `approve_tenant()`) actually correct?**
  _`HTTPException` has 69 INFERRED edges - model-reasoned connections that need verification._
- **What connects `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END` to the rest of the system?**
  _316 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `schemas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0782608695652174 - nodes in this community are weakly interconnected._
- **Should `ApiService.kt` be split into smaller, more focused modules?**
  _Cohesion score 0.10338680926916222 - nodes in this community are weakly interconnected._