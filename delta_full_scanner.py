"""Delta Futures Full Scanner."""

from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from delta_futures import DeltaFutures
from signals import get_signals
from risk_manager import calculate_delta_trade_details

DEFAULT_MAX_WORKERS = 6


def get_delta_market_data():
    """Return live normalized Delta market data keyed by symbol."""
    market = DeltaFutures().get_all_market_data()

    data = {}

    for item in market:
        if not isinstance(item, dict):
            continue

        symbol = str(item.get("symbol", "")).strip()

        state = str(
            item.get("state", "")
        ).strip().lower()

        if symbol and state == "live":
            data[symbol] = item

    return data


def get_delta_symbols():
    """Return live Delta futures/perpetual symbols."""
    market_data = get_delta_market_data()
    return sorted(market_data.keys())


def scan_delta_symbol(symbol, market_data=None):
    """Scan one Delta contract using the existing signal engine."""
    try:
        result = get_signals(symbol)

        if not isinstance(result, dict):
            return {
                "Symbol": symbol,
                "SIGNAL": "ERROR",
                "Signal_Strength": 0.0,
                "Signal_Type": "ERROR",
                "error": "Invalid signal result",
            }

        signal = str(
            result.get(
                "SIGNAL",
                result.get("Signal", "HOLD"),
            )
        ).upper()

        strength = float(
            result.get("Signal_Strength", 0.0) or 0.0
        )

        result["Symbol"] = str(
            result.get("Symbol", symbol)
        ).strip()

        result["SIGNAL"] = signal
        result["Signal_Strength"] = strength

        result["scan_signal"] = signal
        result["confidence"] = strength
        result["score"] = strength

        if signal == "BUY":
            result["execution_direction"] = "LONG"
        elif signal == "SELL":
            result["execution_direction"] = "SHORT"
        else:
            result["execution_direction"] = "FLAT"

        # -------------------------------------------------
        # DELTA MARKET DATA
        # -------------------------------------------------

        if market_data is None:
            market_data = {}

        market = market_data.get(symbol, {})

        result["market_price"] = market.get(
            "price"
        )

        result["mark_price"] = market.get(
            "mark_price"
        )

        result["spot_price"] = market.get(
            "spot_price"
        )

        result["change_24h"] = market.get(
            "change_24h"
        )

        result["mark_change_24h"] = market.get(
            "mark_change_24h"
        )

        result["market_volume"] = market.get(
            "volume"
        )

        result["open_interest"] = market.get(
            "open_interest"
        )

        result["oi_value_usd"] = market.get(
            "oi_value_usd"
        )

        result["oi_change_6h_usd"] = market.get(
            "oi_change_6h_usd"
        )

        result["funding_rate"] = market.get(
            "funding_rate"
        )

        result["best_bid"] = market.get(
            "best_bid"
        )

        result["best_ask"] = market.get(
            "best_ask"
        )

        result["leverage"] = market.get(
            "leverage"
        )

        result["contract_type"] = market.get(
            "contract_type"
        )

        result["position_size_limit"] = market.get("position_size_limit")
        result["position_notional_limit"] = market.get("position_notional_limit")

        result["contract_value"] = market.get(
            "contract_value"
        )

        result["tick_size"] = market.get(
            "tick_size"
        )

        result["trading_status"] = market.get(
            "trading_status"
        )

        result["description"] = market.get(
            "description"
        )

        result["tags"] = market.get(
            "tags"
        )

        return result

    except Exception as exc:
        return {
            "Symbol": symbol,
            "SIGNAL": "ERROR",
            "Signal_Strength": 0.0,
            "Signal_Type": "ERROR",
            "scan_signal": "ERROR",
            "confidence": 0.0,
            "score": 0.0,
            "execution_direction": "FLAT",
            "error": str(exc),
        }


def scan_delta_full(
    symbols=None,
    max_workers=DEFAULT_MAX_WORKERS,
    capital=100000.0,
):
    """Scan Delta futures/perpetual contracts and rank results."""

    market_data = get_delta_market_data()

    if symbols is None:
        symbols = sorted(market_data.keys())

    symbols = [
        str(symbol).strip()
        for symbol in symbols
        if str(symbol).strip()
    ]

    results = []

    workers = max(
        1,
        min(int(max_workers), 8),
    )

    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:

        futures = {
            executor.submit(
                scan_delta_symbol,
                symbol,
                market_data,
            ): symbol
            for symbol in symbols
        }

        for future in as_completed(futures):

            symbol = futures[future]

            try:
                results.append(
                    future.result()
                )

            except Exception as exc:
                results.append(
                    {
                        "Symbol": symbol,
                        "SIGNAL": "ERROR",
                        "Signal_Strength": 0.0,
                        "Signal_Type": "ERROR",
                        "scan_signal": "ERROR",
                        "confidence": 0.0,
                        "score": 0.0,
                        "execution_direction": "FLAT",
                        "error": str(exc),
                    }
                )

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)

    # -----------------------------------------------------
    # NUMERIC RANKING
    # -----------------------------------------------------

    df["confidence"] = pd.to_numeric(
        df.get("confidence", 0),
        errors="coerce",
    ).fillna(0.0)

    signal_priority = {
        "BUY": 2,
        "SELL": 2,
        "HOLD": 1,
        "ERROR": 0,
    }

    df["signal_priority"] = (
        df["SIGNAL"]
        .astype(str)
        .str.upper()
        .map(signal_priority)
        .fillna(0)
    )

    # -----------------------------------------------------
    # DIRECTION-AWARE AI RANK SCORE
    # -----------------------------------------------------

    strength = pd.to_numeric(
        df.get("Signal_Strength", 0),
        errors="coerce",
    ).fillna(0.0).clip(0, 100)

    change_24h = pd.to_numeric(
        df.get("change_24h", 0),
        errors="coerce",
    ).fillna(0.0)

    # Positive momentum supports BUY.
    # Negative momentum supports SELL.
    # The score is centered at 50 and capped to avoid saturation.
    directional_momentum = pd.Series(
        50.0,
        index=df.index,
        dtype="float64",
    )

    buy_mask = df["SIGNAL"].astype(str).str.upper().eq("BUY")
    sell_mask = df["SIGNAL"].astype(str).str.upper().eq("SELL")

    directional_momentum.loc[buy_mask] = (
        50.0 + (change_24h.loc[buy_mask].clip(-20, 20) * 1.5)
    )

    directional_momentum.loc[sell_mask] = (
        50.0 - (change_24h.loc[sell_mask].clip(-20, 20) * 1.5)
    )

    directional_momentum = directional_momentum.clip(0, 100)

    df["Momentum_Score"] = directional_momentum.round(2)

    df["AI_Rank_Score"] = (
        (strength * 0.70)
        + (directional_momentum * 0.20)
        + (df["signal_priority"] * 5.0)
    ).clip(0, 100).round(2)

    # -----------------------------------------------------
    # RANK
    # -----------------------------------------------------

    df = df.sort_values(
        by=[
            "signal_priority",
            "AI_Rank_Score",
            "Signal_Strength",
        ],
        ascending=[
            False,
            False,
            False,
        ],
        kind="stable",
    ).reset_index(drop=True)

    df.insert(
        0,
        "Rank",
        range(1, len(df) + 1),
    )

# -----------------------------------------------------
    # AI CANDIDATE FILTER
    # -----------------------------------------------------

    df["AI_Candidate"] = (
        df["SIGNAL"].astype(str).str.upper().isin(["BUY", "SELL"])
        & (pd.to_numeric(df["Signal_Strength"], errors="coerce").fillna(0) >= 70)
        & (pd.to_numeric(df["AI_Rank_Score"], errors="coerce").fillna(0) >= 75)
    )

    df["AI_Candidate"] = df["AI_Candidate"].astype(bool)


    # -----------------------------------------------------
    # TOP-N AI CANDIDATE SELECTION
    # -----------------------------------------------------

    df["AI_Candidate_Rank"] = 0

    candidate_mask = df["AI_Candidate"]

    candidate_indices = df.loc[candidate_mask].sort_values(
        by=["AI_Rank_Score", "Signal_Strength"],
        ascending=[False, False],
        kind="stable",
    ).head(10).index

    df.loc[candidate_indices, "AI_Candidate_Rank"] = range(
        1,
        len(candidate_indices) + 1,
    )

    df["AI_Top_Candidate"] = df["AI_Candidate_Rank"] == 1
    # -----------------------------------------------------
    # DELTA RISK / SL / TARGET FOR TOP AI CANDIDATES
    # -----------------------------------------------------

    df["AI_Entry"] = 0.0
    df["AI_Stoploss"] = 0.0
    df["AI_Target"] = 0.0
    df["AI_Contracts"] = 0
    df["AI_Risk_Per_Contract"] = 0.0
    df["AI_Actual_Risk"] = 0.0
    df["AI_Potential_Profit"] = 0.0

    for idx in candidate_indices:
        row = df.loc[idx]

        try:
            entry_price = float(row.get("market_price", 0) or 0)
            contract_value = float(row.get("contract_value", 0) or 0)
            tick_size = float(row.get("tick_size", 0) or 0)

            max_contracts = row.get("position_size_limit")
            max_notional = row.get("position_notional_limit")

            direction = str(
                row.get("execution_direction", "FLAT")
            ).upper().strip()

            if (
                entry_price <= 0
                or contract_value <= 0
                or direction not in ("LONG", "SHORT")
            ):
                continue

            if direction == "LONG":
                stoploss_price = entry_price * 0.99
            else:
                stoploss_price = entry_price * 1.01

            risk_details = calculate_delta_trade_details(
                capital=capital,
                entry_price=entry_price,
                stoploss_price=stoploss_price,
                contract_value=contract_value,
                reward_ratio=2.0,
                direction=direction,
                tick_size=tick_size if tick_size > 0 else None,
                max_contracts=(
                    int(float(max_contracts))
                    if max_contracts is not None
                    else None
                ),
                max_notional=(
                    float(max_notional)
                    if max_notional is not None
                    else None
                ),
            )

            df.loc[idx, "AI_Entry"] = risk_details["entry_price"]
            df.loc[idx, "AI_Stoploss"] = risk_details["stoploss_price"]
            df.loc[idx, "AI_Target"] = risk_details["target_price"]
            df.loc[idx, "AI_Contracts"] = risk_details["contracts"]
            df.loc[idx, "AI_Risk_Per_Contract"] = risk_details["risk_per_contract"]
            df.loc[idx, "AI_Actual_Risk"] = risk_details["actual_risk"]
            df.loc[idx, "AI_Potential_Profit"] = risk_details["potential_profit"]

        except Exception as exc:
            df.loc[idx, "AI_Risk_Error"] = str(exc)
    return df
