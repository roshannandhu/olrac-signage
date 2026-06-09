from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

# --- Literal type aliases ---

ContentType = Literal["video", "image"]
ContentOrient = Literal["landscape", "portrait"]
ScreenOrient = Literal["D0", "D90", "D180", "D270"]
ScreenStatus = Literal["pending", "online", "offline"]

# --- Read (response) models ---


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    role: str
    created_at: datetime


class ContentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    type: ContentType
    orientation: ContentOrient
    storage_path: str
    public_url: str
    duration_seconds: int
    file_size: int
    tags: list[str]
    start_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    created_at: datetime


class ScreenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    pairing_code: Optional[str] = None
    pairing_code_expires_at: Optional[datetime] = None
    orientation: ScreenOrient
    status: ScreenStatus
    last_seen_at: Optional[datetime] = None
    screen_token: str
    tags: list[str]
    created_at: datetime


class ContentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: ContentType
    orientation: ContentOrient
    public_url: str
    duration_seconds: int


class PlaylistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    duration_override: Optional[int] = None
    content: ContentSummary


class GroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
    screens: list[ScreenRead] = []
    has_playlist: bool = False


class WebsiteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str
    created_at: datetime


# --- Request bodies ---


class RegisterIn(BaseModel):
    email: str
    password: str
    name: str


class LoginIn(BaseModel):
    email: str
    password: str


class ContentPatchIn(BaseModel):
    name: Optional[str] = None
    tags: Optional[str] = None
    start_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None


class PairIn(BaseModel):
    code: str
    name: str
    orientation: ScreenOrient


class ScreenPatchIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    orientation: Optional[ScreenOrient] = None
    tags: Optional[str] = None


class PlaylistPutItem(BaseModel):
    content_id: UUID
    position: int
    duration_override: Optional[int] = None


class PlaylistPutIn(BaseModel):
    items: list[PlaylistPutItem]


class GroupCreateIn(BaseModel):
    name: str
    screen_ids: list[UUID] = []


class GroupPatchIn(BaseModel):
    name: Optional[str] = None
    screen_ids: Optional[list[UUID]] = None


class WebsiteCreateIn(BaseModel):
    name: str
    url: str


class PlaybackLogIn(BaseModel):
    content_id: UUID
    played_at: datetime
    duration_played: int = Field(ge=0)
