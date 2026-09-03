from __future__ import annotations

from fastapi import APIRouter, Query

from app.config import PAPER_TRADING_DEFAULT_PORTFOLIO_ID
from app.models.schemas import (
    ForwardValidationResponse,
    PaperEquityHistoryResponse,
    PaperEquitySnapshotModel,
    PaperPortfolioResponse,
    PaperPositionModel,
    PaperRiskResponse,
    PaperTradeModel,
    PaperTradeRequest,
)
from app.paper_trading import forward_validation
from app.paper_trading import risk as paper_risk
from app.paper_trading import service as paper_trading_service

router = APIRouter(prefix="/api", tags=["paper-trading"])


def _to_response(view) -> PaperPortfolioResponse:
    return PaperPortfolioResponse(
        portfolio_id=view.portfolio_id,
        starting_capital=view.starting_capital,
        cash=round(view.cash, 2),
        invested_capital=view.invested_capital,
        current_value=view.current_value,
        total_return_percent=view.total_return_percent,
        realized_pnl=view.realized_pnl,
        unrealized_pnl=view.unrealized_pnl,
        number_of_positions=view.number_of_positions,
        exposure_percent=view.exposure_percent,
        largest_position_percent=view.largest_position_percent,
        cash_percent=view.cash_percent,
        positions=[PaperPositionModel(**p.__dict__) for p in view.positions],
        trades=[PaperTradeModel(**t.__dict__) for t in view.trades],
    )


@router.get("/paper-portfolio", response_model=PaperPortfolioResponse)
def get_paper_portfolio(portfolio_id: str = Query(default=PAPER_TRADING_DEFAULT_PORTFOLIO_ID)):
    view = paper_trading_service.get_portfolio(portfolio_id)
    return _to_response(view)


@router.post("/paper-trade", response_model=PaperPortfolioResponse)
def post_paper_trade(request: PaperTradeRequest):
    view = paper_trading_service.execute_trade(
        portfolio_id=request.portfolio_id,
        ticker=request.ticker,
        action=request.action,
        shares=request.shares,
        sizing_mode=request.sizing_mode,
        capital_percent=request.capital_percent,
        risk_percent=request.risk_percent,
        stop_loss_percent=request.stop_loss_percent,
        take_profit_percent=request.take_profit_percent,
        trailing_stop_percent=request.trailing_stop_percent,
        max_position_percent=request.max_position_percent,
    )
    return _to_response(view)


@router.get("/paper-trades", response_model=list[PaperTradeModel])
def get_paper_trades(portfolio_id: str = Query(default=PAPER_TRADING_DEFAULT_PORTFOLIO_ID)):
    view = paper_trading_service.get_portfolio(portfolio_id)
    return [PaperTradeModel(**t.__dict__) for t in view.trades]


@router.post("/paper-portfolio/reset", response_model=PaperPortfolioResponse)
def reset_paper_portfolio(
    portfolio_id: str = Query(default=PAPER_TRADING_DEFAULT_PORTFOLIO_ID),
    starting_capital: float | None = Query(default=None, gt=0),
):
    view = paper_trading_service.reset(portfolio_id, starting_capital)
    return _to_response(view)


@router.post("/paper-portfolio/close-all", response_model=PaperPortfolioResponse)
def close_all_paper_positions(portfolio_id: str = Query(default=PAPER_TRADING_DEFAULT_PORTFOLIO_ID)):
    view = paper_trading_service.close_all_positions(portfolio_id, exit_reason="END_OF_TEST")
    return _to_response(view)


@router.get("/paper-portfolio/risk", response_model=PaperRiskResponse)
def get_paper_portfolio_risk(portfolio_id: str = Query(default=PAPER_TRADING_DEFAULT_PORTFOLIO_ID)):
    view = paper_trading_service.get_portfolio(portfolio_id)
    result = paper_risk.assess_portfolio_risk(view)
    return PaperRiskResponse(**result.__dict__)


@router.get("/paper-portfolio/history", response_model=PaperEquityHistoryResponse)
def get_paper_portfolio_history(portfolio_id: str = Query(default=PAPER_TRADING_DEFAULT_PORTFOLIO_ID)):
    view = paper_trading_service.get_equity_history(portfolio_id)
    return PaperEquityHistoryResponse(
        portfolio_id=view.portfolio_id,
        starting_capital=view.starting_capital,
        benchmark_ticker=view.benchmark_ticker,
        snapshots=[PaperEquitySnapshotModel(**s.__dict__) for s in view.snapshots],
    )


@router.get("/paper-portfolio/forward-validation", response_model=ForwardValidationResponse)
def get_forward_validation(portfolio_id: str = Query(default=PAPER_TRADING_DEFAULT_PORTFOLIO_ID)):
    view = forward_validation.get_forward_validation(portfolio_id)
    return ForwardValidationResponse(**view.__dict__)
