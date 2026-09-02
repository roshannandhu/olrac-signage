# Graph Report - OLRAC SIGNAGE  (2026-09-02)

## Corpus Check
- 325 files · ~365,242 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2728 nodes · 6426 edges · 208 communities (159 shown, 49 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 227 edges (avg confidence: 0.78)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `fea793e8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_tv_deep_link.py
- schemas.py
- PlaylistItemEntity
- ApiService.kt
- MainActivity
- cn
- PlaybackService
- admin-ui.tsx
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
- media_urls.py
- worker.py
- main.py
- get_password_hash
- dependencies
- devDependencies
- TenantScope
- OLRAC Signage
- TransitionType
- admin.py
- app/layout.tsx
- google_device.py
- R2Presigner
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
- health_check
- test_media_storage.py
- _post
- SyncBackoffPolicyTest
- gradlew
- .onCreate
- FakeOrg
- model_validator
- PlayerSupervisor
- eslint.config.mjs
- next.config.ts
- DeviceState
- OLRAC Signage — 80-TV Rollout Deployment Guide
- PlayerScreen.kt
- GoogleDeviceStartRequest
- analytics.py
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
- database.py
- ScheduleEvaluatorTest
- DeviceOwnerManagerTest
- playlists.py
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
- get_payment_provider
- AGENTS.md
- lucide-react
- check-maps-keys.py
- upload_content
- SignageDeviceAdminReceiver
- PlayEventDao
- select_rendition
- start-dev.ps1
- useAuthStore
- test_media_worker.py
- UtcDateTime
- test_p6_websockets.py
- provision-tv.sh
- build.sh
- ApiClient
- booking_report.py
- ResolveLinkRequest
- screens/[id]/page.tsx
- test_rollout_policy.py
- branding.py
- MaintenanceGesture
- resolve_rotation
- screens.py
- test_release_rollout.py
- PlayCompletionTest
- check_r2.py
- PlayEndReason
- UpdateGateTest
- BrandingUpdate
- theme-toggle.tsx
- HTTPException
- UpdateGate
- a1b4e7c92f38_play_log_campaign_attribution.py
- .query
- send
- react
- tw-animate-css
- @types/leaflet
- GoogleDeviceStartResponse
- models.py
- test_reinstall_reconnect.py
- ClientBase
- resolve_media_url
- TenantPlanBase
- test_booking_report.py
- acknowledge_alert
- shadcn
- playlist-builder.tsx
- @dnd-kit/core
- websockets.py
- User
- _serialize_client
- e2e_test.py
- GoogleWebSignInRequest
- PlacementSplit
- @dnd-kit/sortable
- @dnd-kit/utilities
- next-themes
- ExtensionCreate
- recharts
- leaflet
- @types/qrcode.react
- AlertSummaryResponse
- promote_release
- ScreenSignInRequest

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
- `test_s3_delete()` --calls--> `delete()`  [EXTRACTED]
  tests/test_media_storage.py → backend/media_storage.py
- `run()` --calls--> `is_configured()`  [EXTRACTED]
  tests/test_google_signin.py → backend/google_device.py
- `run()` --calls--> `_claims()`  [EXTRACTED]
  tests/test_google_signin.py → backend/google_device.py
- `test_the_media_route_refuses_to_climb_out_of_the_bucket()` --calls--> `serve_media()`  [EXTRACTED]
  tests/test_storage_prefix.py → backend/main.py
- `test_a_genuine_google_subdomain_is_still_accepted()` --calls--> `parse()`  [EXTRACTED]
  tests/test_maps_link.py → backend/maps_link.py

## Import Cycles
- None detected.

## Communities (208 total, 49 thin omitted)

### Community 0 - "test_tv_deep_link.py"
Cohesion: 0.16
Nodes (16): _android_intent_url(), The TV's Custom Tab landing page, which then hands back to the player app.…, Rewrite an "olrac://" deep link into the intent: form a browser will actually…, _tv_result_page(), HTMLResponse, The TV hand-back link must be openable by a browser: python…, The whole bug in one assertion: a raw custom scheme is what Chrome rejects., No APK change: the intent's data must still be the olrac:// URL already… (+8 more)

### Community 1 - "schemas.py"
Cohesion: 0.08
Nodes (45): AlertResponse, AppVersionResponse, BillingSummaryResponse, BrandingResponse, CheckoutRequest, CheckoutResponse, ClientUpdate, ContentClientAdUpdate (+37 more)

### Community 2 - "PlaylistItemEntity"
Cohesion: 0.24
Nodes (3): PlaylistDao, PlaylistItemEntity, Flow

### Community 3 - "ApiService.kt"
Cohesion: 0.10
Nodes (21): ApiService, AuthMethodsResponse, ContentDto, DeviceAuthRequest, DeviceTokenResponse, EnrollResponse, GoogleOAuthUrlResponse, GooglePollResponse (+13 more)

### Community 4 - "MainActivity"
Cohesion: 0.14
Nodes (7): RegistrationSnapshot, Intent, MainActivity, GooglePollRequest, SignInRequest, ComponentActivity, KeyEvent

### Community 5 - "cn"
Cohesion: 0.12
Nodes (23): exportFormats, StatusIndicator(), CardAction(), CardDescription(), CardFooter(), CardHeader(), CardTitle(), DialogOverlay() (+15 more)

### Community 6 - "PlaybackService"
Cohesion: 0.06
Nodes (22): ConnectivityWatcher, Response, WebSocket, RealtimeClient, WebSocketListener, Context, Intent, Job (+14 more)

### Community 7 - "admin-ui.tsx"
Cohesion: 0.15
Nodes (18): AdminApprovalsPage(), AdminPackagesPage(), blank, AdminTenantDetailPage(), Tab, AdminTenantsPage(), Accent, accents (+10 more)

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
Cohesion: 0.06
Nodes (49): AdminReleasesPage(), EditClientAdModalProps, MediaThumbnail(), API_HOST, ApiError, authFetch(), configuredUrl, fetchWithAuth() (+41 more)

### Community 15 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 16 - "OLRAC Signage — Work Order for Antigravity (Gemini Pro)"
Cohesion: 0.08
Nodes (23): 0. Ground rules, 1. Device knowledge — the most important section, 2. What already exists and is verified, 3. Gap analysis — what the new goal needs, 4. Phases, 5. Infrastructure, 6. Regression suite — run after every phase, 7. Definition of done for the whole programme (+15 more)

### Community 17 - "PlaybackTelemetry"
Cohesion: 0.15
Nodes (9): HeartbeatReporter, Context, PlaybackSnapshot, PlaybackTelemetry, enqueue(), Context, CoroutineWorker, Result (+1 more)

### Community 18 - "media_urls.py"
Cohesion: 0.09
Nodes (34): Stable URL for a stored object; signs the real one fresh on every request. This…, serve_media(), _client(), fetch_to(), is_remote(), Path, Reading and writing media wherever it happens to live. The transcoder needs a…, Persist `local_path` under `key` and return the location to save on the row.… (+26 more)

### Community 19 - "worker.py"
Cohesion: 0.12
Nodes (22): Any, Safe, alphanumeric bucket key prefix for an organization., storage_prefix(), broadcast_ws_event(), Broadcast an event to both in-memory sockets and Redis pubsub., compute_sha256(), probe_file(), process_media() (+14 more)

### Community 20 - "main.py"
Cohesion: 0.08
Nodes (43): ensure_billing_catalog(), plan_features(), Plan, Session, OLRAC Signage backend package. Explicit package marker. Without it `backend` is…, _ensure_schema(), lifespan(), Request (+35 more)

### Community 21 - "get_password_hash"
Cohesion: 0.07
Nodes (38): auth_methods(), change_own_password(), ensure_initial_owner(), get_current_user(), get_current_user_ws(), get_or_create_default_organization(), get_password_hash(), get_secret_key() (+30 more)

### Community 22 - "dependencies"
Cohesion: 0.10
Nodes (21): @base-ui/react, class-variance-authority, clsx, dependencies, @base-ui/react, class-variance-authority, clsx, next (+13 more)

### Community 23 - "devDependencies"
Cohesion: 0.09
Nodes (23): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, @opennextjs/cloudflare, tailwindcss, @tailwindcss/postcss (+15 more)

### Community 24 - "TenantScope"
Cohesion: 0.08
Nodes (65): AdPlacement, AdPlacementTarget, An advert sold to a client: what runs, for whom, when, and for how much.…, One place a booked advert runs, and the playlist item it put there. Exactly one…, Address that names this tenant's storage folder. See media_urls.storage_prefix.…, update_content_client_ad(), add_extension(), add_target() (+57 more)

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
Cohesion: 0.10
Nodes (31): build_oauth_url(), _claims(), client_id(), client_secret(), exchange_code(), GoogleError, is_configured(), is_web_configured() (+23 more)

### Community 30 - "R2Presigner"
Cohesion: 0.11
Nodes (10): AppVersionDto, R2Presigner, OkHttpClient, StorageManager, Context, OkHttpClient, UpdateManager, Context (+2 more)

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
Cohesion: 0.10
Nodes (36): ContentPage(), isSupported(), QueuedUpload, stripExtension(), FileSort, SORTS, GroupsPage(), accountLinks (+28 more)

### Community 36 - "test_alerting.py"
Cohesion: 0.07
Nodes (72): AlertCondition, _as_utc(), evaluate_all(), evaluate_content(), evaluate_placement(), evaluate_screen(), is_scheduled_off(), _minutes() (+64 more)

### Community 37 - "OLRAC Signage — Build Goal & Agent Work Order"
Cohesion: 0.12
Nodes (15): 10. Phase P7 — Remote player updates (R9), 11. Regression suite — run after every phase, 12. Definition of done, 13. Rules for the implementing agent, 1. Product requirements (the contract), 1a. Verified status — audit of 2026-08-07, 2. Current state — audit (original, pre-implementation), 3. Phase P0 — Offline-first playback (fix D1) (+7 more)

### Community 38 - "OLRAC Watchdog — build and TV setup"
Cohesion: 0.22
Nodes (8): Build, Checking a TV, How recovery actually works, Known issue in the player (not the watchdog), OLRAC Watchdog — build and TV setup, Provision a TV, Retargeting, The three things that silently break this

### Community 39 - "team/page.tsx"
Cohesion: 0.16
Nodes (27): BillingPage(), percent(), BLANK, roleDescription, TENANT_ROLES, EmailReportModal(), EmailReportModalProps, ErrorState() (+19 more)

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

### Community 49 - "health_check"
Cohesion: 0.40
Nodes (5): health_check(), get, Session, Liveness, plus WHICH database is actually behind it. This used to answer…, read_root()

### Community 50 - "test_media_storage.py"
Cohesion: 0.11
Nodes (23): The backend-relative key inside a stored location. Both schemes carry the same…, storage_key_for(), local_mode(), fixture, Media storage: fetch and store, on local disk and on object storage. The…, A fake S3, with the environment the code reads to decide it is enabled., So _fetch_image can tell "not mine, try HTTP" from "mine, and missing"., The whole point: a report renders its images with the network unavailable. (+15 more)

### Community 51 - "_post"
Cohesion: 0.12
Nodes (18): _post(), Form-post to Google and return (status, parsed body). A 4xx is returned rather…, create_checkout(), BroadcastRequest, cancel_emergency_broadcast(), get_active_broadcasts(), BaseModel, get (+10 more)

### Community 53 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 72 - ".onCreate"
Cohesion: 0.32
Nodes (13): BrandedMessage(), GoogleLogo(), GoogleSignInScreen(), Bundle, Modifier, PairingScreen(), PinPromptScreen(), secondaryButtonColors() (+5 more)

### Community 74 - "FakeOrg"
Cohesion: 0.16
Nodes (13): FakeOrg, FakeUser, Stands in for models.Organization; owner_email is a property over .users., Consistent org-{id} prefix for Cloudflare R2 compatibility., Two organisations must never share a folder, or their media mixes in the bucket., A workspace prefix is stably based on organisation ID., seed_admin creates an owner with no email, and an upload must still work., A key containing "/" would invent a folder; one with spaces breaks URLs. The… (+5 more)

### Community 75 - "model_validator"
Cohesion: 0.15
Nodes (7): MediaRenditionResponse, PlacementCreate, PlaylistItemBase, PlaylistItemCreate, PlaylistItemResponse, PlaylistUpdate, model_validator

### Community 76 - "PlayerSupervisor"
Cohesion: 0.16
Nodes (8): ExoPlayer, Job, PlaybackException, onPlayerError(), PlayerSupervisor, Context, ExoPlayer, PlayerSupervisorTest

### Community 79 - "DeviceState"
Cohesion: 0.15
Nodes (5): DeviceState, Activity, ScreenshotManager, Bitmap, WeakReference

### Community 80 - "OLRAC Signage — 80-TV Rollout Deployment Guide"
Cohesion: 0.10
Nodes (18): 1. Server Environment Setup, 2. Storage Configuration, 3. Start the Stack, 4. Database Migration, 5. Create the Platform Owner, 6. TV Enrollment & Provisioning, 7. Watchdog Setup (Crucial for Budget TVs), Build the Watchdog (+10 more)

### Community 81 - "PlayerScreen.kt"
Cohesion: 0.21
Nodes (15): android, awaitPlayerReady(), clearPlayCheckpoint(), DualSurfacePlayer(), com, ExoPlayer, Modifier, PlaybackSurface() (+7 more)

### Community 83 - "analytics.py"
Cohesion: 0.20
Nodes (16): Campaign, PlayLog, PlayLogHourlyRollup, export_campaign_report(), get_campaign_info(), get_campaign_stats(), get_campaign_timeseries(), get_media_report() (+8 more)

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

### Community 95 - "database.py"
Cohesion: 0.08
Nodes (19): Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online(), get_db(), fresh_start(), run_test(), auth_header() (+11 more)

### Community 98 - "playlists.py"
Cohesion: 0.27
Nodes (18): add_item_to_playlist(), bump_playlist(), create_playlist(), delete_playlist(), get_playlist(), get_playlists(), get, Playlist (+10 more)

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

### Community 114 - "get_payment_provider"
Cohesion: 0.30
Nodes (6): CheckoutSession, get_payment_provider(), MockPaymentProvider, PaymentProvider, RazorpayProvider, Protocol

### Community 118 - "check-maps-keys.py"
Cohesion: 0.32
Nodes (7): check_server_key(), main(), Path, Check the Google Maps keys and say plainly what is wrong with them. Run this…, Value of `name` in a .env file, or '' when absent - no dependency on dotenv., Ask Static Maps for a real image; its rejection text is the diagnosis., read_env()

### Community 119 - "upload_content"
Cohesion: 0.19
Nodes (13): delete_content(), generate_video_thumbnail(), get_all_content(), get, put, UploadFile, queue_processing(), Hand a video to the transcode worker, ensuring it is processed immediately. In… (+5 more)

### Community 120 - "SignageDeviceAdminReceiver"
Cohesion: 0.33
Nodes (5): EnrollRequest, Context, Intent, SignageDeviceAdminReceiver, DeviceAdminReceiver

### Community 122 - "select_rendition"
Cohesion: 0.22
Nodes (18): Screen, Selects the most appropriate media rendition for a screen based on its hardware…, select_rendition(), Filtering everything out must not fall through to the biggest file we own. When…, test_a_constrained_panel_is_never_handed_the_master(), Rendition selection, against the set the transcoder actually produces.…, Content carrying exactly what the transcoder produces today., real_content() (+10 more)

### Community 128 - "useAuthStore"
Cohesion: 0.13
Nodes (25): AdminLayout(), navItems, AccountPage(), BrandingPage(), LOGO_TYPES, ClientsPage(), EmergencyPage(), GroupDetailPage() (+17 more)

### Community 130 - "test_media_worker.py"
Cohesion: 0.25
Nodes (14): skipif, cleanup_tempdir(), _do_not_process_on_upload(), fixture, Path, Test for media worker and ffmpeg pipeline, Stop the upload from transcoding, so only the explicit worker run below does.…, DISCARD_SOURCE_AFTER_TRANSCODE removes the upload and promotes the master. This… (+6 more)

### Community 131 - "UtcDateTime"
Cohesion: 0.40
Nodes (3): A DateTime that always reads back as timezone-aware UTC. Postgres with…, UtcDateTime, TypeDecorator

### Community 132 - "test_p6_websockets.py"
Cohesion: 0.27
Nodes (11): EmergencyBroadcast, P6 realtime checks: python tests/test_p6_websockets.py Covers hierarchical…, /api/ws/dashboard/ws must reach the dashboard handler, not the device one. Both…, Push must never be the only path. The spec is explicit: if the socket is down…, _redis_available(), run(), setup_db(), test_dashboard_websocket_is_not_shadowed_by_device_route() (+3 more)

### Community 137 - "ApiClient"
Cohesion: 0.38
Nodes (3): ApiClient, Context, okhttp3

### Community 139 - "booking_report.py"
Cohesion: 0.07
Nodes (43): api_key(), _choose_zoom(), fetch_static_map(), google_configured(), is_enabled(), _project(), Map imagery for reports, behind a single switch. Everything map-related…, The closest zoom that still fits every pin, with a margin so none sits on the… (+35 more)

### Community 143 - "screens/[id]/page.tsx"
Cohesion: 0.08
Nodes (40): Alert, AlertsPage(), buildAlerts(), hoursSince(), Severity, asDate(), CampaignsPage(), getPlacementState() (+32 more)

### Community 144 - "test_rollout_policy.py"
Cohesion: 0.18
Nodes (18): apply_update_status(), eligible_for_fallback(), Staged player rollout: which build a screen is offered, and when to give up on…, Point a screen at a build, clearing any state from the previous attempt.…, Restrict an AppRelease query to builds that unpinned screens may be offered., Fold one device-reported update result into `screen`. Returns a short human-…, repin(), Staged-rollout decisions — pure logic, no database, no device. Run directly:… (+10 more)

### Community 145 - "branding.py"
Cohesion: 0.30
Nodes (11): get_branding(), _organization(), get, put, UploadFile, How a tenant's own brand appears on the report they give their client. The…, Put the tenant's mark in their own storage folder. Through media_storage.store…, remove_logo() (+3 more)

### Community 147 - "resolve_rotation"
Cohesion: 0.23
Nodes (12): normalise(), Resolve the rotation a screen should apply to one playlist item. The player…, Coerce anything to one of 0/90/180/270, defaulting to 0., Degrees the player should rotate this item on this screen., resolve_rotation(), Rotation precedence — pure logic, no database, no device. Run directly: python…, A screen mounted portrait with one item deliberately pinned to landscape., test_defaults_when_nothing_is_set() (+4 more)

### Community 148 - "screens.py"
Cohesion: 0.05
Nodes (89): AppRelease, get_redis(), _pool_for_current_loop(), delete(), Remove a stored object. Best effort -- a missing object is not an error. Local…, Return a timezone-aware UTC timestamp., utcnow(), verify_password() (+81 more)

### Community 149 - "test_release_rollout.py"
Cohesion: 0.23
Nodes (11): AppRelease, bearer(), _database_url(), device_headers(), publish(), Player releases: who may publish one, and who it reaches. Covers the defect…, Read the screen straight from the database. There is no GET /api/screens/{id};…, Postgres when a server is there, SQLite otherwise. Production is Postgres and… (+3 more)

### Community 152 - "PlayEndReason"
Cohesion: 0.22
Nodes (6): PlayCompletion, PlayEndReason, FAILED, INTERRUPTED, PLAYED_TO_END, SKIPPED

### Community 155 - "theme-toggle.tsx"
Cohesion: 0.83
Nodes (3): subscribe(), ThemeToggle(), useHydrated()

### Community 156 - "HTTPException"
Cohesion: 0.11
Nodes (33): revoke_token(), assign_group_playlist(), create_group(), delete_group(), list_groups(), get, put, Reject a parent that is not ours, is the group itself, or would close a loop.… (+25 more)

### Community 167 - "send"
Cohesion: 0.27
Nodes (11): _describe_missing(), is_configured(), MailNotConfigured, RuntimeError, Sending mail, behind a single switch. There was no mail path in this codebase…, Raised instead of silently discarding a message nobody could have received., The From address, falling back to the login when only that is set., Deliver one message. Raises rather than returning False, so a caller cannot… (+3 more)

### Community 177 - "models.py"
Cohesion: 0.07
Nodes (49): AdPlacementExtension, Alert, Client, Content, EnrollmentToken, MediaRendition, Organization, Plan (+41 more)

### Community 178 - "test_reinstall_reconnect.py"
Cohesion: 0.30
Nodes (13): check(), dashboard_token(), fleet(), One account on the TV and the dashboard, and a screen that survives a…, What the player sends when the installer types their account on the TV., What the player sends on every cold start, before it knows anything., A wipe on a panel whose serial is unreadable CANNOT be auto-recovered. Pinned…, A caller holding only the device id must not be handed a device secret.… (+5 more)

### Community 179 - "ClientBase"
Cohesion: 0.67
Nodes (3): ClientBase, ClientCreate, ClientResponse

### Community 180 - "resolve_media_url"
Cohesion: 0.12
Nodes (23): media_base_url(), Origin that players and browsers should fetch media from., Absolute, fetchable URL for a stored media location. An object-storage key…, resolve_media_url(), list_screenshots(), get, Tenant storage folders are named, unique and stable: python…, Local disk and R2 must file a capture under the same key, or the folder layout… (+15 more)

### Community 181 - "TenantPlanBase"
Cohesion: 0.67
Nodes (3): TenantPlanBase, TenantPlanCreate, TenantPlanResponse

### Community 184 - "test_booking_report.py"
Cohesion: 0.17
Nodes (12): client_key(), Request, Who to count this request against. slowapi's get_remote_address returns…, pages_of(), A client report must count that client's window and that client's screens.…, auth(), check(), Super Admin boundary and the auth holes it closed: python… (+4 more)

### Community 185 - "acknowledge_alert"
Cohesion: 0.25
Nodes (9): Alert, acknowledge_alert(), alert_summary(), list_alerts(), get, Open alerts, newest first. Resolved ones only when asked for. The default is…, Mark an alert as picked up, without claiming the underlying fault is fixed.…, Counts for the navigation badge, so the header does not fetch the whole list. (+1 more)

### Community 189 - "playlist-builder.tsx"
Cohesion: 0.10
Nodes (31): targetLabels, AssignTarget, looksLikeLink(), Place, PlaceSearch(), dayLabels, dayNames, DefaultTransitionPanel() (+23 more)

### Community 192 - "websockets.py"
Cohesion: 0.29
Nodes (11): dashboard_websocket(), Screen, Session, WebSocket, Live fleet events for one dashboard user., Identity check for a screen's push socket. Kept deliberately identical to…, Push channel for one screen. Held open for the life of the device., register_ws() (+3 more)

### Community 194 - "User"
Cohesion: 0.09
Nodes (31): Exposed so UserResponse can show the tenant by name instead of a bare id., User, create_access_token(), aggregate_play_logs_sync(), Atomic aggregation of unaggregated play_logs into play_log_hourly_rollups., main(), main(), main() (+23 more)

### Community 195 - "_serialize_client"
Cohesion: 0.21
Nodes (12): create_client(), delete_client(), get_client(), list_clients(), next_client_code(), Client, get, put (+4 more)

### Community 209 - "promote_release"
Cohesion: 0.40
Nodes (5): promote_release(), patch, Move a build along the rollout ring: draft -> canary -> released. Promoting to…, AppReleasePatch, Promote (or demote) a build. The only mutable field: version_code, apk_url and…

## Knowledge Gaps
- **318 isolated node(s):** `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END`, `SKIPPED`, `FAILED` (+313 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **49 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TenantScope` connect `TenantScope` to `playlists.py`, `_serialize_client`, `.query`, `branding.py`, `promote_release`, `analytics.py`, `main.py`, `_post`, `screens.py`, `upload_content`, `resolve_media_url`, `acknowledge_alert`, `models.py`, `admin.py`, `HTTPException`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `resolve_media_url()` connect `resolve_media_url` to `schemas.py`, `model_validator`, `ContentResponse`, `branding.py`, `media_urls.py`, `test_media_storage.py`, `main.py`, `screens.py`, `TenantScope`, `admin.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `screens.py` to `User`, `_serialize_client`, `playlists.py`, `test_p6_websockets.py`, `models.py`, `_post`, `main.py`, `worker.py`, `get_password_hash`, `upload_content`, `TenantScope`, `acknowledge_alert`, `test_release_rollout.py`, `admin.py`, `HTTPException`, `google_device.py`, `database.py`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Are the 86 inferred relationships involving `HTTPException` (e.g. with `health_check()` and `serve_media()`) actually correct?**
  _`HTTPException` has 86 INFERRED edges - model-reasoned connections that need verification._
- **What connects `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END` to the rest of the system?**
  _318 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `schemas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0821256038647343 - nodes in this community are weakly interconnected._
- **Should `ApiService.kt` be split into smaller, more focused modules?**
  _Cohesion score 0.10338680926916222 - nodes in this community are weakly interconnected._