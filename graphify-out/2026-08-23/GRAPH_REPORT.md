# Graph Report - OLRAC SIGNAGE  (2026-08-18)

## Corpus Check
- 227 files · ~105,011 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1671 nodes · 3578 edges · 143 communities (109 shown, 34 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 58 edges (avg confidence: 0.74)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `31ed65a0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- get_password_hash
- schemas.py
- PlaylistItemEntity
- ApiService.kt
- MainActivity
- content/[id]/page.tsx
- PlaybackService
- screens.py
- MainActivity
- AbleSign Auto-Launch — Full Documentation
- compilerOptions
- models.py
- ValueError
- websockets.py
- api.ts
- components.json
- OLRAC Signage — Work Order for Antigravity (Gemini Pro)
- PlaybackTelemetry
- TenantScope
- resolve_rotation
- AppDatabase
- worker.py
- dependencies
- devDependencies
- placements.py
- OLRAC Signage
- TransitionType
- model_validator
- app/layout.tsx
- provider.py
- StorageManagerTest
- conftest.py
- .doWork
- package.json
- resolve_media_url
- content/page.tsx
- run
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
- env.py
- cn
- playlists.py
- SyncBackoffPolicyTest
- gradlew
- e2e_test.py
- badge.tsx
- @dnd-kit/sortable
- @dnd-kit/utilities
- eslint.config.mjs
- next.config.ts
- next
- OLRAC Signage — 80-TV Rollout Deployment Guide
- PlayerScreen.kt
- tailwind-merge
- test_p6_websockets.py
- maps_link.py
- P9 — Zero-touch provisioning for 80+ TVs (no ADB)
- postcss.config.mjs
- backup_db.sh
- validation_script.sh
- useAuthStore
- Player
- playlist-builder.tsx
- P8 — Per-TV capability detection and rendition selection
- Tests
- PlayerViewModel
- create_release
- ScheduleEvaluatorTest
- DeviceOwnerManagerTest
- razorpay_webhook
- Part B — Operations home page
- ScheduleEvaluator
- use-google-maps.ts
- create_token
- UtcDateTime
- health_check
- frontend/README.md
- Google Maps setup
- select_rendition
- rules/graphify.md
- workflows/graphify.md
- theme-toggle.tsx
- PlayEventDao
- AGENTS.md
- lucide-react
- check-maps-keys.py
- qrcode.react
- redacted_validation_error
- recharts
- screen-settings-dialog.tsx
- start-dev.ps1
- resolve_location_link
- find_orphans
- @tanstack/react-query
- provision-tv.sh
- build.sh
- class-variance-authority
- react-dom
- shadcn
- sonner
- @types/qrcode.react

## God Nodes (most connected - your core abstractions)
1. `TenantScope` - 89 edges
2. `cn()` - 74 edges
3. `useAuthStore` - 34 edges
4. `utcnow()` - 33 edges
5. `Button()` - 28 edges
6. `get_password_hash()` - 26 edges
7. `api` - 26 edges
8. `MainActivity` - 20 edges
9. `Skeleton()` - 20 edges
10. `relativeTime()` - 20 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `Screen`  [EXTRACTED]
  tests/test_sqlite_utc.py → backend/models.py
- `run()` --calls--> `utcnow()`  [EXTRACTED]
  tests/test_feature_parity.py → backend/models.py
- `run()` --calls--> `utcnow()`  [EXTRACTED]
  tests/test_tenant_isolation.py → backend/models.py
- `setup_db()` --calls--> `Organization`  [EXTRACTED]
  tests/test_p6_websockets.py → backend/models.py
- `setup_db()` --calls--> `User`  [EXTRACTED]
  tests/test_p6_websockets.py → backend/models.py

## Import Cycles
- None detected.

## Communities (143 total, 34 thin omitted)

### Community 0 - "get_password_hash"
Cohesion: 0.10
Nodes (40): AppRelease, Campaign, Content, EnrollmentToken, MediaRendition, Organization, Plan, Playlist (+32 more)

### Community 1 - "schemas.py"
Cohesion: 0.10
Nodes (37): create_checkout(), post, AppVersionResponse, BillingSummaryResponse, CheckoutRequest, CheckoutResponse, DeviceAuthRequest, DeviceTokenResponse (+29 more)

### Community 2 - "PlaylistItemEntity"
Cohesion: 0.24
Nodes (3): PlaylistDao, PlaylistItemEntity, Flow

### Community 3 - "ApiService.kt"
Cohesion: 0.07
Nodes (26): ApiClient, Context, ApiService, AppVersionDto, ContentDto, EnrollRequest, EnrollResponse, HeartbeatRequest (+18 more)

### Community 4 - "MainActivity"
Cohesion: 0.06
Nodes (28): CheckingLocalState, DeviceState, LaunchState, LaunchStateResolver, Pairing, Playing, RegistrationSnapshot, SignIn (+20 more)

### Community 5 - "content/[id]/page.tsx"
Cohesion: 0.16
Nodes (16): AdBookings(), asDate(), runState(), rupees(), EmptyState(), AssignScreensDialog(), GroupSettingsDialog(), Skeleton() (+8 more)

### Community 6 - "PlaybackService"
Cohesion: 0.08
Nodes (18): ConnectivityWatcher, Context, Intent, Job, PlaybackService, requestImmediateSync(), scheduleWorkers(), start() (+10 more)

### Community 7 - "screens.py"
Cohesion: 0.10
Nodes (46): datetime, Return a timezone-aware UTC timestamp., utcnow(), verify_password(), as_aware_utc(), assign_playlist(), auth_device(), batch_upload_play_logs() (+38 more)

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
Cohesion: 0.11
Nodes (23): ensure_billing_catalog(), plan_features(), Plan, Session, OLRAC Signage backend package. Explicit package marker. Without it `backend` is…, lifespan(), Subscription, get_tenant_scope() (+15 more)

### Community 12 - "ValueError"
Cohesion: 0.12
Nodes (14): HeartbeatRequest, PlaylistItemUpdate, Partial screen update: only the fields actually present are written. The PUT…, Each day maps to exactly [start, end] as HH:MM. Validated here rather than in…, ScheduleBase, ScheduleResponse, ScreenBase, ScreenCreate (+6 more)

### Community 13 - "websockets.py"
Cohesion: 0.13
Nodes (26): get_redis(), EmergencyBroadcast, ensure_initial_owner(), get_current_user(), get_current_user_ws(), get_or_create_default_organization(), get_secret_key(), get (+18 more)

### Community 14 - "api.ts"
Cohesion: 0.07
Nodes (41): BillingPage(), percent(), ALL_DAY, MODES, ScreenHoursDialog(), Windows, withDefaults(), ApiError (+33 more)

### Community 15 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 16 - "OLRAC Signage — Work Order for Antigravity (Gemini Pro)"
Cohesion: 0.08
Nodes (23): 0. Ground rules, 1. Device knowledge — the most important section, 2. What already exists and is verified, 3. Gap analysis — what the new goal needs, 4. Phases, 5. Infrastructure, 6. Regression suite — run after every phase, 7. Definition of done for the whole programme (+15 more)

### Community 17 - "PlaybackTelemetry"
Cohesion: 0.08
Nodes (17): ExoPlayer, Job, PlaybackException, onPlayerError(), PlayerSupervisor, HeartbeatReporter, Context, PlaybackSnapshot (+9 more)

### Community 18 - "TenantScope"
Cohesion: 0.09
Nodes (37): get_db(), PlayLogHourlyRollup, export_campaign_report(), get_campaign_info(), get_campaign_stats(), get_campaign_timeseries(), get_media_report(), list_campaigns() (+29 more)

### Community 19 - "resolve_rotation"
Cohesion: 0.23
Nodes (12): normalise(), Resolve the rotation a screen should apply to one playlist item. The player…, Coerce anything to one of 0/90/180/270, defaulting to 0., Degrees the player should rotate this item on this screen., resolve_rotation(), Rotation precedence — pure logic, no database, no device. Run directly: python…, A screen mounted portrait with one item deliberately pinned to landscape., test_defaults_when_nothing_is_set() (+4 more)

### Community 20 - "AppDatabase"
Cohesion: 0.29
Nodes (6): AppDatabase, getDatabase(), Context, migrate(), RoomDatabase, SupportSQLiteDatabase

### Community 21 - "worker.py"
Cohesion: 0.12
Nodes (21): delete_stored_file(), Remove the local file a stored location points at. Returns True if it went.…, delete_content(), public_upload_url(), delete, Where an asset lives, stored as a path rather than a full URL. This used to…, compute_sha256(), probe_file() (+13 more)

### Community 22 - "dependencies"
Cohesion: 0.11
Nodes (19): @base-ui/react, clsx, @dnd-kit/core, dependencies, @base-ui/react, clsx, @dnd-kit/core, leaflet (+11 more)

### Community 23 - "devDependencies"
Cohesion: 0.11
Nodes (19): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/google.maps (+11 more)

### Community 24 - "placements.py"
Cohesion: 0.08
Nodes (49): api_key(), fetch_static_map(), is_enabled(), Map imagery for reports, behind a single switch. Everything map-related…, URL for an image pinning every point, or None when maps are not configured.…, The map image itself, or None if unavailable. A report must never fail because…, static_map_url(), AdPlacement (+41 more)

### Community 25 - "OLRAC Signage"
Cohesion: 0.11
Nodes (16): Acceptance checks, Build-time server configuration, Install and pair, Kiosk and boot provisioning, OLRAC Android TV player, Supported devices, 1. Configure the backend, 2. Apply database migrations (+8 more)

### Community 26 - "TransitionType"
Cohesion: 0.19
Nodes (11): fromWire(), TransitionSpec, TransitionSpecResolver, TransitionType, FADE, NONE, SLIDE_DOWN, SLIDE_LEFT (+3 more)

### Community 27 - "model_validator"
Cohesion: 0.20
Nodes (6): PlacementCreate, PlaylistItemBase, PlaylistItemCreate, PlaylistItemResponse, PlaylistUpdate, model_validator

### Community 28 - "app/layout.tsx"
Cohesion: 0.19
Nodes (8): geistMono, geistSans, metadata, Providers(), Toaster(), TransitionClass, ViewTransition(), ViewTransitionProps

### Community 29 - "provider.py"
Cohesion: 0.30
Nodes (6): CheckoutSession, get_payment_provider(), MockPaymentProvider, PaymentProvider, RazorpayProvider, Protocol

### Community 30 - "StorageManagerTest"
Cohesion: 0.22
Nodes (4): OkHttpClient, StorageManager, Context, StorageManagerTest

### Community 31 - "conftest.py"
Cohesion: 0.22
Nodes (6): pytest_collect_file(), pytest_collection_modifyitems(), Run each backend test script in its own process. `backend/database.py` builds…, Fail loudly if a script also got imported as a module. pytest.ini restricts…, ScriptFile, ScriptItem

### Community 32 - ".doWork"
Cohesion: 0.38
Nodes (5): CoroutineWorker, Result, PlayEventDto, PlayLogBatchRequest, ProofOfPlayWorker

### Community 33 - "package.json"
Cohesion: 0.22
Nodes (8): name, private, scripts, build, dev, lint, start, version

### Community 34 - "resolve_media_url"
Cohesion: 0.09
Nodes (29): _detect_lan_host(), is_s3_enabled(), media_base_url(), Turning a stored media location into something a browser or a TV can fetch.…, Best-effort LAN address of this machine, so devices on the network can reach…, Origin that players and browsers should fetch media from. Defaults to this…, Absolute, fetchable URL for a stored media location., resolve_media_url() (+21 more)

### Community 35 - "content/page.tsx"
Cohesion: 0.10
Nodes (42): QueuedUpload, FileSort, SORTS, GroupsPage(), accountLinks, adminLinks, primaryLinks, StatusFilter (+34 more)

### Community 36 - "run"
Cohesion: 0.67
Nodes (4): mock_aws, owner_headers(), TestClient, run()

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

### Community 49 - "env.py"
Cohesion: 0.40
Nodes (4): Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 50 - "cn"
Cohesion: 0.12
Nodes (31): exportFormats, targetLabels, AssignTarget, PageHeader(), Card(), CardAction(), CardContent(), CardDescription() (+23 more)

### Community 51 - "playlists.py"
Cohesion: 0.24
Nodes (18): add_item_to_playlist(), bump_playlist(), create_playlist(), delete_playlist(), get_playlist(), get_playlists(), delete, get (+10 more)

### Community 53 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 74 - "badge.tsx"
Cohesion: 0.28
Nodes (4): MapPoint, ScreenMap(), Badge(), badgeVariants

### Community 80 - "OLRAC Signage — 80-TV Rollout Deployment Guide"
Cohesion: 0.17
Nodes (11): 1. Server Environment Setup, 2. Storage Configuration, 3. Start the Stack, 4. Database Migration, 5. Create the Platform Owner, 6. TV Enrollment & Provisioning, 7. Watchdog Setup (Crucial for Budget TVs), Build the Watchdog (+3 more)

### Community 81 - "PlayerScreen.kt"
Cohesion: 0.26
Nodes (10): awaitPlayerReady(), DecoderSnapshot, DualSurfacePlayer(), Player, ExoPlayer, PlaybackSurface(), PlayerScreen(), preparePlayer() (+2 more)

### Community 83 - "test_p6_websockets.py"
Cohesion: 0.22
Nodes (15): ScreenGroup, create_access_token(), login_for_access_token(), post, OAuth2PasswordRequestForm, P6 realtime checks: python tests/test_p6_websockets.py Covers hierarchical…, /api/ws/dashboard/ws must reach the dashboard handler, not the device one. Both…, Push must never be the only path. The spec is explicit: if the socket is down… (+7 more)

### Community 84 - "maps_link.py"
Cohesion: 0.20
Nodes (14): _expand(), geocode(), MapsLinkError, _name_from(), _name_from_search(), parse(), Turn a shared Google Maps link into coordinates. This exists so setting a…, (latitude, longitude, place name or None) from any Google Maps URL. Raises… (+6 more)

### Community 85 - "P9 — Zero-touch provisioning for 80+ TVs (no ADB)"
Cohesion: 0.20
Nodes (9): 1. Make the app a working Device Policy Controller, 2. Silent updates (finishes P7), 3. Generate the provisioning QR, 4. Auto-enrol on first boot, 5. Retire the accessibility watchdog on provisioned devices, Definition of done, Deployment paths, in order of preference, P9 — Zero-touch provisioning for 80+ TVs (no ADB) (+1 more)

### Community 89 - "useAuthStore"
Cohesion: 0.12
Nodes (22): Alert, AlertsPage(), buildAlerts(), hoursSince(), Severity, EmergencyPage(), FileManagementPage(), GroupDetailPage() (+14 more)

### Community 90 - "Player"
Cohesion: 0.40
Nodes (3): Player, PlaybackException, Player

### Community 91 - "playlist-builder.tsx"
Cohesion: 0.13
Nodes (22): AdDetailPage(), ContentPage(), isSupported(), stripExtension(), dayLabels, dayNames, DefaultTransitionPanel(), ItemRow() (+14 more)

### Community 92 - "P8 — Per-TV capability detection and rendition selection"
Cohesion: 0.25
Nodes (7): 1. Device reports its capabilities (Android), 2. Backend stores the profile, 3. Backend picks the rendition, 4. Dashboard, Definition of done, P8 — Per-TV capability detection and rendition selection, Tests

### Community 93 - "Tests"
Cohesion: 0.25
Nodes (7): Feature parity check, Live E2E test, Quota enforcement, Run everything, Storage and failure-path validation, Tenant isolation probe, Tests

### Community 94 - "PlayerViewModel"
Cohesion: 0.38
Nodes (3): PlayerViewModel, AndroidViewModel, StateFlow

### Community 95 - "create_release"
Cohesion: 0.29
Nodes (7): create_release(), list_releases(), get, post, Session, AppReleaseCreate, AppReleaseResponse

### Community 98 - "razorpay_webhook"
Cohesion: 0.18
Nodes (12): WebhookEvent, billing_summary(), list_plans(), datetime, get, Plan, Request, razorpay_webhook() (+4 more)

### Community 99 - "Part B — Operations home page"
Cohesion: 0.12
Nodes (16): Backend, Dashboard, Definition of done, Definition of done, Every panel below uses data that already exists, Layout, Order of work, P10 — Display rotation, and an operations home page (+8 more)

### Community 101 - "use-google-maps.ts"
Cohesion: 0.27
Nodes (10): listeners, loadSdk(), MAPS_KEY, MapsWindow, publish(), serverSnapshot(), snapshot(), Status (+2 more)

### Community 102 - "create_token"
Cohesion: 0.22
Nodes (10): create_token(), list_tokens(), get, post, _token_to_dict(), generate_provisioning_qr(), ProvisioningRequest, BaseModel (+2 more)

### Community 106 - "UtcDateTime"
Cohesion: 0.40
Nodes (3): A DateTime that always reads back as timezone-aware UTC. Postgres with…, UtcDateTime, TypeDecorator

### Community 107 - "health_check"
Cohesion: 0.50
Nodes (4): health_check(), get, Session, read_root()

### Community 108 - "frontend/README.md"
Cohesion: 0.50
Nodes (3): Deploy on Vercel, Getting Started, Learn More

### Community 109 - "Google Maps setup"
Cohesion: 0.20
Nodes (9): 1. Create a project and enable billing, 2. Enable the three APIs, 3. Create the browser key, 4. Create the server key, 5. Check the keys, 6. Restart, Google Maps setup, If the map does not appear (+1 more)

### Community 110 - "select_rendition"
Cohesion: 0.20
Nodes (8): Screen, Selects the most appropriate media rendition for a screen based on its hardware…, select_rendition(), ContentBase, ContentResponse, ContentUpdate, MediaRenditionResponse, Make stored locations fetchable, wherever this response is embedded. Doing it…

### Community 113 - "theme-toggle.tsx"
Cohesion: 0.83
Nodes (3): subscribe(), ThemeToggle(), useHydrated()

### Community 118 - "check-maps-keys.py"
Cohesion: 0.32
Nodes (7): check_server_key(), main(), Path, Check the Google Maps keys and say plainly what is wrong with them. Run this…, Value of `name` in a .env file, or '' when absent - no dependency on dotenv., Ask Static Maps for a real image; its rejection text is the diagnosis., read_env()

### Community 120 - "redacted_validation_error"
Cohesion: 0.40
Nodes (5): Request, _redact(), redacted_validation_error(), exception_handler, RequestValidationError

### Community 122 - "screen-settings-dialog.tsx"
Cohesion: 0.19
Nodes (10): Place, PlaceSearch(), FIT_MODES, ORIENTATIONS, ScreenSettingsDialog(), splitTags(), timezones(), api (+2 more)

### Community 130 - "resolve_location_link"
Cohesion: 0.40
Nodes (5): Coordinates for a pasted Google Maps link. Deliberately not a Google API call:…, resolve_location_link(), A Google Maps share link, pasted by an operator., ResolveLinkRequest, ResolveLinkResponse

### Community 131 - "find_orphans"
Cohesion: 0.50
Nodes (5): find_orphans(), main(), Path, Every upload path any row still points at, relative to the uploads root., referenced_paths()

## Knowledge Gaps
- **274 isolated node(s):** `CheckingLocalState`, `NONE`, `FADE`, `SLIDE_LEFT`, `SLIDE_RIGHT` (+269 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TenantScope` connect `TenantScope` to `get_password_hash`, `schemas.py`, `razorpay_webhook`, `resolve_media_url`, `resolve_location_link`, `create_token`, `screens.py`, `models.py`, `websockets.py`, `playlists.py`, `worker.py`, `placements.py`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Why does `PlaylistItemEntity` connect `PlaylistItemEntity` to `ScheduleEvaluatorTest`, `ScheduleEvaluator`, `PlaybackService`, `PlayerScreen.kt`, `TransitionType`, `PlayerViewModel`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Why does `PlayerScreen()` connect `PlayerScreen.kt` to `PlaybackTelemetry`, `MainActivity`, `PlayerViewModel`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **What connects `CheckingLocalState`, `NONE`, `FADE` to the rest of the system?**
  _274 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `get_password_hash` be split into smaller, more focused modules?**
  _Cohesion score 0.09693877551020408 - nodes in this community are weakly interconnected._
- **Should `schemas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09815078236130868 - nodes in this community are weakly interconnected._
- **Should `ApiService.kt` be split into smaller, more focused modules?**
  _Cohesion score 0.06802721088435375 - nodes in this community are weakly interconnected._