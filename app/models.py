import uuid
from datetime import datetime
from sqlalchemy import (
    Integer, BigInteger, DateTime, ForeignKey, Text, String,
    CheckConstraint, PrimaryKeyConstraint, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    content = relationship("Content", back_populates="owner", cascade="all, delete-orphan")
    screens = relationship("Screen", back_populates="owner")
    groups = relationship("ScreenGroup", back_populates="owner", cascade="all, delete-orphan")
    websites = relationship("Website", back_populates="owner", cascade="all, delete-orphan")


class Content(Base):
    __tablename__ = "content"
    __table_args__ = (
        CheckConstraint("type IN ('video', 'image')", name="ck_content_type"),
        CheckConstraint("orientation IN ('landscape', 'portrait')", name="ck_content_orientation"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    orientation: Mapped[str] = mapped_column(String(15), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    public_url: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tags: Mapped[list] = mapped_column(ARRAY(String), nullable=False, default=list)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("Profile", back_populates="content")
    playlist_items = relationship("PlaylistItem", back_populates="content", cascade="all, delete-orphan")


class Screen(Base):
    __tablename__ = "screens"
    __table_args__ = (
        CheckConstraint("orientation IN ('D0', 'D90', 'D180', 'D270')", name="ck_screen_orientation"),
        CheckConstraint("status IN ('pending', 'online', 'offline')", name="ck_screen_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pairing_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    pairing_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    orientation: Mapped[str] = mapped_column(String(10), nullable=False, default="D0")
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="pending")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    screen_token: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    tags: Mapped[list] = mapped_column(ARRAY(String), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("Profile", back_populates="screens")
    playlist = relationship("Playlist", uselist=False, back_populates="screen", cascade="all, delete-orphan")


class ScreenGroup(Base):
    __tablename__ = "screen_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("Profile", back_populates="groups")
    playlist = relationship("Playlist", uselist=False, back_populates="group", cascade="all, delete-orphan")
    screens = relationship("Screen", secondary="group_screens", backref="screen_groups")


class GroupScreen(Base):
    __tablename__ = "group_screens"
    __table_args__ = (
        PrimaryKeyConstraint("group_id", "screen_id", name="pk_group_screens"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("screen_groups.id", ondelete="CASCADE"), primary_key=True)
    screen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("screens.id", ondelete="CASCADE"), primary_key=True)


class Playlist(Base):
    __tablename__ = "playlists"
    __table_args__ = (
        UniqueConstraint("screen_id", name="uq_playlist_screen"),
        UniqueConstraint("group_id", name="uq_playlist_group"),
        CheckConstraint(
            "(screen_id IS NOT NULL AND group_id IS NULL) OR (screen_id IS NULL AND group_id IS NOT NULL)",
            name="ck_playlist_owner",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    screen_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("screens.id", ondelete="CASCADE"), nullable=True, unique=True)
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("screen_groups.id", ondelete="CASCADE"), nullable=True, unique=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    screen = relationship("Screen", back_populates="playlist")
    group = relationship("ScreenGroup", back_populates="playlist")
    items = relationship("PlaylistItem", back_populates="playlist", cascade="all, delete-orphan", order_by="PlaylistItem.position")


class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playlist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("content.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_override: Mapped[int | None] = mapped_column(Integer, nullable=True)

    playlist = relationship("Playlist", back_populates="items")
    content = relationship("Content", back_populates="playlist_items")


class Website(Base):
    __tablename__ = "websites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("Profile", back_populates="websites")


class PlaybackLog(Base):
    __tablename__ = "playback_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    screen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("screens.id", ondelete="CASCADE"), nullable=False)
    content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("content.id", ondelete="CASCADE"), nullable=False)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_played: Mapped[int] = mapped_column(Integer, nullable=False)
