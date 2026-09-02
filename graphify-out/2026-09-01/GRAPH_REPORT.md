# Graph Report - OLRAC SIGNAGE  (2026-09-01)

## Corpus Check
- 323 files · ~361,831 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2690 nodes · 6342 edges · 198 communities (153 shown, 45 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 222 edges (avg confidence: 0.78)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7a60dd2a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_tv_deep_link.py
- schemas.py
- PlaylistDao
- ApiService.kt
- MainActivity
- cn
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
- clients.py
- worker.py
- main.py
- test_signup_lifecycle.py
- dependencies
- devDependencies
- placements.py
- OLRAC Signage
- TransitionType
- admin.py
- app/layout.tsx
- websockets.py
- StorageManagerTest
- conftest.py
- ProofOfPlayWorker.kt
- scripts
- WatchdogAccessibilityService
- content/page.tsx
- test_alerting.py
- OLRAC Signage — Build Goal & Agent Work Order
- OLRAC Watchdog — build and TV setup
- team/page.tsx
- BootReceiver
- InstallReceiver
- ApiClientTest
- preflight.py
- SyncBackoffPolicy
- compute
- HeartbeatWorker
- LaunchStateResolverTest
- TransitionSpecResolverTest
- redacted_validation_error
- _restore_process_globals
- _post
- SyncBackoffPolicyTest
- gradlew
- .onCreate
- content.py
- model_validator
- test_media_worker.py
- eslint.config.mjs
- next.config.ts
- DeviceState
- OLRAC Signage — 80-TV Rollout Deployment Guide
- PlaylistItemEntity
- google_device_start
- content/[id]/page.tsx
- parse
- P9 — Zero-touch provisioning for 80+ TVs (no ADB)
- postcss.config.mjs
- backup_db.sh
- validation_script.sh
- test_google_signin.py
- Player
- AppDatabase
- P8 — Per-TV capability detection and rendition selection
- Tests
- PlayerViewModel
- utcnow
- ScheduleEvaluatorTest
- DeviceOwnerManagerTest
- HTTPException
- Part B — Operations home page
- cleanup_orphans.py
- screen-map.tsx
- LaunchState
- test_quotas.py
- test_role_separation.py
- frontend/README.md
- Google Maps setup
- ContentResponse
- rules/graphify.md
- workflows/graphify.md
- Deploying to Render + Cloudflare (or Vercel)
- routers/billing.py
- AGENTS.md
- lucide-react
- check-maps-keys.py
- .downloadAndInstallUpdate
- SignageDeviceAdminReceiver
- PlayEventDao
- select_rendition
- start-dev.ps1
- useAuthStore
- env.py
- UtcDateTime
- create_access_token
- provision-tv.sh
- build.sh
- ApiClient
- booking_report.py
- google_device_poll
- resolve_location_link
- playlist-builder.tsx
- test_rollout_policy.py
- branding.py
- MaintenanceGesture
- recharts
- screens.py
- test_play_log_attribution.py
- PlayCompletionTest
- check_r2.py
- PlayEndReason
- UpdateGateTest
- BrandingUpdate
- theme-toggle.tsx
- GoogleWebSignInRequest
- UpdateGate
- a1b4e7c92f38_play_log_campaign_attribution.py
- run
- ScreenBase
- react
- tw-animate-css
- @types/leaflet
- analytics.py
- Organization
- test_reinstall_reconnect.py
- ClientBase
- TenantPlanBase
- test_platform_admin.py
- shadcn
- emergency/page.tsx
- @dnd-kit/core
- TenantScope
- e2e_test.py
- js-sha256
- qrcode.react
- tailwind-merge
- @tanstack/react-query
- ExtensionCreate
- leaflet
- next

## God Nodes (most connected - your core abstractions)
1. `TenantScope` - 151 edges
2. `cn()` - 74 edges
3. `utcnow()` - 61 edges
4. `get_password_hash()` - 56 edges
5. `_post()` - 53 edges
6. `Organization` - 51 edges
7. `useAuthStore` - 50 edges
8. `User` - 43 edges
9. `create_access_token()` - 42 edges
10. `delete()` - 36 edges

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

## Communities (198 total, 45 thin omitted)

### Community 0 - "test_tv_deep_link.py"
Cohesion: 0.16
Nodes (16): _android_intent_url(), The TV's Custom Tab landing page, which then hands back to the player app.…, Rewrite an "olrac://" deep link into the intent: form a browser will actually…, _tv_result_page(), HTMLResponse, The TV hand-back link must be openable by a browser: python…, The whole bug in one assertion: a raw custom scheme is what Chrome rejects., No APK change: the intent's data must still be the olrac:// URL already… (+8 more)

### Community 1 - "schemas.py"
Cohesion: 0.07
Nodes (48): AlertResponse, AlertSummaryResponse, AppReleasePatch, BillingSummaryResponse, BrandingResponse, CheckoutRequest, CheckoutResponse, ClientUpdate (+40 more)

### Community 3 - "ApiService.kt"
Cohesion: 0.10
Nodes (22): ApiService, AuthMethodsResponse, ContentDto, DeviceAuthRequest, DeviceTokenResponse, EnrollResponse, GoogleOAuthUrlResponse, GooglePollResponse (+14 more)

### Community 4 - "MainActivity"
Cohesion: 0.15
Nodes (6): RegistrationSnapshot, Intent, MainActivity, GooglePollRequest, ComponentActivity, KeyEvent

### Community 5 - "cn"
Cohesion: 0.11
Nodes (30): AssignTarget, looksLikeLink(), Place, PlaceSearch(), FIT_MODES, ORIENTATIONS, ScreenSettingsDialog(), splitTags() (+22 more)

### Community 6 - "PlaybackService"
Cohesion: 0.06
Nodes (22): ConnectivityWatcher, Response, WebSocket, RealtimeClient, WebSocketListener, Context, Intent, Job (+14 more)

### Community 7 - "models.py"
Cohesion: 0.11
Nodes (26): AdPlacementExtension, AdPlacementTarget, Alert, Campaign, Client, EmergencyBroadcast, Plan, PlayLog (+18 more)

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
Cohesion: 0.12
Nodes (14): AppReleaseCreate, AppReleaseResponse, HeartbeatRequest, PasswordChange, PlaylistItemUpdate, Partial screen update: only the fields actually present are written. The PUT…, Each day maps to exactly [start, end] as HH:MM. Validated here rather than in…, ScheduleBase (+6 more)

### Community 13 - "test_screen_approval.py"
Cohesion: 0.26
Nodes (11): auth_header(), Screen pairing is instant: python tests/test_screen_approval.py This file used…, sign_in(), test_a_secret_does_not_authenticate_a_different_screen(), test_a_signed_in_screen_syncs_straight_away(), test_enrolment_token_admits_immediately(), test_pairing_admits_immediately(), test_re_signing_in_keeps_the_screen_admitted() (+3 more)

### Community 14 - "api.ts"
Cohesion: 0.04
Nodes (72): AdminApprovalsPage(), AdminPackagesPage(), blank, AdminTenantDetailPage(), Tab, AdminTenantsPage(), Accent, accents (+64 more)

### Community 15 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 16 - "OLRAC Signage — Work Order for Antigravity (Gemini Pro)"
Cohesion: 0.08
Nodes (23): 0. Ground rules, 1. Device knowledge — the most important section, 2. What already exists and is verified, 3. Gap analysis — what the new goal needs, 4. Phases, 5. Infrastructure, 6. Regression suite — run after every phase, 7. Definition of done for the whole programme (+15 more)

### Community 17 - "PlaybackTelemetry"
Cohesion: 0.08
Nodes (17): ExoPlayer, Job, PlaybackException, onPlayerError(), PlayerSupervisor, HeartbeatReporter, Context, PlaybackSnapshot (+9 more)

### Community 18 - "clients.py"
Cohesion: 0.24
Nodes (13): create_client(), delete_client(), get_client(), list_clients(), next_client_code(), Client, get, put (+5 more)

### Community 19 - "worker.py"
Cohesion: 0.11
Nodes (18): MediaRendition, probe_file(), prune_finished_bookings(), prune_play_log_rollups(), prune_play_logs(), prune_screenshots(), _publish_alert(), Notice what is wrong with the fleet, and what has stopped being wrong. Runs… (+10 more)

### Community 20 - "main.py"
Cohesion: 0.07
Nodes (31): _pool_for_current_loop(), _ensure_schema(), lifespan(), Whether this API process should also run the arq worker. Off by default:…, Build the schema on a brand-new database, and stamp it so Alembic can take…, _run_worker_in_process(), ensure_initial_owner(), get_or_create_default_organization() (+23 more)

### Community 21 - "test_signup_lifecycle.py"
Cohesion: 0.26
Nodes (11): ensure_screen_quota(), Reject the caller when the organisation is already at its screen limit. Two…, check(), hdr(), promote_platform_operator(), A company from signup to paying customer: python tests/test_signup_lifecycle.py…, Stand in for Google's token endpoint. Only the exchange is replaced. Everything…, The bootstrap account is created as an ordinary owner; make it the operator.… (+3 more)

### Community 22 - "dependencies"
Cohesion: 0.10
Nodes (21): @base-ui/react, class-variance-authority, clsx, @dnd-kit/sortable, @dnd-kit/utilities, dependencies, @base-ui/react, class-variance-authority (+13 more)

### Community 23 - "devDependencies"
Cohesion: 0.09
Nodes (23): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, @opennextjs/cloudflare, tailwindcss, @tailwindcss/postcss (+15 more)

### Community 24 - "placements.py"
Cohesion: 0.06
Nodes (70): _describe_missing(), is_configured(), MailNotConfigured, RuntimeError, Sending mail, behind a single switch. There was no mail path in this codebase…, Raised instead of silently discarding a message nobody could have received., The From address, falling back to the login when only that is set., Deliver one message. Raises rather than returning False, so a caller cannot… (+62 more)

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

### Community 29 - "websockets.py"
Cohesion: 0.06
Nodes (56): build_oauth_url(), _claims(), client_id(), client_secret(), exchange_code(), GoogleError, is_configured(), is_web_configured() (+48 more)

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

### Community 35 - "content/page.tsx"
Cohesion: 0.12
Nodes (30): ContentPage(), isSupported(), QueuedUpload, stripExtension(), GroupsPage(), accountLinks, primaryLinks, toolLinks (+22 more)

### Community 36 - "test_alerting.py"
Cohesion: 0.07
Nodes (71): AlertCondition, _as_utc(), evaluate_all(), evaluate_content(), evaluate_placement(), evaluate_screen(), is_scheduled_off(), _minutes() (+63 more)

### Community 37 - "OLRAC Signage — Build Goal & Agent Work Order"
Cohesion: 0.12
Nodes (15): 10. Phase P7 — Remote player updates (R9), 11. Regression suite — run after every phase, 12. Definition of done, 13. Rules for the implementing agent, 1. Product requirements (the contract), 1a. Verified status — audit of 2026-08-07, 2. Current state — audit (original, pre-implementation), 3. Phase P0 — Offline-first playback (fix D1) (+7 more)

### Community 38 - "OLRAC Watchdog — build and TV setup"
Cohesion: 0.22
Nodes (8): Build, Checking a TV, How recovery actually works, Known issue in the player (not the watchdog), OLRAC Watchdog — build and TV setup, Provision a TV, Retargeting, The three things that silently break this

### Community 39 - "team/page.tsx"
Cohesion: 0.18
Nodes (29): FileSort, SORTS, BLANK, roleDescription, TENANT_ROLES, EmailReportModal(), EmailReportModalProps, ALL_DAY (+21 more)

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

### Community 49 - "redacted_validation_error"
Cohesion: 0.25
Nodes (8): login_page(), get, Request, read_root(), _redact(), redacted_validation_error(), exception_handler, RequestValidationError

### Community 50 - "_restore_process_globals"
Cohesion: 0.40
Nodes (5): fixture, A fake S3, with the environment the code reads to decide it is enabled., Undo every module-level and environment mutation this file makes. `local_mode`…, _restore_process_globals(), s3()

### Community 51 - "_post"
Cohesion: 0.20
Nodes (12): _post(), Form-post to Google and return (status, parsed body). A 4xx is returned rather…, create_checkout(), Request, razorpay_webhook(), BroadcastRequest, cancel_emergency_broadcast(), get_active_broadcasts() (+4 more)

### Community 53 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 72 - ".onCreate"
Cohesion: 0.32
Nodes (13): BrandedMessage(), GoogleLogo(), GoogleSignInScreen(), Bundle, Modifier, PairingScreen(), PinPromptScreen(), secondaryButtonColors() (+5 more)

### Community 74 - "content.py"
Cohesion: 0.05
Nodes (80): _client(), delete(), fetch_to(), is_remote(), Path, Reading and writing media wherever it happens to live. The transcoder needs a…, Remove a stored object. Best effort -- a missing object is not an error. Local…, The backend-relative key inside a stored location. Both schemes carry the same… (+72 more)

### Community 75 - "model_validator"
Cohesion: 0.15
Nodes (7): MediaRenditionResponse, PlacementCreate, PlaylistItemBase, PlaylistItemCreate, PlaylistItemResponse, PlaylistUpdate, model_validator

### Community 76 - "test_media_worker.py"
Cohesion: 0.25
Nodes (14): skipif, cleanup_tempdir(), _do_not_process_on_upload(), fixture, Path, Test for media worker and ffmpeg pipeline, Stop the upload from transcoding, so only the explicit worker run below does.…, DISCARD_SOURCE_AFTER_TRANSCODE removes the upload and promotes the master. This… (+6 more)

### Community 79 - "DeviceState"
Cohesion: 0.15
Nodes (5): DeviceState, Activity, ScreenshotManager, Bitmap, WeakReference

### Community 80 - "OLRAC Signage — 80-TV Rollout Deployment Guide"
Cohesion: 0.10
Nodes (18): 1. Server Environment Setup, 2. Storage Configuration, 3. Start the Stack, 4. Database Migration, 5. Create the Platform Owner, 6. TV Enrollment & Provisioning, 7. Watchdog Setup (Crucial for Budget TVs), Build the Watchdog (+10 more)

### Community 81 - "PlaylistItemEntity"
Cohesion: 0.20
Nodes (15): android, PlaylistItemEntity, clearPlayCheckpoint(), DualSurfacePlayer(), com, ExoPlayer, Modifier, PlaybackSurface() (+7 more)

### Community 82 - "google_device_start"
Cohesion: 0.33
Nodes (6): google_device_start(), Begin a Google sign-in for this TV and hand back the code to put on screen., GoogleDeviceStartRequest, GoogleDeviceStartResponse, A TV asking for a Google code to put on screen., What the TV displays, plus the handle it polls with. `poll_token` is a short-…

### Community 83 - "content/[id]/page.tsx"
Cohesion: 0.19
Nodes (16): asDate(), CampaignsPage(), getPlacementState(), rupees(), EditClientAdModal(), formatRupees(), EmptyState(), dateTime() (+8 more)

### Community 84 - "parse"
Cohesion: 0.08
Nodes (44): _expand(), geocode(), _is_error_page(), MapsLinkError, _name_from(), _name_from_search(), parse(), Turn a shared Google Maps link into coordinates. This exists so setting a… (+36 more)

### Community 85 - "P9 — Zero-touch provisioning for 80+ TVs (no ADB)"
Cohesion: 0.20
Nodes (9): 1. Make the app a working Device Policy Controller, 2. Silent updates (finishes P7), 3. Generate the provisioning QR, 4. Auto-enrol on first boot, 5. Retire the accessibility watchdog on provisioned devices, Definition of done, Deployment paths, in order of preference, P9 — Zero-touch provisioning for 80+ TVs (no ADB) (+1 more)

### Community 89 - "test_google_signin.py"
Cohesion: 0.24
Nodes (10): approved(), _database_url(), poll(), Signing a TV in with a Google account: who it lets in, and who it must not.…, Postgres when a server is there, SQLite otherwise -- as test_release_rollout…, Point the module's two network calls at canned answers., run(), setup_db() (+2 more)

### Community 90 - "Player"
Cohesion: 0.22
Nodes (6): awaitPlayerReady(), Player, DecoderSnapshot, Player, PlaybackException, Player

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

### Community 95 - "utcnow"
Cohesion: 0.09
Nodes (24): get_db(), AppRelease, datetime, Return a timezone-aware UTC timestamp., utcnow(), recover_stuck_processing(), P8 Media Selection checks: python tests/test_media_selection.py, test_media_selection() (+16 more)

### Community 98 - "HTTPException"
Cohesion: 0.21
Nodes (24): assign_group_playlist(), add_item_to_playlist(), bump_playlist(), create_playlist(), delete_playlist(), get_playlist(), get_playlists(), get (+16 more)

### Community 99 - "Part B — Operations home page"
Cohesion: 0.12
Nodes (16): Backend, Dashboard, Definition of done, Definition of done, Every panel below uses data that already exists, Layout, Order of work, P10 — Display rotation, and an operations home page (+8 more)

### Community 100 - "cleanup_orphans.py"
Cohesion: 0.43
Nodes (6): find_orphans(), main(), Path, Find upload files that no database row points at. Reports by default and…, Every upload path any row still points at, relative to the uploads root., referenced_paths()

### Community 101 - "screen-map.tsx"
Cohesion: 0.16
Nodes (12): MapPoint, TILES, listeners, loadSdk(), MAPS_KEY, MapsWindow, publish(), serverSnapshot() (+4 more)

### Community 102 - "LaunchState"
Cohesion: 0.33
Nodes (7): CheckingLocalState, GoogleSignIn, LaunchState, LaunchStateResolver, Pairing, Playing, SignIn

### Community 106 - "test_quotas.py"
Cohesion: 0.48
Nodes (6): auth_header(), pair_one_screen(), TestClient, Plan-limit enforcement check: python tests/test_quotas.py Covers GOAL.md T6.1…, Register a TV then pair it as the admin. Returns the pair response., run()

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

### Community 114 - "routers/billing.py"
Cohesion: 0.13
Nodes (19): ensure_billing_catalog(), plan_features(), Plan, Session, CheckoutSession, get_payment_provider(), MockPaymentProvider, PaymentProvider (+11 more)

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
Cohesion: 0.12
Nodes (28): Screen, Selects the most appropriate media rendition for a screen based on its hardware…, select_rendition(), normalise(), Resolve the rotation a screen should apply to one playlist item. The player…, Coerce anything to one of 0/90/180/270, defaulting to 0., Degrees the player should rotate this item on this screen., resolve_rotation() (+20 more)

### Community 128 - "useAuthStore"
Cohesion: 0.11
Nodes (29): AdminLayout(), navItems, AccountPage(), BrandingPage(), LOGO_TYPES, ClientsPage(), EmergencyPage(), DashboardLayout() (+21 more)

### Community 130 - "env.py"
Cohesion: 0.40
Nodes (4): Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 131 - "UtcDateTime"
Cohesion: 0.40
Nodes (3): A DateTime that always reads back as timezone-aware UTC. Postgres with…, UtcDateTime, TypeDecorator

### Community 132 - "create_access_token"
Cohesion: 0.17
Nodes (16): ScreenGroup, create_access_token(), capture_screenshot(), main(), P6 realtime checks: python tests/test_p6_websockets.py Covers hierarchical…, /api/ws/dashboard/ws must reach the dashboard handler, not the device one. Both…, Push must never be the only path. The spec is explicit: if the socket is down…, _redis_available() (+8 more)

### Community 137 - "ApiClient"
Cohesion: 0.38
Nodes (3): ApiClient, Context, okhttp3

### Community 139 - "booking_report.py"
Cohesion: 0.07
Nodes (45): api_key(), _choose_zoom(), fetch_static_map(), google_configured(), is_enabled(), _project(), Map imagery for reports, behind a single switch. Everything map-related…, The closest zoom that still fits every pin, with a margin so none sits on the… (+37 more)

### Community 140 - "google_device_poll"
Cohesion: 0.40
Nodes (5): google_device_poll(), Has the installer approved on their phone yet? If so, bind the screen., GoogleDevicePollRequest, GoogleDevicePollResponse, Where the approval has got to. `slow_down` is passed through rather than…

### Community 141 - "resolve_location_link"
Cohesion: 0.40
Nodes (5): Coordinates for a pasted Google Maps link. Deliberately not a Google API call:…, resolve_location_link(), A Google Maps share link, pasted by an operator., ResolveLinkRequest, ResolveLinkResponse

### Community 143 - "playlist-builder.tsx"
Cohesion: 0.10
Nodes (29): AdminReleasesPage(), Alert, AlertsPage(), buildAlerts(), hoursSince(), Severity, AdDetailPage(), FileManagementPage() (+21 more)

### Community 144 - "test_rollout_policy.py"
Cohesion: 0.24
Nodes (15): apply_update_status(), Point a screen at a build, clearing any state from the previous attempt.…, Fold one device-reported update result into `screen`. Returns a short human-…, repin(), Staged-rollout decisions — pure logic, no database, no device. Run directly:…, screen(), test_failures_must_be_consecutive(), test_in_flight_states_are_recorded_without_judgement() (+7 more)

### Community 145 - "branding.py"
Cohesion: 0.30
Nodes (11): get_branding(), _organization(), get, put, UploadFile, How a tenant's own brand appears on the report they give their client. The…, Put the tenant's mark in their own storage folder. Through media_storage.store…, remove_logo() (+3 more)

### Community 148 - "screens.py"
Cohesion: 0.05
Nodes (81): Any, AppRelease, get_redis(), health_check(), Session, Liveness, plus WHICH database is actually behind it. This used to answer…, eligible_for_fallback(), Restrict an AppRelease query to builds that unpinned screens may be offered. (+73 more)

### Community 152 - "PlayEndReason"
Cohesion: 0.22
Nodes (6): PlayCompletion, PlayEndReason, FAILED, INTERRUPTED, PLAYED_TO_END, SKIPPED

### Community 155 - "theme-toggle.tsx"
Cohesion: 0.83
Nodes (3): subscribe(), ThemeToggle(), useHydrated()

### Community 166 - "run"
Cohesion: 0.53
Nodes (5): auth_header(), main(), TestClient, Runnable backend parity check: python tests/test_feature_parity.py, run()

### Community 167 - "ScreenBase"
Cohesion: 0.50
Nodes (3): ScreenBase, ScreenCreate, ScreenResponse

### Community 176 - "analytics.py"
Cohesion: 0.24
Nodes (14): export_campaign_report(), get_campaign_info(), get_campaign_stats(), get_campaign_timeseries(), get_media_report(), list_campaigns(), get, Session (+6 more)

### Community 177 - "Organization"
Cohesion: 0.11
Nodes (41): Content, EnrollmentToken, Organization, Playlist, PlaylistItem, Exposed so UserResponse can show the tenant by name instead of a bare id., Screen, User (+33 more)

### Community 178 - "test_reinstall_reconnect.py"
Cohesion: 0.30
Nodes (13): check(), dashboard_token(), fleet(), One account on the TV and the dashboard, and a screen that survives a…, What the player sends when the installer types their account on the TV., What the player sends on every cold start, before it knows anything., A wipe on a panel whose serial is unreadable CANNOT be auto-recovered. Pinned…, A caller holding only the device id must not be handed a device secret.… (+5 more)

### Community 179 - "ClientBase"
Cohesion: 0.67
Nodes (3): ClientBase, ClientCreate, ClientResponse

### Community 181 - "TenantPlanBase"
Cohesion: 0.67
Nodes (3): TenantPlanBase, TenantPlanCreate, TenantPlanResponse

### Community 184 - "test_platform_admin.py"
Cohesion: 0.21
Nodes (11): client_key(), Request, Who to count this request against. slowapi's get_remote_address returns…, pages_of(), auth(), check(), Super Admin boundary and the auth holes it closed: python…, One platform operator, and one ordinary tenant owner in a separate organisation. (+3 more)

### Community 189 - "emergency/page.tsx"
Cohesion: 0.16
Nodes (16): BillingPage(), percent(), exportFormats, targetLabels, GroupDetailPage(), AssignPlaylistCard(), ErrorState(), AssignScreensDialog() (+8 more)

### Community 195 - "TenantScope"
Cohesion: 0.05
Nodes (69): Alert, OLRAC Signage backend package. Explicit package marker. Without it `backend` is…, Staged player rollout: which build a screen is offered, and when to give up on…, acknowledge_alert(), alert_summary(), list_alerts(), get, Open alerts, newest first. Resolved ones only when asked for. The default is… (+61 more)

## Knowledge Gaps
- **319 isolated node(s):** `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END`, `SKIPPED`, `FAILED` (+314 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **45 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TenantScope` connect `TenantScope` to `HTTPException`, `content.py`, `resolve_location_link`, `analytics.py`, `branding.py`, `routers/billing.py`, `_post`, `clients.py`, `screens.py`, `Organization`, `placements.py`, `admin.py`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Why does `build_pdf()` connect `booking_report.py` to `placements.py`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Why does `get_password_hash()` connect `main.py` to `TenantScope`, `create_access_token`, `run`, `models.py`, `booking_report.py`, `ValueError`, `test_role_separation.py`, `Organization`, `worker.py`, `screens.py`, `test_platform_admin.py`, `test_google_signin.py`, `websockets.py`, `utcnow`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Are the 85 inferred relationships involving `HTTPException` (e.g. with `health_check()` and `approve_tenant()`) actually correct?**
  _`HTTPException` has 85 INFERRED edges - model-reasoned connections that need verification._
- **What connects `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END` to the rest of the system?**
  _319 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `schemas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07482993197278912 - nodes in this community are weakly interconnected._
- **Should `ApiService.kt` be split into smaller, more focused modules?**
  _Cohesion score 0.09682539682539683 - nodes in this community are weakly interconnected._