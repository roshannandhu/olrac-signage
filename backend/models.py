from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Time, JSON, Float
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
    storage_quota_bytes = Column(BigInteger, nullable=False, default=10 * 1024 * 1024 * 1024)
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)

    users = relationship("User", back_populates="organization")
    screens = relationship("Screen", back_populates="organization")
    groups = relationship("ScreenGroup", back_populates="organization")
    content = relationship("Content", back_populates="organization")
    playlists = relationship("Playlist", back_populates="organization")
    plan = relationship("Plan", back_populates="organizations")
    subscription = relationship("Subscription", back_populates="organization", uselist=False)


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

    organization = relationship("Organization", back_populates="users")


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
    update_status = Column(String, nullable=True) # pending, downloading, installing, success, failed

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
    created_at = Column(UtcDateTime, nullable=False, default=utcnow)


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


class PlayLog(Base):
    __tablename__ = "play_logs"

    event_id = Column(String, primary_key=True, index=True)
    screen_id = Column(Integer, ForeignKey("screens.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    media_id = Column(Integer, ForeignKey("content.id"), nullable=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)

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

from sqlalchemy import Index
Index("ix_play_logs_org_started_at", PlayLog.organization_id, PlayLog.corrected_started_at)
Index("ix_play_logs_media_started_at", PlayLog.media_id, PlayLog.corrected_started_at)


class PlayLogHourlyRollup(Base):
    __tablename__ = "play_log_hourly_rollups"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    screen_id = Column(Integer, ForeignKey("screens.id"), nullable=False, index=True)
    media_id = Column(Integer, ForeignKey("content.id"), nullable=True, index=True)
    
    date_hour = Column(UtcDateTime, nullable=False, index=True)
    
    total_plays = Column(Integer, nullable=False, default=0)
    completed_plays = Column(Integer, nullable=False, default=0)
    partial_plays = Column(Integer, nullable=False, default=0)
    error_plays = Column(Integer, nullable=False, default=0)
    duration_ms = Column(BigInteger, nullable=False, default=0)

Index(
    "ix_play_log_hourly_rollups_unique",
    PlayLogHourlyRollup.organization_id,
    PlayLogHourlyRollup.campaign_id,
    PlayLogHourlyRollup.screen_id,
    PlayLogHourlyRollup.media_id,
    PlayLogHourlyRollup.date_hour,
    unique=True
)
