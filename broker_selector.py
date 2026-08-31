import pandas as pd
import numpy as np
import logging


def create_features(df):
    """
    Safely creates normalized features for Machine Learning model.
    Returns a clean copy of DataFrame without side effects or NaN values.
    """
    # 1. Check for Empty or Invalid Input DataFrame
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        logging.warning("⚠️ Invalid or empty DataFrame passed to create_features.")
        return pd.DataFrame()

    # Required Indicator Columns Check
    required_cols = ["EMA20", "EMA50", "RSI", "Volume"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        logging.error(f"❌ Missing required columns for feature creation: {missing_cols}")
        return df

    # 2. Avoid modifying original DataFrame (Use Copy)
    df_feat = df.copy()

    # 3. Feature Calculations
    df_feat["EMA_DIFF"] = df_feat["EMA20"] - df_feat["EMA50"]
    df_feat["RSI_NORM"] = df_feat["RSI"] / 100.0

    # Rolling Volume Ratio with Zero-Division Protection
    vol_ma20 = df_feat["Volume"].rolling(20, min_periods=1).mean()
    df_feat["VOL_RATIO"] = np.where(vol_ma20 > 0, df_feat["Volume"] / vol_ma20, 1.0)

    # 4. Fill potential NaNs safely
    df_feat["EMA_DIFF"] = df_feat["EMA_DIFF"].fillna(0.0)
    df_feat["RSI_NORM"] = df_feat["RSI_NORM"].fillna(0.5)
    df_feat["VOL_RATIO"] = df_feat["VOL_RATIO"].fillna(1.0)

    return df_feat