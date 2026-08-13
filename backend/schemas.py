from datetime import datetime, time
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Role = Literal["owner", "editor", "viewer"]
PlaybackState = Literal["playing", "idle", "error"]
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
    role: Role = "viewer"

    @field_validator("password")
    @classmethod
    def valid_bcrypt_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 UTF-8 bytes")
        return value


class UserUpdate(BaseModel):
    role: Optional[Role] = None
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

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


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


class ScreenPatch(BaseModel):
    """Partial screen update: only the fields actually present are written.

    The PUT above takes a whole ScreenBase, so a caller editing just the name had
    to resend orientation and would reset a portrait display to landscape.
    """

    name: Optional[str] = None
    orientation: Optional[int] = None
    group_id: Optional[int] = None
    target_version_code: Optional[int] = None

    @field_validator("orientation")
    @classmethod
    def valid_orientation(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value not in (0, 90, 180, 270):
            raise ValueError("orientation must be 0, 90, 180, or 270")
        return value


class ScreenResponse(ScreenBase):
    id: int
    pair_code: Optional[str]
    status: str
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
    order: int = Field(default=0, ge=0)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    transition: Optional[TransitionName] = None
    transition_ms: Optional[int] = Field(default=None, ge=100, le=3000)

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
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    schedule: Optional[ScheduleBase] = None
    transition: Optional[TransitionName] = None
    transition_ms: Optional[int] = Field(default=None, ge=100, le=3000)

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
    version_code: int
    version_name: str
    apk_url: str
    # Optional so an existing release can be registered before its checksum is known,
    # but UpdateManager refuses to install when it is absent on the device side.
    sha256: Optional[str] = None
    mandatory: bool = False


class AppReleaseResponse(AppReleaseCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SyncResponse(BaseModel):
    playlist: Optional[PlaylistResponse] = None
    playlist_updated_at: Optional[datetime] = None
    status: Optional[str] = None
    app_version: Optional[AppVersionResponse] = None
    sync_interval_seconds: int = Field(default=60, ge=15, le=3600)


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
    screen_id: int
    organization_id: int
    events: List[PlayEventItem] = Field(..., max_length=500)
