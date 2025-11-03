from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class InvoiceCreate(BaseModel):
    parent_email: str
    amount_rub: Decimal = Field(gt=0)


class InvoiceResponse(BaseModel):
    invoice_id: str
    payment_url: str | None = None
    status: str = "PENDING"
