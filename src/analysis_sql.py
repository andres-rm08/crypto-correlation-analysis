
def metrics():
    import pandas as pd
    import sqlite3
    from scipy.stats import zscore

    conn = sqlite3.connect("../crypto_data.db")

    df = pd.read_sql_query(
        """SELECT c.name, c.symbol, p.timestamp, p.price 
        FROM prices p JOIN coins c ON p.coin_id = c.id""", conn)
    conn.close()

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["symbol", "timestamp"])
    df["return"] = df.groupby("symbol")["price"].pct_change()   #Daily returns
    df["rolling_mean_7d"] = df.groupby("symbol")["price"].transform(
        lambda x: x.rolling(7).mean())   #over the course of 7 days
    df["rolling_mean_30d"] = df.groupby("symbol")["price"].transform(
        lambda x: x.rolling(30).mean())  #over the course of 30 days
    df["momentum"] = (df["rolling_mean_7d"] - df["rolling_mean_30d"]) / df["rolling_mean_30d"]

    '''Stats for this DataFrame'''

    volatility = df.groupby("symbol")["return"].std()
    avg_return = df.groupby("symbol")["return"].mean()

    returns_tbl = df.pivot(index = "timestamp", columns = "symbol", values = "return")
    corr_coffs = returns_tbl.corr()

    '''Standardization using z-scores'''
    avg_return = avg_return.sort_index()
    volatility = volatility.sort_index()
    df_recent = df.groupby("symbol").tail(1).set_index("symbol").sort_index()
    df_recent['z_score_return'] = zscore(avg_return.values)
    df_recent['z_score_volatility'] = zscore(volatility.values)
    df_recent['z_score_momentum'] = zscore(df_recent['momentum'].values)
    df_recent['rec_score'] = (df_recent['z_score_return'] 
                                - df_recent['z_score_volatility'] 
                                + df_recent['z_score_momentum'] * 0.5)
    
    '''Ranking of coins'''
    df_recent = df_recent.sort_values('rec_score', ascending = False)

    df_recent = df_recent.reset_index()

    return df, df_recent, volatility, avg_return, corr_coffs



