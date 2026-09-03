from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.comparison.service import compare_stocks
from app.models.schemas import ComparisonRequest, ComparisonResponse, ComparisonRowModel
from app.utils.validation import normalize_and_validate_ticker

router = APIRouter(prefix="/api", tags=["comparison"])


@router.post("/compare", response_model=ComparisonResponse)
def post_compare(request: ComparisonRequest):
    tickers = [normalize_and_validate_ticker(t) for t in request.tickers]
    benchmark = normalize_and_validate_ticker(request.benchmark_ticker)

    try:
        result = compare_stocks(tickers, benchmark_ticker=benchmark)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ComparisonResponse(
        tickers=result.tickers,
        benchmark_ticker=result.benchmark_ticker,
        rows=[ComparisonRowModel(**r.__dict__) for r in result.rows],
        methodology=result.methodology,
    )
