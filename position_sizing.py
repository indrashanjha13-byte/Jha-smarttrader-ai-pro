def create_features(df):

    df["EMA_DIFF"] = (
        df["EMA20"] - df["EMA50"]
    )

    df["RSI_NORM"] = (
        df["RSI"] / 100
    )

    df["VOL_RATIO"] = (
        df["Volume"] /
        df["Volume"].rolling(20).mean()
    )

    return df
