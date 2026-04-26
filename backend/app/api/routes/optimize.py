from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.adaptive import OptimizeStartRequest
from app.services.optimize_service import OptimizeService, get_optimize_service

router = APIRouter()


@router.post("/run")
async def run(
    req: OptimizeStartRequest,
    svc: OptimizeService = Depends(get_optimize_service),
) -> dict[str, int]:
    run_id = await svc.submit(req.base_params, req.symbols, req.n_trials, req.days)
    return {"run_id": run_id}


@router.post("/{run_id}/apply")
async def apply(
    run_id: int,
    svc: OptimizeService = Depends(get_optimize_service),
) -> dict:
    try:
        return await svc.apply_best(run_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
