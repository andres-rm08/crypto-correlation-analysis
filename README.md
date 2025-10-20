# Project Details
- This project looks at historical price data of Cryptocurrency to showcase return correlations and risk-return tradeoffs over the course of one year
- Uses an end-to-end data pipeline connecting API data to statistical analysis 

# Structure
- Data collection: Connects to CoinGecko API to populate SQL tables (found in crypto_data.db) with timestamp and price data (interval: 1 day, range: 365 days)
- Analysis: Joins & sorts SQL tables from crypto_data.db to calculate metrics such as daily returns & volatility 
- Visualization: Generates a heatmap & scatterplot based on the previously calculated metrics

# Results
- Heatmap showcasing relationships between daily returns of various coins
- Scatterplot showcasing average return vs volatility
- Ranking of coins based on z-scores from three different metrics

# Dashboard
- Interactive interface with the following sections:
    1. Overview: Ranked recommendations
    2. Return vs Risk: Plot of average return vs volatility
    3. Correlation Heatmap: Heatmap of return correlations between coins
    4. Recommendation Table: Breakdown of z-scores

- Auto-updates as the database receives new data from following day
- Hosted on Streamlit
- Built using Python (pandas, seaborn, matplotlib, and Streamlit) and SQLite.
