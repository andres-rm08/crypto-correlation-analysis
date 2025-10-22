# src/analysis_sql.py
from util_db import path_db
import numpy as np


def _z(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    m = np.nanmean(x)
    s = np.nanstd(x, ddof=0)
    if not np.isfinite(s) or s == 0:
        out = np.zeros_like(x, dtype=float)
        out[~np.isfinite(x)] = np.nan
        return out
    return (x - m) / s


def metrics():
    import pandas as pd
    import sqlite3
    conn = sqlite3.connect(path_db)
    df = pd.read_sql_query(
        """
        SELECT c.name, c.symbol, p.timestamp, p.price
        FROM prices p
        JOIN coins c ON p.coin_id = c.id
        """,
        conn,
    )
    conn.close()

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["symbol", "timestamp"])

    df["return"] = df.groupby("symbol", observed=True)["price"].pct_change()
    df["rolling_mean_7d"] = df.groupby("symbol", observed=True)["price"].transform(
        lambda x: x.rolling(7, min_periods=1).mean()
    )
    df["rolling_mean_30d"] = df.groupby("symbol", observed=True)["price"].transform(
        lambda x: x.rolling(30, min_periods=1).mean()
    )
    df["momentum"] = (df["rolling_mean_7d"] - df["rolling_mean_30d"]) / df[
        "rolling_mean_30d"
    ]

    volatility = df.groupby("symbol", observed=True)["return"].std()
    avg_return = df.groupby("symbol", observed=True)["return"].mean()

    returns_tbl = df.pivot(index="timestamp", columns="symbol", values="return")
    corr_coffs = returns_tbl.corr()

    avg_return = avg_return.sort_index()
    volatility = volatility.sort_index()

    df_recent = (
        df.groupby("symbol", observed=True)
        .tail(1)
        .set_index("symbol")
        .sort_index()
    )

    df_recent["z_score_return"] = _z(avg_return.values)
    df_recent["z_score_volatility"] = _z(volatility.values)
    df_recent["z_score_momentum"] = _z(df_recent["momentum"].values)

    df_recent["rec_score"] = (
        df_recent["z_score_return"]
        - df_recent["z_score_volatility"]
        + 0.5 * df_recent["z_score_momentum"]
    )

    df_recent = df_recent.sort_values("rec_score", ascending=False).reset_index()

    return df, df_recent, volatility, avg_return, corr_coffs
