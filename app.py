import io
import os
from datetime import datetime

import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="AsyncSignals",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top, rgba(37,99,235,0.10), transparent 28%),
        linear-gradient(180deg, #0b1020 0%, #0f172a 100%);
}

[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stToolbar"] {
    right: 1rem;
}

.block-container {
    padding-top: 1.5rem;
}

.login-shell {
    margin-top: 14vh;
}

.login-box {
    padding: 1.6rem 1.45rem 1.1rem 1.45rem;
    border-radius: 22px;
    background: rgba(15, 23, 42, 0.94);
    border: 1px solid rgba(148, 163, 184, 0.16);
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.34);
    text-align: left;
}

.login-kicker {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.78rem;
    color: #93c5fd;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}

.login-title {
    font-size: 1.9rem;
    font-weight: 720;
    color: #f8fafc;
    margin-bottom: 0.55rem;
    line-height: 1.1;
}

.login-subtitle {
    color: #cbd5e1;
    font-size: 0.98rem;
    line-height: 1.58;
    margin-bottom: 1rem;
}

.login-points {
    margin: 0 0 1rem 0;
    padding: 0;
    list-style: none;
}

.login-points li {
    color: #94a3b8;
    font-size: 0.88rem;
    line-height: 1.5;
    margin-bottom: 0.4rem;
}

.login-domain {
    color: #e2e8f0;
    font-size: 0.83rem;
    margin-bottom: 1rem;
    padding: 0.7rem 0.85rem;
    border-radius: 12px;
    background: rgba(30, 41, 59, 0.9);
    border: 1px solid rgba(148, 163, 184, 0.12);
}

div.stButton > button {
    width: 100%;
    border-radius: 12px;
    padding: 0.82rem 1rem;
    font-size: 0.98rem;
    font-weight: 650;
    background: #2563eb;
    color: white;
    border: 1px solid #2563eb;
    box-shadow: 0 8px 22px rgba(37, 99, 235, 0.22);
}

div.stButton > button:hover {
    background: #1d4ed8;
    color: white;
    border: 1px solid #1d4ed8;
}

.login-note {
    color: #94a3b8;
    font-size: 0.8rem;
    line-height: 1.45;
    margin-top: 0.9rem;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

if not st.user.is_logged_in:
    left, center, right = st.columns([1.2, 0.8, 1.2])

    with center:
        st.markdown('<div class="login-shell">', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="login-box">
                <div class="login-kicker">◆ AsyncSignals Secure Access</div>
                <div class="login-title">Continue to hosted sign in</div>
                <div class="login-subtitle">
                    Access the AsyncSignals research dashboard through the secure hosted authentication page.
                </div>
                <ul class="login-points">
                    <li>Hosted authentication flow.</li>
                    <li>Secure redirect and return to dashboard.</li>
                    <li>No credentials are entered on this page.</li>
                </ul>
                <div class="login-domain">login.asyncsignals.tech</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button("Continue securely", on_click=st.login, use_container_width=True)
        st.markdown(
            '<div class="login-note">You will be redirected to the official AsyncSignals login page and returned here after sign in.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

st.sidebar.success(f"Logged in as {st.user.name}")
st.sidebar.button("Log out", on_click=st.logout)

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {visibility: hidden;}
[data-testid="stToolbar"] {display: none !important;}
button[kind="header"] {display: none !important;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
:root {
    --bg: #07111a;
    --bg-2: #091522;
    --panel: rgba(10, 18, 28, 0.88);
    --panel-2: rgba(14, 24, 36, 0.92);
    --text: #ecf3f8;
    --muted: #97a9bc;
    --line: rgba(255,255,255,0.08);
    --line-strong: rgba(255,255,255,0.14);
    --green: #14f195;
    --teal: #4de2d1;
    --purple: #9945ff;
    --purple-soft: rgba(153,69,255,0.20);
    --green-soft: rgba(20,241,149,0.14);
    --red: #ff6b7a;
    --amber: #ffb84d;
}

/* Hide Streamlit chrome */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {visibility: hidden;}
[data-testid="stToolbar"] {display: none !important;}
button[kind="header"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
[data-testid="stSidebar"] {display: none !important;}

/* Main app background */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 0% 0%, rgba(153,69,255,0.18), transparent 26%),
        radial-gradient(circle at 100% 0%, rgba(20,241,149,0.12), transparent 24%),
        radial-gradient(circle at 50% 100%, rgba(77,226,209,0.08), transparent 20%),
        linear-gradient(180deg, #06111a 0%, #08131d 50%, #09131c 100%);
    color: var(--text);
}

html, body, [class*="css"] {
    color: var(--text);
}

.block-container {
    max-width: 1410px;
    padding-top: 0.9rem;
    padding-bottom: 2rem;
}

section.main > div {
    padding-top: 0.2rem;
}

a {
    color: #8ff5e7 !important;
    text-decoration: none !important;
}
a:hover {
    color: #b5fff2 !important;
}

/* Hero */
.hero-wrap {
    position: relative;
    overflow: hidden;
    padding: 1.45rem 1.45rem 1.2rem 1.45rem;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 26px;
    background:
        linear-gradient(135deg, rgba(17,28,43,0.96), rgba(7,16,24,0.95)),
        radial-gradient(circle at top right, rgba(20,241,149,0.10), transparent 25%);
    box-shadow:
        0 0 0 1px rgba(255,255,255,0.02) inset,
        0 30px 80px rgba(0,0,0,0.22),
        0 0 50px rgba(153,69,255,0.06);
    margin-bottom: 1.1rem;
}
.hero-wrap::before {
    content: "";
    position: absolute;
    inset: 0;
    background:
        linear-gradient(120deg, transparent 0%, rgba(255,255,255,0.025) 20%, transparent 40%);
    pointer-events: none;
}
.brand-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 18px;
    flex-wrap: wrap;
}
.brand-mark {
    display: inline-flex;
    align-items: center;
    gap: 12px;
    font-weight: 750;
    letter-spacing: 0.2px;
    font-size: 1.15rem;
}
.brand-icon {
    width: 38px;
    height: 38px;
    border-radius: 13px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background:
        linear-gradient(135deg, rgba(153,69,255,0.96), rgba(20,241,149,0.90));
    box-shadow:
        0 8px 30px rgba(153,69,255,0.22),
        0 0 22px rgba(20,241,149,0.12);
    color: #051018;
    font-weight: 900;
    font-size: 1rem;
}
.brand-sub {
    color: var(--muted);
    font-size: 0.97rem;
    margin-top: 0.42rem;
    max-width: 760px;
    line-height: 1.45;
}
.badge-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}
.status-badge {
    padding: 0.45rem 0.82rem;
    border: 1px solid rgba(255,255,255,0.09);
    background: rgba(255,255,255,0.035);
    backdrop-filter: blur(8px);
    border-radius: 999px;
    font-size: 0.84rem;
    color: var(--text);
    box-shadow: 0 0 0 1px rgba(255,255,255,0.01) inset;
}
.status-live {
    border-color: rgba(20,241,149,0.24);
    color: #b9f8d9;
    box-shadow: 0 0 18px rgba(20,241,149,0.08);
}
.status-sol {
    border-color: rgba(153,69,255,0.28);
    color: #dcc9ff;
    box-shadow: 0 0 18px rgba(153,69,255,0.08);
}
.status-b2b {
    border-color: rgba(77,226,209,0.22);
    color: #c6fff7;
    box-shadow: 0 0 18px rgba(77,226,209,0.07);
}

/* Panels */
.panel {
    border: 1px solid rgba(255,255,255,0.08);
    background:
        linear-gradient(180deg, rgba(13,23,34,0.90), rgba(9,18,28,0.94));
    border-radius: 24px;
    padding: 1rem 1rem 0.95rem 1rem;
    margin-bottom: 1rem;
    box-shadow:
        0 18px 50px rgba(0,0,0,0.18),
        0 0 0 1px rgba(255,255,255,0.015) inset;
}

/* KPI cards */
.kpi-card {
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.08);
    background:
        linear-gradient(180deg, rgba(255,255,255,0.028), rgba(255,255,255,0.012));
    border-radius: 22px;
    padding: 1rem 1rem 0.95rem 1rem;
    min-height: 132px;
    box-shadow:
        0 12px 34px rgba(0,0,0,0.16),
        0 0 0 1px rgba(255,255,255,0.01) inset;
}
.kpi-card::after {
    content: "";
    position: absolute;
    top: -20px;
    right: -20px;
    width: 100px;
    height: 100px;
    background: radial-gradient(circle, rgba(153,69,255,0.11), transparent 62%);
    pointer-events: none;
}
.kpi-label {
    color: var(--muted);
    font-size: 0.86rem;
    margin-bottom: 0.28rem;
}
.kpi-value {
    font-size: 1.78rem;
    font-weight: 760;
    margin-bottom: 0.25rem;
    letter-spacing: -0.02em;
}
.kpi-delta {
    font-size: 0.89rem;
    color: #bbcad8;
}

/* Text helpers */
.section-title {
    font-size: 1.04rem;
    font-weight: 700;
    margin-bottom: 0.72rem;
    letter-spacing: 0.01em;
}
.helper {
    color: var(--muted);
    font-size: 0.93rem;
    margin-bottom: 0.85rem;
    line-height: 1.5;
}
.small-note {
    color: var(--muted);
    font-size: 0.83rem;
}
.mono {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

/* Divider */
hr {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.08);
    margin: 0.9rem 0 1rem 0;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    padding-bottom: 0.2rem;
    border-bottom: none !important;
    background: transparent !important;
    box-shadow: none !important;
}

.stTabs [data-baseweb="tab"] {
    height: 44px;
    border-radius: 999px;
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.08);
    padding: 0 16px;
    color: #dce7f3;
    transition: all 0.18s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    border-color: rgba(153,69,255,0.22);
    background: rgba(255,255,255,0.05);
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(153,69,255,0.20), rgba(20,241,149,0.10)) !important;
    border-color: rgba(255,255,255,0.13) !important;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.02) inset, 0 0 24px rgba(153,69,255,0.08);
}

div[data-baseweb="tab-border"] {
    display: none !important;
}

div[data-baseweb="tab-highlight"] {
    display: none !important;
    background: transparent !important;
    height: 0 !important;
}

.stTabs > div > div > div {
    border-bottom: none !important;
    box-shadow: none !important;
}

/* Inputs */
div[data-baseweb="select"] > div,
div[data-baseweb="base-input"] > div,
.stTextInput > div > div,
.stSelectbox > div > div {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 16px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: var(--text) !important;
}

.stButton > button,
.stDownloadButton > button,
button[kind="secondaryFormSubmit"],
button[kind="primaryFormSubmit"] {
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    background:
        linear-gradient(135deg, rgba(153,69,255,0.18), rgba(20,241,149,0.10)) !important;
    color: #f3f8fd !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.14);
}
.stButton > button:hover,
.stDownloadButton > button:hover,
button[kind="secondaryFormSubmit"]:hover,
button[kind="primaryFormSubmit"]:hover {
    border-color: rgba(20,241,149,0.22) !important;
    box-shadow: 0 10px 30px rgba(20,241,149,0.08);
}

/* Data tables */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 14px 34px rgba(0,0,0,0.14);
}

.dataframe th, .dataframe td {
    white-space: nowrap;
}

/* Info/success/error */
div[data-baseweb="notification"] {
    border-radius: 16px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
}
</style>
""", unsafe_allow_html=True)

def get_connection():
    return oracledb.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dsn="asyncsignalsdatabase_high",
        config_dir="/home/ubuntu/wallet",
        wallet_location="/home/ubuntu/wallet",
        wallet_password=os.getenv("DB_PASSWORD"),
    )


@st.cache_data(ttl=60, show_spinner=False)
def run_query(query: str) -> pd.DataFrame:
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [col[0].lower() for col in cursor.description]
        rows = cursor.fetchall()
        processed = []
        for row in rows:
            processed.append([val.read() if hasattr(val, "read") else val for val in row])
        return pd.DataFrame(processed, columns=columns)
    except Exception as e:
        st.error(f"DB ERROR: {e}")
        return pd.DataFrame()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@st.cache_data(ttl=60, show_spinner=False)
def load_prices():
    return run_query("""
        SELECT symbol, current_price, market_cap, price_change_percentage_24h
        FROM prices
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_news():
    return run_query("""
        SELECT title, source_id, pubdate, description, link
        FROM news
        ORDER BY pubdate DESC
        FETCH FIRST 10 ROWS ONLY
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_whales():
    return run_query("""
        SELECT time, asset, amount, raw_qty, from_address, to_address
        FROM whales
        ORDER BY time DESC
        FETCH FIRST 150 ROWS ONLY
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_paprika():
    return run_query("""
        SELECT symbol, name, price
        FROM paprika
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_signals():
    return run_query("""
        SELECT type, msg, timestamp, entry_price, exit_price, status
        FROM signals
        ORDER BY timestamp DESC
        FETCH FIRST 120 ROWS ONLY
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_ai_summaries():
    return run_query("""
        SELECT asset, summary, timestamp
        FROM (
            SELECT
                asset,
                summary,
                timestamp,
                ROW_NUMBER() OVER (
                    PARTITION BY asset
                    ORDER BY timestamp DESC
                ) AS rn
            FROM ai_summaries
        )
        WHERE rn = 1
        ORDER BY timestamp DESC
    """)


def subscribe_chat_id(chat_id: str):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM subscribers WHERE chat_id = :1", [chat_id])
        exists = cursor.fetchone()[0]
        if exists == 0:
            cursor.execute("INSERT INTO subscribers (chat_id) VALUES (:1)", [chat_id])
            conn.commit()
            return True, "Alert channel registered."
        return True, "Alert channel already registered."
    except Exception as e:
        return False, f"DB Error: {e}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def ensure_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            out[col] = None
    return out


def to_num(series, default=0.0):
    return pd.to_numeric(series, errors="coerce").fillna(default)


def fmt_usd(value):
    try:
        value = float(value)
        if abs(value) >= 1_000_000_000:
            return f"${value/1_000_000_000:.2f}B"
        if abs(value) >= 1_000_000:
            return f"${value/1_000_000:.2f}M"
        if abs(value) >= 1_000:
            return f"${value/1_000:.2f}K"
        return f"${value:,.2f}"
    except Exception:
        return "$0.00"


def fmt_num(value):
    try:
        value = float(value)
        if abs(value) >= 1_000_000:
            return f"{value/1_000_000:.2f}M"
        if abs(value) >= 1_000:
            return f"{value/1_000:.2f}K"
        return f"{value:,.0f}"
    except Exception:
        return "0"


def short_addr(value):
    value = str(value or "")
    if len(value) <= 14:
        return value
    return f"{value[:6]}...{value[-6:]}"


def status_badge(label, cls=""):
    st.markdown(f'<span class="status-badge {cls}">{label}</span>', unsafe_allow_html=True)


def mini_line(df: pd.DataFrame, x_col: str, y_col: str, color: str = "#14f195", title: str = ""):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x_col],
        y=df[y_col],
        mode="lines+markers",
        line=dict(color=color, width=3),
        fill="tozeroy",
        fillcolor="rgba(20,241,149,0.08)",
        marker=dict(size=6),
        hovertemplate="%{x}<br>%{y}<extra></extra>"
    ))
    fig.update_layout(
        title=title,
        margin=dict(l=10, r=10, t=32, b=10),
        height=220,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e9f1f7"),
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title="", gridcolor="rgba(255,255,255,0.06)")
    )
    return fig


def build_export_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


prices = ensure_cols(load_prices(), ["symbol", "current_price", "market_cap", "price_change_percentage_24h"])
news = ensure_cols(load_news(), ["title", "source_id", "pubdate", "description", "link"])
whales = ensure_cols(load_whales(), ["time", "asset", "amount", "raw_qty", "from_address", "to_address"])
paprika = ensure_cols(load_paprika(), ["symbol", "name", "price"])
signals = ensure_cols(load_signals(), ["type", "msg", "timestamp", "entry_price", "exit_price", "status"])
ai_summaries = ensure_cols(load_ai_summaries(), ["asset", "summary", "timestamp"])

prices["current_price"] = to_num(prices["current_price"])
prices["market_cap"] = to_num(prices["market_cap"])
prices["price_change_percentage_24h"] = to_num(prices["price_change_percentage_24h"])

whales["amount"] = to_num(whales["amount"])
whales["raw_qty"] = to_num(whales["raw_qty"])
whales["asset"] = whales["asset"].astype(str).str.upper()

signals["entry_price"] = to_num(signals["entry_price"])
signals["exit_price"] = to_num(signals["exit_price"])

price_map = {str(r["symbol"]).upper(): float(r["current_price"]) for _, r in prices.iterrows() if str(r["symbol"]).strip()}
btc_row = prices[prices["symbol"].astype(str).str.lower() == "btc"]
sol_row = prices[prices["symbol"].astype(str).str.lower() == "sol"]
eth_row = prices[prices["symbol"].astype(str).str.lower() == "eth"]

btc_price = float(btc_row["current_price"].iloc[0]) if not btc_row.empty else 0.0
btc_change = float(btc_row["price_change_percentage_24h"].iloc[0]) if not btc_row.empty else 0.0
sol_price = float(sol_row["current_price"].iloc[0]) if not sol_row.empty else 0.0
sol_change = float(sol_row["price_change_percentage_24h"].iloc[0]) if not sol_row.empty else 0.0
eth_price = float(eth_row["current_price"].iloc[0]) if not eth_row.empty else 0.0

sol_whales = whales[whales["asset"] == "SOL"].copy()
evm_whales = whales[whales["asset"] != "SOL"].copy()

total_whale_usd = whales["raw_qty"].sum() if not whales.empty else 0
sol_whale_usd = sol_whales["raw_qty"].sum() if not sol_whales.empty else 0
evm_whale_usd = evm_whales["raw_qty"].sum() if not evm_whales.empty else 0

latest_signal = signals.iloc[0] if not signals.empty else None
latest_signal_type = str(latest_signal["type"]) if latest_signal is not None else "No active signal"
latest_signal_status = str(latest_signal["status"]) if latest_signal is not None else "Standby"

summary_btc = ai_summaries[ai_summaries["asset"].astype(str).str.upper() == "BTC"].head(1)
summary_sol = ai_summaries[ai_summaries["asset"].astype(str).str.upper() == "SOL"].head(1)

st.markdown("""
<div class="hero-wrap">
    <div class="brand-row">
        <div>
            <div class="brand-mark">
                <span class="brand-icon">◆</span>
                <span>AsyncSignals Mission Control</span>
            </div>
            <div class="brand-sub">
                Solana-first telemetry infrastructure for research teams, trading desks, ecosystem operators, and on-chain intelligence workflows.
            </div>
        </div>
        <div class="badge-row">
            <span class="status-badge status-live">Live Oracle Feed</span>
            <span class="status-badge status-sol">SOL-Native Grant Mode</span>
            <span class="status-badge status-b2b">B2B Telemetry Console</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">SOL spot</div>
        <div class="kpi-value">{fmt_usd(sol_price)}</div>
        <div class="kpi-delta">24h change: {sol_change:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">SOL flow tracked</div>
        <div class="kpi-value">{fmt_usd(sol_whale_usd)}</div>
        <div class="kpi-delta">{len(sol_whales)} recent SOL whale rows</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Cross-chain flow</div>
        <div class="kpi-value">{fmt_usd(total_whale_usd)}</div>
        <div class="kpi-delta">{len(whales)} combined whale rows</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Latest signal</div>
        <div class="kpi-value" style="font-size:1.1rem;">{latest_signal_type}</div>
        <div class="kpi-delta">{latest_signal_status}</div>
    </div>
    """, unsafe_allow_html=True)

tab_home, tab_whales, tab_signals, tab_ai, tab_news, tab_market, tab_alerts = st.tabs([
    "Mission Control",
    "Whale Tracker",
    "Signal Ledger",
    "AI Context",
    "News Context",
    "Market Surface",
    "Alerts Access",
])

with tab_home:
    st.markdown('<div class="section-title">SOL spotlight</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="helper">This control surface highlights real SOL flow, cross-chain whale telemetry, and operator-ready signal visibility for grant reviewers and research users.</div>',
        unsafe_allow_html=True
    )

    left, right = st.columns([1.3, 1])
    with left:
        if not sol_whales.empty:
            sol_chart = sol_whales.copy().head(20).iloc[::-1]
            sol_chart["seq"] = range(1, len(sol_chart) + 1)
            fig = mini_line(sol_chart, "seq", "raw_qty", color="#9945ff", title="SOL whale USD flow")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No SOL whale rows available yet in the latest cache window.")
    with right:
        st.markdown(f"""
        <div class="panel" style="margin-bottom:0;">
            <div class="section-title">Operator brief</div>
            <div class="helper">
                AsyncSignals is a Solana-first telemetry layer built on Oracle-backed persistence. The interface is the observability surface; the product value is reusable cross-chain data, stored signal history, and operational alerting.
            </div>
            <div class="small-note">Current BTC spot: {fmt_usd(btc_price)} | ETH spot: {fmt_usd(eth_price)} | EVM whale flow: {fmt_usd(evm_whale_usd)}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-title">SOL summary</div>', unsafe_allow_html=True)
        if not summary_sol.empty:
            st.markdown(f"""
            <div class="panel">
                <div class="small-note">Updated: {summary_sol.iloc[0]['timestamp']}</div>
                <div>{summary_sol.iloc[0]['summary']}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No SOL AI summary available yet.")

    with c2:
        st.markdown('<div class="section-title">BTC macro check</div>', unsafe_allow_html=True)
        if not summary_btc.empty:
            st.markdown(f"""
            <div class="panel">
                <div class="small-note">Updated: {summary_btc.iloc[0]['timestamp']}</div>
                <div>{summary_btc.iloc[0]['summary']}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No BTC AI summary available yet.")

with tab_whales:
    st.markdown('<div class="section-title">Whale tracker</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="helper">Raw token amount is stored in <span class="mono">amount</span>. USD-converted transfer value is stored in <span class="mono">raw_qty</span>.</div>',
        unsafe_allow_html=True
    )

    sub_sol, sub_cross = st.tabs(["SOL Spotlight", "Cross-Chain View"])

    with sub_sol:
        sol_display = sol_whales.copy()
        if not sol_display.empty:
            sol_display = sol_display.rename(columns={
                "time": "time",
                "asset": "asset",
                "amount": "amount",
                "raw_qty": "usd_value",
                "from_address": "from_address",
                "to_address": "to_address"
            })
            sol_export = sol_display.copy()
            sol_display["amount"] = sol_display["amount"].map(lambda x: round(float(x), 6))
            sol_display["usd_value"] = sol_display["usd_value"].map(fmt_usd)
            sol_display["from_address"] = sol_display["from_address"].map(short_addr)
            sol_display["to_address"] = sol_display["to_address"].map(short_addr)

            st.download_button(
                "Export SOL whale rows",
                data=build_export_bytes(sol_export),
                file_name="asyncsignals_sol_whales.csv",
                mime="text/csv"
            )
            st.dataframe(sol_display, width="stretch", hide_index=True)
        else:
            st.info("No SOL whale rows in the latest fetch window.")

    with sub_cross:
        asset_options = ["ALL"] + sorted([a for a in whales["asset"].dropna().astype(str).unique().tolist() if a])
        selected_asset = st.selectbox("Asset lens", asset_options, index=0)
        cross = whales.copy()
        if selected_asset != "ALL":
            cross = cross[cross["asset"] == selected_asset]

        if not cross.empty:
            cross_export = cross.copy()
            cross = cross.rename(columns={"raw_qty": "usd_value"})
            cross["amount"] = cross["amount"].map(lambda x: round(float(x), 6))
            cross["usd_value"] = cross["usd_value"].map(fmt_usd)
            cross["from_address"] = cross["from_address"].map(short_addr)
            cross["to_address"] = cross["to_address"].map(short_addr)

            st.download_button(
                "Export cross-chain whales",
                data=build_export_bytes(cross_export),
                file_name="asyncsignals_cross_chain_whales.csv",
                mime="text/csv"
            )
            st.dataframe(cross, width="stretch", hide_index=True)
        else:
            st.warning("No rows found for the selected asset filter.")

with tab_signals:
    st.markdown('<div class="section-title">Signal ledger</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="helper">Execution-oriented signal history from Oracle, including generated status outcomes and signal classifications.</div>',
        unsafe_allow_html=True
    )

    if not signals.empty:
        signal_export = signals.copy()
        st.download_button(
            "Export signal ledger",
            data=build_export_bytes(signal_export),
            file_name="asyncsignals_signals.csv",
            mime="text/csv"
        )

        signal_view = signals.copy()
        signal_view["entry_price"] = signal_view["entry_price"].map(fmt_usd)
        signal_view["exit_price"] = signal_view["exit_price"].map(fmt_usd)
        st.dataframe(signal_view, width="stretch", hide_index=True)
    else:
        st.info("No signal records available.")

with tab_ai:
    st.markdown('<div class="section-title">AI context</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="helper">Oracle-stored model summaries designed to turn raw tables into operator-readable market context.</div>',
        unsafe_allow_html=True
    )

    if not ai_summaries.empty:
        ai_assets = ["ALL"] + sorted(ai_summaries["asset"].astype(str).str.upper().unique().tolist())
        selected_ai = st.selectbox("Summary lens", ai_assets, index=0)
        ai_view = ai_summaries.copy()
        if selected_ai != "ALL":
            ai_view = ai_view[ai_view["asset"].astype(str).str.upper() == selected_ai]

        for _, row in ai_view.iterrows():
            st.markdown(f"""
            <div class="panel">
                <div class="section-title">{row['asset']}</div>
                <div class="small-note">Updated: {row['timestamp']}</div>
                <div>{row['summary']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No AI summaries available.")

with tab_news:
    st.markdown('<div class="section-title">News context</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="helper">Recent headlines feed the narrative layer behind volatility and whale movement.</div>',
        unsafe_allow_html=True
    )

    if not news.empty:
        for _, row in news.iterrows():
            title = row.get("title", "Untitled")
            source = row.get("source_id", "Unknown source")
            pubdate = row.get("pubdate", "")
            desc = str(row.get("description", "") or "")
            link = row.get("link", "")
            body = desc[:280] + ("..." if len(desc) > 280 else "")

            st.markdown(f"""
            <div class="panel">
                <div class="section-title">{title}</div>
                <div class="small-note">{source} | {pubdate}</div>
                <div style="margin-top:0.45rem;">{body}</div>
                <div style="margin-top:0.55rem;"><a href="{link}" target="_blank">Open source article</a></div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No recent news found.")

with tab_market:
    st.markdown('<div class="section-title">Market surface</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="helper">High-level spot and market-cap reference table, useful for quick price verification and macro checks.</div>',
        unsafe_allow_html=True
    )

    if not prices.empty:
        market = prices.copy()
        market["symbol"] = market["symbol"].astype(str).str.upper()
        market["current_price"] = market["current_price"].map(fmt_usd)
        market["market_cap"] = market["market_cap"].map(fmt_usd)
        market["price_change_percentage_24h"] = market["price_change_percentage_24h"].map(lambda x: f"{float(x):+.2f}%")
        st.download_button(
            "Export market table",
            data=build_export_bytes(prices),
            file_name="asyncsignals_market_surface.csv",
            mime="text/csv"
        )
        st.dataframe(market, width="stretch", hide_index=True)

        topcaps = prices.copy().sort_values("market_cap", ascending=False).head(12)
        if not topcaps.empty:
            topcaps["symbol"] = topcaps["symbol"].astype(str).str.upper()
            fig = px.bar(
                topcaps,
                x="symbol",
                y="market_cap",
                color="price_change_percentage_24h",
                color_continuous_scale=["#ff6b7a", "#1e2b38", "#14f195"],
                title="Market cap surface"
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e9f1f7"),
                margin=dict(l=10, r=10, t=40, b=10),
                height=340
            )
            st.plotly_chart(fig, width="stretch")
    else:
        st.info("No market rows available.")
 
with tab_alerts:
    st.markdown('<div class="section-title">Alerts access</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="helper">Register a Telegram destination for operational signal delivery. This access point is framed for teams and analysts rather than a retail bot workflow.</div>',
        unsafe_allow_html=True
    )

    a1, a2 = st.columns([1.2, 1])
    with a1:
        with st.form("subscribe_form", clear_on_submit=False):
            chat_id = st.text_input("Telegram chat ID", placeholder="e.g. 123456789")
            submitted = st.form_submit_button("Register alert channel", width="stretch")
            if submitted:
                if chat_id.strip():
                    ok, msg = subscribe_chat_id(chat_id.strip())
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.warning("Enter a valid Telegram chat ID.")

    with a2:
        st.markdown("""
        <div class="panel" style="margin-bottom:0;">
            <div class="section-title">Deployment note</div>
            <div class="helper">
                AsyncSignals uses Oracle-backed persistence for signal history and subscriber routing. This surface is intended for teams, analysts, and ecosystem operators rather than retail chart browsing.
            </div>
            <div class="small-note">Recommended demo flow: Mission Control → Whale Tracker → Signal Ledger → AI Context.</div>
        </div>
        """, unsafe_allow_html=True)

st.caption("AsyncSignals | Oracle-backed, Solana-first telemetry console")