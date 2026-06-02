from __future__ import annotations

import numpy as np
import pandas as pd

try:
    import vectorbt as vbt
except ImportError as exc:
    raise ImportError(
        "vectorbt is required for competition/code/src. Create the uv environment with 'uv sync' and run the notebook from that environment."
    ) from exc


TRADING_DAYS_PER_YEAR = 252


def _align_inputs(prices: pd.DataFrame, target_weights: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    common_index = prices.index.intersection(target_weights.index)
    common_columns = prices.columns.intersection(target_weights.columns)
    if common_index.empty or len(common_columns) == 0:
        raise ValueError("prices and target_weights must share a non-empty index and columns")

    aligned_prices = prices.loc[common_index, common_columns].sort_index().ffill()
    aligned_weights = target_weights.loc[common_index, common_columns].sort_index().fillna(0.0)
    return aligned_prices, aligned_weights


def _base_nav(nav: pd.Series, portfolio: vbt.Portfolio) -> pd.Series:
    return nav.shift(1).fillna(float(portfolio.get_init_cash()))


def _order_records(portfolio: vbt.Portfolio) -> pd.DataFrame:
    records = portfolio.orders.records_readable.copy()
    if records.empty:
        return records
    records["Timestamp"] = pd.to_datetime(records["Timestamp"])
    return records


def _extract_fee_and_turnover_returns(portfolio: vbt.Portfolio, nav: pd.Series) -> tuple[pd.Series, pd.Series]:
    base_nav = _base_nav(nav, portfolio)
    fee_return = pd.Series(0.0, index=nav.index, dtype=float)
    turnover = pd.Series(0.0, index=nav.index, dtype=float)
    records = _order_records(portfolio)
    if records.empty:
        return fee_return, turnover

    fees_by_date = records.groupby("Timestamp")["Fees"].sum()
    notional_by_date = (records["Size"].abs() * records["Price"].abs()).groupby(records["Timestamp"]).sum()
    fee_return.loc[fees_by_date.index.intersection(fee_return.index)] = fees_by_date.reindex(fee_return.index, fill_value=0.0)
    turnover.loc[notional_by_date.index.intersection(turnover.index)] = notional_by_date.reindex(turnover.index, fill_value=0.0)

    fee_return = fee_return.div(base_nav).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    turnover = turnover.div(base_nav).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return fee_return, turnover


def build_vectorbt_portfolio(
    prices: pd.DataFrame,
    target_weights: pd.DataFrame,
    starting_nav: float = 1_000_000.0,
    transaction_cost_bps: float = 0.0,
) -> vbt.Portfolio:
    aligned_prices, aligned_weights = _align_inputs(prices, target_weights)
    return vbt.Portfolio.from_orders(
        close=aligned_prices,
        size=aligned_weights,
        size_type="targetpercent",
        init_cash=float(starting_nav),
        fees=float(transaction_cost_bps) / 10_000.0,
        cash_sharing=True,
        group_by=["portfolio"] * len(aligned_prices.columns),
    )


def compute_weight_diagnostics(
    prices: pd.DataFrame,
    target_weights: pd.DataFrame,
    portfolio: vbt.Portfolio | None = None,
    transaction_cost_bps: float = 0.0,
) -> pd.DataFrame:
    aligned_prices, aligned_weights = _align_inputs(prices, target_weights)
    if portfolio is None:
        portfolio = build_vectorbt_portfolio(
            prices=aligned_prices,
            target_weights=aligned_weights,
            transaction_cost_bps=transaction_cost_bps,
        )

    nav = portfolio.value()
    net_returns = portfolio.returns().reindex(aligned_prices.index).fillna(0.0)
    gross_exposure = portfolio.gross_exposure().reindex(aligned_prices.index).fillna(0.0)
    transaction_cost, turnover = _extract_fee_and_turnover_returns(portfolio, nav)
    gross_returns = net_returns + transaction_cost

    diagnostics = pd.DataFrame(
        {
            "gross_return": gross_returns,
            "return": net_returns,
            "nav": nav,
            "gross_exposure": gross_exposure,
            "turnover": turnover,
            "transaction_cost": transaction_cost,
        },
        index=aligned_prices.index,
    )
    diagnostics.index.name = aligned_prices.index.name
    return diagnostics


def performance_summary(
    returns: pd.Series,
    nav: pd.Series,
    gross_exposure: pd.Series | None = None,
    turnover: pd.Series | None = None,
    transaction_cost: pd.Series | None = None,
) -> pd.Series:
    clean_returns = pd.Series(returns, copy=False).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    clean_nav = pd.Series(nav, copy=False).replace([np.inf, -np.inf], np.nan).dropna()
    if clean_nav.empty:
        raise ValueError("nav must contain at least one finite observation")

    downside = np.minimum(clean_returns, 0.0)
    downside_deviation = float(np.sqrt(TRADING_DAYS_PER_YEAR * np.mean(downside ** 2)))
    annualized_return = float(clean_returns.mean() * TRADING_DAYS_PER_YEAR)
    annualized_vol = float(clean_returns.std(ddof=0) * np.sqrt(TRADING_DAYS_PER_YEAR))
    running_peak = clean_nav.cummax()
    drawdown = clean_nav / running_peak - 1.0
    max_drawdown = float(abs(drawdown.min()))
    sortino = float(annualized_return / downside_deviation) if downside_deviation > 0 else 0.0
    score_sr = float(sortino)

    summary = {
        "annualized_return": annualized_return,
        "annualized_vol": annualized_vol,
        "sortino": sortino,
        "max_drawdown": max_drawdown,
        "score_sr": score_sr,
        "final_nav": float(clean_nav.iloc[-1]),
        "total_return": float(clean_nav.iloc[-1] / clean_nav.iloc[0] - 1.0),
    }

    if gross_exposure is not None:
        gross_exposure = pd.Series(gross_exposure, copy=False).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        summary["avg_gross_exposure"] = float(gross_exposure.mean())
        summary["gross_exposure_p95"] = float(gross_exposure.quantile(0.95))

    if turnover is not None:
        turnover = pd.Series(turnover, copy=False).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        summary["avg_daily_turnover"] = float(turnover.mean())
        summary["turnover_p95"] = float(turnover.quantile(0.95))

    if transaction_cost is not None:
        transaction_cost = pd.Series(transaction_cost, copy=False).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        summary["annualized_transaction_cost"] = float(transaction_cost.mean() * TRADING_DAYS_PER_YEAR)
        summary["total_transaction_cost"] = float(transaction_cost.sum())

    return pd.Series(summary)