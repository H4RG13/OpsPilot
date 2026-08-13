import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(gt=0)
    active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    price: Decimal | None = Field(default=None, gt=0)
    active: bool | None = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    price: Decimal
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
