# Graph Report - .  (2026-08-08)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1171 nodes · 2405 edges · 119 communities (71 shown, 48 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 28 edges (avg confidence: 0.71)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- models.py
- schemas.py
- PlaylistItemEntity
- ApiService.kt
- MainActivity
- screens/page.tsx
- PlaybackService
- screens.py
- MainActivity
- emergency/page.tsx
- compilerOptions
- main.py
- TenantScope
- api.ts
- content.py
- components.json
- cn
- PlayerSupervisor
- playlists.py
- routers/billing.py
- AppDatabase
- PlaybackTelemetry
- dependencies
- devDependencies
- get_redis
- useAuthStore
- TransitionType
- playlists/[id]/page.tsx
- app/layout.tsx
- provider.py
- StorageManagerTest
- conftest.py
- .doWork
- package.json
- PlayerLauncher
- ScreenshotManager
- analytics.py
- SignageDeviceAdminReceiver
- button.tsx
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
- validation.py
- ConnectivityWatcher
- SyncBackoffPolicyTest
- gradlew
- e2e_test.py
- clsx
- @dnd-kit/sortable
- @dnd-kit/utilities
- eslint.config.mjs
- next.config.ts
- next
- react-dom
- sonner
- tailwind-merge
- @tanstack/react-query
- tw-animate-css
- zustand
- postcss.config.mjs
- backup_db.sh
- validation_script.sh
- String
- Boolean
- Int
- String
- String
- Boolean
- Int
- Int
- String
- Boolean
- Boolean
- List
- String
- List
- BaseModel
- BroadcastReceiver
- Bundle
- ExoPlayer
- File
- Float
- Job
- Response
- Set
- TestClient
- Unit
- UploadFile

## God Nodes (most connected - your core abstractions)
1. `TenantScope` - 67 edges
2. `cn()` - 58 edges
3. `utcnow()` - 26 edges
4. `useAuthStore` - 24 edges
5. `Button()` - 18 edges
6. `MainActivity` - 18 edges
7. `get_password_hash()` - 18 edges
8. `compilerOptions` - 16 edges
9. `PlaybackService` - 16 edges
10. `Organization` - 16 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `utcnow()`  [EXTRACTED]
  tests/test_feature_parity.py → backend/models.py
- `run()` --calls--> `utcnow()`  [EXTRACTED]
  tests/test_tenant_isolation.py → backend/models.py
- `run()` --calls--> `TenantScope`  [EXTRACTED]
  tests/manual_pipeline_check.py → backend/tenancy.py
- `create_checkout()` --calls--> `get_payment_provider()`  [INFERRED]
  backend/routers/billing.py → backend/payments/provider.py
- `SortableItemCard()` --calls--> `cn()`  [EXTRACTED]
  frontend/src/app/dashboard/playlists/[id]/page.tsx → frontend/src/lib/utils.ts

## Import Cycles
- None detected.

## Communities (119 total, 48 thin omitted)

### Community 0 - "models.py"
Cohesion: 0.05
Nodes (82): AppRelease, Campaign, Content, EmergencyBroadcast, EnrollmentToken, MediaRendition, Organization, Plan (+74 more)

### Community 1 - "schemas.py"
Cohesion: 0.05
Nodes (61): Screen, Selects the most appropriate media rendition for a screen based on its hardware…, select_rendition(), create_checkout(), create_release(), list_releases(), get, post (+53 more)

### Community 2 - "PlaylistItemEntity"
Cohesion: 0.05
Nodes (32): Boolean, Int, List, String, PlaylistDao, PlaylistItemEntity, Boolean, String (+24 more)

### Community 3 - "ApiService.kt"
Cohesion: 0.06
Nodes (30): CheckingLocalState, DeviceState, Boolean, String, LaunchState, LaunchStateResolver, Pairing, Playing (+22 more)

### Community 4 - "MainActivity"
Cohesion: 0.09
Nodes (18): BrandedMessage(), Bundle, MainActivity, PairingScreen(), secondaryButtonColors(), ServerControls(), ServerSetupScreen(), SetupSurface() (+10 more)

### Community 5 - "screens/page.tsx"
Cohesion: 0.20
Nodes (17): roleDescription, EmptyState(), ErrorState(), PageHeader(), Badge(), badgeVariants, Dialog(), DialogContent() (+9 more)

### Community 6 - "PlaybackService"
Cohesion: 0.08
Nodes (18): Context, Intent, Job, PlaybackService, requestImmediateSync(), scheduleWorkers(), start(), ActivationTarget (+10 more)

### Community 7 - "screens.py"
Cohesion: 0.14
Nodes (33): datetime, Return a timezone-aware UTC timestamp., utcnow(), as_aware_utc(), assign_playlist(), batch_upload_play_logs(), clear_direct_assignment(), current_app_version() (+25 more)

### Community 8 - "MainActivity"
Cohesion: 0.10
Nodes (16): android.accessibilityservice.AccessibilityService, android.app.Activity, android.content.BroadcastReceiver, android.content.Context, android.content.Intent, android.os.Bundle, android.os.Handler, android.view.accessibility.AccessibilityEvent (+8 more)

### Community 9 - "emergency/page.tsx"
Cohesion: 0.13
Nodes (23): CampaignAnalyticsPage(), fetchCampaignInfo(), fetchCampaignStats(), fetchCampaignTimeSeries(), CampaignsPage(), fetchCampaigns(), Card(), CardAction() (+15 more)

### Community 10 - "compilerOptions"
Cohesion: 0.06
Nodes (30): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+22 more)

### Community 11 - "main.py"
Cohesion: 0.15
Nodes (18): get_db(), OLRAC Signage backend package. Explicit package marker. Without it `backend` is…, health_check(), lifespan(), get, Session, read_root(), create_token() (+10 more)

### Community 12 - "TenantScope"
Cohesion: 0.14
Nodes (21): delete, revoke_token(), assign_group_playlist(), create_group(), delete_group(), list_groups(), delete, get (+13 more)

### Community 13 - "api.ts"
Cohesion: 0.14
Nodes (21): ScreenDetailPage(), selectRendition(), ApiError, AuthState, AppRelease, BillingSummary, CheckoutSession, ContentItem (+13 more)

### Community 14 - "content.py"
Cohesion: 0.14
Nodes (22): delete_content(), generate_video_thumbnail(), get_all_content(), delete, get, post, put, UploadFile (+14 more)

### Community 15 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 16 - "cn"
Cohesion: 0.17
Nodes (17): DashboardLayout(), primaryLinks, StatusIndicator(), options, subscribe(), ThemeToggle(), useHydrated(), DialogOverlay() (+9 more)

### Community 17 - "PlayerSupervisor"
Cohesion: 0.15
Nodes (9): ExoPlayer, Job, PlaybackException, onPlayerError(), PlayerSupervisor, Context, ExoPlayer, PlaybackTelemetry (+1 more)

### Community 18 - "playlists.py"
Cohesion: 0.24
Nodes (18): add_item_to_playlist(), bump_playlist(), create_playlist(), delete_playlist(), get_playlist(), get_playlists(), delete, get (+10 more)

### Community 19 - "routers/billing.py"
Cohesion: 0.18
Nodes (16): ensure_billing_catalog(), plan_features(), Plan, Session, billing_summary(), list_plans(), datetime, get (+8 more)

### Community 20 - "AppDatabase"
Cohesion: 0.13
Nodes (9): AppDatabase, getDatabase(), Context, migrate(), PlayEventDao, PlayEventEntity, PlaylistDao, RoomDatabase (+1 more)

### Community 21 - "PlaybackTelemetry"
Cohesion: 0.18
Nodes (9): Int, String, PlaybackSnapshot, PlaybackTelemetry, enqueue(), Context, CoroutineWorker, Result (+1 more)

### Community 22 - "dependencies"
Cohesion: 0.12
Nodes (17): @base-ui/react, class-variance-authority, @dnd-kit/core, dependencies, @base-ui/react, class-variance-authority, @dnd-kit/core, lucide-react (+9 more)

### Community 23 - "devDependencies"
Cohesion: 0.12
Nodes (17): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node (+9 more)

### Community 24 - "get_redis"
Cohesion: 0.20
Nodes (15): get_redis(), BroadcastRequest, cancel_emergency_broadcast(), get_active_broadcasts(), BaseModel, get, post, Session (+7 more)

### Community 25 - "useAuthStore"
Cohesion: 0.18
Nodes (15): BillingPage(), percent(), ContentPage(), EnrollmentPage(), DashboardPage(), PlaylistBuilderPage(), PlaylistsPage(), ScreenCard() (+7 more)

### Community 26 - "TransitionType"
Cohesion: 0.17
Nodes (13): fromWire(), Int, String, TransitionSpec, TransitionSpecResolver, TransitionType, FADE, NONE (+5 more)

### Community 27 - "playlists/[id]/page.tsx"
Cohesion: 0.19
Nodes (13): dayLabels, dayNames, DefaultTransitionPanel(), ItemTransitionEditor(), previewStyle(), ScheduleEditor(), SortableItemCard(), transitionLabel() (+5 more)

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
Nodes (7): PlayEventDto, PlayLogBatchRequest, ProofOfPlayApi, ProofOfPlayWorker, CoroutineWorker, Result, retrofit2

### Community 33 - "package.json"
Cohesion: 0.22
Nodes (8): name, private, scripts, build, dev, lint, start, version

### Community 34 - "PlayerLauncher"
Cohesion: 0.54
Nodes (3): Context, Intent, PlayerLauncher

### Community 35 - "ScreenshotManager"
Cohesion: 0.39
Nodes (4): Activity, ScreenshotManager, Bitmap, WeakReference

### Community 36 - "analytics.py"
Cohesion: 0.54
Nodes (7): export_campaign_report(), get_campaign_info(), get_campaign_stats(), get_campaign_timeseries(), list_campaigns(), get, Session

### Community 37 - "SignageDeviceAdminReceiver"
Cohesion: 0.38
Nodes (4): Context, Intent, SignageDeviceAdminReceiver, DeviceAdminReceiver

### Community 38 - "button.tsx"
Cohesion: 0.43
Nodes (3): LoginPage(), Button(), buttonVariants

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
Nodes (4): Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online()

### Community 50 - "validation.py"
Cohesion: 0.60
Nodes (4): owner_headers(), TestClient, Isolated storage and failure-path validation: python tests/validation.py, run()

### Community 53 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

## Knowledge Gaps
- **105 isolated node(s):** `RegistrationSnapshot`, `NONE`, `FADE`, `SLIDE_LEFT`, `SLIDE_RIGHT` (+100 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **48 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PlaylistItemEntity` connect `PlaylistItemEntity` to `TransitionType`, `PlaybackService`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `TenantScope` connect `TenantScope` to `models.py`, `schemas.py`, `analytics.py`, `screens.py`, `main.py`, `content.py`, `playlists.py`, `routers/billing.py`, `get_redis`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Why does `PlayerScreen()` connect `PlaylistItemEntity` to `MainActivity`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **What connects `RegistrationSnapshot`, `NONE`, `FADE` to the rest of the system?**
  _105 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `models.py` be split into smaller, more focused modules?**
  _Cohesion score 0.051089108910891086 - nodes in this community are weakly interconnected._
- **Should `schemas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0505175983436853 - nodes in this community are weakly interconnected._
- **Should `PlaylistItemEntity` be split into smaller, more focused modules?**
  _Cohesion score 0.05201636469900643 - nodes in this community are weakly interconnected._