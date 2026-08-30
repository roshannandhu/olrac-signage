# Graph Report - OLRAC SIGNAGE  (2026-08-30)

## Corpus Check
- 296 files · ~376,666 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2387 nodes · 5433 edges · 188 communities (149 shown, 39 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 199 edges (avg confidence: 0.78)
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
- playlist-builder.tsx
- PlaybackService
- sign_in_with_google
- MainActivity
- AbleSign Auto-Launch — Full Documentation
- compilerOptions
- verify_device_token
- ValueError
- test_screen_approval.py
- api.ts
- components.json
- OLRAC Signage — Work Order for Antigravity (Gemini Pro)
- PlaybackTelemetry
- ensure_billing_catalog
- resolve_rotation
- models.py
- update_group
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
- playlists.py
- ad-bookings.tsx
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
- tv_google_oauth_callback
- worker.py
- trigger_emergency_broadcast
- SyncBackoffPolicyTest
- gradlew
- .onCreate
- env.py
- PlacementTargetRef
- @dnd-kit/utilities
- eslint.config.mjs
- next.config.ts
- ScreenshotManager
- OLRAC Signage — 80-TV Rollout Deployment Guide
- PlayerScreen.kt
- test_google_signin.py
- list_alerts
- parse
- P9 — Zero-touch provisioning for 80+ TVs (no ADB)
- postcss.config.mjs
- backup_db.sh
- validation_script.sh
- content/[id]/page.tsx
- Player
- PlayEventDao
- P8 — Per-TV capability detection and rendition selection
- Tests
- PlayerViewModel
- test_release_rollout.py
- ScheduleEvaluatorTest
- DeviceOwnerManagerTest
- test_signup_lifecycle.py
- Part B — Operations home page
- admin-ui.tsx
- screen-map.tsx
- LaunchState
- UtcDateTime
- test_role_separation.py
- frontend/README.md
- Google Maps setup
- ContentResponse
- rules/graphify.md
- workflows/graphify.md
- current_app_version
- AppDatabase
- AGENTS.md
- lucide-react
- check-maps-keys.py
- .downloadAndInstallUpdate
- DeviceState
- ScheduleEvaluator
- select_rendition
- start-dev.ps1
- useAuthStore
- test_sqlite_utc.py
- cleanup_orphans.py
- vercel.json
- provision-tv.sh
- build.sh
- ApiService
- booking_report.py
- health_check
- @types/qrcode.react
- content/page.tsx
- test_rollout_policy.py
- lifespan
- MaintenanceGesture
- recharts
- HTTPException
- get_payment_provider
- PlayCompletionTest
- PlayEndReason
- UpdateGateTest
- sync_tv
- theme-toggle.tsx
- ScreenBase
- analytics.py
- UpdateGate
- a1b4e7c92f38_play_log_campaign_attribution.py
- google_device_start
- next-themes
- react
- tw-animate-css
- @types/leaflet
- auth_methods
- get_password_hash
- test_reinstall_reconnect.py
- test_platform_admin.py
- leaflet
- @dnd-kit/sortable
- shadcn
- limiter.py
- promote_release
- @dnd-kit/core

## God Nodes (most connected - your core abstractions)
1. `TenantScope` - 119 edges
2. `cn()` - 74 edges
3. `utcnow()` - 53 edges
4. `get_password_hash()` - 51 edges
5. `_post()` - 48 edges
6. `Organization` - 44 edges
7. `useAuthStore` - 42 edges
8. `User` - 38 edges
9. `Screen` - 32 edges
10. `create_access_token()` - 31 edges

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

## Communities (188 total, 39 thin omitted)

### Community 0 - "cn"
Cohesion: 0.13
Nodes (25): accountLinks, adminLinks, primaryLinks, StatusIndicator(), CardAction(), CardFooter(), DropdownMenuContent(), DropdownMenuItem() (+17 more)

### Community 1 - "schemas.py"
Cohesion: 0.08
Nodes (42): AlertResponse, AlertSummaryResponse, CheckoutRequest, CheckoutResponse, DeviceAuthRequest, DeviceTokenResponse, EnrollmentTokenCreate, EnrollmentTokenResponse (+34 more)

### Community 2 - "PlaylistItemEntity"
Cohesion: 0.24
Nodes (3): PlaylistDao, PlaylistItemEntity, Flow

### Community 3 - "ApiService.kt"
Cohesion: 0.08
Nodes (21): AuthMethodsResponse, ContentDto, DeviceAuthRequest, DeviceTokenResponse, EnrollResponse, GoogleOAuthUrlResponse, GooglePollRequest, GooglePollResponse (+13 more)

### Community 4 - "MainActivity"
Cohesion: 0.15
Nodes (6): RegistrationSnapshot, Intent, MainActivity, SignInRequest, ComponentActivity, KeyEvent

### Community 5 - "playlist-builder.tsx"
Cohesion: 0.12
Nodes (33): exportFormats, targetLabels, roleDescription, TENANT_ROLES, AssignTarget, EmptyState(), ErrorState(), PageHeader() (+25 more)

### Community 6 - "PlaybackService"
Cohesion: 0.06
Nodes (22): ConnectivityWatcher, Response, WebSocket, RealtimeClient, WebSocketListener, Context, Intent, Job (+14 more)

### Community 7 - "sign_in_with_google"
Cohesion: 0.15
Nodes (22): auth_methods(), change_own_password(), ensure_initial_owner(), get_current_user(), get_current_user_ws(), login_for_access_token(), get, limit (+14 more)

### Community 8 - "MainActivity"
Cohesion: 0.06
Nodes (27): android.accessibilityservice.AccessibilityService, android.app.Activity, android.content.BroadcastReceiver, android.content.ComponentName, android.content.Context, android.content.Intent, android.content.SharedPreferences, android.os.Bundle (+19 more)

### Community 9 - "AbleSign Auto-Launch — Full Documentation"
Cohesion: 0.07
Nodes (28): AbleSign Auto-Launch — Full Documentation, AbleSign not launching after reboot, Build commands, Check if watchdog is running, Files in This Folder, How to Install on ANY Android TV, How to Rebuild the APK (if you change the code), If Something Goes Wrong (+20 more)

### Community 10 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 11 - "verify_device_token"
Cohesion: 0.25
Nodes (11): dashboard_websocket(), Screen, Session, WebSocket, Push channel for one screen. Held open for the life of the device., Identity check for a screen's push socket. Kept deliberately identical to…, Live fleet events for one dashboard user., register_ws() (+3 more)

### Community 12 - "ValueError"
Cohesion: 0.12
Nodes (14): AppReleaseCreate, AppReleaseResponse, HeartbeatRequest, PasswordChange, PlaylistItemUpdate, Partial screen update: only the fields actually present are written. The PUT…, Each day maps to exactly [start, end] as HH:MM. Validated here rather than in…, ScheduleBase (+6 more)

### Community 13 - "test_screen_approval.py"
Cohesion: 0.26
Nodes (11): auth_header(), Screen pairing is instant: python tests/test_screen_approval.py This file used…, sign_in(), test_a_secret_does_not_authenticate_a_different_screen(), test_a_signed_in_screen_syncs_straight_away(), test_enrolment_token_admits_immediately(), test_pairing_admits_immediately(), test_re_signing_in_keeps_the_screen_admitted() (+3 more)

### Community 14 - "api.ts"
Cohesion: 0.06
Nodes (46): FileManagementPage(), FileSort, SORTS, SortOption, MediaThumbnail(), DialogFooter(), API_HOST, ApiError (+38 more)

### Community 15 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 16 - "OLRAC Signage — Work Order for Antigravity (Gemini Pro)"
Cohesion: 0.08
Nodes (23): 0. Ground rules, 1. Device knowledge — the most important section, 2. What already exists and is verified, 3. Gap analysis — what the new goal needs, 4. Phases, 5. Infrastructure, 6. Regression suite — run after every phase, 7. Definition of done for the whole programme (+15 more)

### Community 17 - "PlaybackTelemetry"
Cohesion: 0.08
Nodes (17): ExoPlayer, Job, PlaybackException, onPlayerError(), PlayerSupervisor, HeartbeatReporter, Context, PlaybackSnapshot (+9 more)

### Community 18 - "ensure_billing_catalog"
Cohesion: 0.18
Nodes (14): ensure_billing_catalog(), plan_features(), Plan, Session, billing_summary(), list_plans(), get, Plan (+6 more)

### Community 19 - "resolve_rotation"
Cohesion: 0.23
Nodes (12): normalise(), Resolve the rotation a screen should apply to one playlist item. The player…, Coerce anything to one of 0/90/180/270, defaulting to 0., Degrees the player should rotate this item on this screen., resolve_rotation(), Rotation precedence — pure logic, no database, no device. Run directly: python…, A screen mounted portrait with one item deliberately pinned to landscape., test_defaults_when_nothing_is_set() (+4 more)

### Community 20 - "models.py"
Cohesion: 0.07
Nodes (39): OLRAC Signage backend package. Explicit package marker. Without it `backend` is…, Alert, Something wrong with the fleet, recorded so it can be delivered and reviewed.…, Staged player rollout: which build a screen is offered, and when to give up on…, datetime, timestamp_to_datetime(), public_upload_url(), Where an asset lives, stored as a path rather than a full URL. This used to… (+31 more)

### Community 21 - "update_group"
Cohesion: 0.33
Nodes (10): create_group(), list_groups(), get, put, Reject a parent that is not ours, is the group itself, or would close a loop.…, serialize_group(), set_group_screens(), update_group() (+2 more)

### Community 22 - "dependencies"
Cohesion: 0.10
Nodes (21): @base-ui/react, class-variance-authority, clsx, dependencies, @base-ui/react, class-variance-authority, clsx, next (+13 more)

### Community 23 - "devDependencies"
Cohesion: 0.09
Nodes (23): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, @opennextjs/cloudflare, tailwindcss, @tailwindcss/postcss (+15 more)

### Community 24 - "TenantScope"
Cohesion: 0.09
Nodes (47): AdPlacement, AdPlacementTarget, An advert sold to a client: what runs, for whom, when, and for how much.…, One place a booked advert runs, and the playlist item it put there. Exactly one…, add_target(), _booking_screen_ids(), build_booking_report(), create_placement() (+39 more)

### Community 25 - "OLRAC Signage"
Cohesion: 0.11
Nodes (16): Acceptance checks, Build-time server configuration, Install and pair, Kiosk and boot provisioning, OLRAC Android TV player, Supported devices, 1. Configure the backend, 2. Apply database migrations (+8 more)

### Community 26 - "TransitionType"
Cohesion: 0.19
Nodes (11): fromWire(), TransitionSpec, TransitionSpecResolver, TransitionType, FADE, NONE, SLIDE_DOWN, SLIDE_LEFT (+3 more)

### Community 27 - "admin.py"
Cohesion: 0.06
Nodes (70): delete_stored_file(), _detect_lan_host(), is_s3_enabled(), media_base_url(), Turning a stored media location into something a browser or a TV can fetch.…, Best-effort LAN address of this machine, so devices on the network can reach…, Origin that players and browsers should fetch media from. Defaults to this…, Absolute, fetchable URL for a stored media location. (+62 more)

### Community 28 - "app/layout.tsx"
Cohesion: 0.19
Nodes (8): geistMono, geistSans, metadata, Providers(), Toaster(), TransitionClass, ViewTransition(), ViewTransitionProps

### Community 29 - "google_device.py"
Cohesion: 0.17
Nodes (21): build_oauth_url(), _claims(), client_id(), client_secret(), exchange_code(), GoogleError, is_configured(), is_web_configured() (+13 more)

### Community 30 - "StorageManagerTest"
Cohesion: 0.22
Nodes (4): OkHttpClient, StorageManager, Context, StorageManagerTest

### Community 31 - "conftest.py"
Cohesion: 0.16
Nodes (10): _postgres_reachable(), pytest_collect_file(), pytest_collection_finish(), pytest_collection_modifyitems(), Run each backend test script in its own process. `backend/database.py` builds…, Fail loudly if a script also got imported as a module. pytest.ini restricts…, Fail if any tests/test_*.py is collected by neither mechanism. A file that is…, Whether a server is listening on the port the scripts create their databases… (+2 more)

### Community 32 - "ProofOfPlayWorker.kt"
Cohesion: 0.13
Nodes (16): Context, ProofOfPlayReporter, BatchOutcome, ACCEPTED, DISCARD, RETRY_LATER, enqueueNow(), isoFormatter() (+8 more)

### Community 33 - "scripts"
Cohesion: 0.17
Nodes (11): name, private, scripts, build, cf:build, cf:deploy, cf:preview, dev (+3 more)

### Community 34 - "playlists.py"
Cohesion: 0.26
Nodes (16): Schedule, add_item_to_playlist(), bump_playlist(), create_playlist(), get_playlist(), get_playlists(), get, Playlist (+8 more)

### Community 35 - "ad-bookings.tsx"
Cohesion: 0.08
Nodes (37): GroupDetailPage(), AdBookings(), asDate(), runState(), rupees(), AssignScreensDialog(), GroupSettingsDialog(), looksLikeLink() (+29 more)

### Community 36 - "test_alerting.py"
Cohesion: 0.09
Nodes (56): AlertCondition, _as_utc(), evaluate_all(), evaluate_content(), evaluate_screen(), is_scheduled_off(), _minutes(), datetime (+48 more)

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

### Community 49 - "tv_google_oauth_callback"
Cohesion: 0.24
Nodes (10): get_tv_google_oauth_url(), public_base_url(), Request, The address a phone or a TV can actually reach this API on. OAuth redirect URIs…, Generate a direct Google OAuth URL for Android TV / Custom Tab login., The TV's Custom Tab landing page, which then hands back to the player app.…, Handle Google OAuth return on Android TV Custom Tab and auto-bind screen.…, tv_google_oauth_callback() (+2 more)

### Community 50 - "worker.py"
Cohesion: 0.06
Nodes (54): _client(), fetch_to(), is_remote(), Path, Reading and writing media wherever it happens to live. The transcoder needs a…, The backend-relative key inside a stored location. Both schemes carry the same…, Put the bytes of `stored_url` at `destination` and return it. A local file is…, Persist `local_path` under `key` and return the location to save on the row.… (+46 more)

### Community 51 - "trigger_emergency_broadcast"
Cohesion: 0.29
Nodes (8): EmergencyBroadcast, BroadcastRequest, cancel_emergency_broadcast(), get_active_broadcasts(), BaseModel, get, Session, trigger_emergency_broadcast()

### Community 53 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 72 - ".onCreate"
Cohesion: 0.32
Nodes (13): BrandedMessage(), GoogleLogo(), GoogleSignInScreen(), Bundle, Modifier, PairingScreen(), PinPromptScreen(), secondaryButtonColors() (+5 more)

### Community 74 - "env.py"
Cohesion: 0.40
Nodes (4): Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 75 - "PlacementTargetRef"
Cohesion: 0.18
Nodes (6): MediaRenditionResponse, PlacementCreate, PlacementTargetRef, PlaylistUpdate, One place a booking runs. Exactly one of the two ids is set., model_validator

### Community 79 - "ScreenshotManager"
Cohesion: 0.39
Nodes (4): Activity, ScreenshotManager, Bitmap, WeakReference

### Community 80 - "OLRAC Signage — 80-TV Rollout Deployment Guide"
Cohesion: 0.11
Nodes (17): 1. Server Environment Setup, 2. Storage Configuration, 3. Start the Stack, 4. Database Migration, 5. Create the Platform Owner, 6. TV Enrollment & Provisioning, 7. Watchdog Setup (Crucial for Budget TVs), Build the Watchdog (+9 more)

### Community 81 - "PlayerScreen.kt"
Cohesion: 0.23
Nodes (14): android, awaitPlayerReady(), clearPlayCheckpoint(), DualSurfacePlayer(), com, ExoPlayer, Modifier, PlaybackSurface() (+6 more)

### Community 82 - "test_google_signin.py"
Cohesion: 0.24
Nodes (10): approved(), _database_url(), poll(), Signing a TV in with a Google account: who it lets in, and who it must not.…, Postgres when a server is there, SQLite otherwise -- as test_release_rollout…, Point the module's two network calls at canned answers., run(), setup_db() (+2 more)

### Community 83 - "list_alerts"
Cohesion: 0.29
Nodes (7): Alert, alert_summary(), list_alerts(), get, Open alerts, newest first. Resolved ones only when asked for. The default is…, Counts for the navigation badge, so the header does not fetch the whole list., serialize()

### Community 84 - "parse"
Cohesion: 0.08
Nodes (44): _expand(), geocode(), _is_error_page(), MapsLinkError, _name_from(), _name_from_search(), parse(), Turn a shared Google Maps link into coordinates. This exists so setting a… (+36 more)

### Community 85 - "P9 — Zero-touch provisioning for 80+ TVs (no ADB)"
Cohesion: 0.20
Nodes (9): 1. Make the app a working Device Policy Controller, 2. Silent updates (finishes P7), 3. Generate the provisioning QR, 4. Auto-enrol on first boot, 5. Retire the accessibility watchdog on provisioned devices, Definition of done, Deployment paths, in order of preference, P9 — Zero-touch provisioning for 80+ TVs (no ADB) (+1 more)

### Community 89 - "content/[id]/page.tsx"
Cohesion: 0.14
Nodes (20): Alert, AlertsPage(), buildAlerts(), hoursSince(), Severity, ReleasesPage(), orientationLabel(), ScreenDetailPage() (+12 more)

### Community 90 - "Player"
Cohesion: 0.25
Nodes (5): Player, DecoderSnapshot, Player, PlaybackException, Player

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
Cohesion: 0.13
Nodes (17): get_db(), AppRelease, bearer(), _database_url(), device_headers(), publish(), Player releases: who may publish one, and who it reaches. Covers the defect…, Read the screen straight from the database. There is no GET /api/screens/{id};… (+9 more)

### Community 98 - "test_signup_lifecycle.py"
Cohesion: 0.31
Nodes (9): check(), hdr(), promote_platform_operator(), A company from signup to paying customer: python tests/test_signup_lifecycle.py…, Stand in for Google's token endpoint. Only the exchange is replaced. Everything…, The bootstrap account is created as an ordinary owner; make it the operator.…, run(), stub_google() (+1 more)

### Community 99 - "Part B — Operations home page"
Cohesion: 0.12
Nodes (16): Backend, Dashboard, Definition of done, Definition of done, Every panel below uses data that already exists, Layout, Order of work, P10 — Display rotation, and an operations home page (+8 more)

### Community 100 - "admin-ui.tsx"
Cohesion: 0.15
Nodes (18): AdminApprovalsPage(), AdminPackagesPage(), blank, AdminTenantDetailPage(), Tab, AdminTenantsPage(), Accent, accents (+10 more)

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

### Community 113 - "current_app_version"
Cohesion: 0.40
Nodes (6): AppRelease, eligible_for_fallback(), Restrict an AppRelease query to builds that unpinned screens may be offered., current_app_version(), _release_response(), AppVersionResponse

### Community 114 - "AppDatabase"
Cohesion: 0.25
Nodes (6): AppDatabase, getDatabase(), Context, migrate(), RoomDatabase, SupportSQLiteDatabase

### Community 118 - "check-maps-keys.py"
Cohesion: 0.32
Nodes (7): check_server_key(), main(), Path, Check the Google Maps keys and say plainly what is wrong with them. Run this…, Value of `name` in a .env file, or '' when absent - no dependency on dotenv., Ask Static Maps for a real image; its rejection text is the diagnosis., read_env()

### Community 119 - ".downloadAndInstallUpdate"
Cohesion: 0.36
Nodes (4): AppVersionDto, Context, OkHttpClient, UpdateManager

### Community 120 - "DeviceState"
Cohesion: 0.15
Nodes (6): DeviceState, EnrollRequest, Context, Intent, SignageDeviceAdminReceiver, DeviceAdminReceiver

### Community 122 - "select_rendition"
Cohesion: 0.25
Nodes (16): Screen, Selects the most appropriate media rendition for a screen based on its hardware…, select_rendition(), Rendition selection, against the set the transcoder actually produces.…, Content carrying exactly what the transcoder produces today., real_content(), rendition(), screen() (+8 more)

### Community 128 - "useAuthStore"
Cohesion: 0.14
Nodes (19): AdminLayout(), isSuperAdmin(), navItems, AccountPage(), BillingPage(), percent(), EmergencyPage(), DashboardLayout() (+11 more)

### Community 131 - "cleanup_orphans.py"
Cohesion: 0.43
Nodes (6): find_orphans(), main(), Path, Find upload files that no database row points at. Reports by default and…, Every upload path any row still points at, relative to the uploads root., referenced_paths()

### Community 132 - "vercel.json"
Cohesion: 0.29
Nodes (6): framework, root, rewrites, $schema, services, frontend

### Community 137 - "ApiService"
Cohesion: 0.33
Nodes (4): ApiClient, Context, okhttp3, ApiService

### Community 139 - "booking_report.py"
Cohesion: 0.22
Nodes (14): api_key(), fetch_static_map(), is_enabled(), Map imagery for reports, behind a single switch. Everything map-related…, URL for an image pinning every point, or None when maps are not configured.…, The map image itself, or None if unavailable. A report must never fail because…, static_map_url(), build_pdf() (+6 more)

### Community 140 - "health_check"
Cohesion: 0.18
Nodes (11): health_check(), login_page(), get, Request, Session, Liveness, plus WHICH database is actually behind it. This used to answer…, read_root(), _redact() (+3 more)

### Community 143 - "content/page.tsx"
Cohesion: 0.12
Nodes (29): AdDetailPage(), ContentPage(), isSupported(), QueuedUpload, stripExtension(), GroupsPage(), ScreensPage(), StatusFilter (+21 more)

### Community 144 - "test_rollout_policy.py"
Cohesion: 0.24
Nodes (15): apply_update_status(), Point a screen at a build, clearing any state from the previous attempt.…, Fold one device-reported update result into `screen`. Returns a short human-…, repin(), Staged-rollout decisions — pure logic, no database, no device. Run directly:…, screen(), test_failures_must_be_consecutive(), test_in_flight_states_are_recorded_without_judgement() (+7 more)

### Community 145 - "lifespan"
Cohesion: 0.40
Nodes (5): _ensure_schema(), lifespan(), Build the schema on a brand-new database, and stamp it so Alembic can take…, Whether this API process should also run the arq worker. Off by default:…, _run_worker_in_process()

### Community 148 - "HTTPException"
Cohesion: 0.05
Nodes (98): get_redis(), _pool_for_current_loop(), _post(), Form-post to Google and return (status, parsed body). A 4xx is returned rather…, delete(), Remove a stored object. Best effort -- a missing object is not an error. Local…, datetime, Return a timezone-aware UTC timestamp. (+90 more)

### Community 149 - "get_payment_provider"
Cohesion: 0.16
Nodes (11): CheckoutSession, get_payment_provider(), MockPaymentProvider, PaymentProvider, RazorpayProvider, Protocol, Query, RuntimeError (+3 more)

### Community 152 - "PlayEndReason"
Cohesion: 0.22
Nodes (6): PlayCompletion, PlayEndReason, FAILED, INTERRUPTED, PLAYED_TO_END, SKIPPED

### Community 154 - "sync_tv"
Cohesion: 0.18
Nodes (11): as_aware_utc(), player_sync_interval_seconds(), datetime, sync_tv(), PlaylistBase, PlaylistCreate, PlaylistItemBase, PlaylistItemCreate (+3 more)

### Community 155 - "theme-toggle.tsx"
Cohesion: 0.83
Nodes (3): subscribe(), ThemeToggle(), useHydrated()

### Community 156 - "ScreenBase"
Cohesion: 0.50
Nodes (3): ScreenBase, ScreenCreate, ScreenResponse

### Community 158 - "analytics.py"
Cohesion: 0.27
Nodes (14): PlayLogHourlyRollup, export_campaign_report(), get_campaign_info(), get_campaign_stats(), get_campaign_timeseries(), get_media_report(), list_campaigns(), get (+6 more)

### Community 166 - "google_device_start"
Cohesion: 0.33
Nodes (6): google_device_start(), Begin a Google sign-in for this TV and hand back the code to put on screen., GoogleDeviceStartRequest, GoogleDeviceStartResponse, A TV asking for a Google code to put on screen., What the TV displays, plus the handle it polls with. `poll_token` is a short-…

### Community 177 - "get_password_hash"
Cohesion: 0.06
Nodes (76): Campaign, Content, EnrollmentToken, MediaRendition, Organization, Plan, Playlist, PlaylistItem (+68 more)

### Community 178 - "test_reinstall_reconnect.py"
Cohesion: 0.32
Nodes (11): check(), dashboard_token(), fleet(), One account on the TV and the dashboard, and a screen that survives a…, What the player sends when the installer types their account on the TV., What the player sends on every cold start, before it knows anything., A wipe on a panel whose serial is unreadable CANNOT be auto-recovered. Pinned…, run() (+3 more)

### Community 181 - "test_platform_admin.py"
Cohesion: 0.39
Nodes (7): auth(), check(), Super Admin boundary and the auth holes it closed: python…, One platform operator, and one ordinary tenant owner in a separate organisation., run(), seed(), token_for()

### Community 187 - "limiter.py"
Cohesion: 0.50
Nodes (3): client_key(), Request, Who to count this request against. slowapi's get_remote_address returns…

### Community 188 - "promote_release"
Cohesion: 0.40
Nodes (5): promote_release(), patch, Move a build along the rollout ring: draft -> canary -> released. Promoting to…, AppReleasePatch, Promote (or demote) a build. The only mutable field: version_code, apk_url and…

## Knowledge Gaps
- **306 isolated node(s):** `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END`, `SKIPPED`, `FAILED` (+301 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TenantScope` connect `TenantScope` to `playlists.py`, `get_password_hash`, `ensure_billing_catalog`, `list_alerts`, `HTTPException`, `models.py`, `trigger_emergency_broadcast`, `update_group`, `get_payment_provider`, `admin.py`, `promote_release`, `analytics.py`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `get_password_hash()` connect `get_password_hash` to `sign_in_with_google`, `test_role_separation.py`, `ValueError`, `test_google_signin.py`, `HTTPException`, `models.py`, `test_platform_admin.py`, `TenantScope`, `test_release_rollout.py`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Why does `dependencies` connect `dependencies` to `scripts`, `next-themes`, `react`, `tw-animate-css`, `@types/leaflet`, `@dnd-kit/utilities`, `@types/qrcode.react`, `recharts`, `lucide-react`, `leaflet`, `@dnd-kit/sortable`, `shadcn`, `@dnd-kit/core`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Are the 69 inferred relationships involving `HTTPException` (e.g. with `health_check()` and `approve_tenant()`) actually correct?**
  _`HTTPException` has 69 INFERRED edges - model-reasoned connections that need verification._
- **What connects `CheckingLocalState`, `GoogleSignIn`, `PLAYED_TO_END` to the rest of the system?**
  _306 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `cn` be split into smaller, more focused modules?**
  _Cohesion score 0.12903225806451613 - nodes in this community are weakly interconnected._
- **Should `schemas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08194905869324474 - nodes in this community are weakly interconnected._