# Graph Report - .  (2026-08-07)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 787 nodes · 1492 edges · 53 communities (38 shown, 15 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 11 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- cn
- PlaylistItemEntity
- schemas.py
- MainActivity
- dependencies
- auth.py
- compilerOptions
- PlaybackService
- ApiService.kt
- devDependencies
- models.py
- PlaybackTelemetry
- main.py
- components.json
- PlaylistSynchronizer
- screens.py
- TenantScope
- get_payment_provider
- layout.tsx
- test_quotas.py
- content.py
- .isActive
- groups.py
- ScriptItem
- AppDatabase
- users.py
- BootReceiver
- ApiClientTest
- .query
- SyncBackoffPolicy
- HeartbeatWorker
- LaunchStateResolverTest
- TransitionSpecResolverTest
- SyncBackoffPolicyTest
- quotedBuildConfig
- CacheCleanupTest
- e2e_test.py
- eslint.config.mjs
- next.config.ts
- next-env.d.ts
- postcss.config.mjs
- backup_db.sh
- validation_script.sh

## God Nodes (most connected - your core abstractions)
1. `cn()` - 56 edges
2. `TenantScope` - 45 edges
3. `useAuthStore` - 22 edges
4. `MainActivity` - 16 edges
5. `PlaybackService` - 16 edges
6. `compilerOptions` - 16 edges
7. `PlaylistItemEntity` - 14 edges
8. `Button()` - 13 edges
9. `relativeTime()` - 12 edges
10. `get_password_hash()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `get_password_hash()`  [EXTRACTED]
  tests/test_feature_parity.py → backend/routers/auth.py
- `build_org_b()` --calls--> `get_password_hash()`  [EXTRACTED]
  tests/test_tenant_isolation.py → backend/routers/auth.py
- `delete_content()` --references--> `TenantScope`  [EXTRACTED]
  backend/routers/content.py → backend/tenancy.py
- `delete_group()` --references--> `TenantScope`  [EXTRACTED]
  backend/routers/groups.py → backend/tenancy.py
- `assign_playlist()` --references--> `TenantScope`  [EXTRACTED]
  backend/routers/screens.py → backend/tenancy.py

## Import Cycles
- 1-file cycle: `backend/routers/__init__.py -> backend/routers/__init__.py`

## Communities (53 total, 15 thin omitted)

### Community 0 - "cn"
Cohesion: 0.05
Nodes (95): BillingPage(), percent(), ContentPage(), DashboardLayout(), primaryLinks, DashboardPage(), dayLabels, dayNames (+87 more)

### Community 1 - "PlaylistItemEntity"
Cohesion: 0.05
Nodes (40): Boolean, Int, List, String, PlaylistDao, PlaylistItemEntity, fromWire(), Int (+32 more)

### Community 2 - "schemas.py"
Cohesion: 0.07
Nodes (38): update_screen(), update_user(), AppVersionResponse, BillingSummaryResponse, CheckoutRequest, CheckoutResponse, ContentBase, ContentResponse (+30 more)

### Community 3 - "MainActivity"
Cohesion: 0.11
Nodes (22): CheckingLocalState, DeviceState, Boolean, String, LaunchState, LaunchStateResolver, Pairing, Playing (+14 more)

### Community 4 - "dependencies"
Cohesion: 0.06
Nodes (35): @base-ui/react, class-variance-authority, clsx, @dnd-kit/core, @dnd-kit/sortable, @dnd-kit/utilities, dependencies, @base-ui/react (+27 more)

### Community 5 - "auth.py"
Cohesion: 0.11
Nodes (26): create_access_token(), ensure_initial_owner(), get_current_user(), get_or_create_default_organization(), get_password_hash(), get_secret_key(), login_for_access_token(), Session (+18 more)

### Community 6 - "compilerOptions"
Cohesion: 0.06
Nodes (30): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+22 more)

### Community 7 - "PlaybackService"
Cohesion: 0.12
Nodes (13): ConnectivityWatcher, Boolean, Context, Int, Intent, PlaybackService, requestImmediateSync(), scheduleWorkers() (+5 more)

### Community 8 - "ApiService.kt"
Cohesion: 0.13
Nodes (16): ApiClient, Context, String, ApiService, AppVersionDto, ContentDto, HeartbeatRequest, String (+8 more)

### Community 9 - "devDependencies"
Cohesion: 0.08
Nodes (25): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node (+17 more)

### Community 10 - "models.py"
Cohesion: 0.12
Nodes (19): Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online(), Content, Organization, Plan, Playlist (+11 more)

### Community 11 - "PlaybackTelemetry"
Cohesion: 0.13
Nodes (12): HeartbeatReporter, Boolean, Context, Int, String, PlaybackSnapshot, PlaybackTelemetry, enqueue() (+4 more)

### Community 12 - "main.py"
Cohesion: 0.15
Nodes (18): ensure_billing_catalog(), plan_features(), Plan, Session, health_check(), lifespan(), Session, billing_summary() (+10 more)

### Community 13 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 14 - "PlaylistSynchronizer"
Cohesion: 0.15
Nodes (11): ActivationTarget, Int, String, PlaylistSynchronizer, StagedDownload, SyncOutcome, CoroutineWorker, Result (+3 more)

### Community 15 - "screens.py"
Cohesion: 0.18
Nodes (17): as_naive_utc(), assign_playlist(), clear_direct_assignment(), current_app_version(), generate_pair_code(), get_screens(), heartbeat(), pair_screen() (+9 more)

### Community 16 - "TenantScope"
Cohesion: 0.26
Nodes (16): add_item_to_playlist(), bump_playlist(), create_playlist(), delete_playlist(), get_playlist(), get_playlists(), remove_item_from_playlist(), reorder_playlist_items() (+8 more)

### Community 17 - "get_payment_provider"
Cohesion: 0.27
Nodes (7): CheckoutSession, get_payment_provider(), MockPaymentProvider, PaymentProvider, RazorpayProvider, create_checkout(), Protocol

### Community 18 - "layout.tsx"
Cohesion: 0.19
Nodes (8): geistMono, geistSans, metadata, Providers(), Toaster(), TransitionClass, ViewTransition(), ViewTransitionProps

### Community 19 - "test_quotas.py"
Cohesion: 0.24
Nodes (10): auth_header(), pair_one_screen(), TestClient, Plan-limit enforcement check: python tests/test_quotas.py  Covers GOAL.md T6.1 (, Register a TV then pair it as the admin. Returns the pair response., run(), owner_headers(), TestClient (+2 more)

### Community 20 - "content.py"
Cohesion: 0.33
Nodes (10): delete_content(), generate_video_thumbnail(), get_all_content(), public_upload_url(), serialize_content(), update_content(), upload_content(), is_s3_enabled() (+2 more)

### Community 21 - ".isActive"
Cohesion: 0.33
Nodes (5): Boolean, String, ScheduleEvaluator, LocalDateTime, LocalTime

### Community 22 - "groups.py"
Cohesion: 0.39
Nodes (8): assign_group_playlist(), create_group(), delete_group(), list_groups(), serialize_group(), set_group_screens(), update_group(), ScreenGroup

### Community 23 - "ScriptItem"
Cohesion: 0.28
Nodes (4): pytest_collect_file(), Run each backend test script in its own process.  `backend/database.py` builds t, ScriptFile, ScriptItem

### Community 24 - "AppDatabase"
Cohesion: 0.29
Nodes (6): AppDatabase, getDatabase(), Context, migrate(), RoomDatabase, SupportSQLiteDatabase

### Community 25 - "users.py"
Cohesion: 0.29
Nodes (6): delete_user(), list_users(), get_tenant_scope(), Session, User, require_tenant_roles()

### Community 26 - "BootReceiver"
Cohesion: 0.33
Nodes (4): BootReceiver, Context, Intent, BroadcastReceiver

### Community 30 - "HeartbeatWorker"
Cohesion: 0.40
Nodes (3): HeartbeatWorker, CoroutineWorker, Result

## Knowledge Gaps
- **105 isolated node(s):** `NONE`, `FADE`, `SLIDE_LEFT`, `SLIDE_RIGHT`, `SLIDE_UP` (+100 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PlaylistItemEntity` connect `PlaylistItemEntity` to `.isActive`, `PlaylistSynchronizer`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `PlayerScreen()` connect `PlaylistItemEntity` to `PlaybackTelemetry`, `MainActivity`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `DualSurfacePlayer()` connect `PlaylistItemEntity` to `PlaybackTelemetry`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **What connects `NONE`, `FADE`, `SLIDE_LEFT` to the rest of the system?**
  _118 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `cn` be split into smaller, more focused modules?**
  _Cohesion score 0.05196078431372549 - nodes in this community are weakly interconnected._
- **Should `PlaylistItemEntity` be split into smaller, more focused modules?**
  _Cohesion score 0.05141242937853107 - nodes in this community are weakly interconnected._
- **Should `schemas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07400555041628122 - nodes in this community are weakly interconnected._