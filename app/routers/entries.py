"""Food entry CRUD and the daily summary."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import Entry, User
from ..schemas import DailySummary, EntryCreate, EntryOut

router = APIRouter(prefix="/entries", tags=["entries"])


@router.post("", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: EntryCreate,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Entry:
    entry = Entry(
        user_id=user.id,
        **payload.model_dump(exclude_none=True, exclude={"logged_on"}),
        logged_on=payload.logged_on or date.today(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("", response_model=list[EntryOut])
def list_entries(
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    on: date | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Entry]:
    # user_id filter is not optional. It is the whole authorization model.
    stmt = select(Entry).where(Entry.user_id == user.id)
    if on:
        stmt = stmt.where(Entry.logged_on == on)
    stmt = stmt.order_by(Entry.logged_on.desc(), Entry.id.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


@router.get("/summary", response_model=DailySummary)
def daily_summary(
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    on: date | None = None,
) -> DailySummary:
    """Totals for one day, aggregated in the database rather than in Python."""
    day = on or date.today()
    row = db.execute(
        select(
            func.coalesce(func.sum(Entry.calories), 0.0),
            func.coalesce(func.sum(Entry.protein_g), 0.0),
            func.coalesce(func.sum(Entry.carbs_g), 0.0),
            func.coalesce(func.sum(Entry.fat_g), 0.0),
            func.count(Entry.id),
        ).where(Entry.user_id == user.id, Entry.logged_on == day)
    ).one()

    cals, protein, carbs, fat, count = row
    return DailySummary(
        logged_on=day,
        total_calories=round(cals, 1),
        total_protein_g=round(protein, 1),
        total_carbs_g=round(carbs, 1),
        total_fat_g=round(fat, 1),
        goal=user.daily_calorie_goal,
        remaining=round(user.daily_calorie_goal - cals, 1),
        entry_count=count,
    )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    entry = db.get(Entry, entry_id)
    # 404 rather than 403 when the entry belongs to someone else: a 403 would
    # confirm that the id exists.
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entry not found")
    db.delete(entry)
    db.commit()
