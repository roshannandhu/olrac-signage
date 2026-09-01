# Graph Report - OLRAC SIGNAGE  (2026-09-01)

## Corpus Check
- 321 files · ~359,492 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2679 nodes · 6279 edges · 208 communities (158 shown, 50 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 220 edges (avg confidence: 0.78)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `94c7c5f9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_tv_deep_link.py
- schemas.py
- PlaylistItemEntity
- ApiService.kt
- MainActivity
- screens/[id]/page.tsx
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
- main.py
- resolve_media_url
- dependencies
- devDependencies
- TenantScope
- OLRAC Signage
- TransitionType
- admin.py
- app/layout.tsx
- google_device.py
- StorageManagerTest
- conftest.py
- ProofOfPlayWorker.kt
- scripts
- WatchdogAccessibilityService
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
- delete
- _post
- SyncBackoffPolicyTest
- gradlew
- .onCreate
- storage_prefix
- model_validator
- test_media_worker.py
- eslint.config.mjs
- next.config.ts
- DeviceState
- OLRAC Signage — 80-TV Rollout Deployment Guide
- PlayerScreen.kt
- GoogleDeviceStartRequest
- PlayerSupervisor
- parse
- P9 — Zero-touch provisioning for 80+ TVs (no ADB)
- postcss.config.mjs
- backup_db.sh
- validation_script.sh
- send
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
- test_booking_report.py
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
- get_payment_provider
- AGENTS.md
- lucide-react
- check-maps-keys.py
- .downloadAndInstallUpdate
- SignageDeviceAdminReceiver
- PlayEventDao
- select_rendition
- start-dev.ps1
- useAuthStore
- ScreenshotManager
- cleanup_orphans.py
- create_access_token
- provision-tv.sh
- build.sh
- ApiClient
- booking_report.py
- utcnow
- @types/qrcode.react
- content/[id]/page.tsx
- test_rollout_policy.py
- branding.py
- MaintenanceGesture
- recharts
- screens.py
- redacted_validation_error
- PlayCompletionTest
- check_r2.py
- PlayEndReason
- UpdateGateTest
- .query
- theme-toggle.tsx
- users.py
- UpdateGate
- a1b4e7c92f38_play_log_campaign_attribution.py
- env.py
- next-themes
- react
- tw-animate-css
- @types/leaflet
- ScreenSignInRequest
- worker.py
- Organization
- test_reinstall_reconnect.py
- @dnd-kit/sortable
- content.py
- process_media_sync
- test_google_signin.py
- _restore_process_globals
- shadcn
- playlist-builder.tsx
- @dnd-kit/core
- routers/billing.py
- client_key
- GoogleDevicePollResponse
- groups.py
- e2e_test.py
- AlertSummaryResponse
- create_checkout
- acknowledge_alert
- PlacementSplit
- BrandingUpdate
- ResolveLinkRequest
- ExtensionCreate
- GoogleDeviceStartResponse
- leaflet
- ProfileUpdate
- next

## God Nodes (most connected - your core abstractions)
1. `TenantScope` - 150 edges
2. `cn()` - 74 edges
3. `utcnow()` - 60 edges
4. `get_password_hash()` - 56 edges
5. `_post()` - 53 edges
6. `Organization` - 51 edges
7. `useAuthStore` - 50 edges
8. `User` - 43 edges
9. `create_access_token()` - 42 edges
10. `delete()` - 35 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `Screen`  [EXTRACTED]
  tests/test_sqlite_utc.py → backend/models.py
- `run()` --calls--> `is_configured()`  [EXTRACTED]
  tests/test_google_signin.py → backend/google_device.py
- `run()` --calls--> `_claims()`  [EXTRACTED]
  tests/test_google_signin.py → backend/google_device.py
- `test_a_genuine_google_subdomain_is_still_accepted()` --calls--> `parse()`  [EXTRACTED]
  tests/test_maps_link.py → backend/maps_link.py
- `test_a_link_pasted_without_its_scheme_still_works()` --calls--> `parse()`  [EXTRACTED]
  tests/test_maps_link.py → backend/maps_link.py

## Import Cycles
- None detected.

## Communities (208 total, 50 thin omitted)

### Community 0 - "test_tv_deep_link.py"
Cohesion: 0.16
Nodes (16): _android_intent_url(), The TV's Custom Tab landing page, which then hands back to the player app.…, Rewrite an "olrac://" deep link into the intent: form a browser will actually…, _tv_result_page(), HTMLResponse, The TV hand-back link must be openable by a browser: python…, The whole bug in one assertion: a raw custom scheme is what Chrome rejects., No APK change: the intent's data must still be the olrac:// URL already… (+8 more)

### Community 1 - "schemas.py"
Cohesion: 0.08
Nodes (46): AlertResponse, AppReleasePatch, AppVersionResponse, BillingSummaryResponse, BrandingResponse, ClientBase, ClientCreate, ClientResponse (+38 more)

### Community 2 - "PlaylistItemEntity"
Cohesion: 0.24
Nodes (3): PlaylistDao, PlaylistItemEntity, Flow

### Community 3 - "ApiService.kt"
Cohesion: 0.10
Nodes (22): ApiService, AuthMethodsResponse, ContentDto, DeviceAuthRequest, DeviceTokenResponse, EnrollResponse, GoogleOAuthUrlResponse, GooglePollResponse (+14 more)

### Community 4 - "MainActivity"
Cohesion: 0.17
Nodes (5): Intent, MainActivity, GooglePollRequest, ComponentActivity, KeyEvent

### Community 5 - "screens/[id]/page.tsx"
Cohesion: 0.08
Nodes (42): GroupDetailPage(), orientationLabel(), ScreenDetailPage(), AdBookings(), asDate(), runState(), rupees(), AssignPlaylistCard() (+34 more)

### Community 6 - "PlaybackService"
Cohesion: 0.06
Nodes (22): ConnectivityWatcher, Response, WebSocket, RealtimeClient, WebSocketListener, Context, Intent, Job (+14 more)

### Community 7 - "models.py"
Cohesion: 0.11
Nodes (25): AdPlacementExtension, Alert, Campaign, Client, EmergencyBroadcast, Plan, PlayLog, PlayLogHourlyRollup (+17 more)

### Community 8 - "MainActivity"
Cohesion: 0.06
Nodes (29): android.accessibilityservice.AccessibilityService, android.app.Activity, android.app.PendingIntent, android.content.BroadcastReceiver, android.content.ComponentName, android.content.Context, android.content.Intent, android.content.SharedPreferences (+21 more)

### Community 9 - "AbleSign Auto-Launch — Full Documentation"
Cohesion: 0.07
Nodes (28): AbleSign Auto-Launch — Full Documentation, AbleSign not launching after reboot, Build commands, Check if watchdog is running, Files in This Folder, How to Install on ANY Android TV, How to Rebuild the APK (if you change the code), If Something Goes Wrong (+20 more)

### Community 10 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 12 - "ValueError"
Cohesion: 0.10
Nodes (17): AppReleaseCreate, AppReleaseResponse, HeartbeatRequest, PasswordChange, PlaylistItemUpdate, Partial screen update: only the fields actually present are written. The PUT…, Each day maps to exactly [start, end] as HH:MM. Validated here rather than in…, ScheduleBase (+9 more)

### Community 13 - "test_screen_approval.py"
Cohesion: 0.26
Nodes (11): auth_header(), Screen pairing is instant: python tests/test_screen_approval.py This file used…, sign_in(), test_a_secret_does_not_authenticate_a_different_screen(), test_a_signed_in_screen_syncs_straight_away(), test_enrolment_token_admits_immediately(), test_pairing_admits_immediately(), test_re_signing_in_keeps_the_screen_admitted() (+3 more)

### Community 14 - "api.ts"
Cohesion: 0.05
Nodes (61): AdminApprovalsPage(), AdminPackagesPage(), blank, AdminReleasesPage(), AdminTenantDetailPage(), Tab, AdminTenantsPage(), Accent (+53 more)

### Community 15 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 16 - "OLRAC Signage — Work Order for Antigravity (Gemini Pro)"
Cohesion: 0.08
Nodes (23): 0. Ground rules, 1. Device knowledge — the most important section, 2. What already exists and is verified, 3. Gap analysis — what the new goal needs, 4. Phases, 5. Infrastructure, 6. Regression suite — run after every phase, 7. Definition of done for the whole programme (+15 more)

### Community 17 - "PlaybackTelemetry"
Cohesion: 0.15
Nodes (9): HeartbeatReporter, Context, PlaybackSnapshot, PlaybackTelemetry, enqueue(), Context, CoroutineWorker, Result (+1 more)

### Community 18 - "tenancy.py"
Cohesion: 0.06
Nodes (48): OLRAC Signage backend package. Explicit package marker. Without it `backend` is…, eligible_for_fallback(), Staged player rollout: which build a screen is offered, and when to give up on…, Restrict an AppRelease query to builds that unpinned screens may be offered., create_client(), delete_client(), get_client(), list_clients() (+40 more)

### Community 19 - "resolve_rotation"
Cohesion: 0.23
Nodes (12): normalise(), Resolve the rotation a screen should apply to one playlist item. The player…, Coerce anything to one of 0/90/180/270, defaulting to 0., Degrees the player should rotate this item on this screen., resolve_rotation(), Rotation precedence — pure logic, no database, no device. Run directly: python…, A screen mounted portrait with one item deliberately pinned to landscape., test_defaults_when_nothing_is_set() (+4 more)

### Community 20 - "main.py"
Cohesion: 0.07
Nodes (30): _ensure_schema(), lifespan(), Whether this API process should also run the arq worker. Off by default:…, Build the schema on a brand-new database, and stamp it so Alembic can take…, _run_worker_in_process(), ensure_initial_owner(), get_or_create_default_organization(), get_password_hash() (+22 more)

### Community 21 - "resolve_media_url"
Cohesion: 0.20
Nodes (15): _detect_lan_host(), get_s3_config(), is_s3_enabled(), media_base_url(), Turning a stored media location into something a browser or a TV can fetch.…, Best-effort LAN address of this machine, so devices on the network can reach…, Origin that players and browsers should fetch media from., Absolute, fetchable URL for a stored media location. (+7 more)

### Community 22 - "dependencies"
Cohesion: 0.10
Nodes (21): @base-ui/react, class-variance-authority, clsx, @dnd-kit/utilities, dependencies, @base-ui/react, class-variance-authority, clsx (+13 more)

### Community 23 - "devDependencies"
Cohesion: 0.09
Nodes (23): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, @opennextjs/cloudflare, tailwindcss, @tailwindcss/postcss (+15 more)

### Community 24 - "TenantScope"
Cohesion: 0.08
Nodes (62): AdPlacement, AdPlacementTarget, An advert sold to a client: what runs, for whom, when, and for how much.…, One place a booked advert runs, and the playlist item it put there. Exactly one…, Address that names this tenant's storage folder. See media_urls.storage_prefix.…, add_extension(), add_target(), _booking_screen_ids() (+54 more)

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

### Community 29 - "google_device.py"
Cohesion: 0.07
Nodes (48): build_oauth_url(), _claims(), client_id(), client_secret(), exchange_code(), GoogleError, is_configured(), is_web_configured() (+40 more)

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

### Community 34 - "WatchdogAccessibilityService"
Cohesion: 0.22
Nodes (5): bringToFront(), AccessibilityEvent, AccessibilityService, Context, WatchdogAccessibilityService

### Community 35 - "cn"
Cohesion: 0.09
Nodes (45): ContentPage(), isSupported(), QueuedUpload, stripExtension(), GroupsPage(), accountLinks, primaryLinks, toolLinks (+37 more)

### Community 36 - "test_alerting.py"
Cohesion: 0.07
Nodes (71): AlertCondition, _as_utc(), evaluate_all(), evaluate_content(), evaluate_placement(), evaluate_screen(), is_scheduled_off(), _minutes() (+63 more)

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

### Community 50 - "delete"
Cohesion: 0.13
Nodes (26): _client(), delete(), fetch_to(), is_remote(), Path, Reading and writing media wherever it happens to live. The transcoder needs a…, Remove a stored object. Best effort -- a missing object is not an error. Local…, The backend-relative key inside a stored location. Both schemes carry the same… (+18 more)

### Community 51 - "_post"
Cohesion: 0.08
Nodes (35): Any, get_redis(), _pool_for_current_loop(), _post(), Form-post to Google and return (status, parsed body). A 4xx is returned rather…, health_check(), Session, Liveness, plus WHICH database is actually behind it. This used to answer… (+27 more)

### Community 53 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 72 - ".onCreate"
Cohesion: 0.29
Nodes (13): BrandedMessage(), GoogleLogo(), GoogleSignInScreen(), Bundle, Modifier, PairingScreen(), PinPromptScreen(), secondaryButtonColors() (+5 more)

### Community 74 - "storage_prefix"
Cohesion: 0.14
Nodes (20): Safe, alphanumeric bucket key prefix for an organization., storage_prefix(), FakeOrg, FakeUser, Tenant storage folders are named, unique and stable: python…, Local disk and R2 must file a capture under the same key, or the folder layout…, Stands in for models.Organization; owner_email is a property over .users., Consistent org-{id} prefix for Cloudflare R2 compatibility. (+12 more)

### Community 75 - "model_validator"
Cohesion: 0.15
Nodes (7): MediaRenditionResponse, PlacementCreate, PlaylistItemBase, PlaylistItemCreate, PlaylistItemResponse, PlaylistUpdate, model_validator

### Community 76 - "test_media_worker.py"
Cohesion: 0.25
Nodes (14): skipif, cleanup_tempdir(), _do_not_process_on_upload(), fixture, Path, Test for media worker and ffmpeg pipeline, Stop the upload from transcoding, so only the explicit worker run below does.…, DISCARD_SOURCE_AFTER_TRANSCODE removes the upload and promotes the master. This… (+6 more)

### Community 80 - "OLRAC Signage — 80-TV Rollout Deployment Guide"
Cohesion: 0.10
Nodes (18): 1. Server Environment Setup, 2. Storage Configuration, 3. Start the Stack, 4. Database Migration, 5. Create the Platform Owner, 6. TV Enrollment & Provisioning, 7. Watchdog Setup (Crucial for Budget TVs), Build the Watchdog (+10 more)

### Community 81 - "PlayerScreen.kt"
Cohesion: 0.21
Nodes (15): android, awaitPlayerReady(), clearPlayCheckpoint(), DualSurfacePlayer(), com, ExoPlayer, Modifier, PlaybackSurface() (+7 more)

### Community 83 - "PlayerSupervisor"
Cohesion: 0.16
Nodes (8): ExoPlayer, Job, PlaybackException, onPlayerError(), PlayerSupervisor, Context, ExoPlayer, PlayerSupervisorTest

### Community 84 - "parse"
Cohesion: 0.08
Nodes (44): _expand(), geocode(), _is_error_page(), MapsLinkError, _name_from(), _name_from_search(), parse(), Turn a shared Google Maps link into coordinates. This exists so setting a… (+36 more)

### Community 85 - "P9 — Zero-touch provisioning for 80+ TVs (no ADB)"
Cohesion: 0.20
Nodes (9): 1. Make the app a working Device Policy Controller, 2. Silent updates (finishes P7), 3. Generate the provisioning QR, 4. Auto-enrol on first boot, 5. Retire the accessibility watchdog on provisioned devices, Definition of done, Deployment paths, in order of preference, P9 — Zero-touch provisioning for 80+ TVs (no ADB) (+1 more)

### Community 89 - "send"
Cohesion: 0.27
Nodes (11): _describe_missing(), is_configured(), MailNotConfigured, RuntimeError, Sending mail, behind a single switch. There was no mail path in this codebase…, Raised instead of silently discarding a message nobody could have received., The From address, falling back to the login when only that is set., Deliver one message. Raises rather than returning False, so a caller cannot… (+3 more)

### Community 90 - "Player"
Cohesion: 0.25
Nodes (5): Player, DecoderSnapshot, Player, PlaybackException, Player

### Community 91 - "AppDatabase"
Cohesion: 0.29
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
Cohesion: 0.15
Nodes (32): export_campaign_report(), get_campaign_info(), get_campaign_stats(), get_campaign_timeseries(), get_media_report(), list_campaigns(), get, Session (+24 more)

### Community 99 - "Part B — Operations home page"
Cohesion: 0.12
Nodes (16): Backend, Dashboard, Definition of done, Definition of done, Every panel below uses data that already exists, Layout, Order of work, P10 — Display rotation, and an operations home page (+8 more)

### Community 100 - "test_booking_report.py"
Cohesion: 0.23
Nodes (10): pages_of(), A client report must count that client's window and that client's screens.…, rollup(), auth(), check(), Super Admin boundary and the auth holes it closed: python…, One platform operator, and one ordinary tenant owner in a separate organisation., run() (+2 more)

### Community 101 - "screen-map.tsx"
Cohesion: 0.16
Nodes (12): MapPoint, TILES, listeners, loadSdk(), MAPS_KEY, MapsWindow, publish(), serverSnapshot() (+4 more)

### Community 102 - "LaunchState"
Cohesion: 0.29
Nodes (8): CheckingLocalState, GoogleSignIn, LaunchState, LaunchStateResolver, Pairing, Playing, RegistrationSnapshot, SignIn

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

### Community 114 - "get_payment_provider"
Cohesion: 0.30
Nodes (6): CheckoutSession, get_payment_provider(), MockPaymentProvider, PaymentProvider, RazorpayProvider, Protocol

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
Cohesion: 0.12
Nodes (26): AdminLayout(), navItems, AccountPage(), BillingPage(), percent(), BrandingPage(), LOGO_TYPES, ClientsPage() (+18 more)

### Community 130 - "ScreenshotManager"
Cohesion: 0.39
Nodes (4): Activity, ScreenshotManager, Bitmap, WeakReference

### Community 131 - "cleanup_orphans.py"
Cohesion: 0.43
Nodes (6): find_orphans(), main(), Path, Find upload files that no database row points at. Reports by default and…, Every upload path any row still points at, relative to the uploads root., referenced_paths()

### Community 132 - "create_access_token"
Cohesion: 0.14
Nodes (18): create_access_token(), capture_screenshot(), main(), P6 realtime checks: python tests/test_p6_websockets.py Covers hierarchical…, /api/ws/dashboard/ws must reach the dashboard handler, not the device one. Both…, Push must never be the only path. The spec is explicit: if the socket is down…, _redis_available(), run() (+10 more)

### Community 137 - "ApiClient"
Cohesion: 0.38
Nodes (3): ApiClient, Context, okhttp3

### Community 139 - "booking_report.py"
Cohesion: 0.07
Nodes (43): api_key(), _choose_zoom(), fetch_static_map(), google_configured(), is_enabled(), _project(), Map imagery for reports, behind a single switch. Everything map-related…, The closest zoom that still fits every pin, with a margin so none sits on the… (+35 more)

### Community 140 - "utcnow"
Cohesion: 0.16
Nodes (14): datetime, Return a timezone-aware UTC timestamp., utcnow(), auth_header(), main(), TestClient, Runnable backend parity check: python tests/test_feature_parity.py, run() (+6 more)

### Community 143 - "content/[id]/page.tsx"
Cohesion: 0.09
Nodes (32): Alert, AlertsPage(), buildAlerts(), hoursSince(), Severity, AdDetailPage(), FileManagementPage(), FileSort (+24 more)

### Community 144 - "test_rollout_policy.py"
Cohesion: 0.24
Nodes (15): apply_update_status(), Point a screen at a build, clearing any state from the previous attempt.…, Fold one device-reported update result into `screen`. Returns a short human-…, repin(), Staged-rollout decisions — pure logic, no database, no device. Run directly:…, screen(), test_failures_must_be_consecutive(), test_in_flight_states_are_recorded_without_judgement() (+7 more)

### Community 145 - "branding.py"
Cohesion: 0.30
Nodes (11): get_branding(), _organization(), get, put, UploadFile, How a tenant's own brand appears on the report they give their client. The…, Put the tenant's mark in their own storage folder. Through media_storage.store…, remove_logo() (+3 more)

### Community 148 - "screens.py"
Cohesion: 0.06
Nodes (71): AppRelease, get_secret_key(), verify_password(), as_aware_utc(), auth_device(), auth_methods(), batch_upload_play_logs(), bind_screen_to_org() (+63 more)

### Community 149 - "redacted_validation_error"
Cohesion: 0.25
Nodes (8): login_page(), get, Request, read_root(), _redact(), redacted_validation_error(), exception_handler, RequestValidationError

### Community 152 - "PlayEndReason"
Cohesion: 0.22
Nodes (6): PlayCompletion, PlayEndReason, FAILED, INTERRUPTED, PLAYED_TO_END, SKIPPED

### Community 155 - "theme-toggle.tsx"
Cohesion: 0.83
Nodes (3): subscribe(), ThemeToggle(), useHydrated()

### Community 156 - "users.py"
Cohesion: 0.31
Nodes (10): active_owner_count(), create_user(), delete_user(), deny_platform_account(), list_users(), get, put, User (+2 more)

### Community 166 - "env.py"
Cohesion: 0.40
Nodes (4): Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 176 - "worker.py"
Cohesion: 0.12
Nodes (19): MediaRendition, aggregate_play_logs_sync(), prune_finished_bookings(), prune_play_log_rollups(), prune_play_logs(), prune_screenshots(), _publish_alert(), Notice what is wrong with the fleet, and what has stopped being wrong. Runs… (+11 more)

### Community 177 - "Organization"
Cohesion: 0.10
Nodes (44): get_db(), Content, EnrollmentToken, Organization, Playlist, PlaylistItem, Exposed so UserResponse can show the tenant by name instead of a bare id., Screen (+36 more)

### Community 178 - "test_reinstall_reconnect.py"
Cohesion: 0.30
Nodes (13): check(), dashboard_token(), fleet(), One account on the TV and the dashboard, and a screen that survives a…, What the player sends when the installer types their account on the TV., What the player sends on every cold start, before it knows anything., A wipe on a panel whose serial is unreadable CANNOT be auto-recovered. Pinned…, A caller holding only the device id must not be handed a device secret.… (+5 more)

### Community 180 - "content.py"
Cohesion: 0.21
Nodes (16): delete_content(), generate_video_thumbnail(), get_all_content(), get_s3_client(), public_upload_url(), get, put, UploadFile (+8 more)

### Community 181 - "process_media_sync"
Cohesion: 0.50
Nodes (5): compute_sha256(), probe_file(), process_media(), process_media_sync(), run_command_sync()

### Community 184 - "test_google_signin.py"
Cohesion: 0.24
Nodes (10): approved(), _database_url(), poll(), Signing a TV in with a Google account: who it lets in, and who it must not.…, Postgres when a server is there, SQLite otherwise -- as test_release_rollout…, Point the module's two network calls at canned answers., run(), setup_db() (+2 more)

### Community 185 - "_restore_process_globals"
Cohesion: 0.40
Nodes (5): fixture, A fake S3, with the environment the code reads to decide it is enabled., Undo every module-level and environment mutation this file makes. `local_mode`…, _restore_process_globals(), s3()

### Community 189 - "playlist-builder.tsx"
Cohesion: 0.11
Nodes (40): exportFormats, asDate(), CampaignsPage(), getPlacementState(), rupees(), targetLabels, BLANK, roleDescription (+32 more)

### Community 192 - "routers/billing.py"
Cohesion: 0.21
Nodes (15): ensure_billing_catalog(), plan_features(), Plan, Session, billing_summary(), list_plans(), datetime, get (+7 more)

### Community 193 - "client_key"
Cohesion: 0.67
Nodes (3): client_key(), Request, Who to count this request against. slowapi's get_remote_address returns…

### Community 194 - "GoogleDevicePollResponse"
Cohesion: 0.33
Nodes (4): GoogleDevicePollResponse, Where the approval has got to. `slow_down` is passed through rather than…, Deliberately narrow: /screens/register is unauthenticated, so it must not reuse…, RegisterResponse

### Community 195 - "groups.py"
Cohesion: 0.33
Nodes (12): assign_group_playlist(), create_group(), delete_group(), list_groups(), get, put, Reject a parent that is not ours, is the group itself, or would close a loop.…, serialize_group() (+4 more)

### Community 198 - "create_checkout"
Cohesion: 0.67
Nodes (3): create_checkout(), CheckoutRequest, CheckoutResponse

### Community 199 - "acknowledge_alert"
Cohesion: 0.25
Nodes (9): Alert, acknowledge_alert(), alert_summary(), list_alerts(), get, Open alerts, newest first. Resolved ones only when asked for. The default is…, Mark an alert as picked up, without claiming the underlying fault is fixed.…, Counts for the navigation badge, so the header does not fetch the whole list. (+1 more)

## Knowledge Gaps
- **318 isolated node(s):** `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END`, `SKIPPED`, `FAILED` (+313 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **50 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TenantScope` connect `TenantScope` to `routers/billing.py`, `HTTPException`, `groups.py`, `create_checkout`, `models.py`, `acknowledge_alert`, `branding.py`, `tenancy.py`, `_post`, `content.py`, `screens.py`, `resolve_media_url`, `Organization`, `.query`, `admin.py`, `users.py`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Why does `parse()` connect `parse` to `screens.py`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Why does `build_pdf()` connect `booking_report.py` to `TenantScope`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Are the 84 inferred relationships involving `HTTPException` (e.g. with `health_check()` and `approve_tenant()`) actually correct?**
  _`HTTPException` has 84 INFERRED edges - model-reasoned connections that need verification._
- **What connects `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END` to the rest of the system?**
  _318 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `schemas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08140610545790934 - nodes in this community are weakly interconnected._
- **Should `ApiService.kt` be split into smaller, more focused modules?**
  _Cohesion score 0.10084033613445378 - nodes in this community are weakly interconnected._