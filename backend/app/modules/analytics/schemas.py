import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class OverviewResponse(BaseModel):
    start_date: date
    end_date: date
    revenue: Decimal
    order_count: int
    average_order_value: Decimal
    total_customers: int
    active_customers: int


class RevenuePoint(BaseModel):
    period_start: date
    revenue: Decimal
    order_count: int


class RevenueTrendResponse(BaseModel):
    start_date: date
    end_date: date
    granularity: str
    points: list[RevenuePoint]


class TopProductItem(BaseModel):
    product_id: uuid.UUID
    name: str
    category: str
    revenue: Decimal
    quantity_sold: int


class ProductsPerformanceResponse(BaseModel):
    start_date: date
    end_date: date
    products: list[TopProductItem]


class CustomerMetricsResponse(BaseModel):
    start_date: date
    end_date: date
    total_customers: int
    new_customers: int
    active_customers: int
    at_risk_customers: int
