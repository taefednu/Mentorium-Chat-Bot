from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, status

from .config import BillingSettings
from .schemas import InvoiceCreate, InvoiceResponse
from .service import create_invoice

app = FastAPI(title="Mentorium Billing Service")


def get_settings() -> BillingSettings:
    return BillingSettings()


@app.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def post_invoice(
    payload: InvoiceCreate,
    settings: BillingSettings = Depends(get_settings),
) -> InvoiceResponse:
    if settings.provider_api_key is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment provider disabled")

    return await create_invoice(payload)
