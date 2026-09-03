from __future__ import annotations

from fastapi import APIRouter, Query

from app.config import PAPER_TRADING_DEFAULT_PORTFOLIO_ID
from app.models.schemas import PaperPortfolioResponse, PaperPositionModel, PaperTradeModel, PaperTradeRequest
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
        positions=[
            PaperPositionModel(
                ticker=p.ticker,
                shares=p.shares,
                avg_entry_price=p.avg_entry_price,
                current_price=p.current_price,
                market_value=p.market_value,
                unrealized_pnl=p.unrealized_pnl,
                unrealized_pnl_percent=p.unrealized_pnl_percent,
            )
            for p in view.positions
        ],
        trades=[
            PaperTradeModel(date=t.date, ticker=t.ticker, action=t.action, shares=t.shares, price=t.price, realized_pnl=t.realized_pnl)
            for t in view.trades
        ],
    )


@router.get("/paper-portfolio", response_model=PaperPortfolioResponse)
def get_paper_portfolio(portfolio_id: str = Query(default=PAPER_TRADING_DEFAULT_PORTFOLIO_ID)):
    view = paper_trading_service.get_portfolio(portfolio_id)
    return _to_response(view)


@router.post("/paper-trade", response_model=PaperPortfolioResponse)
def post_paper_trade(request: PaperTradeRequest):
    view = paper_trading_service.execute_trade(
        request.portfolio_id, request.ticker, request.action, request.shares
    )
    return _to_response(view)


@router.get("/paper-trades", response_model=list[PaperTradeModel])
def get_paper_trades(portfolio_id: str = Query(default=PAPER_TRADING_DEFAULT_PORTFOLIO_ID)):
    view = paper_trading_service.get_portfolio(portfolio_id)
    return [
        PaperTradeModel(date=t.date, ticker=t.ticker, action=t.action, shares=t.shares, price=t.price, realized_pnl=t.realized_pnl)
        for t in view.trades
    ]


@router.post("/paper-portfolio/reset", response_model=PaperPortfolioResponse)
def reset_paper_portfolio(
    portfolio_id: str = Query(default=PAPER_TRADING_DEFAULT_PORTFOLIO_ID),
    starting_capital: float | None = Query(default=None, gt=0),
):
    view = paper_trading_service.reset(portfolio_id, starting_capital)
    return _to_response(view)
