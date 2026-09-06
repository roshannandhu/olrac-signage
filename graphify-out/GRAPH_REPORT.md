# Graph Report - OLRAC SIGNAGE  (2026-09-06)

## Corpus Check
- 365 files · ~400,783 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3100 nodes · 7339 edges · 221 communities (178 shown, 43 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 280 edges (avg confidence: 0.78)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `63a7a8a9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_tv_deep_link.py
- schemas.py
- PlaylistItemEntity
- ApiService.kt
- MainActivity
- services/__init__.py
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
- invoices/page.tsx
- process_media_sync
- main.py
- booking_report.py
- dependencies
- devDependencies
- HTTPException
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
- timedelta
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
- groups_by_id
- test_media_storage.py
- websockets.py
- SyncBackoffPolicyTest
- gradlew
- .onCreate
- resolve_media_url
- PlacementTargetRef
- PlayerSupervisor
- eslint.config.mjs
- next.config.ts
- DeviceState
- OLRAC Signage — 80-TV Rollout Deployment Guide
- PlayerScreen.kt
- routers/billing.py
- analytics.py
- parse
- P9 — Zero-touch provisioning for 80+ TVs (no ADB)
- postcss.config.mjs
- backup_db.sh
- validation_script.sh
- ad-bookings.tsx
- placement_service.py
- PlayEventDao
- P8 — Per-TV capability detection and rendition selection
- Tests
- PlayerViewModel
- groups.py
- ScheduleEvaluatorTest
- DeviceOwnerManagerTest
- TenantScope
- Part B — Operations home page
- cleanup_orphans.py
- screen-map.tsx
- LaunchState
- test_quotas.py
- test_role_separation.py
- frontend/README.md
- Google Maps setup
- sync_tv
- rules/graphify.md
- workflows/graphify.md
- Deploying to Render + Cloudflare (or Vercel)
- backend/__init__.py
- AGENTS.md
- lucide-react
- check-maps-keys.py
- media_urls.py
- SignageDeviceAdminReceiver
- branding.py
- select_rendition
- start-dev.ps1
- useAuthStore
- users.py
- UtcDateTime
- OperatingHoursTest
- provision-tv.sh
- build.sh
- ApiClient
- test_release_rollout.py
- BaseRepository
- test_screen_quota.py
- screens/[id]/page.tsx
- test_rollout_policy.py
- playlist-builder.tsx
- MaintenanceGesture
- resolve_rotation
- screens.py
- SessionLocal
- PlayCompletionTest
- check_r2.py
- PlayEndReason
- UpdateGateTest
- ScreenshotManager
- theme-toggle.tsx
- models.py
- UpdateGate
- a1b4e7c92f38_play_log_campaign_attribution.py
- presignR2Url
- send
- react
- tw-animate-css
- @types/leaflet
- redacted_validation_error
- SignageClock
- utcnow
- test_reinstall_reconnect.py
- content.py
- screen_pairing_service.py
- alerts.py
- .effective_ends_at
- emergency.py
- shadcn
- cn
- test_google_signin.py
- Commercial Signage Architecture & Domain Invariants
- screen_telemetry_service.py
- create_access_token
- PlaylistRepository
- e2e_test.py
- test_per_location_ad_window.py
- js-sha256
- next
- qrcode.react
- tailwind-merge
- @tanstack/react-query
- .__init__
- leaflet
- quote_paise
- ScreenBase
- ScreenRepository
- test_platform_admin.py
- PlacementRepository
- clsx
- env.py
- @dnd-kit/core
- .effective_playlist_id
- patch-opennext.js
- client_key

## God Nodes (most connected - your core abstractions)
1. `TenantScope` - 188 edges
2. `cn()` - 76 edges
3. `utcnow()` - 67 edges
4. `get_password_hash()` - 64 edges
5. `Organization` - 58 edges
6. `_post()` - 56 edges
7. `useAuthStore` - 54 edges
8. `create_access_token()` - 49 edges
9. `User` - 46 edges
10. `Screen` - 40 edges

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

## Communities (221 total, 43 thin omitted)

### Community 0 - "test_tv_deep_link.py"
Cohesion: 0.16
Nodes (16): _android_intent_url(), Rewrite an "olrac://" deep link into the intent: form a browser will actually…, The TV's Custom Tab landing page, which then hands back to the player app.…, _tv_result_page(), HTMLResponse, The TV hand-back link must be openable by a browser: python…, The whole bug in one assertion: a raw custom scheme is what Chrome rejects., No APK change: the intent's data must still be the olrac:// URL already… (+8 more)

### Community 1 - "schemas.py"
Cohesion: 0.05
Nodes (71): AlertResponse, AlertSummaryResponse, AppReleasePatch, BillingSummaryResponse, BrandingResponse, BrandingUpdate, CheckoutRequest, CheckoutResponse (+63 more)

### Community 2 - "PlaylistItemEntity"
Cohesion: 0.24
Nodes (3): PlaylistDao, PlaylistItemEntity, Flow

### Community 3 - "ApiService.kt"
Cohesion: 0.10
Nodes (23): ApiService, AppVersionDto, AuthMethodsResponse, ContentDto, DeviceAuthRequest, DeviceTokenResponse, EnrollResponse, GoogleOAuthUrlResponse (+15 more)

### Community 4 - "MainActivity"
Cohesion: 0.16
Nodes (5): Intent, MainActivity, GooglePollRequest, ComponentActivity, KeyEvent

### Community 5 - "services/__init__.py"
Cohesion: 0.09
Nodes (27): BaseService, Base Service class for Clean Architecture Application Layer. Encapsulates…, Base application service with transaction handling and structured logging., Commit current database transaction., Roll back current database transaction., Refresh instance from database., collect_device_secret(), DeviceAuthService (+19 more)

### Community 6 - "PlaybackService"
Cohesion: 0.06
Nodes (22): ConnectivityWatcher, Response, WebSocket, RealtimeClient, WebSocketListener, Context, Intent, Job (+14 more)

### Community 7 - "admin-ui.tsx"
Cohesion: 0.15
Nodes (17): AdminApprovalsPage(), AdminPackagesPage(), blank, AdminTenantDetailPage(), Tab, AdminTenantsPage(), Accent, accents (+9 more)

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
Cohesion: 0.09
Nodes (17): AppReleaseCreate, AppReleaseResponse, ContentClientAdUpdate, HeartbeatRequest, PasswordChange, PaymentWrite, PlaylistItemUpdate, One receipt against a booking -- not the booking's whole settlement. Posting… (+9 more)

### Community 13 - "test_screen_approval.py"
Cohesion: 0.26
Nodes (11): auth_header(), Screen pairing is instant: python tests/test_screen_approval.py This file used…, sign_in(), test_a_secret_does_not_authenticate_a_different_screen(), test_a_signed_in_screen_syncs_straight_away(), test_enrolment_token_admits_immediately(), test_pairing_admits_immediately(), test_re_signing_in_keeps_the_screen_admitted() (+3 more)

### Community 14 - "api.ts"
Cohesion: 0.05
Nodes (53): AdminReleasesPage(), looksLikeLink(), Place, PlaceSearch(), FIT_MODES, ORIENTATIONS, ScreenSettingsDialog(), splitTags() (+45 more)

### Community 15 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 16 - "OLRAC Signage — Work Order for Antigravity (Gemini Pro)"
Cohesion: 0.08
Nodes (23): 0. Ground rules, 1. Device knowledge — the most important section, 2. What already exists and is verified, 3. Gap analysis — what the new goal needs, 4. Phases, 5. Infrastructure, 6. Regression suite — run after every phase, 7. Definition of done for the whole programme (+15 more)

### Community 17 - "PlaybackTelemetry"
Cohesion: 0.15
Nodes (9): HeartbeatReporter, Context, PlaybackSnapshot, PlaybackTelemetry, enqueue(), Context, CoroutineWorker, Result (+1 more)

### Community 18 - "invoices/page.tsx"
Cohesion: 0.26
Nodes (15): Filter, METHOD_LABELS, BLANK, EmailReportModalProps, Badge(), badgeVariants, Dialog(), DialogContent() (+7 more)

### Community 19 - "process_media_sync"
Cohesion: 0.18
Nodes (19): compute_sha256(), probe_file(), process_media(), process_media_sync(), run_command_sync(), skipif, cleanup_tempdir(), _do_not_process_on_upload() (+11 more)

### Community 20 - "main.py"
Cohesion: 0.06
Nodes (38): _pool_for_current_loop(), _ensure_schema(), lifespan(), Whether this API process should also run the arq worker. Off by default:…, Build the schema on a brand-new database, and stamp it so Alembic can take…, _run_worker_in_process(), ensure_initial_owner(), get_or_create_default_organization() (+30 more)

### Community 21 - "booking_report.py"
Cohesion: 0.06
Nodes (57): api_key(), _choose_zoom(), fetch_static_map(), google_configured(), is_enabled(), _project(), Map imagery for reports, behind a single switch. Everything map-related…, The closest zoom that still fits every pin, with a margin so none sits on the… (+49 more)

### Community 22 - "dependencies"
Cohesion: 0.10
Nodes (21): @base-ui/react, class-variance-authority, @dnd-kit/sortable, @dnd-kit/utilities, dependencies, @base-ui/react, class-variance-authority, @dnd-kit/sortable (+13 more)

### Community 23 - "devDependencies"
Cohesion: 0.09
Nodes (23): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, @opennextjs/cloudflare, tailwindcss, @tailwindcss/postcss (+15 more)

### Community 24 - "HTTPException"
Cohesion: 0.07
Nodes (73): AdPlacement, AdPlacementExtension, An advert sold to a client: what runs, for whom, when, and for how much.…, One paid extension of a booking's run. A row per extension rather than an…, update_content_client_ad(), add_extension(), add_target(), _booking_screen_ids() (+65 more)

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
Cohesion: 0.09
Nodes (37): build_oauth_url(), _claims(), client_id(), client_secret(), exchange_code(), GoogleError, is_configured(), is_web_configured() (+29 more)

### Community 30 - "R2Presigner"
Cohesion: 0.11
Nodes (9): R2Presigner, OkHttpClient, StorageManager, Context, OkHttpClient, UpdateManager, Context, StorageManagerTest (+1 more)

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
Cohesion: 0.17
Nodes (24): ContentPage(), isSupported(), QueuedUpload, stripExtension(), GroupsPage(), ScreensPage(), StatusFilter, useStoredView() (+16 more)

### Community 36 - "timedelta"
Cohesion: 0.07
Nodes (71): AlertCondition, _as_utc(), evaluate_all(), evaluate_content(), evaluate_placement(), evaluate_screen(), is_scheduled_off(), _minutes() (+63 more)

### Community 37 - "OLRAC Signage — Build Goal & Agent Work Order"
Cohesion: 0.12
Nodes (15): 10. Phase P7 — Remote player updates (R9), 11. Regression suite — run after every phase, 12. Definition of done, 13. Rules for the implementing agent, 1. Product requirements (the contract), 1a. Verified status — audit of 2026-08-07, 2. Current state — audit (original, pre-implementation), 3. Phase P0 — Offline-first playback (fix D1) (+7 more)

### Community 38 - "OLRAC Watchdog — build and TV setup"
Cohesion: 0.22
Nodes (8): Build, Checking a TV, How recovery actually works, Known issue in the player (not the watchdog), OLRAC Watchdog — build and TV setup, Provision a TV, Retargeting, The three things that silently break this

### Community 39 - "team/page.tsx"
Cohesion: 0.13
Nodes (20): AccountPage(), BillingPage(), percent(), exportFormats, asTenantRole(), roleDescription, TeamPage(), TENANT_ROLES (+12 more)

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

### Community 49 - "groups_by_id"
Cohesion: 0.20
Nodes (12): groups_by_id(), Screen, ScreenGroup, Session, Map screen groups by id for fast ancestry walking during playlist resolution., Determine the active playlist ID a screen should be playing right now.…, resolve_screen_playlist(), agree() (+4 more)

### Community 50 - "test_media_storage.py"
Cohesion: 0.10
Nodes (34): _client(), fetch_to(), is_remote(), Path, Reading and writing media wherever it happens to live. The transcoder needs a…, Persist `local_path` under `key` and return the location to save on the row.…, The backend-relative key inside a stored location. Both schemes carry the same…, Put the bytes of `stored_url` at `destination` and return it. A local file is… (+26 more)

### Community 51 - "websockets.py"
Cohesion: 0.10
Nodes (31): change_own_password(), get_current_user(), get_current_user_ws(), get_secret_key(), login_for_access_token(), limit, patch, Request (+23 more)

### Community 53 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 72 - ".onCreate"
Cohesion: 0.17
Nodes (13): Bundle, GoogleSignInScreen(), PairingScreen(), PinPromptScreen(), ServerControls(), ServerSetupScreen(), BrandedMessage(), secondaryButtonColors() (+5 more)

### Community 74 - "resolve_media_url"
Cohesion: 0.09
Nodes (32): media_base_url(), Origin that players and browsers should fetch media from., Absolute, fetchable URL for a stored media location. An object-storage key…, resolve_media_url(), FakeOrg, FakeUser, Tenant storage folders are named, unique and stable: python…, Local disk and R2 must file a capture under the same key, or the folder layout… (+24 more)

### Community 75 - "PlacementTargetRef"
Cohesion: 0.15
Nodes (8): MediaRenditionResponse, PlacementCreate, PlacementTargetRef, PlanQuoteRequest, PlaylistUpdate, One place a booking runs. Exactly one of the two ids is set., A custom shape to price: one entry per location, holding that location's days.…, model_validator

### Community 76 - "PlayerSupervisor"
Cohesion: 0.16
Nodes (8): ExoPlayer, Job, PlaybackException, onPlayerError(), PlayerSupervisor, Context, ExoPlayer, PlayerSupervisorTest

### Community 80 - "OLRAC Signage — 80-TV Rollout Deployment Guide"
Cohesion: 0.10
Nodes (18): 1. Server Environment Setup, 2. Storage Configuration, 3. Start the Stack, 4. Database Migration, 5. Create the Platform Owner, 6. TV Enrollment & Provisioning, 7. Watchdog Setup (Crucial for Budget TVs), Build the Watchdog (+10 more)

### Community 81 - "PlayerScreen.kt"
Cohesion: 0.13
Nodes (20): android, awaitPlayerReady(), Player, clearPlayCheckpoint(), DecoderSnapshot, DualSurfacePlayer(), Player, com (+12 more)

### Community 82 - "routers/billing.py"
Cohesion: 0.12
Nodes (21): ensure_billing_catalog(), plan_features(), Plan, Session, CheckoutSession, get_payment_provider(), MockPaymentProvider, PaymentProvider (+13 more)

### Community 83 - "analytics.py"
Cohesion: 0.24
Nodes (14): export_campaign_report(), get_campaign_info(), get_campaign_stats(), get_campaign_timeseries(), get_media_report(), list_campaigns(), get, Session (+6 more)

### Community 84 - "parse"
Cohesion: 0.08
Nodes (44): _expand(), geocode(), _is_error_page(), MapsLinkError, _name_from(), _name_from_search(), parse(), Turn a shared Google Maps link into coordinates. This exists so setting a… (+36 more)

### Community 85 - "P9 — Zero-touch provisioning for 80+ TVs (no ADB)"
Cohesion: 0.20
Nodes (9): 1. Make the app a working Device Policy Controller, 2. Silent updates (finishes P7), 3. Generate the provisioning QR, 4. Auto-enrol on first boot, 5. Retire the accessibility watchdog on provisioned devices, Definition of done, Deployment paths, in order of preference, P9 — Zero-touch provisioning for 80+ TVs (no ADB) (+1 more)

### Community 89 - "ad-bookings.tsx"
Cohesion: 0.18
Nodes (24): AdDetailPage(), SECTIONS, asDate(), InvoicesPage(), AdBookings(), METHOD_LABELS, CreateBookingModal(), CreateBookingModalProps (+16 more)

### Community 90 - "placement_service.py"
Cohesion: 0.15
Nodes (13): AdPlacementTarget, One place a booked advert runs, and the playlist item it put there. Exactly one…, When this location actually begins carrying the advert. max() against…, When this location stops, its own window winning over the booking's., place_advert(), playlist_for_target(), datetime, Playlist (+5 more)

### Community 91 - "PlayEventDao"
Cohesion: 0.12
Nodes (8): AppDatabase, getDatabase(), Context, migrate(), PlayEventDao, PlayEventEntity, RoomDatabase, SupportSQLiteDatabase

### Community 92 - "P8 — Per-TV capability detection and rendition selection"
Cohesion: 0.25
Nodes (7): 1. Device reports its capabilities (Android), 2. Backend stores the profile, 3. Backend picks the rendition, 4. Dashboard, Definition of done, P8 — Per-TV capability detection and rendition selection, Tests

### Community 93 - "Tests"
Cohesion: 0.22
Nodes (8): Feature parity check, Live E2E test, Quota enforcement, Run everything, Storage and failure-path validation, Tenant isolation probe, Tests, What the suite needs

### Community 94 - "PlayerViewModel"
Cohesion: 0.38
Nodes (3): PlayerViewModel, AndroidViewModel, StateFlow

### Community 95 - "groups.py"
Cohesion: 0.08
Nodes (31): assign_group_playlist(), create_group(), delete_group(), list_groups(), get, put, ScreenGroup, Reject a parent that is not ours, is the group itself, or would close a loop.… (+23 more)

### Community 98 - "TenantScope"
Cohesion: 0.09
Nodes (35): create_client(), delete_client(), get_client(), list_clients(), next_client_code(), Client, get, put (+27 more)

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
Cohesion: 0.29
Nodes (8): CheckingLocalState, GoogleSignIn, LaunchState, LaunchStateResolver, Pairing, Playing, RegistrationSnapshot, SignIn

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

### Community 110 - "sync_tv"
Cohesion: 0.12
Nodes (13): datetime, sync_tv(), ContentBase, ContentResponse, ContentUpdate, PlaylistBase, PlaylistCreate, PlaylistItemBase (+5 more)

### Community 113 - "Deploying to Render + Cloudflare (or Vercel)"
Cohesion: 0.12
Nodes (16): 0. Before either dashboard, 1. Render: the API and worker, 2. The dashboard: Cloudflare Workers, or Vercel, 2a. Cloudflare Workers (via OpenNext), 2b. Vercel, 3. Back to Render, 4. Create the platform operator, 5. Verify before provisioning a screen (+8 more)

### Community 114 - "backend/__init__.py"
Cohesion: 0.09
Nodes (36): OLRAC Signage backend package. Explicit package marker. Without it `backend` is…, create_token(), list_tokens(), get, _token_to_dict(), add_item_to_playlist(), create_playlist(), delete_playlist() (+28 more)

### Community 118 - "check-maps-keys.py"
Cohesion: 0.32
Nodes (7): check_server_key(), main(), Path, Check the Google Maps keys and say plainly what is wrong with them. Run this…, Value of `name` in a .env file, or '' when absent - no dependency on dotenv., Ask Static Maps for a real image; its rejection text is the diagnosis., read_env()

### Community 119 - "media_urls.py"
Cohesion: 0.08
Nodes (34): health_check(), get, Session, Stable URL for a stored object; signs the real one fresh on every request. This…, Liveness, plus WHICH database is actually behind it. This used to answer…, read_root(), serve_media(), delete_stored_file() (+26 more)

### Community 120 - "SignageDeviceAdminReceiver"
Cohesion: 0.33
Nodes (5): EnrollRequest, Context, Intent, SignageDeviceAdminReceiver, DeviceAdminReceiver

### Community 121 - "branding.py"
Cohesion: 0.25
Nodes (13): Safe, alphanumeric bucket key prefix for an organization., storage_prefix(), get_branding(), _organization(), get, put, UploadFile, How a tenant's own brand appears on the report they give their client. The… (+5 more)

### Community 122 - "select_rendition"
Cohesion: 0.22
Nodes (18): Screen, Selects the most appropriate media rendition for a screen based on its hardware…, select_rendition(), Filtering everything out must not fall through to the biggest file we own. When…, test_a_constrained_panel_is_never_handed_the_master(), Rendition selection, against the set the transcoder actually produces.…, Content carrying exactly what the transcoder produces today., real_content() (+10 more)

### Community 128 - "useAuthStore"
Cohesion: 0.12
Nodes (26): AdminLayout(), navItems, BrandingPage(), LOGO_TYPES, ClientsPage(), GroupDetailPage(), accountLinks, DashboardLayout() (+18 more)

### Community 130 - "users.py"
Cohesion: 0.31
Nodes (10): active_owner_count(), create_user(), delete_user(), deny_platform_account(), list_users(), get, put, User (+2 more)

### Community 131 - "UtcDateTime"
Cohesion: 0.40
Nodes (3): A DateTime that always reads back as timezone-aware UTC. Postgres with…, UtcDateTime, TypeDecorator

### Community 137 - "ApiClient"
Cohesion: 0.38
Nodes (3): ApiClient, Context, okhttp3

### Community 139 - "test_release_rollout.py"
Cohesion: 0.13
Nodes (16): get_db(), AppRelease, bearer(), _database_url(), device_headers(), publish(), Player releases: who may publish one, and who it reaches. Covers the defect…, Read the screen straight from the database. There is no GET /api/screens/{id};… (+8 more)

### Community 140 - "BaseRepository"
Cohesion: 0.10
Nodes (18): BaseRepository, Any, Query, Session, Base Repository for Clean Architecture persistence layer. Encapsulates generic…, Generic repository providing clean database operations for an ORM model., Fetch a single record by primary key id., Fetch all records with optional offset and limit. (+10 more)

### Community 141 - "test_screen_quota.py"
Cohesion: 0.29
Nodes (11): build_tenant(), check(), fill_to_cap(), The screen cap actually caps: python tests/test_screen_quota.py A tenant on a…, The derivation itself, before any endpoint uses it., The bypass: /register first, then /enroll finds the row and skips the check., A workspace capped at CAP screens, limited either by its package or by an…, CAP screens already claimed, so the next one is the one over the line. (+3 more)

### Community 143 - "screens/[id]/page.tsx"
Cohesion: 0.15
Nodes (20): Alert, AlertsPage(), buildAlerts(), hoursSince(), Severity, asDate(), CampaignsPage(), orientationLabel() (+12 more)

### Community 144 - "test_rollout_policy.py"
Cohesion: 0.18
Nodes (18): apply_update_status(), eligible_for_fallback(), Staged player rollout: which build a screen is offered, and when to give up on…, Point a screen at a build, clearing any state from the previous attempt.…, Restrict an AppRelease query to builds that unpinned screens may be offered., Fold one device-reported update result into `screen`. Returns a short human-…, repin(), Staged-rollout decisions — pure logic, no database, no device. Run directly:… (+10 more)

### Community 145 - "playlist-builder.tsx"
Cohesion: 0.10
Nodes (23): FileManagementPage(), FileSort, SORTS, EditClientAdModalProps, SortOption, MediaThumbnail(), dayLabels, dayNames (+15 more)

### Community 147 - "resolve_rotation"
Cohesion: 0.23
Nodes (12): normalise(), Resolve the rotation a screen should apply to one playlist item. The player…, Coerce anything to one of 0/90/180/270, defaulting to 0., Degrees the player should rotate this item on this screen., resolve_rotation(), Rotation precedence — pure logic, no database, no device. Run directly: python…, A screen mounted portrait with one item deliberately pinned to landscape., test_defaults_when_nothing_is_set() (+4 more)

### Community 148 - "screens.py"
Cohesion: 0.06
Nodes (69): get_redis(), _post(), Form-post to Google and return (status, parsed body). A 4xx is returned rather…, delete(), Remove a stored object. Best effort -- a missing object is not an error. Local…, create_checkout(), revoke_token(), create_release() (+61 more)

### Community 149 - "SessionLocal"
Cohesion: 0.08
Nodes (26): prune_finished_bookings(), prune_play_log_rollups(), prune_play_logs(), prune_screenshots(), _publish_alert(), Notice what is wrong with the fleet, and what has stopped being wrong. Runs…, Tell any connected dashboard, best effort. Wrapped: Redis being unavailable…, Age out the hourly rollups. Nothing deleted from this table -- no cron, no… (+18 more)

### Community 152 - "PlayEndReason"
Cohesion: 0.22
Nodes (6): PlayCompletion, PlayEndReason, FAILED, INTERRUPTED, PLAYED_TO_END, SKIPPED

### Community 154 - "ScreenshotManager"
Cohesion: 0.39
Nodes (4): Activity, ScreenshotManager, Bitmap, WeakReference

### Community 155 - "theme-toggle.tsx"
Cohesion: 0.83
Nodes (3): subscribe(), ThemeToggle(), useHydrated()

### Community 156 - "models.py"
Cohesion: 0.10
Nodes (27): AdPayment, Alert, Campaign, Client, EmergencyBroadcast, Plan, PlayLog, PlayLogHourlyRollup (+19 more)

### Community 166 - "presignR2Url"
Cohesion: 0.53
Nodes (4): dynamic, GET(), getSigningKey(), presignR2Url()

### Community 167 - "send"
Cohesion: 0.27
Nodes (11): _describe_missing(), is_configured(), MailNotConfigured, RuntimeError, Sending mail, behind a single switch. There was no mail path in this codebase…, Raised instead of silently discarding a message nobody could have received., The From address, falling back to the login when only that is set., Deliver one message. Raises rather than returning False, so a caller cannot… (+3 more)

### Community 175 - "redacted_validation_error"
Cohesion: 0.40
Nodes (5): Request, _redact(), redacted_validation_error(), exception_handler, RequestValidationError

### Community 176 - "SignageClock"
Cohesion: 0.20
Nodes (4): OperatingHours, getInstance(), Context, SignageClock

### Community 177 - "utcnow"
Cohesion: 0.10
Nodes (42): Content, EnrollmentToken, MediaRendition, Organization, Playlist, PlaylistItem, Screens this tenant may actually have. None means no limit. None rather than 0…, Return a timezone-aware UTC timestamp. (+34 more)

### Community 178 - "test_reinstall_reconnect.py"
Cohesion: 0.30
Nodes (13): check(), dashboard_token(), fleet(), One account on the TV and the dashboard, and a screen that survives a…, What the player sends when the installer types their account on the TV., What the player sends on every cold start, before it knows anything., A wipe on a panel whose serial is unreadable CANNOT be auto-recovered. Pinned…, A caller holding only the device id must not be handed a device secret.… (+5 more)

### Community 179 - "content.py"
Cohesion: 0.30
Nodes (11): delete_content(), get_all_content(), get_content_item(), get, put, queue_processing(), Hand a video to the transcode worker, ensuring it is processed immediately. In…, One asset, for the pages that show a single advert. The detail page used to… (+3 more)

### Community 180 - "screen_pairing_service.py"
Cohesion: 0.20
Nodes (9): as_aware_utc(), generate_pair_code(), datetime, Session, Screen Hardware Pairing and Enrollment Application Service., Generate a 6-digit numeric pairing code for screen display., Ensure datetime has explicit UTC timezone awareness., Application Service managing pairing codes, onboarding tokens, and hardware… (+1 more)

### Community 181 - "alerts.py"
Cohesion: 0.29
Nodes (9): Alert, acknowledge_alert(), alert_summary(), list_alerts(), get, Open alerts, newest first. Resolved ones only when asked for. The default is…, Mark an alert as picked up, without claiming the underlying fault is fixed.…, Counts for the navigation badge, so the header does not fetch the whole list. (+1 more)

### Community 184 - ".effective_ends_at"
Cohesion: 0.40
Nodes (4): When the run actually finishes, extensions and per-location windows counted.…, The same answer, computed in SQL. Without this it was a plain property, so…, expression, hybrid_property

### Community 185 - "emergency.py"
Cohesion: 0.39
Nodes (7): BroadcastRequest, cancel_emergency_broadcast(), get_active_broadcasts(), BaseModel, get, Session, trigger_emergency_broadcast()

### Community 189 - "cn"
Cohesion: 0.08
Nodes (39): SectionNav(), EmergencyPage(), targetLabels, AssignPlaylistCard(), AssignTarget, ALL_DAY, MODES, ScreenHoursDialog() (+31 more)

### Community 190 - "test_google_signin.py"
Cohesion: 0.24
Nodes (10): approved(), _database_url(), poll(), Signing a TV in with a Google account: who it lets in, and who it must not.…, Postgres when a server is there, SQLite otherwise -- as test_release_rollout…, Point the module's two network calls at canned answers., run(), setup_db() (+2 more)

### Community 192 - "Commercial Signage Architecture & Domain Invariants"
Cohesion: 0.40
Nodes (4): 1. Strict Separation of Creative Assets vs. Commercial Bookings, 2. Backend Clean Architecture Layers, 3. Screen Quota & Plan Cap Invariants, Commercial Signage Architecture & Domain Invariants

### Community 193 - "screen_telemetry_service.py"
Cohesion: 0.16
Nodes (13): AppRelease, AppVersionResponse, _command_key(), current_app_version(), player_sync_interval_seconds(), pop_device_command(), Session, Screen Telemetry, Versioning & Remote Command Management Service. (+5 more)

### Community 194 - "create_access_token"
Cohesion: 0.13
Nodes (22): ScreenGroup, create_access_token(), capture_screenshot(), main(), check(), days_between(), ok(), The client-ad editor must obey the same rules as the bookings tab. python… (+14 more)

### Community 195 - "PlaylistRepository"
Cohesion: 0.13
Nodes (11): PlaylistRepository, Playlist, PlaylistItem, Session, Repository handling database operations for Playlists and PlaylistItems., Fetch all playlists for tenant scope with eager loaded content and items., Fetch a single playlist with eager loaded relations within tenant scope., Fetch a specific playlist item by id and playlist id. (+3 more)

### Community 197 - "test_per_location_ad_window.py"
Cohesion: 0.60
Nodes (4): check(), days_between(), One booking, different run lengths per location: python…, run()

### Community 208 - "quote_paise"
Cohesion: 0.30
Nodes (10): plan_capacity_screen_days(), quote_paise(), What a custom shape costs on a plan. Never below the plan's own price. Pro-rata…, What a plan actually sells, expressed in screen-days: locations x days. The…, FakePlan, Pricing a custom run against a plan: pytest tests/test_plan_quote.py The per-…, Just the four columns the quote reads. A real TenantPlan would need a session., test_a_custom_shape_is_priced_in_screen_days() (+2 more)

### Community 209 - "ScreenBase"
Cohesion: 0.50
Nodes (3): ScreenBase, ScreenCreate, ScreenResponse

### Community 211 - "ScreenRepository"
Cohesion: 0.12
Nodes (12): Screen, ScreenGroup, Session, Repository handling database operations for Screens and ScreenGroups., Look up a screen by its unique hardware device_id., Look up a screen by its 6-digit active pairing code., List screens within tenant scope with optional group and status filtering., Map screen groups by id for the given organization IDs. (+4 more)

### Community 212 - "test_platform_admin.py"
Cohesion: 0.33
Nodes (8): pages_of(), auth(), check(), Super Admin boundary and the auth holes it closed: python…, One platform operator, and one ordinary tenant owner in a separate organisation., run(), seed(), token_for()

### Community 213 - "PlacementRepository"
Cohesion: 0.11
Nodes (11): PlacementRepository, Client, Session, Repository handling database operations for Ad Placements, Campaigns, and…, Fetch all ad placements for tenant scope., Fetch a single ad placement within tenant scope., Fetch all ad clients for tenant scope., Fetch an ad client by id. (+3 more)

### Community 215 - "env.py"
Cohesion: 0.40
Nodes (4): Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 221 - "patch-opennext.js"
Cohesion: 0.50
Nodes (3): fs, handlerPath, path

### Community 225 - "client_key"
Cohesion: 0.67
Nodes (3): client_key(), Request, Who to count this request against. slowapi's get_remote_address returns…

## Knowledge Gaps
- **332 isolated node(s):** `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END`, `SKIPPED`, `FAILED` (+327 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **43 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TenantScope` connect `TenantScope` to `users.py`, `BaseRepository`, `screens.py`, `HTTPException`, `admin.py`, `utcnow`, `content.py`, `alerts.py`, `emergency.py`, `PlaylistRepository`, `routers/billing.py`, `ScreenRepository`, `analytics.py`, `PlacementRepository`, `placement_service.py`, `groups.py`, `backend/__init__.py`, `media_urls.py`, `branding.py`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `resolve_media_url()` connect `resolve_media_url` to `schemas.py`, `TenantScope`, `PlacementTargetRef`, `sync_tv`, `backend/__init__.py`, `content.py`, `screens.py`, `test_media_storage.py`, `booking_report.py`, `media_urls.py`, `HTTPException`, `branding.py`, `admin.py`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Why does `Organization` connect `utcnow` to `create_access_token`, `test_release_rollout.py`, `test_screen_quota.py`, `groups_by_id`, `websockets.py`, `main.py`, `screens.py`, `SessionLocal`, `process_media_sync`, `test_platform_admin.py`, `admin.py`, `models.py`, `test_google_signin.py`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Are the 95 inferred relationships involving `HTTPException` (e.g. with `health_check()` and `serve_media()`) actually correct?**
  _`HTTPException` has 95 INFERRED edges - model-reasoned connections that need verification._
- **What connects `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END` to the rest of the system?**
  _332 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `schemas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.04890453834115806 - nodes in this community are weakly interconnected._
- **Should `ApiService.kt` be split into smaller, more focused modules?**
  _Cohesion score 0.09682539682539683 - nodes in this community are weakly interconnected._