import secrets
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text, Time, JSON, Float
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import TypeDecorator

from .database import Base


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class UtcDateTime(TypeDecorator):
    """A DateTime that always reads back as timezone-aware UTC.

    Postgres with timezone=True already does this, but SQLite silently drops the
    tzinfo, so the same row served from a dev database came back naive and every
    JSON client re-read it as *local* time. In IST that shifted last_seen by
    5h30m, which made healthy screens look hours stale. Normalising on read keeps
    SQLite and Postgres serving identical instants.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        # SQLite stores the naive part, so convert to UTC first rather than
        # letting a non-UTC offset be truncated into the wrong wall time.
        if isinstance(value, datetime) and value.tzinfo is not None:
            return value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    monthly_price_paise = Column(Integer, nullable=False, default=0)
    yearly_price_paise = Column(Integer, nullable=False, default=0)
    max_screens = Column(Integer, nullable=False)
    max_storage_bytes = Column(BigInteger, nullable=False)
    # 0 = unlimited, matching Organization.max_ad_slots. A package carries the default;
    # Organization.max_ad_slots overrides it for one tenant without editing the package.
    max_ad_slots = Column(Integer, nullable=False, default=0, server_default="0")
    feature_flags_json = Column(Text, nullable=False, default="{}")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)

    organizations = relationship("Organization", back_populates="plan")
    subscriptions = relationship("Subscription", back_populates="plan")


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    status = Column(String, nullable=False, default="active") # pending_approval, active, suspended, rejected
    approved_at = Column(UtcDateTime, nullable=True)
    approved_by_user_id = Column(Integer, nullable=True)
    rejection_reason = Column(String, nullable=True)
    storage_quota_bytes = Column(BigInteger, nullable=False, default=10 * 1024 * 1024 * 1024)
    # Per-tenant quotas set by Super Admin. 0 = unlimited (default).
    max_screens = Column(Integer, nullable=False, default=0)
    max_ad_slots = Column(Integer, nullable=False, default=0)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)

    users = relationship("User", back_populates="organization")
    screens = relationship("Screen", back_populates="organization")
    groups = relationship("ScreenGroup", back_populates="organization")
    content = relationship("Content", back_populates="organization")
    playlists = relationship("Playlist", back_populates="organization")
    plan = relationship("Plan", back_populates="organizations")
    subscription = relationship("Subscription", back_populates="organization", uselist=False)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(String, nullable=True)
    updated_at = Column(UtcDateTime, nullable=False, default=utcnow, onupdate=utcnow)



class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), unique=True, nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="active")
    billing_period = Column(String, nullable=False, default="monthly")
    current_period_start = Column(UtcDateTime, nullable=True)
    current_period_end = Column(UtcDateTime, nullable=True)
    grace_period_end = Column(UtcDateTime, nullable=True)
    provider = Column(String, nullable=True)
    provider_subscription_id = Column(String, unique=True, nullable=True, index=True)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)
    updated_at = Column(UtcDateTime, nullable=False, default=utcnow, onupdate=utcnow)

    organization = relationship("Organization", back_populates="subscription")
    plan = relationship("Plan", back_populates="subscriptions")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False)
    provider_event_id = Column(String, unique=True, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    received_at = Column(UtcDateTime, nullable=False, default=utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="viewer")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)
    # Profile fields. Nullable because every existing account predates them and username
    # stays the login identifier -- these are display/contact only, so nothing breaks when
    # they are unset.
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    google_sub = Column(String, unique=True, index=True, nullable=True)
    picture = Column(String, nullable=True)
    auth_provider = Column(String, nullable=False, default="local")

    organization = relationship("Organization", back_populates="users", foreign_keys=[organization_id])

    @property
    def organization_name(self) -> str | None:
        """Exposed so UserResponse can show the tenant by name instead of a bare id."""
        return self.organization.name if self.organization else None

    @property
    def organization_status(self) -> str:
        return self.organization.status if self.organization else "active"


class ScreenshotLog(Base):
    __tablename__ = "screenshot_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    screen_id = Column(Integer, ForeignKey("screens.id", ondelete="CASCADE"), nullable=False, index=True)
    file_url = Column(String, nullable=False)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)
    
    screen = relationship("Screen", back_populates="screenshots")
    organization = relationship("Organization")


class ScreenGroup(Base):
    __tablename__ = "screen_groups"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("screen_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String, nullable=False)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True)
    target_version_code = Column(Integer, ForeignKey("app_releases.version_code", ondelete="SET NULL"), nullable=True)
    is_dynamic = Column(Boolean, nullable=False, default=False, server_default="false")
    dynamic_criteria = Column(JSON, nullable=True)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)
    updated_at = Column(UtcDateTime, nullable=False, default=utcnow, onupdate=utcnow)

    playlist = relationship("Playlist", back_populates="groups")
    screens = relationship("Screen", back_populates="group")
    organization = relationship("Organization", back_populates="groups")
    children = relationship("ScreenGroup", backref=backref('parent', remote_side=[id]))


class Screen(Base):
    __tablename__ = "screens"

    id = Column(Integer, primary_key=True, index=True)
    # Unpaired registrations are deliberately unbound until an authenticated
    # organization claims their pairing code.
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=True)
    device_secret_hash = Column(String, nullable=True)
    installation_id = Column(String, nullable=True)
    pair_code = Column(String, unique=True, index=True, nullable=True)
    pair_code_expires_at = Column(UtcDateTime, nullable=True)
    name = Column(String, nullable=True)
    orientation = Column(Integer, default=0)
    # "auto" = whatever the panel last reported; "manual" = an operator set it and the
    # heartbeat must stop overwriting it. Without this an override silently reverts on the
    # next heartbeat, which reads as "rotation keeps resetting itself".
    orientation_source = Column(String, nullable=False, default="auto")
    description = Column(String, nullable=True)
    # Free-form comma-separated labels, the same shape Content.tags uses.
    tags = Column(String, nullable=True)
    # Where the screen physically is. Stored together with the coordinates that produced
    # it so a report's label and its map pin can never disagree; place_id lets a later
    # lookup re-resolve the same place without re-searching by name.
    location = Column(String, nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    place_id = Column(String, nullable=True)
    # How the player letterboxes content whose aspect ratio does not match the panel.
    # "contain" shows the whole frame, "cover" fills the panel and crops.
    fit_mode = Column(String, nullable=False, default="contain")
    # Gate on the player's on-TV maintenance screen, reached by a remote key sequence.
    # Per screen rather than per org so one leaked pin does not open the whole fleet;
    # the player caches it locally because the screen exists to fix connectivity and
    # must therefore work with the server unreachable.
    maintenance_pin = Column(
        String, nullable=False, default=lambda: f"{secrets.randbelow(10000):04d}"
    )
    # Video-wall support: followers take their playback clock from a leader screen.
    sync_playback = Column(Boolean, nullable=False, default=False)
    sync_role = Column(String, nullable=False, default="leader")
    leader_screen_id = Column(Integer, ForeignKey("screens.id", ondelete="SET NULL"), nullable=True)
    # When an operator let this screen into the fleet. NULL means it has claimed an
    # organisation but nobody has confirmed it yet, so it syncs nothing.
    #
    # Its own column rather than a `status` value: status is rewritten to "online" by
    # every heartbeat (see the heartbeat route), so an approval state parked there would
    # be erased within a minute of the screen powering on.
    #
    # Only the self-service routes leave this NULL. /pair and /enroll already prove intent
    # -- one needs an operator at the dashboard, the other a token an operator issued --
    # so re-confirming them would be a second lock on the same door.
    approved_at = Column(UtcDateTime, nullable=True)
    # Mon..Sun operating windows as {"mon": ["00:00", "23:59"], ...}; null means always on.
    operating_hours = Column(JSON, nullable=True)
    # "always" | "hours" | "never" — kept separate so clearing the schedule does not
    # lose the windows an operator already typed in.
    operating_mode = Column(String, nullable=False, default="always")
    status = Column(String, default="offline")
    last_seen = Column(UtcDateTime, nullable=False, default=utcnow)
    device_version = Column(String, nullable=True)
    app_version = Column(String, nullable=True)
    storage_used = Column(String, nullable=True)
    
    # TV Capabilities
    screen_width = Column(Integer, nullable=True)
    screen_height = Column(Integer, nullable=True)
    refresh_rate = Column(Integer, nullable=True) # Integer, or should we use Float? The spec says Float in Kotlin. We can use Float in DB or just Integer for simplicity. Let's use sqlalchemy.Float
    total_ram_mb = Column(Integer, nullable=True)
    available_ram_mb = Column(Integer, nullable=True)
    total_storage_mb = Column(Integer, nullable=True)
    free_storage_mb = Column(Integer, nullable=True)
    supported_video_codecs = Column(JSON, nullable=True)
    max_decode_width = Column(Integer, nullable=True)
    max_decode_height = Column(Integer, nullable=True)
    manufacturer = Column(String, nullable=True)
    model = Column(String, nullable=True)
    android_version = Column(String, nullable=True)
    sdk_int = Column(Integer, nullable=True)
    network_type = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    
    playback_state = Column(String, nullable=False, default="idle")
    current_item_id = Column(Integer, nullable=True)
    last_error = Column(String, nullable=True)
    last_error_at = Column(UtcDateTime, nullable=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True)
    group_id = Column(Integer, ForeignKey("screen_groups.id", ondelete="SET NULL"), nullable=True)
    assignment_updated_at = Column(UtcDateTime, nullable=False, default=utcnow)
    
    target_version_code = Column(Integer, ForeignKey("app_releases.version_code", ondelete="SET NULL"), nullable=True)
    update_status = Column(String, nullable=True) # pending, downloading, installing, success, failed, rolled_back
    # Consecutive failed install attempts of target_version_code. Reset on success and on
    # every re-pin. Once it reaches rollout.ROLLBACK_THRESHOLD the pin is dropped, which
    # is the automatic rollback the fleet-operations spec asks for: without this a screen
    # retried a build that could never install, forever, on every heartbeat.
    update_failure_count = Column(Integer, nullable=False, default=0)

    playlist = relationship("Playlist", back_populates="screens")
    group = relationship("ScreenGroup", back_populates="screens")
    organization = relationship("Organization", back_populates="screens")
    screenshots = relationship("ScreenshotLog", back_populates="screen", cascade="all, delete-orphan")

    @property
    def effective_playlist_id(self):
        return self.playlist_id or (self.group.playlist_id if self.group else None)


class AppRelease(Base):
    __tablename__ = "app_releases"

    id = Column(Integer, primary_key=True, index=True)
    version_code = Column(Integer, unique=True, index=True, nullable=False)
    version_name = Column(String(50), nullable=False)
    apk_url = Column(String(2048), nullable=False)
    sha256 = Column(String(64), nullable=True)
    mandatory = Column(Boolean, nullable=False, default=False)
    # "draft" | "canary" | "released". This is what makes a staged rollout possible.
    #
    # The global fallback in current_app_version hands every unpinned screen the highest
    # version_code it can find. While every release was implicitly live, publishing one
    # *was* shipping it to the entire fleet, so a canary ring could not exist: the 5 test
    # TVs and the other 495 were offered the same build the moment it was created.
    #
    # Only "released" rows are eligible for that fallback. A draft or canary build reaches
    # a screen solely through an explicit target_version_code pin, which is how a ring is
    # built -- 5 screens, then 20, then promote to "released" for the rest.
    rollout_state = Column(String, nullable=False, default="draft", index=True)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint(
            "rollout_state IN ('draft', 'canary', 'released')",
            name="ck_app_releases_rollout_state",
        ),
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)
    updated_at = Column(UtcDateTime, nullable=False, default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")
    playlists = relationship("Playlist", back_populates="campaign")


class Content(Base):
    __tablename__ = "content"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    type = Column(String)
    file_url = Column(String)
    thumbnail = Column(String, nullable=True)
    name = Column(String)
    tags = Column(String, nullable=True)
    file_size_bytes = Column(BigInteger, nullable=False, default=0)
    sha256 = Column(String(64), nullable=True)
    # Real length of the source video, filled in by the worker from ffprobe. Without it
    # a playlist item falls back to a flat 10 seconds, so a 30-second advert is cut off
    # at 10 on every screen. Null for images, which have no intrinsic duration.
    duration_ms = Column(Integer, nullable=True)
    uploaded_at = Column(UtcDateTime, default=utcnow)
    status = Column(String, nullable=False, default="processing")
    # When the current processing attempt began. The reaper uses this to find rows whose
    # worker died mid-job; without it a killed worker leaves a permanent spinner.
    processing_started_at = Column(UtcDateTime, nullable=True)
    processing_retries = Column(Integer, nullable=False, default=0)
    failed_reason = Column(String, nullable=True)

    playlist_items = relationship("PlaylistItem", back_populates="content")
    organization = relationship("Organization", back_populates="content")
    renditions = relationship("MediaRendition", back_populates="content", cascade="all, delete-orphan")

    @property
    def expires_at(self):
        expiries = [item.end_at for item in self.playlist_items if item.end_at]
        return min(expiries) if expiries else None


class MediaRendition(Base):
    __tablename__ = "media_renditions"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content.id", ondelete="CASCADE"), nullable=False, index=True)
    resolution = Column(String, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    rotation = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=True)
    codec = Column(String, nullable=True)
    sha256 = Column(String(64), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=False, default=0)
    file_url = Column(String, nullable=False)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)

    content = relationship("Content", back_populates="renditions")


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String, index=True)
    default_transition = Column(String, nullable=False, default="fade")
    default_transition_ms = Column(Integer, nullable=False, default=600)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)
    updated_at = Column(UtcDateTime, nullable=False, default=utcnow, onupdate=utcnow)

    screens = relationship("Screen", back_populates="playlist")
    groups = relationship("ScreenGroup", back_populates="playlist")
    organization = relationship("Organization", back_populates="playlists")
    campaign = relationship("Campaign", back_populates="playlists")
    items = relationship(
        "PlaylistItem",
        back_populates="playlist",
        order_by="PlaylistItem.order",
        cascade="all, delete-orphan",
    )


class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    content_id = Column(Integer, ForeignKey("content.id", ondelete="CASCADE"), nullable=False)
    duration = Column(Integer, default=10)
    order = Column(Integer, default=0)
    start_at = Column(UtcDateTime, nullable=True)
    end_at = Column(UtcDateTime, nullable=True)
    # NULL means inherit the containing playlist's transition setting.
    transition = Column(String, nullable=True)
    transition_ms = Column(Integer, nullable=True)
    # Per-item rotation override in degrees (0/90/180/270). Null means "follow the
    # screen", which is what almost every item should be.
    rotation = Column(Integer, nullable=True)

    playlist = relationship("Playlist", back_populates="items")
    content = relationship("Content", back_populates="playlist_items")
    schedule = relationship(
        "Schedule",
        back_populates="playlist_item",
        uselist=False,
        cascade="all, delete-orphan",
    )


class EmergencyBroadcast(Base):
    __tablename__ = "emergency_broadcasts"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    target_type = Column(String, nullable=False)  # 'all', 'group', 'screen'
    target_id = Column(Integer, nullable=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)
    updated_at = Column(UtcDateTime, nullable=False, default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")
    playlist = relationship("Playlist")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    playlist_item_id = Column(
        Integer,
        ForeignKey("playlist_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    days_of_week = Column(String, nullable=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)

    playlist_item = relationship("PlaylistItem", back_populates="schedule")


class EnrollmentToken(Base):
    __tablename__ = "enrollment_tokens"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    expires_at = Column(UtcDateTime, nullable=True)
    max_uses = Column(Integer, nullable=True)
    use_count = Column(Integer, nullable=False, default=0)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)

    organization = relationship("Organization")


class AdPlacement(Base):
    """An advert sold to a client: what runs, for whom, when, and for how much.

    Deliberately a thin record. It does not schedule anything itself — it owns the
    playlist items it created (see AdPlacementTarget), so the playlist stays the single
    thing the player, proof-of-play and rendition selection all read from. Two schedulers
    would mean two answers to "what is on that screen right now".
    """

    __tablename__ = "ad_placements"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    content_id = Column(Integer, ForeignKey("content.id", ondelete="CASCADE"), nullable=False, index=True)
    advertiser = Column(String, nullable=False)
    # Stored in the smallest currency unit so money never touches a float.
    price_paise = Column(BigInteger, nullable=False, default=0)
    is_paid = Column(Boolean, nullable=False, default=False)
    starts_at = Column(UtcDateTime, nullable=False)
    ends_at = Column(UtcDateTime, nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)
    updated_at = Column(UtcDateTime, nullable=False, default=utcnow, onupdate=utcnow)

    content = relationship("Content")
    organization = relationship("Organization")
    targets = relationship("AdPlacementTarget", back_populates="placement", cascade="all, delete-orphan")


class AdPlacementTarget(Base):
    """One place a booked advert runs, and the playlist item it put there.

    Exactly one of screen_id / group_id is set. Holding playlist_item_id is what makes
    "take this ad off that one screen" a single precise delete instead of a guess.
    """

    __tablename__ = "ad_placement_targets"

    id = Column(Integer, primary_key=True, index=True)
    placement_id = Column(Integer, ForeignKey("ad_placements.id", ondelete="CASCADE"), nullable=False, index=True)
    screen_id = Column(Integer, ForeignKey("screens.id", ondelete="CASCADE"), nullable=True, index=True)
    group_id = Column(Integer, ForeignKey("screen_groups.id", ondelete="CASCADE"), nullable=True, index=True)
    # SET NULL rather than CASCADE: if an operator deletes the item by hand on the screen
    # page, the booking should survive as a record of what was sold, just no longer placed.
    playlist_item_id = Column(Integer, ForeignKey("playlist_items.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint(
            "(screen_id IS NOT NULL) <> (group_id IS NOT NULL)",
            name="ck_placement_target_exactly_one",
        ),
    )

    placement = relationship("AdPlacement", back_populates="targets")
    screen = relationship("Screen")
    group = relationship("ScreenGroup")
    playlist_item = relationship("PlaylistItem")


class PlayLog(Base):
    __tablename__ = "play_logs"

    event_id = Column(String, primary_key=True, index=True)
    screen_id = Column(Integer, ForeignKey("screens.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    # No foreign keys on these three on purpose. This is an append-only audit log whose
    # referents -- content, playlists, campaigns -- get deleted in normal operation, and a
    # device can still be holding queued events for a deleted row. With FKs, that insert
    # raised IntegrityError, the device retried its oldest batch forever, and every later
    # play on that screen was lost behind the wedge. Indexes stay for the report queries.
    media_id = Column(Integer, nullable=True, index=True)
    playlist_id = Column(Integer, nullable=True, index=True)
    campaign_id = Column(Integer, nullable=True, index=True)

    # Device local time (raw)
    device_started_at = Column(UtcDateTime, nullable=False)
    device_finished_at = Column(UtcDateTime, nullable=False)

    # Corrected time (adjusted for server clock drift)
    corrected_started_at = Column(UtcDateTime, nullable=False)
    corrected_finished_at = Column(UtcDateTime, nullable=False)

    duration_ms = Column(Integer, nullable=False)
    
    # "completed", "partial", "error"
    status = Column(String, nullable=False)
    error_message = Column(Text, nullable=True)

    received_at = Column(UtcDateTime, nullable=False, default=utcnow)
    aggregated = Column(Boolean, nullable=False, default=False, index=True)

from sqlalchemy import Index, func
Index("ix_play_logs_org_started_at", PlayLog.organization_id, PlayLog.corrected_started_at)
Index("ix_play_logs_media_started_at", PlayLog.media_id, PlayLog.corrected_started_at)


class Alert(Base):
    """Something wrong with the fleet, recorded so it can be delivered and reviewed.

    Persisted rather than derived on demand because an alert has a life beyond the moment
    it is true: it has to be deliverable to a phone, acknowledgeable by whoever picked it
    up, and answerable afterwards ("when did that screen actually drop?"). The dashboard
    computed all of this in the browser, so none of that was possible.
    """

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)

    kind = Column(String(40), nullable=False, index=True)
    severity = Column(String(10), nullable=False)

    # No foreign keys, for the same reason PlayLog carries none: an alert outlives the row
    # it describes. Deleting the screen that failed must not delete the record that it did.
    screen_id = Column(Integer, nullable=True, index=True)
    content_id = Column(Integer, nullable=True, index=True)

    title = Column(String(300), nullable=False)
    detail = Column(Text, nullable=True)

    # Identity of the situation ("screen_offline:42"), not of one observation. The partial
    # unique index below uses it to make re-raising an already-open alert impossible at the
    # database level, rather than relying on the reconciler to check first -- which would
    # be a race every time two workers swept at once.
    dedupe_key = Column(String(80), nullable=False)

    raised_at = Column(UtcDateTime, nullable=False, default=utcnow, index=True)
    # Set when the condition stops being true. Null means "still wrong right now".
    resolved_at = Column(UtcDateTime, nullable=True, index=True)
    acknowledged_at = Column(UtcDateTime, nullable=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Channels this alert has already been delivered through, so a retry or a second worker
    # cannot send the same message to a phone twice.
    notified = Column(JSON, nullable=False, default=list)


# Partial, so the constraint applies only to alerts that are still open. Without the WHERE
# clause a screen that goes offline, recovers, and goes offline again could never raise a
# second alert -- the resolved one from last week would block it forever.
Index(
    "ix_alerts_open_unique",
    Alert.organization_id,
    Alert.dedupe_key,
    unique=True,
    postgresql_where=Alert.resolved_at.is_(None),
    sqlite_where=Alert.resolved_at.is_(None),
)


class PlayLogHourlyRollup(Base):
    __tablename__ = "play_log_hourly_rollups"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    # Same reasoning as PlayLog: derived from an append-only log whose referents get
    # deleted. Here it matters more -- the rollup is written by aggregate_play_logs, whose
    # exception handler only prints (worker.py), so one FK violation would stop aggregation
    # for the whole fleet and every report would read zero with no error surfaced.
    campaign_id = Column(Integer, nullable=True, index=True)
    screen_id = Column(Integer, ForeignKey("screens.id"), nullable=False, index=True)
    media_id = Column(Integer, nullable=True, index=True)

    date_hour = Column(UtcDateTime, nullable=False, index=True)
    
    total_plays = Column(Integer, nullable=False, default=0)
    completed_plays = Column(Integer, nullable=False, default=0)
    partial_plays = Column(Integer, nullable=False, default=0)
    error_plays = Column(Integer, nullable=False, default=0)
    duration_ms = Column(BigInteger, nullable=False, default=0)

# COALESCE, not the bare columns. campaign_id and media_id are both nullable, and Postgres
# treats NULLs as distinct in a unique index -- so on the bare columns this index enforced
# nothing at all for the rows most likely to collide: plays from a playlist with no campaign.
# The aggregation query is written NULL-safely (IS NOT DISTINCT FROM), so nothing has gone
# wrong in practice, but the constraint that was supposed to be the backstop was not one.
# -1 is safe as the sentinel because both columns are positive primary keys.
Index(
    "ix_play_log_hourly_rollups_unique",
    PlayLogHourlyRollup.organization_id,
    func.coalesce(PlayLogHourlyRollup.campaign_id, -1),
    PlayLogHourlyRollup.screen_id,
    func.coalesce(PlayLogHourlyRollup.media_id, -1),
    PlayLogHourlyRollup.date_hour,
    unique=True
)
