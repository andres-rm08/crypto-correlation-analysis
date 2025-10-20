import pandas as pd
import sqlite3

conn = sqlite3.connect("../crypto_data.db")

df = pd.read_sql_query("""
    SELECT c.name, c.symbol, p.timestamp, p.price
    FROM prices p
    JOIN coins c ON p.coin_id = c.id
""", conn)

df['timestamp'] = pd.to_datetime(df['timestamp'])
print(df.head())
print(df.info())
