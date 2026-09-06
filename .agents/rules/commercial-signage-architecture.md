# Commercial Signage Architecture & Domain Invariants

## 1. Strict Separation of Creative Assets vs. Commercial Bookings
- **Creative / Asset Metadata**: Components and endpoints dealing with content assets (e.g., `EditClientAdModal`, `Content` routes) must strictly manage media metadata: creative title, media files, advertiser brand name, contact email/phone, tags, and campaign reference notes.
- **Commercial Placements & Booking**: Pricing plans, custom rate negotiation, campaign run dates (`starts_at`, `ends_at`), target screen/group allocations, and extensions belong exclusively to the booking domain (`CreateBookingModal`, `AdBookings`, `placements` service). Never duplicate plan or screen assignment controls inside asset-editing modals.

## 2. Backend Clean Architecture Layers
- **Thin Controllers**: FastAPI routers in `backend/routers/` must remain thin HTTP adapters. Input validation, scope verification, and HTTP response mapping belong in routers; business rules, quota checks, and transaction management belong in `backend/services/`.
- **Repository Isolation**: Database queries must use repository interfaces (`backend/repositories/`) to keep database access testable and swappable.

## 3. Screen Quota & Plan Cap Invariants
- When checking screen limits against a pricing package (`max_locations`), always evaluate effective screen coverage: direct screen targets PLUS all screens inherited through venue group targets.
- A booking moved off a plan onto a custom negotiated rate must explicitly clear the plan binding so it is no longer restricted by that plan's location cap.
