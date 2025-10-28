import requests
import pandas as pd
import sqlite3
import time

conn = sqlite3.connect("../data/processed/crypto_data.db")
cursor = conn.cursor()

cursor.executescript(
    """CREATE TABLE IF NOT EXISTS coins 
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    symbol TEXT
    );
    CREATE TABLE IF NOT EXISTS prices 
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
    coin_id INTEGER,
    timestamp TEXT,
    price REAL,
    FOREIGN KEY (coin_id) REFERENCES coins (id)
    );
    """)

coins = [{"id": "bitcoin", "symbol": "BTC"},
    {"id": "ethereum", "symbol": "ETH"},
    {"id": "solana", "symbol": "SOL"},
    {"id": "cardano", "symbol": "ADA"},
    {"id": "binancecoin", "symbol": "BNB"},
    {"id": "ripple", "symbol": "XRP"},
    {"id": "polkadot", "symbol": "DOT"},
    {"id": "dogecoin", "symbol": "DOGE"},
    {"id": "avalanche-2", "symbol": "AVAX"},
    {"id": "chainlink", "symbol": "LINK"},
    {"id": "polygon", "symbol": "MATIC"},
    {"id": "litecoin", "symbol": "LTC"},
    {"id": "uniswap", "symbol": "UNI"},
    {"id": "stellar", "symbol": "XLM"},
    {"id": "cosmos", "symbol": "ATOM"},
    {"id": "algorand", "symbol": "ALGO"},
    {"id": "vechain", "symbol": "VET"},
    {"id": "filecoin", "symbol": "FIL"},
    {"id": "tron", "symbol": "TRX"},
    {"id": "monero", "symbol": "XMR"},
    {"id": "ethereum-classic", "symbol": "ETC"},
    {"id": "bitcoin-cash", "symbol": "BCH"},
    {"id": "hedera-hashgraph", "symbol": "HBAR"},
    {"id": "near", "symbol": "NEAR"},
    {"id": "fantom", "symbol": "FTM"},
    {"id": "the-sandbox", "symbol": "SAND"},
    {"id": "decentraland", "symbol": "MANA"},
    {"id": "axie-infinity", "symbol": "AXS"},
    {"id": "chiliz", "symbol": "CHZ"},
    {"id": "enjincoin", "symbol": "ENJ"}]

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



