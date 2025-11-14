from pathlib import Path
import sqlite3 
import time 
import requests
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]   
DATA_DIR = BASE_DIR / "data" / "processed"
DATA_DIR.mkdir(parents=True, exist_ok=True)
path_db = DATA_DIR / "crypto_data.db"

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

def init_prices(days: int = 365):
    conn = get_conn()
    try:
        cur = conn.cursor()
        fetch_coins = cur.execute('SELECT id, name FROM coins').fetchall()
        if not fetch_coins:
            return
        
        # Track which coins need data
        coins_needing_data = []
        for c_id, c_name in fetch_coins:
            has_any = cur.execute(
                'SELECT 1 FROM prices WHERE coin_id=? LIMIT 1', (c_id,)
            ).fetchone()
            if not has_any:
                coins_needing_data.append((c_id, c_name))
        
        # Retry logic for failed coins
        max_retries = 3
        failed_coins = []
        
        for attempt in range(max_retries):
            if attempt > 0:
                # Wait longer between retry attempts
                time.sleep(5)
            
            for c_id, c_name in coins_needing_data:
                # Check if we already got data for this coin
                has_any = cur.execute(
                    'SELECT 1 FROM prices WHERE coin_id=? LIMIT 1', (c_id,)
                ).fetchone()
                if has_any:
                    continue
                
                try:
                    prices = price_verify(c_name, days=days)
                    cur.executemany(
                        'INSERT OR IGNORE INTO prices (coin_id, timestamp, price) VALUES (?,?,?)',
                        ((c_id, pd.to_datetime(ts, unit="ms").isoformat(), price) for ts, price in prices),
                    )
                    conn.commit()
                    print(f"Successfully fetched data for {c_name}")
                    time.sleep(2.0)  # Increased sleep time to respect rate limits
                except requests.RequestException as e:
                    print(f"Attempt {attempt + 1} failed for {c_name}: {e}")
                    failed_coins.append((c_id, c_name))
                    time.sleep(2.0)  # Still wait even on failure
            
            # Update list for next retry
            coins_needing_data = failed_coins
            failed_coins = []
            
            if not coins_needing_data:
                break
        
        if coins_needing_data:
            print(f"Warning: Could not fetch data for {len(coins_needing_data)} coins after {max_retries} attempts")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def update_missing(days_back_probe: int = 4, sleep_seconds: float = 1.5) -> None:
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

            # FIX: If coin has no data, fetch full 365 days instead of just 1 day
            if last_local is None:
                miss_days = 365  # Fetch full year for coins with no data
            else:
                miss_days = max(
                    (datetime.fromisoformat(last_remote_iso) - datetime.fromisoformat(last_local)).days, 1
                )

            try:
                newer = price_verify(coin_name, days=min(miss_days + 1, 365))  # Cap at 365 days
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
                print(f"Updated {len(to_add)} data points for {coin_name}")

            time.sleep(sleep_seconds)
    finally:
        conn.close()

        

