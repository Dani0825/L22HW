# Student Name: Daniela Huber
# Student ID: U0000022710
 
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
 
# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Crypto Market Dashboard",
    page_icon="📈",
    layout="wide",
)
 
# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark finance-grade theme */
    .stApp { background-color: #0d1117; color: #e6edf3; }
    .block-container { padding-top: 1.5rem; }
    section[data-testid="stSidebar"] { background-color: #161b22; }
    h1, h2, h3 { color: #e6edf3; }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        text-align: center;
    }
    .stDataFrame { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)
 
# ─────────────────────────────────────────────
# API HELPERS  (all wrapped with @st.cache_data)
# ─────────────────────────────────────────────
 
BASE_URL = "https://api.coingecko.com/api/v3"
 
# Headers help avoid being flagged as a bot by CoinGecko's rate limiter
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PA4Dashboard/1.0)",
    "Accept": "application/json",
}
 
 
@st.cache_data(ttl=600)
def fetch_markets(vs_currency: str, per_page: int) -> pd.DataFrame:
    """Fetch top N coins by market cap from CoinGecko /coins/markets."""
    url = f"{BASE_URL}/coins/markets"
    params = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h,7d",
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data)
        # Keep only the columns we care about
        cols = [
            "id", "symbol", "name", "image",
            "current_price", "market_cap", "total_volume",
            "price_change_percentage_24h",
            "price_change_percentage_7d_in_currency",
            "high_24h", "low_24h", "circulating_supply",
        ]
        df = df[[c for c in cols if c in df.columns]]
        df["symbol"] = df["symbol"].str.upper()
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Failed to fetch market data: {e}")
        return pd.DataFrame()
 
 
@st.cache_data(ttl=600)
def fetch_price_history(coin_id: str, vs_currency: str, days: int) -> pd.DataFrame:
    """Fetch historical price data for a single coin."""
    url = f"{BASE_URL}/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": days}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        prices = data.get("prices", [])
        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Failed to fetch price history for {coin_id}: {e}")
        return pd.DataFrame()
 
 
@st.cache_data(ttl=600)
def fetch_global() -> dict:
    """Fetch global crypto market stats."""
    url = f"{BASE_URL}/global"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", {})
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Failed to fetch global data: {e}")
        return {}
 
 
# ─────────────────────────────────────────────
# SIDEBAR – User Inputs
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Dashboard Controls")
    st.markdown("---")
 
    # Widget 1 – Currency selector
    currency = st.selectbox(
        "Display currency",
        options=["usd", "eur", "gbp", "jpy", "btc"],
        index=0,
        format_func=lambda x: x.upper(),
    )
 
    # Widget 2 – Number of top coins
    top_n = st.slider(
        "Number of top coins",
        min_value=5,
        max_value=50,
        value=15,
        step=5,
    )
 
    # Widget 3 – History window for the time series chart
    days_map = {"24 hours": 1, "7 days": 7, "30 days": 30, "90 days": 90}
    days_label = st.radio(
        "Price history window",
        options=list(days_map.keys()),
        index=2,
    )
    days = days_map[days_label]
 
    st.markdown("---")
    st.caption("Data provided by [CoinGecko](https://www.coingecko.com) · refreshes every 5 min")
 
# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
currency_sym = {"usd": "$", "eur": "€", "gbp": "£", "jpy": "¥", "btc": "₿"}.get(currency, currency.upper())
 
df_markets = fetch_markets(currency, top_n)
global_data = fetch_global()
 
# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.title("📈 Crypto Market Dashboard")
st.markdown(f"Live overview of the top **{top_n}** cryptocurrencies · prices in **{currency.upper()}** · updated every 5 min")
st.markdown("---")
 
# ─────────────────────────────────────────────
# COMPONENT 1 – Global KPI Metrics  (st.metric)
# ─────────────────────────────────────────────
st.subheader("🌐 Global Market Snapshot")
 
if global_data:
    total_mcap = global_data.get("total_market_cap", {}).get(currency, 0)
    total_vol = global_data.get("total_volume", {}).get(currency, 0)
    btc_dom = global_data.get("market_cap_percentage", {}).get("btc", 0)
    active_coins = global_data.get("active_cryptocurrencies", 0)
    mcap_change = global_data.get("market_cap_change_percentage_24h_usd", 0)
 
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Total Market Cap",
        f"{currency_sym}{total_mcap / 1e12:.2f}T",
        delta=f"{mcap_change:+.2f}% (24h)",
    )
    col2.metric(
        "24h Volume",
        f"{currency_sym}{total_vol / 1e9:.1f}B",
    )
    col3.metric(
        "BTC Dominance",
        f"{btc_dom:.1f}%",
    )
    col4.metric(
        "Active Coins",
        f"{active_coins:,}",
    )
 
st.markdown("---")
 
# ─────────────────────────────────────────────
# COMPONENT 2 – Time Series Chart  (Plotly)
# ─────────────────────────────────────────────
st.subheader(f"📉 Price History – {days_label}")
 
if not df_markets.empty:
    # Let the user pick which coin to chart
    coin_options = df_markets["id"].tolist()
    coin_names   = df_markets.set_index("id")["name"].to_dict()
    selected_coin = st.selectbox(
        "Select coin for price history",
        options=coin_options,
        format_func=lambda x: coin_names.get(x, x).title(),
    )
 
    df_history = fetch_price_history(selected_coin, currency, days)
 
    if not df_history.empty:
        fig_ts = go.Figure()
        fig_ts.add_trace(go.Scatter(
            x=df_history.index,
            y=df_history["price"],
            mode="lines",
            line=dict(color="#58a6ff", width=2),
            fill="tozeroy",
            fillcolor="rgba(88,166,255,0.07)",
            name=coin_names.get(selected_coin, selected_coin),
        ))
        fig_ts.update_layout(
            paper_bgcolor="#0d1117",
            plot_bgcolor="#0d1117",
            font=dict(color="#e6edf3"),
            xaxis=dict(gridcolor="#21262d", title="Date"),
            yaxis=dict(gridcolor="#21262d", title=f"Price ({currency.upper()})"),
            margin=dict(l=10, r=10, t=30, b=10),
            height=380,
        )
        st.plotly_chart(fig_ts, use_container_width=True)
    else:
        st.warning("No price history data available for the selected coin.")
 
st.markdown("---")
 
# ─────────────────────────────────────────────
# COMPONENT 3 – Bar Chart: Top Coins by Market Cap
# ─────────────────────────────────────────────
st.subheader(f"🏆 Top {top_n} Coins by Market Cap")
 
if not df_markets.empty:
    df_bar = df_markets.copy()
    df_bar["market_cap_B"] = df_bar["market_cap"] / 1e9
    df_bar["color"] = df_bar["price_change_percentage_24h"].apply(
        lambda x: "#3fb950" if (x or 0) >= 0 else "#f85149"
    )
 
    fig_bar = go.Figure(go.Bar(
        x=df_bar["symbol"],
        y=df_bar["market_cap_B"],
        marker_color=df_bar["color"],
        text=df_bar["market_cap_B"].apply(lambda v: f"{currency_sym}{v:.1f}B"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Market Cap: " + currency_sym + "%{y:.2f}B<extra></extra>",
    ))
    fig_bar.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font=dict(color="#e6edf3"),
        xaxis=dict(gridcolor="#21262d"),
        yaxis=dict(gridcolor="#21262d", title=f"Market Cap ({currency.upper()}, Billions)"),
        margin=dict(l=10, r=10, t=20, b=10),
        height=400,
    )
    st.plotly_chart(fig_bar, use_container_width=True)
 
st.markdown("---")
 
# ─────────────────────────────────────────────
# COMPONENT 4 – Data Table with styled 24h change
# ─────────────────────────────────────────────
st.subheader("📋 Market Data Table")
 
if not df_markets.empty:
    df_display = df_markets[[
        "symbol", "name", "current_price",
        "market_cap", "total_volume",
        "price_change_percentage_24h",
        "price_change_percentage_7d_in_currency",
        "high_24h", "low_24h",
    ]].copy()
 
    df_display.columns = [
        "Symbol", "Name", f"Price ({currency_sym})",
        "Market Cap", "24h Volume",
        "24h Change %", "7d Change %",
        f"24h High ({currency_sym})", f"24h Low ({currency_sym})",
    ]
 
    # Format numeric columns for readability
    df_display["Market Cap"]   = df_display["Market Cap"].apply(lambda v: f"{currency_sym}{v/1e9:.2f}B")
    df_display["24h Volume"]   = df_display["24h Volume"].apply(lambda v: f"{currency_sym}{v/1e9:.2f}B")
 
    def color_change(val):
        if pd.isna(val):
            return ""
        color = "#3fb950" if val >= 0 else "#f85149"
        return f"color: {color}"
 
    styled = df_display.style.applymap(color_change, subset=["24h Change %", "7d Change %"]) \
                              .format({
                                  f"Price ({currency_sym})": lambda v: f"{currency_sym}{v:,.4f}",
                                  "24h Change %": "{:+.2f}%",
                                  "7d Change %": "{:+.2f}%",
                                  f"24h High ({currency_sym})": lambda v: f"{currency_sym}{v:,.4f}",
                                  f"24h Low ({currency_sym})": lambda v: f"{currency_sym}{v:,.4f}",
                              })
 
    st.dataframe(styled, use_container_width=True, hide_index=True)
 
# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.caption(f"Last rendered: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC · Data © CoinGecko")