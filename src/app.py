import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from analysis_sql import metrics
from util_db import verify, init_prices, update_missing

st.set_page_config(page_title="Crypto Analytics Dashboard", layout="wide", page_icon="📊",)

@st.cache_resource
def bootstrap():
    verify()
    init_prices(days=365)

bootstrap()

@st.cache_data(ttl=60*60)  
def load_metrics():
    return metrics()

df, df_recent, volatility, avg_return, corr_coffs = load_metrics()

st.sidebar.title("⚙️ Dashboard Controls")

if st.sidebar.button("🔄 Update data"):
    with st.spinner("Updating from CoinGecko…"):
        update_missing()
        load_metrics.clear() 
        df, df_recent, volatility, avg_return, corr_coffs = load_metrics()
        st.success("Data updated.")

view_choice = st.sidebar.radio("Select View:",["Overview", "Return vs Risk", 
    "Correlation Heatmap", "Recommendation Table"],)

st.sidebar.markdown(
    f"Last updated: **{pd.to_datetime(df['timestamp']).max().strftime('%Y-%m-%d')}**")
st.sidebar.write(f"Data points: {len(df):,}")
st.sidebar.write(f"Coins analyzed: {df['symbol'].nunique()}")


st.title("📈 Crypto Analytics and Recommendation Dashboard")
st.markdown("""This dashboard analyzes cryptocurrency performance over the past year 
    using **CoinGecko** data. Metrics include daily returns, volatility, momentum, 
    and a composite recommendation score.""")


if view_choice == "Overview":
    st.header("Top Cryptocurrency Recommendations")

    st.markdown("""**Recommendation Score = z(Return) − z(Volatility) + 0.5 × z(Momentum)**  
        Higher scores indicate stronger recent performance adjusted for risk.""")

    st.dataframe(df_recent[["symbol", "price", "z_score_return", 
    "z_score_volatility", "z_score_momentum", "rec_score"]].rename(columns={
            "symbol": "Symbol","price": "Latest Price (USD)","z_score_return": "Z-Return",
            "z_score_volatility": "Z-Volatility","z_score_momentum": "Z-Momentum",
            "rec_score": "Recommendation Score"})
        .style.background_gradient(subset=["Recommendation Score"], cmap="Greens")
        .format({"Latest Price (USD)": "${:,.2f}"}))


elif view_choice == "Return vs Risk":
    st.header("Return vs Risk (Volatility)")

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.scatterplot(x=volatility, y=avg_return, s=200)

    for symbol in volatility.index:
        ax.text(volatility[symbol], avg_return[symbol], symbol, fontsize=12)

    ax.set_title("Average Daily Return vs Volatility")
    ax.set_xlabel("Volatility (Risk)")
    ax.set_ylabel("Average Daily Return")

    st.pyplot(fig)


elif view_choice == "Correlation Heatmap":
    st.header("Return Correlation Heatmap")
    
    col1, col2 = st.columns(2)
    with col1:
        show_annotations = st.checkbox("Show correlation values", value=False, help="Toggle to show/hide individual correlation values")
    with col2:
        font_scale = st.slider("Label font size", min_value=0.5, max_value=1.5, value=0.8, step=0.1)
    

    st.subheader("Filter Options")
    selected_coins = st.multiselect(
        "Select cryptocurrencies to display (leave empty for all)",
        options=corr_coffs.columns.tolist(),
        default=[],
        help="Select specific coins to focus on, or leave empty to see all correlations"
    )
    

    if selected_coins:
        filtered_corr = corr_coffs.loc[selected_coins, selected_coins]
    else:
        filtered_corr = corr_coffs
    
    num_coins = len(filtered_corr)
    fig_size = max(10, num_coins * 0.5)  
    

    fig, ax = plt.subplots(figsize=(fig_size, fig_size))
    
    annot = show_annotations and num_coins <= 15
    
    sns.heatmap(
        filtered_corr, 
        annot=annot,
        fmt='.2f' if annot else '',
        cmap="coolwarm", 
        center=0, 
        ax=ax,
        square=True,
        linewidths=0.5,
        cbar_kws={"shrink": 0.8},
        xticklabels=True,
        yticklabels=True
    )
    
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right', fontsize=8*font_scale)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=8*font_scale)
    ax.set_title(f"Correlation Matrix of Daily Returns ({num_coins} cryptocurrencies)", fontsize=12, pad=20)
    
    plt.tight_layout()
    st.pyplot(fig)

    st.subheader("Correlation Summary")
    col1, col2, col3 = st.columns(3)
    with col1:

        mask = np.triu(np.ones_like(filtered_corr, dtype=bool), k=1)
        upper_triangle = filtered_corr.where(mask)
        st.metric("Average Correlation", f"{upper_triangle.mean().mean():.3f}")
    with col2:
        st.metric("Max Correlation", f"{upper_triangle.max().max():.3f}")
    with col3:
        st.metric("Min Correlation", f"{upper_triangle.min().min():.3f}")


elif view_choice == "Recommendation Table":
    st.header("Detailed Recommendation Scores")
    st.write("Sorted by the computed recommendation score:")

    st.dataframe(df_recent[["symbol", "z_score_return", "z_score_volatility",
     "z_score_momentum", "rec_score"]].rename(columns={"symbol": "Symbol",
            "z_score_return": "Z-Return","z_score_volatility": "Z-Volatility",
            "z_score_momentum": "Z-Momentum","rec_score": "Recommendation Score"})
        .sort_values("Recommendation Score", ascending=False)
        .style.background_gradient(subset=["Recommendation Score"], cmap="Blues"))


st.markdown("---")
st.markdown(
    "📊 *Built using Python, Streamlit, SQLite, and CoinGecko API*")
