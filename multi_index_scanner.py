# =========================================================
# JHA SMARTTRADER AI PRO
# MULTI INDEX SCANNER
# =========================================================

from index_config import INDIAN_OPTION_INDICES


# =========================================================
# SCANNABLE INDICES
# =========================================================

def get_scannable_indices():

    return list(
        INDIAN_OPTION_INDICES.keys()
    )


# =========================================================
# INDEX DISPLAY INFO
# =========================================================

def get_index_info(index_name):

    index_name = str(
        index_name
    ).upper().strip()

    return INDIAN_OPTION_INDICES.get(
        index_name,
        {}
    )


# =========================================================
# SCAN RESULT
# =========================================================

def create_scan_result(
    index_name,
    signal="WAIT",
    price=0.0,
    strategy="AI Combo"
):

    info = get_index_info(
        index_name
    )

    return {
        "index": index_name,
        "name": info.get(
            "name",
            index_name
        ),
        "symbol": info.get(
            "symbol",
            ""
        ),
        "exchange": info.get(
            "exchange",
            "NSE"
        ),
        "signal": str(
            signal
        ).upper(),
        "price": price,
        "strategy": strategy,
    }


# =========================================================
# MULTI INDEX SCANNER
# =========================================================

def scan_indices(signal_provider=None):

    results = []

    for index_name in get_scannable_indices():

        try:

            if signal_provider:

                result = signal_provider(
                    index_name
                )

                if isinstance(
                    result,
                    dict
                ):

                    result.setdefault(
                        "index",
                        index_name
                    )

                    results.append(
                        result
                    )

                else:

                    results.append(
                        create_scan_result(
                            index_name,
                            signal=str(
                                result
                            )
                        )
                    )

            else:

                results.append(
                    create_scan_result(
                        index_name
                    )
                )

        except Exception as e:

            results.append(
                {
                    "index": index_name,
                    "name": get_index_info(
                        index_name
                    ).get(
                        "name",
                        index_name
                    ),
                    "signal": "WAIT",
                    "price": 0.0,
                    "strategy": "AI Combo",
                    "error": str(e),
                }
            )

    return results


# =========================================================
# STRONGEST SIGNAL
# =========================================================

def get_best_signal(results):

    priority = {
        "BUY": 3,
        "SELL": 2,
        "WAIT": 1,
    }

    valid_results = [
        item
        for item in results
        if item.get(
            "signal",
            "WAIT"
        ) in priority
    ]

    if not valid_results:
        return None

    return max(
        valid_results,
        key=lambda item:
        priority.get(
            item.get(
                "signal",
                "WAIT"
            ),
            1
        )
    )


# =========================================================
# SIGNAL SUMMARY
# =========================================================

def signal_summary(results):

    summary = {
        "BUY": 0,
        "SELL": 0,
        "WAIT": 0,
    }

    for item in results:

        signal = str(
            item.get(
                "signal",
                "WAIT"
            )
        ).upper()

        if signal in summary:
            summary[signal] += 1

    return summary