"""ORM models: the actual database schema."""
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Unique + indexed because every login looks a user up by email.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # The bcrypt hash, never the password itself.
    password_hash: Mapped[str] = mapped_column(String(255))
    daily_calorie_goal: Mapped[int] = mapped_column(default=2000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    entries: Mapped[list["Entry"]] = relationship(
        back_populates="user",
        # Deleting a user removes their entries in the database, not just in
        # Python, so no orphan rows survive.
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Entry(Base):
    """One logged food item on one day."""

    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    calories: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)
    logged_on: Mapped[date] = mapped_column(Date, default=lambda: utcnow().date())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="entries")

    __table_args__ = (
        # The daily-summary query filters on both columns together, so a
        # composite index serves it with one lookup.
        Index("ix_entries_user_day", "user_id", "logged_on"),
    )
