import re
from datetime import datetime, time
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .media_urls import resolve_media_url


# "super_admin" is the platform operator, not a tenant role: it is the only role that may
# publish an AppRelease, and a release installs across every tenant's fleet.
#
# Role is the *output* type -- what a user may be. TenantRole is the *input* type: the
# roles an organisation's owner is allowed to hand out from the team page. They are
# deliberately different. Sharing one type let an owner POST {"role": "super_admin"} to
# /api/users and mint themselves a platform operator, turning tenant ownership into
# control of every other tenant's TVs. A super_admin is created only by
# `python -m backend.seed_admin --role super_admin`, which needs shell access to the host.
Role = Literal["super_admin", "owner", "editor", "viewer"]
TenantRole = Literal["owner", "editor", "viewer"]
PlaybackState = Literal["playing", "idle", "error"]
# Promotion order for a player build: draft -> canary -> released. Only "released"
# is offered to screens that carry no explicit target_version_code pin.
RolloutState = Literal["draft", "canary", "released"]
TransitionName = Literal[
    "none",
    "fade",
    "slide_left",
    "slide_right",
    "slide_up",
    "slide_down",
    "zoom",
]


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: TenantRole = "viewer"

    @field_validator("password")
    @classmethod
    def valid_bcrypt_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 UTF-8 bytes")
        return value


class UserUpdate(BaseModel):
    role: Optional[TenantRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def valid_optional_bcrypt_length(cls, value: Optional[str]) -> Optional[str]:
        if value and len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 UTF-8 bytes")
        return value


class UserResponse(BaseModel):
    id: int
    organization_id: int
    username: str
    role: Role
    is_active: bool
    created_at: datetime
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    # Read-only convenience for the account menu, which otherwise has only a numeric
    # organization_id to show. Resolved from the relationship, never written through here.
    organization_name: Optional[str] = None

    # organization_name is resolved by User.organization_name on the model, so
    # from_attributes picks it up like any other column.
    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    """Self-service profile edit. Deliberately excludes role, is_active and password --
    privilege changes stay on the owner-gated /api/users routes, and a password change
    needs the current password (see PasswordChange)."""

    full_name: Optional[str] = Field(default=None, max_length=120)
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def valid_bcrypt_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 UTF-8 bytes")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_HHMM = re.compile(r"([01]\d|2[0-3]):[0-5]\d")

FitMode = Literal["contain", "cover"]
SyncRole = Literal["leader", "follower"]
OperatingMode = Literal["always", "hours", "never"]


class ScreenBase(BaseModel):
    name: Optional[str] = None
    orientation: int = 0
    device_id: Optional[str] = None
    group_id: Optional[int] = None
    @field_validator("orientation")
    @classmethod
    def valid_orientation(cls, value: int) -> int:
        if value not in (0, 90, 180, 270):
            raise ValueError("orientation must be 0, 90, 180, or 270")
        return value


class ScreenCreate(ScreenBase):
    pass


class ScreenSignInRequest(BaseModel):
    """Credentials typed on the TV itself, so a screen can join without a pairing code."""

    username: str
    password: str
    device_id: str
    name: Optional[str] = Field(default=None, max_length=120)


class GoogleWebSignInRequest(BaseModel):
    """The authorization code a browser just came back from Google holding."""

    code: str
    # Echoed back to Google, which requires it to match the one used to obtain the code.
    redirect_uri: str


class GoogleDeviceStartRequest(BaseModel):
    """A TV asking for a Google code to put on screen."""

    device_id: str
    name: Optional[str] = Field(default=None, max_length=120)


class GoogleDeviceStartResponse(BaseModel):
    """What the TV displays, plus the handle it polls with.

    `poll_token` is a short-lived JWT holding the device_code and the device_id it was
    issued for. Google's device_code is meant to live on the device, but on its own it
    says nothing about *which* screen is being claimed -- wrapping the pair means a code
    lifted off one TV cannot be redeemed to bind a different one.
    """

    user_code: str
    verification_url: str
    interval: int
    expires_in: int
    poll_token: str


class GoogleDevicePollRequest(BaseModel):
    poll_token: str


class GoogleDevicePollResponse(BaseModel):
    """Where the approval has got to.

    `slow_down` is passed through rather than swallowed: Google returns it when the TV is
    polling too fast, and the player has to widen its own interval or it will simply keep
    earning the same answer.
    """

    status: Literal["pending", "slow_down", "denied", "expired", "bound"]
    screen: Optional["ScreenResponse"] = None
    detail: Optional[str] = None


class ScreenPatch(BaseModel):
    """Partial screen update: only the fields actually present are written.

    The PUT above takes a whole ScreenBase, so a caller editing just the name had
    to resend orientation and would reset a portrait display to landscape.
    """

    name: Optional[str] = None
    orientation: Optional[int] = None
    group_id: Optional[int] = None
    target_version_code: Optional[int] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    # Set together: the label and the pin must always describe the same place.
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_id: Optional[str] = None
    timezone: Optional[str] = None
    fit_mode: Optional[FitMode] = None
    # Exactly four digits: the player prompts for it on a TV remote, where anything
    # longer or non-numeric is painful to type on a d-pad.
    maintenance_pin: Optional[str] = Field(default=None, pattern=r"^\d{4}$")
    sync_playback: Optional[bool] = None
    sync_role: Optional[SyncRole] = None
    leader_screen_id: Optional[int] = None
    operating_mode: Optional[OperatingMode] = None
    operating_hours: Optional[dict[str, list[str]]] = None

    @field_validator("orientation")
    @classmethod
    def valid_orientation(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value not in (0, 90, 180, 270):
            raise ValueError("orientation must be 0, 90, 180, or 270")
        return value

    @field_validator("operating_hours")
    @classmethod
    def valid_hours(cls, value: Optional[dict[str, list[str]]]) -> Optional[dict[str, list[str]]]:
        """Each day maps to exactly [start, end] as HH:MM.

        Validated here rather than in the player: a malformed window is the difference
        between a screen that runs all day and one that never wakes up.
        """
        if value is None:
            return None
        for day, window in value.items():
            if day not in WEEKDAYS:
                raise ValueError(f"unknown day '{day}'")
            if len(window) != 2:
                raise ValueError(f"{day} must be [start, end]")
            for stamp in window:
                if not _HHMM.fullmatch(stamp):
                    raise ValueError(f"{day}: '{stamp}' is not HH:MM")
        return value


class ScreenResponse(ScreenBase):
    id: int
    pair_code: Optional[str]
    status: str
    orientation_source: str = "auto"
    # Newest capture, attached by the list endpoint so the fleet grid can show a live
    # thumbnail without a request per card.
    latest_screenshot: Optional[str] = None
    # Update state, so the dashboard can monitor a rollout instead of guessing.
    # app_version above is what the TV reports it is actually running.
    target_version_code: Optional[int] = None
    # Capped but not enumerated: the backend must keep accepting heartbeats from APKs
    # older than whatever the current status vocabulary is, so an unrecognised value is
    # stored rather than rejected. The cap stops a malformed device filling the column.
    update_status: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    tags: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_id: Optional[str] = None
    fit_mode: FitMode = "contain"
    maintenance_pin: Optional[str] = None
    sync_playback: bool = False
    sync_role: SyncRole = "leader"
    leader_screen_id: Optional[int] = None
    operating_mode: OperatingMode = "always"
    operating_hours: Optional[dict[str, list[str]]] = None
    # NULL means the screen claimed this organisation from the TV and is waiting for an
    # operator to let it in. The dashboard reads this to build the approval queue.
    approved_at: Optional[datetime] = None
    installation_id: Optional[str] = None
    last_seen: datetime
    playlist_id: Optional[int]
    group_id: Optional[int]
    device_version: Optional[str]
    app_version: Optional[str] = None
    storage_used: Optional[str]
    playback_state: PlaybackState = "idle"
    current_item_id: Optional[int] = None
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
    effective_playlist_id: Optional[int]
    
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    refresh_rate: Optional[float] = None
    total_ram_mb: Optional[int] = None
    available_ram_mb: Optional[int] = None
    total_storage_mb: Optional[int] = None
    free_storage_mb: Optional[int] = None
    supported_video_codecs: Optional[list[str]] = None
    max_decode_width: Optional[int] = None
    max_decode_height: Optional[int] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    android_version: Optional[str] = None
    sdk_int: Optional[int] = None
    network_type: Optional[str] = None
    timezone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ContentBase(BaseModel):
    name: str
    tags: Optional[str] = None


class MediaRenditionResponse(BaseModel):
    id: int
    resolution: str
    width: int
    height: int
    rotation: int
    duration_ms: Optional[int] = None
    codec: Optional[str] = None
    sha256: Optional[str] = None
    file_size_bytes: int
    file_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def absolutise_urls(self):
        self.file_url = resolve_media_url(self.file_url) or self.file_url
        return self


class ContentResponse(ContentBase):
    id: int
    type: str
    file_url: str
    thumbnail: Optional[str]
    uploaded_at: datetime
    file_size_bytes: int = 0
    sha256: Optional[str] = None
    duration_ms: Optional[int] = None
    expires_at: Optional[datetime] = None
    status: str
    failed_reason: Optional[str] = None
    renditions: List[MediaRenditionResponse] = []

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def absolutise_urls(self):
        """Make stored locations fetchable, wherever this response is embedded.

        Doing it here rather than in each router is deliberate: the playlists endpoint
        forgot to, so nested content came back as bare paths and every thumbnail in the
        playlist editor was blank while the same asset rendered fine in the library.
        """
        self.file_url = resolve_media_url(self.file_url) or self.file_url
        self.thumbnail = resolve_media_url(self.thumbnail)
        return self


class ContentUpdate(ContentBase):
    pass


class ScheduleBase(BaseModel):
    days_of_week: List[int] = Field(default_factory=list)
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    @field_validator("days_of_week", mode="before")
    @classmethod
    def valid_days(cls, value) -> List[int]:
        if isinstance(value, str):
            value = [int(day) for day in value.split(",") if day != ""]
        value = value or []
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("days_of_week values must be between 0 (Monday) and 6 (Sunday)")
        return sorted(set(value))


class ScheduleResponse(ScheduleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class PlaylistItemBase(BaseModel):
    content_id: int
    duration: int = Field(default=10, ge=1, le=86400)
    # None means "follow the screen's own orientation"; a number overrides it for this item.
    rotation: Optional[int] = None
    order: int = Field(default=0, ge=0)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    transition: Optional[TransitionName] = None
    transition_ms: Optional[int] = Field(default=None, ge=100, le=3000)

    @field_validator("rotation")
    @classmethod
    def valid_rotation(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value not in (0, 90, 180, 270):
            raise ValueError("rotation must be 0, 90, 180, or 270")
        return value

    @model_validator(mode="after")
    def valid_date_range(self):
        if "duration" in self.model_fields_set and self.duration is None:
            raise ValueError("duration cannot be null")
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class PlaylistItemCreate(PlaylistItemBase):
    schedule: Optional[ScheduleBase] = None


class PlaylistItemUpdate(BaseModel):
    duration: Optional[int] = Field(default=None, ge=1, le=86400)
    # None clears the override so the item follows the screen's own orientation again.
    rotation: Optional[int] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    schedule: Optional[ScheduleBase] = None
    transition: Optional[TransitionName] = None
    transition_ms: Optional[int] = Field(default=None, ge=100, le=3000)

    @field_validator("rotation")
    @classmethod
    def valid_rotation(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value not in (0, 90, 180, 270):
            raise ValueError("rotation must be 0, 90, 180, or 270")
        return value

    @model_validator(mode="after")
    def valid_date_range(self):
        if "duration" in self.model_fields_set and self.duration is None:
            raise ValueError("duration cannot be null")
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class PlaylistItemResponse(PlaylistItemBase):
    id: int
    content: ContentResponse
    schedule: Optional[ScheduleResponse] = None

    model_config = ConfigDict(from_attributes=True)


class PlaylistBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    default_transition: TransitionName = "fade"
    default_transition_ms: int = Field(default=600, ge=100, le=3000)


class PlaylistCreate(PlaylistBase):
    pass


class PlaylistUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    default_transition: Optional[TransitionName] = None
    default_transition_ms: Optional[int] = Field(default=None, ge=100, le=3000)

    @model_validator(mode="after")
    def has_update(self):
        if not self.model_fields_set:
            raise ValueError("at least one playlist field is required")
        return self


class PlaylistTransitionUpdate(BaseModel):
    transition: TransitionName
    transition_ms: int = Field(default=600, ge=100, le=3000)
    apply_to_all: bool = False


class PlaylistResponse(PlaylistBase):
    id: int
    created_at: datetime
    updated_at: datetime
    items: List[PlaylistItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ScreenGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: Optional[int] = None
    is_dynamic: bool = False
    dynamic_criteria: Optional[dict] = None


class ScreenGroupUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: Optional[int] = None
    is_dynamic: bool = False
    dynamic_criteria: Optional[dict] = None


class ScreenGroupMembersUpdate(BaseModel):
    screen_ids: List[int]


class ScreenGroupResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    is_dynamic: bool
    dynamic_criteria: Optional[dict] = None
    playlist_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    screen_count: int = 0


class RegisterRequest(BaseModel):
    device_id: str


class RegisterResponse(BaseModel):
    """
    Deliberately narrow: /screens/register is unauthenticated, so it must not reuse
    ScreenResponse. That schema carries tenant configuration — including
    maintenance_pin — and anyone who knows a device_id can call this route.
    Only what the TV needs to finish pairing goes here.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: Optional[str] = None
    name: Optional[str] = None
    status: str
    pair_code: Optional[str] = None
    pair_code_expires_at: Optional[datetime] = None


class PairRequest(BaseModel):
    pair_code: str


class EnrollRequest(BaseModel):
    device_id: str
    enrollment_token: str
    installation_id: Optional[str] = None


class EnrollResponse(BaseModel):
    device_id: str
    device_secret: str
    organization_id: int
    screen_id: int


class DeviceAuthRequest(BaseModel):
    device_id: str
    device_secret: str

class DeviceTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class HeartbeatRequest(BaseModel):
    device_id: str
    device_version: Optional[str] = None
    storage_used: Optional[str] = None
    playback_state: Optional[PlaybackState] = None
    current_item_id: Optional[int] = None
    last_error: Optional[str] = Field(default=None, max_length=1000)
    app_version: Optional[str] = Field(default=None, max_length=100)
    version_code: Optional[int] = None
    update_status: Optional[str] = None
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    refresh_rate: Optional[float] = None
    orientation: Optional[int] = None
    total_ram_mb: Optional[int] = None
    available_ram_mb: Optional[int] = None
    total_storage_mb: Optional[int] = None
    free_storage_mb: Optional[int] = None
    supported_video_codecs: Optional[list[str]] = None
    max_decode_width: Optional[int] = None
    max_decode_height: Optional[int] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    android_version: Optional[str] = None
    sdk_int: Optional[int] = None
    network_type: Optional[str] = None
    timezone: Optional[str] = None
    
    model_config = ConfigDict(extra="ignore")

    @field_validator("last_error")
    @classmethod
    def clean_last_error(cls, value: Optional[str]) -> Optional[str]:
        cleaned = value.strip() if value else None
        return cleaned or None


class AppVersionResponse(BaseModel):
    version_code: int
    version_name: str
    apk_url: Optional[str] = None
    sha256: Optional[str] = None
    mandatory: bool = False


class AppReleaseCreate(BaseModel):
    version_code: int = Field(ge=1)
    version_name: str = Field(min_length=1, max_length=50)
    apk_url: str = Field(max_length=2048)
    # Mandatory, and it was not always so. The device verifies the APK it downloads
    # against this digest; when it was optional a release published without one was
    # installed unverified, which made the checksum a decoration rather than a control.
    # There is no legitimate reason to publish a build whose bytes you cannot pin.
    sha256: str = Field(min_length=64, max_length=64)
    mandatory: bool = False
    # New builds land as drafts. Publishing one used to make it live for every unpinned
    # screen the instant it was created, which left no way to try a build on five TVs
    # first. Promote with PATCH /api/releases/{version_code} once the ring looks healthy.
    rollout_state: RolloutState = "draft"

    @field_validator("apk_url")
    @classmethod
    def https_only(cls, value: str) -> str:
        # Plain HTTP would let anyone on the path swap the APK. The digest below would
        # catch that, but defence in depth is cheap here and the player installs this
        # file silently when it is device owner.
        if not value.startswith("https://"):
            raise ValueError("apk_url must be an https:// URL")
        return value

    @field_validator("sha256")
    @classmethod
    def hex_digest(cls, value: str) -> str:
        candidate = value.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", candidate):
            raise ValueError("sha256 must be 64 hexadecimal characters")
        return candidate


class AppReleaseResponse(AppReleaseCreate):
    id: int
    created_at: datetime
    # Widened back to optional purely for rows written before the digest was mandatory.
    # Serialising one of those against the stricter parent raised ValidationError, which
    # surfaced as a 500 on the releases list rather than as the legacy row it is. The
    # player treats a null digest as "refuse to install", so an unpinned old release is
    # inert rather than dangerous.
    sha256: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AppReleasePatch(BaseModel):
    """Promote (or demote) a build. The only mutable field: version_code, apk_url and
    sha256 are the identity of an artefact that screens may already be pinned to, and
    editing them would silently repoint those screens at different bytes."""

    rollout_state: RolloutState


class SyncResponse(BaseModel):
    playlist: Optional[PlaylistResponse] = None
    playlist_updated_at: Optional[datetime] = None
    status: Optional[str] = None
    app_version: Optional[AppVersionResponse] = None
    sync_interval_seconds: int = Field(default=60, ge=15, le=3600)
    # How the player should scale content that does not match the panel's aspect ratio.
    # Per screen rather than per item, which is how an operator thinks about a display.
    fit_mode: FitMode = "contain"
    # Cached by the player so the maintenance screen still opens with no network.
    maintenance_pin: Optional[str] = None
    # The player blanks itself outside these, using its own clock, so a shop TV goes dark
    # at closing time even when the network does not. Sent on every sync because the
    # player evaluates them locally -- it must keep working through an outage, which is
    # the whole point of the offline cache.
    operating_mode: OperatingMode = "always"
    operating_hours: Optional[dict[str, list[str]]] = None


class PlanResponse(BaseModel):
    id: int
    name: str
    slug: str
    monthly_price_paise: int
    yearly_price_paise: int
    max_screens: int
    max_storage_bytes: int
    feature_flags: dict[str, bool] = Field(default_factory=dict)


class SubscriptionResponse(BaseModel):
    status: str
    billing_period: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    grace_period_end: Optional[datetime] = None
    provider: Optional[str] = None
    provider_subscription_id: Optional[str] = None


class BillingSummaryResponse(BaseModel):
    plan: PlanResponse
    subscription: SubscriptionResponse
    screens_used: int
    storage_used_bytes: int
    is_read_only: bool


class CheckoutRequest(BaseModel):
    plan_id: int
    billing_period: Literal["monthly", "yearly"] = "monthly"


class CheckoutResponse(BaseModel):
    provider: str
    provider_subscription_id: str
    checkout_url: str


class EnrollmentTokenCreate(BaseModel):
    description: Optional[str] = None
    expires_at: Optional[datetime] = None
    max_uses: Optional[int] = Field(default=None, ge=1)


class EnrollmentTokenResponse(BaseModel):
    id: int
    token: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    max_uses: Optional[int] = None
    use_count: int = 0
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class PlayEventItem(BaseModel):
    event_id: str
    media_id: Optional[int] = None
    playlist_id: Optional[int] = None
    campaign_id: Optional[int] = None
    
    device_started_at: datetime
    device_finished_at: datetime
    
    corrected_started_at: datetime
    corrected_finished_at: datetime
    
    duration_ms: int
    status: Literal["completed", "partial", "error"]
    error_message: Optional[str] = None


class PlayLogBatchRequest(BaseModel):
    device_id: str
    screen_id: int
    organization_id: int
    events: List[PlayEventItem] = Field(..., max_length=500)


# --- Ad bookings ---------------------------------------------------------------------

class PlacementTargetRef(BaseModel):
    """One place a booking runs. Exactly one of the two ids is set."""

    screen_id: Optional[int] = None
    group_id: Optional[int] = None

    @model_validator(mode="after")
    def exactly_one(self):
        if (self.screen_id is None) == (self.group_id is None):
            raise ValueError("a target must name either a screen or a group, not both")
        return self


class PlacementCreate(BaseModel):
    content_id: int
    advertiser: str = Field(min_length=1, max_length=200)
    price_paise: int = Field(default=0, ge=0)
    is_paid: bool = False
    starts_at: datetime
    ends_at: datetime
    notes: Optional[str] = None
    targets: List[PlacementTargetRef] = []

    @model_validator(mode="after")
    def valid_window(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("the end date must be after the start date")
        return self


class PlacementUpdate(BaseModel):
    advertiser: Optional[str] = Field(default=None, min_length=1, max_length=200)
    price_paise: Optional[int] = Field(default=None, ge=0)
    is_paid: Optional[bool] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    notes: Optional[str] = None


class PlacementSplit(BaseModel):
    """Screens to drop when converting a group booking into per-screen bookings."""

    exclude_screen_ids: List[int] = []


class PlacementTargetResponse(BaseModel):
    id: int
    screen_id: Optional[int]
    group_id: Optional[int]
    name: str
    kind: Literal["screen", "group"]
    # False when the playlist item was deleted by hand on the screen page: the deal is
    # still recorded, it just is not on air there any more.
    is_placed: bool


class PlacementResponse(BaseModel):
    id: int
    content_id: int
    advertiser: str
    price_paise: int
    is_paid: bool
    starts_at: datetime
    ends_at: datetime
    notes: Optional[str]
    created_at: datetime
    targets: List[PlacementTargetResponse] = []


class ResolveLinkRequest(BaseModel):
    """A Google Maps share link, pasted by an operator."""
    link: str


class ResolveLinkResponse(BaseModel):
    latitude: float
    longitude: float
    name: Optional[str] = None


AlertSeverity = Literal["critical", "warning"]


class AlertResponse(BaseModel):
    id: int
    kind: str
    severity: AlertSeverity
    title: str
    detail: Optional[str] = None
    screen_id: Optional[int] = None
    content_id: Optional[int] = None
    raised_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AlertSummaryResponse(BaseModel):
    """Counts for the header badge, so it does not have to fetch every alert."""

    total: int
    critical: int
    warning: int
    unacknowledged: int


# ScreenResponse is defined below the Google models that reference it, so the forward
# reference is resolved here rather than left to be resolved on first use.
GoogleDevicePollResponse.model_rebuild()
