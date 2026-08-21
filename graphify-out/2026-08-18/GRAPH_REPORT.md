# Graph Report - OLRAC SIGNAGE  (2026-08-17)

## Corpus Check
- 202 files · ~87,137 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1473 nodes · 3119 edges · 133 communities (101 shown, 32 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 36 edges (avg confidence: 0.73)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `31ed65a0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- models.py
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
- main.py
- field_validator
- auth.py
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
- trigger_emergency_broadcast
- OLRAC Signage
- TransitionType
- PlaylistItemBase
- app/layout.tsx
- provider.py
- StorageManagerTest
- conftest.py
- .doWork
- package.json
- PlayerLauncher
- content/page.tsx
- analytics.py
- OLRAC Signage — Build Goal & Agent Work Order
- AbleSign Watchdog — TV Setup
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
- dashboard/layout.tsx
- SyncBackoffPolicyTest
- gradlew
- e2e_test.py
- billing/page.tsx
- @dnd-kit/sortable
- @dnd-kit/utilities
- eslint.config.mjs
- next.config.ts
- next
- OLRAC Signage — 80-TV Rollout Deployment Guide
- PlayerScreen.kt
- tailwind-merge
- run
- tw-animate-css
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
- update_user
- Part B — Operations home page
- ScheduleEvaluator
- DeviceOwnerManager
- ScreenBase
- UtcDateTime
- health_check
- frontend/README.md
- create_checkout
- ContentBase
- rules/graphify.md
- workflows/graphify.md
- theme-toggle.tsx
- @dnd-kit/core
- AGENTS.md
- lucide-react
- next-themes
- qrcode.react
- react
- recharts
- start-dev.ps1
- PlaylistBase
- ScreenSignInRequest
- @tanstack/react-query

## God Nodes (most connected - your core abstractions)
1. `TenantScope` - 72 edges
2. `cn()` - 72 edges
3. `useAuthStore` - 34 edges
4. `utcnow()` - 29 edges
5. `Button()` - 25 edges
6. `api` - 23 edges
7. `relativeTime()` - 22 edges
8. `MainActivity` - 20 edges
9. `get_password_hash()` - 20 edges
10. `Skeleton()` - 20 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `utcnow()`  [EXTRACTED]
  tests/test_feature_parity.py → backend/models.py
- `run()` --calls--> `utcnow()`  [EXTRACTED]
  tests/test_tenant_isolation.py → backend/models.py
- `run()` --calls--> `Organization`  [EXTRACTED]
  tests/test_feature_parity.py → backend/models.py
- `setup_db()` --calls--> `Organization`  [EXTRACTED]
  tests/test_media_worker.py → backend/models.py
- `run()` --calls--> `User`  [EXTRACTED]
  tests/test_feature_parity.py → backend/models.py

## Import Cycles
- None detected.

## Communities (133 total, 32 thin omitted)

### Community 0 - "models.py"
Cohesion: 0.08
Nodes (47): Campaign, EmergencyBroadcast, EnrollmentToken, Organization, Plan, Playlist, PlaylistItem, PlayLog (+39 more)

### Community 1 - "schemas.py"
Cohesion: 0.14
Nodes (26): AppReleaseCreate, AppReleaseResponse, AppVersionResponse, BillingSummaryResponse, DeviceAuthRequest, DeviceTokenResponse, EnrollmentTokenCreate, EnrollmentTokenResponse (+18 more)

### Community 2 - "PlaylistItemEntity"
Cohesion: 0.24
Nodes (3): PlaylistDao, PlaylistItemEntity, Flow

### Community 3 - "ApiService.kt"
Cohesion: 0.07
Nodes (25): ApiClient, Context, ApiService, AppVersionDto, ContentDto, EnrollRequest, EnrollResponse, HeartbeatRequest (+17 more)

### Community 4 - "MainActivity"
Cohesion: 0.06
Nodes (28): CheckingLocalState, DeviceState, LaunchState, LaunchStateResolver, Pairing, Playing, RegistrationSnapshot, SignIn (+20 more)

### Community 5 - "content/[id]/page.tsx"
Cohesion: 0.17
Nodes (16): orientationLabel(), ScreenDetailPage(), AssignPlaylistCard(), EmptyState(), dateTime(), ScreenDetailsDrawer(), ScreenHoursDialog(), withDefaults() (+8 more)

### Community 6 - "PlaybackService"
Cohesion: 0.08
Nodes (18): ConnectivityWatcher, Context, Intent, Job, PlaybackService, requestImmediateSync(), scheduleWorkers(), start() (+10 more)

### Community 7 - "screens.py"
Cohesion: 0.10
Nodes (46): Screen, Selects the most appropriate media rendition for a screen based on its hardware…, select_rendition(), Return a timezone-aware UTC timestamp., utcnow(), verify_password(), as_aware_utc(), assign_playlist() (+38 more)

### Community 8 - "MainActivity"
Cohesion: 0.10
Nodes (16): android.accessibilityservice.AccessibilityService, android.app.Activity, android.content.BroadcastReceiver, android.content.Context, android.content.Intent, android.os.Bundle, android.os.Handler, android.view.accessibility.AccessibilityEvent (+8 more)

### Community 9 - "AbleSign Auto-Launch — Full Documentation"
Cohesion: 0.07
Nodes (28): AbleSign Auto-Launch — Full Documentation, AbleSign not launching after reboot, Build commands, Check if watchdog is running, Files in This Folder, How to Install on ANY Android TV, How to Rebuild the APK (if you change the code), If Something Goes Wrong (+20 more)

### Community 10 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 11 - "main.py"
Cohesion: 0.08
Nodes (40): ensure_billing_catalog(), plan_features(), Plan, Session, get_db(), OLRAC Signage backend package. Explicit package marker. Without it `backend` is…, lifespan(), Request (+32 more)

### Community 12 - "field_validator"
Cohesion: 0.14
Nodes (9): HeartbeatRequest, Each day maps to exactly [start, end] as HH:MM. Validated here rather than in…, Partial screen update: only the fields actually present are written. The PUT…, ScheduleBase, ScheduleResponse, ScreenPatch, UserCreate, UserUpdate (+1 more)

### Community 13 - "auth.py"
Cohesion: 0.16
Nodes (21): get_redis(), ensure_initial_owner(), get_current_user(), get_current_user_ws(), get_or_create_default_organization(), get_secret_key(), login_for_access_token(), get (+13 more)

### Community 14 - "api.ts"
Cohesion: 0.09
Nodes (32): ApiError, authFetch(), configuredUrl, fetchWithAuth(), WS_BASE, AuthState, AppRelease, BillingSummary (+24 more)

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
Cohesion: 0.06
Nodes (64): Schedule, ScreenshotLog, delete_content(), generate_video_thumbnail(), get_all_content(), delete, get, post (+56 more)

### Community 19 - "resolve_rotation"
Cohesion: 0.23
Nodes (12): normalise(), Resolve the rotation a screen should apply to one playlist item. The player…, Coerce anything to one of 0/90/180/270, defaulting to 0., Degrees the player should rotate this item on this screen., resolve_rotation(), Rotation precedence — pure logic, no database, no device. Run directly: python…, A screen mounted portrait with one item deliberately pinned to landscape., test_defaults_when_nothing_is_set() (+4 more)

### Community 20 - "AppDatabase"
Cohesion: 0.14
Nodes (8): AppDatabase, getDatabase(), Context, migrate(), PlayEventDao, PlayEventEntity, RoomDatabase, SupportSQLiteDatabase

### Community 21 - "worker.py"
Cohesion: 0.16
Nodes (18): Content, MediaRendition, public_upload_url(), compute_sha256(), probe_file(), process_media(), process_media_sync(), recover_stuck_processing() (+10 more)

### Community 22 - "dependencies"
Cohesion: 0.12
Nodes (17): @base-ui/react, class-variance-authority, clsx, dependencies, @base-ui/react, class-variance-authority, clsx, react-dom (+9 more)

### Community 23 - "devDependencies"
Cohesion: 0.12
Nodes (17): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node (+9 more)

### Community 24 - "trigger_emergency_broadcast"
Cohesion: 0.32
Nodes (8): BroadcastRequest, cancel_emergency_broadcast(), get_active_broadcasts(), BaseModel, get, post, Session, trigger_emergency_broadcast()

### Community 25 - "OLRAC Signage"
Cohesion: 0.11
Nodes (16): Acceptance checks, Build-time server configuration, Install and pair, Kiosk and boot provisioning, OLRAC Android TV player, Supported devices, 1. Configure the backend, 2. Apply database migrations (+8 more)

### Community 26 - "TransitionType"
Cohesion: 0.19
Nodes (11): fromWire(), TransitionSpec, TransitionSpecResolver, TransitionType, FADE, NONE, SLIDE_DOWN, SLIDE_LEFT (+3 more)

### Community 27 - "PlaylistItemBase"
Cohesion: 0.18
Nodes (6): PlaylistItemBase, PlaylistItemCreate, PlaylistItemResponse, PlaylistItemUpdate, PlaylistUpdate, model_validator

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
Cohesion: 0.29
Nodes (7): CoroutineWorker, Result, PlayEventDto, PlayLogBatchRequest, ProofOfPlayApi, ProofOfPlayWorker, retrofit2

### Community 33 - "package.json"
Cohesion: 0.22
Nodes (8): name, private, scripts, build, dev, lint, start, version

### Community 34 - "PlayerLauncher"
Cohesion: 0.54
Nodes (3): Context, Intent, PlayerLauncher

### Community 35 - "content/page.tsx"
Cohesion: 0.14
Nodes (34): QueuedUpload, FileSort, SORTS, StatusFilter, roleDescription, AssetCard(), AssetGrid(), OverlayBadge() (+26 more)

### Community 36 - "analytics.py"
Cohesion: 0.22
Nodes (15): export_campaign_report(), get_campaign_info(), get_campaign_stats(), get_campaign_timeseries(), get_media_report(), list_campaigns(), get, Session (+7 more)

### Community 37 - "OLRAC Signage — Build Goal & Agent Work Order"
Cohesion: 0.12
Nodes (15): 10. Phase P7 — Remote player updates (R9), 11. Regression suite — run after every phase, 12. Definition of done, 13. Rules for the implementing agent, 1. Product requirements (the contract), 1a. Verified status — audit of 2026-08-07, 2. Current state — audit (original, pre-implementation), 3. Phase P0 — Offline-first playback (fix D1) (+7 more)

### Community 38 - "AbleSign Watchdog — TV Setup"
Cohesion: 0.13
Nodes (14): AbleSign Watchdog — TV Setup, For the AI Assistant (OpenCode), Option 1 — Realtek TV, Option 2 — Realme TV, Option 3 — Other Android TV, Step 1 — Check ADB, Step 2 — Ask Which TV, Step 3 — Connect to TV (+6 more)

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

### Community 51 - "dashboard/layout.tsx"
Cohesion: 0.29
Nodes (8): accountLinks, adminLinks, DashboardLayout(), primaryLinks, DropdownMenuContent(), DropdownMenuLabel(), DropdownMenuLinkItem(), DropdownMenuSeparator()

### Community 53 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 74 - "billing/page.tsx"
Cohesion: 0.31
Nodes (5): BillingPage(), percent(), Badge(), badgeVariants, Plan

### Community 80 - "OLRAC Signage — 80-TV Rollout Deployment Guide"
Cohesion: 0.17
Nodes (11): 1. Server Environment Setup, 2. Storage Configuration, 3. Start the Stack, 4. Database Migration, 5. Create the Platform Owner, 6. TV Enrollment & Provisioning, 7. Watchdog Setup (Crucial for Budget TVs), Build the Watchdog (+3 more)

### Community 81 - "PlayerScreen.kt"
Cohesion: 0.36
Nodes (8): awaitPlayerReady(), DualSurfacePlayer(), ExoPlayer, PlaybackSurface(), PlayerScreen(), preparePlayer(), transitionLayer(), Modifier

### Community 83 - "run"
Cohesion: 0.53
Nodes (5): auth_header(), main(), TestClient, Runnable backend parity check: python tests/test_feature_parity.py, run()

### Community 85 - "P9 — Zero-touch provisioning for 80+ TVs (no ADB)"
Cohesion: 0.20
Nodes (9): 1. Make the app a working Device Policy Controller, 2. Silent updates (finishes P7), 3. Generate the provisioning QR, 4. Auto-enrol on first boot, 5. Retire the accessibility watchdog on provisioned devices, Definition of done, Deployment paths, in order of preference, P9 — Zero-touch provisioning for 80+ TVs (no ADB) (+1 more)

### Community 89 - "useAuthStore"
Cohesion: 0.11
Nodes (27): Alert, AlertsPage(), buildAlerts(), hoursSince(), Severity, AdDetailPage(), ContentPage(), isSupported() (+19 more)

### Community 90 - "Player"
Cohesion: 0.25
Nodes (5): Player, DecoderSnapshot, Player, PlaybackException, Player

### Community 91 - "playlist-builder.tsx"
Cohesion: 0.14
Nodes (17): MediaThumbnail(), dayLabels, dayNames, DefaultTransitionPanel(), ItemRow(), PlaylistBuilder(), previewStyle(), rotationLabel() (+9 more)

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
Cohesion: 0.33
Nodes (6): AppRelease, create_release(), list_releases(), get, post, Session

### Community 98 - "update_user"
Cohesion: 0.33
Nodes (6): delete_user(), list_users(), delete, get, put, update_user()

### Community 99 - "Part B — Operations home page"
Cohesion: 0.12
Nodes (16): Backend, Dashboard, Definition of done, Definition of done, Every panel below uses data that already exists, Layout, Order of work, P10 — Display rotation, and an operations home page (+8 more)

### Community 102 - "ScreenBase"
Cohesion: 0.50
Nodes (3): ScreenBase, ScreenCreate, ScreenResponse

### Community 106 - "UtcDateTime"
Cohesion: 0.40
Nodes (3): A DateTime that always reads back as timezone-aware UTC. Postgres with…, UtcDateTime, TypeDecorator

### Community 107 - "health_check"
Cohesion: 0.50
Nodes (4): health_check(), get, Session, read_root()

### Community 108 - "frontend/README.md"
Cohesion: 0.50
Nodes (3): Deploy on Vercel, Getting Started, Learn More

### Community 109 - "create_checkout"
Cohesion: 0.67
Nodes (3): create_checkout(), CheckoutRequest, CheckoutResponse

### Community 110 - "ContentBase"
Cohesion: 0.67
Nodes (3): ContentBase, ContentResponse, ContentUpdate

### Community 113 - "theme-toggle.tsx"
Cohesion: 0.83
Nodes (3): subscribe(), ThemeToggle(), useHydrated()

### Community 130 - "PlaylistBase"
Cohesion: 0.67
Nodes (3): PlaylistBase, PlaylistCreate, PlaylistResponse

## Knowledge Gaps
- **259 isolated node(s):** `CheckingLocalState`, `NONE`, `FADE`, `SLIDE_LEFT`, `SLIDE_RIGHT` (+254 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PlaylistItemEntity` connect `PlaylistItemEntity` to `ScheduleEvaluatorTest`, `ScheduleEvaluator`, `PlaybackService`, `PlayerScreen.kt`, `TransitionType`, `PlayerViewModel`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `PlayerScreen()` connect `PlayerScreen.kt` to `PlaybackTelemetry`, `MainActivity`, `PlayerViewModel`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Why does `PlaybackTelemetry` connect `PlaybackTelemetry` to `PlayerScreen.kt`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **What connects `CheckingLocalState`, `NONE`, `FADE` to the rest of the system?**
  _259 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `models.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0847457627118644 - nodes in this community are weakly interconnected._
- **Should `schemas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14245014245014245 - nodes in this community are weakly interconnected._
- **Should `ApiService.kt` be split into smaller, more focused modules?**
  _Cohesion score 0.07123034227567067 - nodes in this community are weakly interconnected._