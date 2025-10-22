from pathlib import Path
import sqlite3 
import time 
import requests
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]   
DATA_DIR = BASE_DIR / "data" / "processed"
DATA_DIR.mkdir(parents=True, exist_ok=True)
path_db = DATA_DIR / "crypto_data.db"

coins = [{"id": "bitcoin",     "symbol": "BTC"}, {"id": "ethereum",    "symbol": "ETH"},
    {"id": "solana",      "symbol": "SOL"}, {"id": "cardano",     "symbol": "ADA"},
    {"id": "binancecoin", "symbol": "BNB"}, {"id": "ripple",      "symbol": "XRP"},]

def get_conn():     #Helper function to optimize SQL queries
    conn = sqlite3.connect(path_db, check_same_thread=False, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=3000;")
    return conn

def verify():   #Verifies that coins and prices tables exist; creates an index for prices for faster search; populates coins
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.executescript('''CREATE TABLE IF NOT EXISTS coins 
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
        CREATE UNIQUE INDEX IF NOT EXISTS data_index ON prices (coin_id, timestamp
        ); 
        ''')
        for c in coins:
            cursor.execute('''INSERT OR IGNORE INTO coins (name, symbol) 
            VALUES (?,?) ''', (c["id"], c["symbol"]))
        conn.commit()
    finally:
        conn.close()

def price_verify(coin_id_str: str, days: int, interval: str = 'daily'):      #Helper ensures no error occurs when making API call for prices
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id_str}/market_chart"
    params = {"vs_currency": "usd", "days": str(days), "interval": interval}
    response = requests.get(url, params = params, timeout = 30)
    response.raise_for_status()
    return response.json()['prices']

def init_prices(days: int = 365):     #Makes sure prices table is populated (checks first)
    conn = get_conn()
    try:
        cursor = conn.cursor()
        if cursor.execute('''SELECT 1 FROM prices LIMIT 1 ''').fetchone():
            return
        fetch_coins = cursor.execute('''SELECT id, name FROM coins''').fetchall()
        if not fetch_coins:
            return
        for c_id, c_name in fetch_coins:
            try:
                prices = price_verify(c_name, days=days)
            except requests.RequestException as e:
                continue
            cursor.executemany('''INSERT OR IGNORE INTO prices (coin_id, timestamp, price) VALUES (?,?,?)''', 
                ((c_id, pd.to_datetime(timestamp, unit = "ms").isoformat(), price) for timestamp, price in prices))
            time.sleep(1.2)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def update_missing(days_back_probe: int = 4, sleep_seconds: float = 0.8) -> None:
    from datetime import datetime
    conn = get_conn()
    try:
        cur = conn.cursor()
        coins = cur.execute("SELECT id, name FROM coins").fetchall()
        if not coins:
            raise RuntimeError("No coins found. Run verify() first.")

        for coin_id, coin_name in coins:
            try:
                recent = price_verify(coin_name, days=days_back_probe)
            except requests.RequestException as e:
                print(f"Warning: probe failed for {coin_name}: {e}")
                continue
            if not recent:
                continue

            last_remote_iso = pd.to_datetime(recent[-1][0], unit="ms").isoformat()
            last_local = cur.execute(
                "SELECT MAX(timestamp) FROM prices WHERE coin_id = ?",
                (coin_id,),
            ).fetchone()[0]

            miss_days = 1 if last_local is None else max(
                (datetime.fromisoformat(last_remote_iso) - datetime.fromisoformat(last_local)).days, 1
            )

            try:
                newer = price_verify(coin_name, days=miss_days + 1)
            except requests.RequestException as e:
                print(f"Warning: incremental fetch failed for {coin_name}: {e}")
                continue

            to_add = []
            for ts, price in newer:
                iso_t = pd.to_datetime(ts, unit="ms").isoformat()
                if (last_local is None) or (iso_t > last_local):
                    to_add.append((coin_id, iso_t, price))

            if to_add:
                cur.executemany(
                    "INSERT OR IGNORE INTO prices (coin_id, timestamp, price) VALUES (?, ?, ?)",
                    to_add,
                )
                conn.commit()

            time.sleep(sleep_seconds)
    finally:
        conn.close()

        

