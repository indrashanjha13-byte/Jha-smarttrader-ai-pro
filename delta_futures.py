"""
Jha SmartTrader AI Pro
Delta Exchange India - Futures Market Data

Supports:
- All live futures/perpetual contracts
- Product metadata
- Bulk tickers
- Normalized all-contract market data
- Gainers / Losers
- Volume ranking
- Open-interest ranking
- Symbol search
- Single ticker lookup

No live orders are placed by this module.
"""

from __future__ import annotations

import logging
from typing import Any

import requests


# =========================================================
# CONFIG
# =========================================================

BASE_URL = "https://api.india.delta.exchange"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


# =========================================================
# HELPERS
# =========================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert API values to float."""
    try:
        if value is None:
            return default

        result = float(value)

        if result != result:  # NaN
            return default

        return result

    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert API values to int."""
    try:
        if value is None:
            return default

        return int(float(value))

    except (TypeError, ValueError):
        return default


# =========================================================
# DELTA FUTURES
# =========================================================

class DeltaFutures:

    def __init__(self):
        self.base_url = BASE_URL

        self.session = requests.Session()

        self.session.headers.update({
            "Accept": "application/json"
        })

    # =====================================================
    # GET
    # =====================================================

    def _get(
        self,
        endpoint: str,
        params: dict | None = None,
        timeout: int = 10,
    ) -> dict:

        try:

            url = f"{self.base_url}{endpoint}"

            response = self.session.get(
                url,
                params=params or {},
                timeout=timeout,
            )

            response.raise_for_status()

            data = response.json()

            if not isinstance(data, dict):
                return {}

            return data

        except requests.RequestException as e:

            logging.error(
                "Delta API request error | Endpoint=%s | Error=%s",
                endpoint,
                e,
            )

            return {}

        except Exception as e:

            logging.exception(
                "Delta API error | Endpoint=%s | Error=%s",
                endpoint,
                e,
            )

            return {}

    # =====================================================
    # TEST CONNECTION
    # =====================================================

    def test_connection(self):

        try:

            products = self.get_futures()

            if products:
                return True, products

            return False, []

        except Exception as e:

            logging.exception(
                "Delta Futures connection error"
            )

            return False, str(e)

    # =====================================================
    # GET ALL FUTURES / PERPETUAL CONTRACTS
    # =====================================================

    def get_futures(self, max_pages: int = 10):

        all_products = []

        after = None

        for _page in range(max_pages):

            params = {
                "contract_types": "futures,perpetual_futures",
                "states": "live",
                "page_size": 100,
            }

            if after:
                params["after"] = after

            data = self._get(
                "/v2/products",
                params=params,
                timeout=15,
            )

            if not data.get("success"):

                logging.error(
                    "Delta products request failed: %s",
                    data,
                )

                break

            result = data.get(
                "result",
                [],
            )

            if not isinstance(result, list):
                break

            if not result:
                break

            all_products.extend(result)

            meta = data.get(
                "meta",
                {},
            )

            if not isinstance(meta, dict):
                break

            next_cursor = meta.get("after")

            if not next_cursor:
                break

            if next_cursor == after:
                break

            after = next_cursor

            total_count = meta.get(
                "total_count"
            )

            if total_count:

                try:

                    if len(all_products) >= int(
                        total_count
                    ):
                        break

                except (
                    TypeError,
                    ValueError,
                ):
                    pass

        # -------------------------------------------------
        # Remove duplicate symbols
        # -------------------------------------------------

        unique = {}

        for product in all_products:

            if not isinstance(product, dict):
                continue

            symbol = str(
                product.get(
                    "symbol",
                    "",
                )
            ).strip().upper()

            if symbol:
                unique[symbol] = product

        logging.info(
            "Delta Futures loaded | %s unique contracts",
            len(unique),
        )

        return list(unique.values())

    # =====================================================
    # GET PERPETUAL FUTURES ONLY
    # =====================================================

    def get_perpetual_futures(
        self,
        max_pages: int = 10,
    ):

        products = self.get_futures(
            max_pages=max_pages
        )

        perpetual = []

        for product in products:

            if not isinstance(product, dict):
                continue

            contract_type = str(
                product.get(
                    "contract_type",
                    "",
                )
            ).strip().lower()

            state = str(
                product.get(
                    "state",
                    "",
                )
            ).strip().lower()

            if (
                contract_type
                == "perpetual_futures"
                and state == "live"
            ):
                perpetual.append(product)

        logging.info(
            "Delta perpetual futures loaded | %s contracts",
            len(perpetual),
        )

        return perpetual

    # =====================================================
    # GET SINGLE TICKER
    # =====================================================

    def get_ticker(self, symbol: str):

        symbol = str(
            symbol
        ).strip().upper()

        if not symbol:
            return {}

        try:

            data = self._get(
                f"/v2/tickers/{symbol}",
                timeout=10,
            )

            if not data.get("success"):

                logging.error(
                    "Delta ticker failed | Symbol=%s | Response=%s",
                    symbol,
                    data,
                )

                return {}

            result = data.get(
                "result",
                {},
            )

            if not isinstance(result, dict):
                return {}

            # -------------------------------------------------
            # Normalize price
            # -------------------------------------------------

            price = 0.0

            for field in (
                "mark_price",
                "close",
                "last_price",
                "spot_price",
            ):

                value = _safe_float(
                    result.get(field)
                )

                if value > 0:

                    price = value

                    break

            # -------------------------------------------------
            # Bid / Ask fallback
            # -------------------------------------------------

            if price <= 0:

                quotes = result.get(
                    "quotes",
                    {},
                )

                if isinstance(quotes, dict):

                    for field in (
                        "best_bid",
                        "best_ask",
                    ):

                        value = _safe_float(
                            quotes.get(field)
                        )

                        if value > 0:

                            price = value

                            break

            result["price"] = price

            return result

        except Exception as e:

            logging.exception(
                "Delta ticker error | Symbol=%s | Error=%s",
                symbol,
                e,
            )

            return {}

    # =====================================================
    # GET MULTIPLE TICKERS
    # =====================================================

    def get_all_tickers(self):

        try:

            data = self._get(
                "/v2/tickers",
                params={
                    "contract_types":
                        "futures,perpetual_futures",
                },
                timeout=20,
            )

            if not data.get("success"):
                return []

            result = data.get(
                "result",
                [],
            )

            if not isinstance(result, list):
                return []

            normalized = []

            for ticker in result:

                if not isinstance(ticker, dict):
                    continue

                symbol = str(
                    ticker.get(
                        "symbol",
                        "",
                    )
                ).strip().upper()

                if not symbol:
                    continue

                # -------------------------------------------------
                # Normalize price
                # -------------------------------------------------

                price = 0.0

                for field in (
                    "mark_price",
                    "close",
                    "last_price",
                    "spot_price",
                ):

                    value = _safe_float(
                        ticker.get(field)
                    )

                    if value > 0:

                        price = value

                        break

                ticker["price"] = price

                normalized.append(ticker)

            logging.info(
                "Delta tickers loaded | %s contracts",
                len(normalized),
            )

            return normalized

        except Exception:

            logging.exception(
                "Delta bulk ticker error"
            )

            return []

    # =====================================================
    # PRODUCT MAP
    # =====================================================

    def get_product_map(self):

        products = self.get_futures()

        return {
            str(
                product.get(
                    "symbol",
                    "",
                )
            ).strip().upper(): product

            for product in products

            if (
                isinstance(product, dict)
                and product.get("symbol")
            )
        }

    # =====================================================
    # TICKER MAP
    # =====================================================

    def get_ticker_map(self):

        tickers = self.get_all_tickers()

        return {
            str(
                ticker.get(
                    "symbol",
                    "",
                )
            ).strip().upper(): ticker

            for ticker in tickers

            if (
                isinstance(ticker, dict)
                and ticker.get("symbol")
            )
        }

    # =====================================================
    # NORMALIZED ALL CONTRACT MARKET DATA
    # =====================================================

    def get_all_market_data(self):

        products = self.get_futures()

        tickers = self.get_all_tickers()

        product_map = {
            str(
                product.get(
                    "symbol",
                    "",
                )
            ).strip().upper(): product

            for product in products

            if (
                isinstance(product, dict)
                and product.get("symbol")
            )
        }

        ticker_map = {
            str(
                ticker.get(
                    "symbol",
                    "",
                )
            ).strip().upper(): ticker

            for ticker in tickers

            if (
                isinstance(ticker, dict)
                and ticker.get("symbol")
            )
        }

        symbols = sorted(
            set(product_map)
            | set(ticker_map)
        )

        market_data = []

        for symbol in symbols:

            product = product_map.get(
                symbol,
                {},
            )

            ticker = ticker_map.get(
                symbol,
                {},
            )

            quotes = ticker.get(
                "quotes",
                {},
            )

            if not isinstance(quotes, dict):
                quotes = {}

            record = {
                # ---------------------------------------------
                # Identity
                # ---------------------------------------------

                "symbol": symbol,

                "underlying": (
                    ticker.get(
                        "underlying_asset_symbol"
                    )
                    or product.get(
                        "underlying_asset",
                        {}
                    ).get(
                        "symbol"
                    )
                    if isinstance(
                        product.get(
                            "underlying_asset",
                            {}
                        ),
                        dict,
                    )
                    else symbol
                ),

                "product_id": (
                    ticker.get(
                        "product_id"
                    )
                    or product.get("id")
                ),

                "contract_type": (
                    product.get(
                        "contract_type"
                    )
                    or ticker.get(
                        "contract_type"
                    )
                ),

                # ---------------------------------------------
                # Price
                # ---------------------------------------------

                "price": _safe_float(
                    ticker.get("price")
                ),

                "mark_price": _safe_float(
                    ticker.get("mark_price")
                ),

                "spot_price": _safe_float(
                    ticker.get("spot_price")
                ),

                "open": _safe_float(
                    ticker.get("open")
                ),

                "high": _safe_float(
                    ticker.get("high")
                ),

                "low": _safe_float(
                    ticker.get("low")
                ),

                # ---------------------------------------------
                # 24H
                # ---------------------------------------------

                "change_24h": _safe_float(
                    ticker.get(
                        "ltp_change_24h"
                    )
                ),

                "mark_change_24h": _safe_float(
                    ticker.get(
                        "mark_change_24h"
                    )
                ),

                # ---------------------------------------------
                # Volume
                # ---------------------------------------------

                "volume": _safe_float(
                    ticker.get("volume")
                ),

                "turnover": _safe_float(
                    ticker.get("turnover")
                ),

                "turnover_usd": _safe_float(
                    ticker.get("turnover_usd")
                ),

                # ---------------------------------------------
                # Open Interest
                # ---------------------------------------------

                "open_interest": _safe_float(
                    ticker.get("oi")
                ),

                "oi_contracts": _safe_float(
                    ticker.get("oi_contracts")
                ),

                "oi_value": _safe_float(
                    ticker.get("oi_value")
                ),

                "oi_value_usd": _safe_float(
                    ticker.get("oi_value_usd")
                ),

                "oi_change_6h_usd": _safe_float(
                    ticker.get(
                        "oi_change_usd_6h"
                    )
                ),

                # ---------------------------------------------
                # Funding
                # ---------------------------------------------

                "funding_rate": _safe_float(
                    ticker.get(
                        "funding_rate"
                    )
                ),

                # ---------------------------------------------
                # Order book
                # ---------------------------------------------

                "best_bid": _safe_float(
                    quotes.get("best_bid")
                ),

                "best_ask": _safe_float(
                    quotes.get("best_ask")
                ),

                "bid_size": _safe_float(
                    quotes.get("bid_size")
                ),

                "ask_size": _safe_float(
                    quotes.get("ask_size")
                ),

                # ---------------------------------------------
                # Contract information
                # ---------------------------------------------

                "leverage": _safe_float(
                    product.get(
                        "default_leverage"
                    )
                ),

                "initial_margin": _safe_float(
                    product.get(
                        "initial_margin"
                    )
                ),

                "maintenance_margin": _safe_float(
                    product.get(
                        "maintenance_margin"
                    )
                ),

                "contract_value": _safe_float(
                    product.get(
                        "contract_value"
                    )
                ),

                "tick_size": _safe_float(
                    product.get(
                        "tick_size"
                    )
                ),

                "position_size_limit": _safe_float(
                    product.get(
                        "position_size_limit"
                    )
                ),

                "position_notional_limit": _safe_float(
                    product.get(
                        "position_notional_limit"
                    )
                ),

                # ---------------------------------------------
                # Status
                # ---------------------------------------------

                "state": product.get(
                    "state"
                ),

                "trading_status": (
                    ticker.get(
                        "product_trading_status"
                    )
                    or product.get(
                        "trading_status"
                    )
                ),

                "description": (
                    product.get(
                        "short_description"
                    )
                    or ticker.get(
                        "description"
                    )
                ),

                "tags": ticker.get(
                    "tags",
                    [],
                ),
            }

            market_data.append(record)

        logging.info(
            "Delta normalized market data | %s contracts",
            len(market_data),
        )

        return market_data

    # =====================================================
    # SEARCH SYMBOLS
    # =====================================================

    def search_symbols(
        self,
        query: str,
    ):

        query = str(
            query
        ).strip().upper()

        if not query:
            return []

        market_data = self.get_all_market_data()

        return [
            item
            for item in market_data
            if (
                query in str(
                    item.get(
                        "symbol",
                        "",
                    )
                ).upper()
                or query in str(
                    item.get(
                        "underlying",
                        "",
                    )
                ).upper()
            )
        ]

    # =====================================================
    # TOP GAINERS
    # =====================================================

    def get_top_gainers(
        self,
        limit: int = 20,
    ):

        data = self.get_all_market_data()

        return sorted(
            data,
            key=lambda x: x.get(
                "change_24h",
                0.0,
            ),
            reverse=True,
        )[:limit]

    # =====================================================
    # TOP LOSERS
    # =====================================================

    def get_top_losers(
        self,
        limit: int = 20,
    ):

        data = self.get_all_market_data()

        return sorted(
            data,
            key=lambda x: x.get(
                "change_24h",
                0.0,
            ),
        )[:limit]

    # =====================================================
    # TOP VOLUME
    # =====================================================

    def get_top_volume(
        self,
        limit: int = 20,
    ):

        data = self.get_all_market_data()

        return sorted(
            data,
            key=lambda x: x.get(
                "turnover_usd",
                0.0,
            ),
            reverse=True,
        )[:limit]

    # =====================================================
    # TOP OPEN INTEREST
    # =====================================================

    def get_top_open_interest(
        self,
        limit: int = 20,
    ):

        data = self.get_all_market_data()

        return sorted(
            data,
            key=lambda x: x.get(
                "oi_value_usd",
                0.0,
            ),
            reverse=True,
        )[:limit]

    # =====================================================
    # SINGLE NORMALIZED CONTRACT
    # =====================================================

    def get_market_data(
        self,
        symbol: str,
    ):

        symbol = str(
            symbol
        ).strip().upper()

        if not symbol:
            return {}

        data = self.get_all_market_data()

        for item in data:

            if item.get(
                "symbol"
            ) == symbol:

                return item

        return {}

    # =====================================================
    # QUICK SYMBOL LIST
    # =====================================================

    def get_symbols(self):

        products = self.get_futures()

        symbols = []

        for product in products:

            if not isinstance(product, dict):
                continue

            symbol = str(
                product.get(
                    "symbol",
                    "",
                )
            ).strip().upper()

            if symbol:
                symbols.append(symbol)

        return sorted(
            list(set(symbols))
        )


# =========================================================
# QUICK TEST
# =========================================================

if __name__ == "__main__":

    delta = DeltaFutures()

    print("=" * 70)
    print("Jha SmartTrader AI Pro")
    print("Delta Exchange India Futures")
    print("=" * 70)

    success, futures = (
        delta.test_connection()
    )

    if success:

        print(
            "Delta Futures connection OK"
        )

        print(
            "Total Futures/Perpetual Contracts:",
            len(futures),
        )

        print("-" * 70)

        for product in futures[:20]:

            print(
                product.get("symbol"),
                "|",
                product.get("contract_type"),
                "| ID:",
                product.get("id"),
            )

        print("-" * 70)

        print(
            "Loading normalized All Contracts..."
        )

        market_data = (
            delta.get_all_market_data()
        )

        print(
            "Normalized Contracts:",
            len(market_data),
        )

        if market_data:

            print("-" * 70)

            for item in market_data[:10]:

                print(
                    item["symbol"],
                    "| Price:",
                    item["price"],
                    "| 24H:",
                    item["change_24h"],
                    "| Volume:",
                    item["volume"],
                    "| OI:",
                    item["open_interest"],
                    "| Funding:",
                    item["funding_rate"],
                    "| Lev:",
                    item["leverage"],
                )

    else:

        print(
            "Delta Futures connection FAILED"
        )