import requests
import pandas as pd
import sqlite3
import time
from datetime import datetime

conn = sqlite3.connect("../crypto_data.db")
cursor = conn.cursor()

cursor.execute('''SELECT id, name FROM coins''' )

coins_id = cursor.fetchall()

for i in coins_id:
    url = f"https://api.coingecko.com/api/v3/coins/{i[1]}/market_chart"
    params = {"vs_currency": "usd","days": "4","interval": "daily"}
    response = requests.get(url, params = params)
    if response.status_code == 200:
        data = response.json()
        prices = data['prices']
        read_time_2 = pd.to_datetime(prices[-1][0], unit = "ms").isoformat()
        cursor.execute('''SELECT MAX(timestamp) FROM prices WHERE coin_id = ?''', (i[0],))
        final_time = cursor.fetchone()[0]
        if final_time is None or read_time_2 > final_time:
            if final_time is None:
                miss_days = 1
            else:
                miss_days = (
                    datetime.fromisoformat(read_time_2) - datetime.fromisoformat(final_time)
                    ).days
            params = {"vs_currency": "usd","days": str(miss_days + 1),"interval": "daily"}
            response_2 = requests.get(url, params = params)
            if response_2.status_code == 200:
                data_2 = response_2.json()
                prices_2 = data_2['prices']
                for p2 in prices_2:
                    new_time = pd.to_datetime(p2[0], unit = "ms").isoformat()
                    if final_time is None or new_time > final_time:
                        cursor.execute(
                        '''INSERT INTO prices (coin_id, timestamp, price) VALUES (?,?,?)''', 
                        (i[0], new_time, p2[1])
                        )
        time.sleep(2)
conn.commit()






print(coins_id)