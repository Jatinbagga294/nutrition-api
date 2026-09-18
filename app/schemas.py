"""Pydantic schemas: the API's public contract.

Kept separate from the ORM models on purpose. The database has columns the API
must never return (password_hash), and the API accepts shapes the database does
not store (a plaintext password). Mixing the two is how hashes end up in JSON.
"""
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    # 72 is bcrypt's hard limit, not an arbitrary choice.
    password: str = Field(min_length=8, max_length=72)
    daily_calorie_goal: int = Field(default=2000, ge=500, le=10000)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    daily_calorie_goal: int


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EntryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    calories: float = Field(ge=0, le=20000)
    protein_g: float = Field(default=0, ge=0)
    carbs_g: float = Field(default=0, ge=0)
    fat_g: float = Field(default=0, ge=0)
    logged_on: date | None = None


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    logged_on: date


class DailySummary(BaseModel):
    logged_on: date
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    goal: int
    remaining: float
    entry_count: int
