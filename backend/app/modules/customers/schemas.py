import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.modules.customers.models import CustomerStatus


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    status: CustomerStatus = CustomerStatus.ACTIVE
    lifetime_value: Decimal = Field(default=Decimal("0"), ge=0)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    status: CustomerStatus | None = None
    lifetime_value: Decimal | None = Field(default=None, ge=0)


class CustomerResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    status: CustomerStatus
    lifetime_value: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}
