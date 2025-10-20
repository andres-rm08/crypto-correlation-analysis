import requests
import pandas as pd
import sqlite3
import time

conn = sqlite3.connect("../crypto_data.db")
cursor = conn.cursor()

cursor.executescript(
    """CREATE TABLE IF NOT EXISTS coins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    symbol TEXT
    );

    CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coin_id INTEGER,
    timestamp TEXT,
    price REAL,
    FOREIGN KEY (coin_id) REFERENCES coins (id)
    );
    """)

coins = [
    {"id": "bitcoin", "symbol": "BTC"},
    {"id": "ethereum", "symbol": "ETH"},
    {"id": "solana", "symbol": "SOL"},
    {"id": "cardano", "symbol": "ADA"},
    {"id": "binancecoin", "symbol": "BNB"},
    {"id": "ripple", "symbol": "XRP"}
    ]

for c in coins:
    cursor.execute(
        "INSERT OR IGNORE INTO coins (name, symbol) VALUES (?, ?)", 
        (c["id"], c["symbol"]))

conn.commit()

for c in coins:
    coin_id = cursor.execute("SELECT id FROM coins WHERE name = ?", (c["id"],)).fetchone()[0]
    url = f"https://api.coingecko.com/api/v3/coins/{c['id']}/market_chart"
    params = {"vs_currency": "usd","days": "365","interval": "daily"}
    response = requests.get(url, params = params)
    if response.status_code == 200:
        data = response.json()
        prices = data["prices"]
        price_pairs = []
        for p in prices:
            read_time = pd.to_datetime(p[0], unit = "ms").isoformat()
            price_pairs.append((coin_id, read_time, p[1]))
        cursor.executemany("INSERT INTO prices (coin_id, timestamp, price) VALUES (?, ?, ?)", price_pairs)
        conn.commit()
        print(f"Successfully retrieved data for {c['symbol']}")
        time.sleep(2)
    else:
        print(f"Failed to retrieve data for {c['symbol']}")


conn.close()



