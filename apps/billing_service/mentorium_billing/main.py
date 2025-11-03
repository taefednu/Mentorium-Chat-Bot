from __future__ import annotations

import uvicorn

from .api import app


def run() -> None:
    uvicorn.run("mentorium_billing.api:app", host="0.0.0.0", port=8001, reload=True)


if __name__ == "__main__":
    run()
