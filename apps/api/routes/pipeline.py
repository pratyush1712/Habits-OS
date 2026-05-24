"""Manual local pipeline orchestration routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.deps import get_pipeline_service
from apps.api.errors import InvalidOperationError
from apps.api.routes.events import MONTH_PATTERN
from apps.api.services.pipeline import PipelineRenderError, PipelineService, whoop_http_status
from packages.connectors.whoop.client import WhoopApiError


router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/month")
async def run_month_pipeline(
    external_user_id: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    month: str = Query(..., pattern=MONTH_PATTERN),
    upload: bool = Query(False),
    dry_run: bool = Query(True),
    service: PipelineService = Depends(get_pipeline_service),
) -> dict:
    try:
        return await service.run_month(
            external_user_id=external_user_id,
            start=start,
            end=end,
            month=month,
            upload=upload,
            dry_run=dry_run,
        )
    except InvalidOperationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except WhoopApiError as e:
        detail = {"integration": "whoop", "error": str(e), "status_code": e.status_code}
        if e.status_code == 401:
            detail["diagnostic"] = "WHOOP token unauthorized; re-run /whoop/oauth/start and callback."
        raise HTTPException(status_code=whoop_http_status(e), detail=detail) from e
    except PipelineRenderError as e:
        raise HTTPException(status_code=500, detail=e.detail) from e
