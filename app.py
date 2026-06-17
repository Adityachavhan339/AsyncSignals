import io
import json
import os
from datetime import datetime

import requests
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

# ── CSS ───────────────────────────────────────────────────────────────────────
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
.status-base {
    border-color: rgba(0,82,255,0.28);
    color: #a3b8ff;
    box-shadow: 0 0 18px rgba(0,82,255,0.08);
}

/* Base severity */
.base-severity-high {
    border-color: rgba(255,107,122,0.35);
    color: #ff6b7a;
    background: rgba(255,107,122,0.08);
}
.base-severity-medium {
    border-color: rgba(255,184,77,0.35);
    color: #ffb84d;
    background: rgba(255,184,77,0.08);
}
.base-severity-low {
    border-color: rgba(20,241,149,0.25);
    color: #14f195;
    background: rgba(20,241,149,0.06);
}

/* Polkadot severity */
.polkadot-severity-high {
    border-color: rgba(255,107,122,0.35);
    color: #ff6b7a;
    background: rgba(255,107,122,0.08);
}
.polkadot-severity-medium {
    border-color: rgba(255,184,77,0.35);
    color: #ffb84d;
    background: rgba(255,184,77,0.08);
}
.polkadot-severity-low {
    border-color: rgba(20,241,149,0.25);
    color: #14f195;
    background: rgba(20,241,149,0.06);
}

/* Route status */
.route-confirmed {
    border-color: rgba(20,241,149,0.30);
    color: #b9f8d9;
    background: rgba(20,241,149,0.06);
}
.route-pending {
    border-color: rgba(255,184,77,0.30);
    color: #ffe4b3;
    background: rgba(255,184,77,0.06);
}
.route-partial {
    border-color: rgba(147,197,253,0.30);
    color: #bfdbfe;
    background: rgba(147,197,253,0.06);
}
.route-stale {
    border-color: rgba(255,107,122,0.30);
    color: #ffd1d5;
    background: rgba(255,107,122,0.06);
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

# ── Login gate ────────────────────────────────────────────────────────────────
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

# ── DB ────────────────────────────────────────────────────────────────────────
def get_connection():
    return oracledb.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dsn="asyncsignalsdatabase_low",
        config_dir="/home/daniel/wallet",
        wallet_location="/home/daniel/wallet",
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


# ── Base loaders ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def load_base_rpc():
    return run_query("""
        SELECT captured_at, latest_block_number, latest_block_hash, latest_block_timestamp,
               avg_block_time_seconds, tps_1min, gas_used_total, base_fee_gwei
        FROM BASE_RPC_SNAPSHOT
        ORDER BY captured_at DESC
        FETCH FIRST 1 ROWS ONLY
    """)

@st.cache_data(ttl=60, show_spinner=False)
def load_base_activity():
    return run_query("""
        SELECT activity_date, chain_name, tx_count, tps, total_fees_eth,
               total_fees_usd, activity_score, alert_level
        FROM BASE_CHAIN_ACTIVITY_DAILY
        ORDER BY activity_date DESC
        FETCH FIRST 1 ROWS ONLY
    """)

@st.cache_data(ttl=60, show_spinner=False)
def load_base_ecosystem():
    return run_query("""
        SELECT snapshot_date, eth_price_usd, tvl_proxy, stablecoin_proxy
        FROM BASE_ECOSYSTEM_DAILY
        ORDER BY snapshot_date DESC
        FETCH FIRST 1 ROWS ONLY
    """)

@st.cache_data(ttl=60, show_spinner=False)
def load_base_whales():
    return run_query("""
        SELECT timestamp, asset_symbol, value_usd, from_address, to_address,
               tx_hash, block_number, transfer_type
        FROM BASE_TRANSFER_SIGNALS
        ORDER BY timestamp DESC
        FETCH FIRST 50 ROWS ONLY
    """)

@st.cache_data(ttl=60, show_spinner=False)
def load_base_derived():
    return run_query("""
        SELECT signal_date, signal_family, signal_key, severity, score, title,
               description, metric_value_1, metric_value_2, metric_value_3, reference_id
        FROM BASE_DERIVED_SIGNALS
        ORDER BY signal_date DESC, score DESC
        FETCH FIRST 40 ROWS ONLY
    """)


# ── Polkadot loaders ──────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def load_polkadot_rpc():
    return run_query("""
        SELECT captured_at, latest_block_number_int, latest_block_hash, finalized_head, extrinsics_in_latest_block
        FROM POLKADOT_RPC_SNAPSHOT
        ORDER BY captured_at DESC
        FETCH FIRST 1 ROWS ONLY
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_polkadot_activity():
    return run_query("""
        SELECT activity_date, relay_chain, chain_name, tx_count, tps, total_fees_native, total_fees_usd, activity_score, alert_level
        FROM POLKADOT_CHAIN_ACTIVITY_DAILY
        WHERE activity_date = (SELECT MAX(activity_date) FROM POLKADOT_CHAIN_ACTIVITY_DAILY)
        ORDER BY activity_score DESC
        FETCH FIRST 20 ROWS ONLY
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_polkadot_staking():
    return run_query("""
        SELECT staking_date, relay_chain, chain_name, minimum_nominator_active_stake,
               number_of_addresses_staking, number_of_nominators, number_of_pool_members,
               number_of_pools, number_of_validators, staked_dot, staked_dot_in_pools, unbonding_dot
        FROM POLKADOT_STAKING_DAILY
        ORDER BY staking_date DESC
        FETCH FIRST 20 ROWS ONLY
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_polkadot_treasury():
    return run_query("""
        SELECT month_date, relay_chain, chain_name, asset_symbol, balance_token, balance_usd, treasury_share_pct
        FROM POLKADOT_TREASURY_MONTHLY
        ORDER BY month_date DESC
        FETCH FIRST 20 ROWS ONLY
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_polkadot_validators():
    return run_query("""
        SELECT month_date, relay_chain, chain_name, number_of_nominators,
               number_of_active_validators, number_of_waiting_validators, waiting_ratio_pct
        FROM POLKADOT_VALIDATOR_MONTHLY
        ORDER BY month_date DESC
        FETCH FIRST 10 ROWS ONLY
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_polkadot_opengov():
    return run_query("""
        SELECT start_date, end_date, relay_chain, chain_name, referendum_index, origin_name,
               track_id, outcome_status, ayes, nays, support_value, turnout_total, approval_margin, urgency_score, signal_label
        FROM POLKADOT_OPENGOV_SIGNALS
        ORDER BY start_date DESC, urgency_score DESC
        FETCH FIRST 20 ROWS ONLY
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_polkadot_xcm_summary():
    return run_query("""
        SELECT relay_chain, window_hours, total_messages, completed_messages, failed_messages,
               matched_messages, success_rate, avg_latency_seconds, median_latency_seconds, p95_latency_seconds, unmatched_messages
        FROM POLKADOT_XCM_SUMMARY
        ORDER BY window_hours DESC
        FETCH FIRST 5 ROWS ONLY
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_polkadot_xcm_transfers():
    return run_query("""
        SELECT origin_timestamp, relay_chain, origin_chain, dest_chain, origin_para_id, dest_para_id,
               xcm_type, xcm_version, message_hash, origin_account, dest_account, asset_symbol, value_usd,
               origin_block_number, outcome_status, match_status, latency_seconds, route_status, signal_score
        FROM POLKADOT_XCM_TRANSFER_SIGNALS
        ORDER BY origin_timestamp DESC, signal_score DESC
        FETCH FIRST 50 ROWS ONLY
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_polkadot_extrinsics():
    return run_query("""
        SELECT event_time, chain_name, block_number, extrinsic_hash, domain_name, pallet_name,
               method_name, signer_address, success_flag, summary_text
        FROM POLKADOT_EXTRINSIC_SUPPLEMENTARY_FEED
        ORDER BY event_time DESC
        FETCH FIRST 50 ROWS ONLY
    """)


@st.cache_data(ttl=60, show_spinner=False)
def load_polkadot_derived():
    return run_query("""
        SELECT signal_date, signal_family, signal_key, relay_chain, chain_name, severity, score,
               title, description, metric_value_1, metric_value_2, metric_value_3, reference_id
        FROM POLKADOT_DERIVED_SIGNALS
        ORDER BY signal_date DESC, score DESC
        FETCH FIRST 40 ROWS ONLY
    """)


# ── Helpers ───────────────────────────────────────────────────────────────────
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


def route_badge(status: str):
    s = str(status).lower().replace("_", "-")
    cls = "route-unknown"
    if "confirmed" in s:
        cls = "route-confirmed"
    elif "pending" in s:
        cls = "route-pending"
    elif "partial" in s:
        cls = "route-partial"
    elif "stale" in s:
        cls = "route-stale"
    return f'<span class="status-badge {cls}">{status}</span>'


def severity_badge(sev: str):
    s = str(sev).lower()
    cls = "polkadot-severity-low"
    if s == "high":
        cls = "polkadot-severity-high"
    elif s == "medium":
        cls = "polkadot-severity-medium"
    return f'<span class="status-badge {cls}">{s.upper()}</span>'


# ── Load core data ────────────────────────────────────────────────────────────
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

btc_price = float(btc_row["current_price"].iloc[0]) if not btc_row.empty and "current_price" in btc_row.columns else 0.0
btc_change = float(btc_row["price_change_percentage_24h"].iloc[0]) if not btc_row.empty and "price_change_percentage_24h" in btc_row.columns else 0.0
sol_price = float(sol_row["current_price"].iloc[0]) if not sol_row.empty and "current_price" in sol_row.columns else 0.0
sol_change = float(sol_row["price_change_percentage_24h"].iloc[0]) if not sol_row.empty and "price_change_percentage_24h" in sol_row.columns else 0.0
eth_price = float(eth_row["current_price"].iloc[0]) if not eth_row.empty and "current_price" in eth_row.columns else 0.0
eth_change = float(eth_row["price_change_percentage_24h"].iloc[0]) if not eth_row.empty and "price_change_percentage_24h" in eth_row.columns else 0.0

# DOT from prices or paprika
dot_row = prices[prices["symbol"].astype(str).str.lower() == "dot"]
dot_price = 0.0
dot_change = 0.0
if not dot_row.empty and "current_price" in dot_row.columns:
    dot_price = float(dot_row["current_price"].iloc[0])
if not dot_row.empty and "price_change_percentage_24h" in dot_row.columns:
    dot_change = float(dot_row["price_change_percentage_24h"].iloc[0])
else:
    dot_pap = paprika[paprika["symbol"].astype(str).str.lower() == "dot"]
    if not dot_pap.empty:
        dot_price = float(dot_pap["price"].iloc[0])

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

# ── Load Polkadot data ──────────────────────────────────────────────────────
polkadot_rpc = ensure_cols(load_polkadot_rpc(), ["captured_at","latest_block_number_int","latest_block_hash","finalized_head","extrinsics_in_latest_block"])
polkadot_activity = ensure_cols(load_polkadot_activity(), ["activity_date","relay_chain","chain_name","tx_count","tps","total_fees_native","total_fees_usd","activity_score","alert_level"])
polkadot_staking = ensure_cols(load_polkadot_staking(), ["staking_date","relay_chain","chain_name","minimum_nominator_active_stake","number_of_addresses_staking","number_of_nominators","number_of_pool_members","number_of_pools","number_of_validators","staked_dot","staked_dot_in_pools","unbonding_dot"])
polkadot_treasury = ensure_cols(load_polkadot_treasury(), ["month_date","relay_chain","chain_name","asset_symbol","balance_token","balance_usd","treasury_share_pct"])
polkadot_validators = ensure_cols(load_polkadot_validators(), ["month_date","relay_chain","chain_name","number_of_nominators","number_of_active_validators","number_of_waiting_validators","waiting_ratio_pct"])
polkadot_opengov = ensure_cols(load_polkadot_opengov(), ["start_date","end_date","relay_chain","chain_name","referendum_index","origin_name","track_id","outcome_status","ayes","nays","support_value","turnout_total","approval_margin","urgency_score","signal_label"])
polkadot_xcm_summary = ensure_cols(load_polkadot_xcm_summary(), ["relay_chain","window_hours","total_messages","completed_messages","failed_messages","matched_messages","success_rate","avg_latency_seconds","median_latency_seconds","p95_latency_seconds","unmatched_messages"])
polkadot_xcm = ensure_cols(load_polkadot_xcm_transfers(), ["origin_timestamp","relay_chain","origin_chain","dest_chain","origin_para_id","dest_para_id","xcm_type","xcm_version","message_hash","origin_account","dest_account","asset_symbol","value_usd","origin_block_number","outcome_status","match_status","latency_seconds","route_status","signal_score"])
polkadot_extrinsics = ensure_cols(load_polkadot_extrinsics(), ["event_time","chain_name","block_number","extrinsic_hash","domain_name","pallet_name","method_name","signer_address","success_flag","summary_text"])
polkadot_derived = ensure_cols(load_polkadot_derived(), ["signal_date","signal_family","signal_key","relay_chain","chain_name","severity","score","title","description","metric_value_1","metric_value_2","metric_value_3","reference_id"])

# numeric polkadot
polkadot_activity["tx_count"] = to_num(polkadot_activity["tx_count"])
polkadot_activity["tps"] = to_num(polkadot_activity["tps"])
polkadot_activity["total_fees_usd"] = to_num(polkadot_activity["total_fees_usd"])
polkadot_activity["activity_score"] = to_num(polkadot_activity["activity_score"])

polkadot_staking["staked_dot"] = to_num(polkadot_staking["staked_dot"])
polkadot_staking["staked_dot_in_pools"] = to_num(polkadot_staking["staked_dot_in_pools"])
polkadot_staking["unbonding_dot"] = to_num(polkadot_staking["unbonding_dot"])
polkadot_staking["minimum_nominator_active_stake"] = to_num(polkadot_staking["minimum_nominator_active_stake"])
polkadot_staking["number_of_validators"] = to_num(polkadot_staking["number_of_validators"])

polkadot_treasury["balance_usd"] = to_num(polkadot_treasury["balance_usd"])
polkadot_treasury["treasury_share_pct"] = to_num(polkadot_treasury["treasury_share_pct"])

polkadot_validators["number_of_active_validators"] = to_num(polkadot_validators["number_of_active_validators"])
polkadot_validators["number_of_waiting_validators"] = to_num(polkadot_validators["number_of_waiting_validators"])
polkadot_validators["waiting_ratio_pct"] = to_num(polkadot_validators["waiting_ratio_pct"])

polkadot_opengov["urgency_score"] = to_num(polkadot_opengov["urgency_score"])
polkadot_opengov["turnout_total"] = to_num(polkadot_opengov["turnout_total"])
polkadot_opengov["approval_margin"] = to_num(polkadot_opengov["approval_margin"])

polkadot_xcm_summary["total_messages"] = to_num(polkadot_xcm_summary["total_messages"])
polkadot_xcm_summary["success_rate"] = to_num(polkadot_xcm_summary["success_rate"])
polkadot_xcm_summary["avg_latency_seconds"] = to_num(polkadot_xcm_summary["avg_latency_seconds"])
polkadot_xcm_summary["unmatched_messages"] = to_num(polkadot_xcm_summary["unmatched_messages"])

polkadot_xcm["value_usd"] = to_num(polkadot_xcm["value_usd"])
polkadot_xcm["latency_seconds"] = to_num(polkadot_xcm["latency_seconds"])
polkadot_xcm["signal_score"] = to_num(polkadot_xcm["signal_score"])

polkadot_derived["score"] = to_num(polkadot_derived["score"])

polkadot_xcm_usd = polkadot_xcm["value_usd"].sum() if not polkadot_xcm.empty else 0
total_whale_usd += polkadot_xcm_usd

# ── Load Base data ────────────────────────────────────────────────────────────
base_rpc = ensure_cols(load_base_rpc(), ["captured_at","latest_block_number","latest_block_hash","latest_block_timestamp","avg_block_time_seconds","tps_1min","gas_used_total","base_fee_gwei"])
base_activity = ensure_cols(load_base_activity(), ["activity_date","chain_name","tx_count","tps","total_fees_eth","total_fees_usd","activity_score","alert_level"])
base_ecosystem = ensure_cols(load_base_ecosystem(), ["snapshot_date","eth_price_usd","tvl_proxy","stablecoin_proxy"])
base_whales = ensure_cols(load_base_whales(), ["timestamp","asset_symbol","value_usd","from_address","to_address","tx_hash","block_number","transfer_type"])
base_derived = ensure_cols(load_base_derived(), ["signal_date","signal_family","signal_key","severity","score","title","description","metric_value_1","metric_value_2","metric_value_3","reference_id"])

# numeric base
base_rpc["latest_block_number"] = to_num(base_rpc["latest_block_number"])
base_rpc["tps_1min"] = to_num(base_rpc["tps_1min"])
base_rpc["gas_used_total"] = to_num(base_rpc["gas_used_total"])
base_rpc["base_fee_gwei"] = to_num(base_rpc["base_fee_gwei"])

base_activity["tx_count"] = to_num(base_activity["tx_count"])
base_activity["tps"] = to_num(base_activity["tps"])
base_activity["total_fees_usd"] = to_num(base_activity["total_fees_usd"])
base_activity["activity_score"] = to_num(base_activity["activity_score"])

base_whales["value_usd"] = to_num(base_whales["value_usd"])
base_whales["block_number"] = to_num(base_whales["block_number"])

base_derived["score"] = to_num(base_derived["score"])
base_ecosystem["eth_price_usd"] = to_num(base_ecosystem["eth_price_usd"])
base_whale_usd = base_whales["value_usd"].sum() if not base_whales.empty else 0

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrap">
    <div class="brand-row">
        <div>
            <div class="brand-mark">
                <span class="brand-icon">◆</span>
                <span>AsyncSignals Mission Control</span>
            </div>
            <div class="brand-sub">
                Multi-chain telemetry infrastructure for research teams, trading desks, and ecosystem operators.
                Live feeds from Solana, EVM, Base L2, and Polkadot parachain ecosystems.
            </div>
        </div>
        <div class="badge-row">
            <span class="status-badge status-live">Live Oracle Feed</span>
            <span class="status-badge status-sol">Multi-Chain</span>
            <span class="status-badge status-b2b">B2B Telemetry Console</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">BTC spot</div>
        <div class="kpi-value">{fmt_usd(btc_price)}</div>
        <div class="kpi-delta">24h change: {btc_change:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">ETH spot</div>
        <div class="kpi-value">{fmt_usd(eth_price)}</div>
        <div class="kpi-delta">24h change: {eth_change:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">SOL spot</div>
        <div class="kpi-value">{fmt_usd(sol_price)}</div>
        <div class="kpi-delta">24h change: {sol_change:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    if dot_price > 0:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">DOT spot</div>
            <div class="kpi-value">{fmt_usd(dot_price)}</div>
            <div class="kpi-delta">24h change: {dot_change:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Cross-chain flow</div>
            <div class="kpi-value">{fmt_usd(total_whale_usd)}</div>
            <div class="kpi-delta">Polkadot XCM included</div>
        </div>
        """, unsafe_allow_html=True)
with col5:
    base_eth_price = float(base_ecosystem["eth_price_usd"].iloc[0]) if not base_ecosystem.empty and base_ecosystem["eth_price_usd"].iloc[0] > 0 else 0
    if base_eth_price > 0:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Base L2</div>
            <div class="kpi-value">{fmt_usd(base_eth_price)}</div>
            <div class="kpi-delta">ETH on Base | {fmt_usd(base_whale_usd)} flow</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Base L2</div>
            <div class="kpi-value">Live</div>
            <div class="kpi-delta">Oracle telemetry active</div>
        </div>
        """, unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_home, tab_whales, tab_signals, tab_ai, tab_news, tab_market, tab_polkadot, tab_base, tab_alerts = st.tabs([
    "Mission Control",
    "Whale Tracker",
    "Signal Ledger",
    "AI Context",
    "News Context",
    "Market Surface",
    "Polkadot",
    "Base L2",
    "Alerts Access"
])

# ── Mission Control ───────────────────────────────────────────────────────────
with tab_home:
    st.markdown('<div class="section-title">Multi-chain overview</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="helper">Real-time telemetry across BTC, ETH, SOL, DOT, and Base L2. Live Oracle-backed ingestion with visual signal layers.</div>',
        unsafe_allow_html=True
    )

    # ── Latest Signal Inline ─────────────────────────────────────────────────
    if latest_signal is not None and latest_signal_type != "No active signal":
        sig_color = "#ff6b7a" if "DANGER" in latest_signal_type else "#14f195" if "OPPORTUNITY" in latest_signal_type else "#ffb84d"
        sig_icon = "🚨" if "DANGER" in latest_signal_type else "🚀" if "OPPORTUNITY" in latest_signal_type else "🐋"
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:0.8rem; padding:0.5rem 0.8rem; 
                    background:rgba(255,255,255,0.03); border-radius:12px; border:1px solid rgba(255,255,255,0.06);">
            <span style="font-size:1.2rem;">{sig_icon}</span>
            <div style="flex:1;">
                <div style="font-weight:700; font-size:0.9rem; color:{sig_color};">{latest_signal_type}</div>
                <div style="font-size:0.8rem; color:#94a3b8; line-height:1.3;">{latest_signal.get("msg", "")[:80]}...</div>
            </div>
            <span class="status-badge" style="font-size:0.75rem; padding:0.2rem 0.5rem;">{latest_signal_status}</span>
        </div>
        """, unsafe_allow_html=True)

    # ── Top Row: Market + Whale Flow ──────────────────────────────────────────
    left, right = st.columns([1.3, 1])
    with left:
        st.markdown('<div class="section-title">Market snapshot</div>', unsafe_allow_html=True)
        snap_rows = []
        for sym, price, change in [
            ("BTC", btc_price, btc_change),
            ("ETH", eth_price, eth_change),
            ("SOL", sol_price, sol_change),
            ("DOT", dot_price, dot_change),
        ]:
            snap_rows.append({
                "Asset": sym,
                "Price": fmt_usd(price) if price > 0 else "n/a",
                "24h Change": f"{change:+.2f}%" if price > 0 else "-"
            })
        snap_df = pd.DataFrame(snap_rows)
        st.dataframe(snap_df, hide_index=True, width="stretch")

    with right:
        st.markdown('<div class="section-title">Cross-chain whale flow</div>', unsafe_allow_html=True)
        if not whales.empty:
            # Map assets to chains for color grouping
            chain_map = {
                "BTC": "Bitcoin", "ETH": "Ethereum", "WETH": "Ethereum",
                "SOL": "Solana", "USDC": "Stable", "USDT": "Stable",
                "BASE": "Base L2", "WBTC": "Bitcoin"
            }
            whale_lines = whales.copy()
            whale_lines["chain"] = whale_lines["asset"].map(lambda x: chain_map.get(str(x).upper(), "Other"))
            # Group by time bucket (10-min windows) and chain
            whale_lines["time"] = pd.to_datetime(whale_lines["time"], errors="coerce")
            whale_lines = whale_lines.dropna(subset=["time"])
            whale_lines["time_bucket"] = whale_lines["time"].dt.floor("5min")
            line_data = whale_lines.groupby(["time_bucket", "chain"])["raw_qty"].sum().reset_index()
            if not line_data.empty:
                fig = px.line(
                    line_data, x="time_bucket", y="raw_qty", color="chain",
                    color_discrete_map={
                        "Bitcoin": "#f7931a", "Ethereum": "#627eea", "Solana": "#9945ff",
                        "Base L2": "#0052ff", "Stable": "#14f195", "Other": "#94a3b8"
                    },
                    labels={"time_bucket": "", "raw_qty": "USD Flow", "chain": "Chain"}
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e9f1f7"), margin=dict(l=10, r=10, t=10, b=10), height=220,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5,
                               font=dict(size=10, color="#94a3b8")),
                    xaxis=dict(showgrid=False, tickformat="%H:%M"),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", tickprefix="$")
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No time-series whale data.")
        else:
            st.info("No whale flow data.")

    # ── Second Row: Signal History + Activity ───────────────────────────────────
    st.markdown('<hr>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown('<div class="section-title">Recent signal history</div>', unsafe_allow_html=True)
        if not signals.empty:
            sig_hist = signals.head(20).copy()
            sig_hist["timestamp"] = sig_hist["timestamp"].astype(str).str[:16]
            sig_hist["type"] = sig_hist["type"].astype(str).str[:30]
            sig_hist["status"] = sig_hist["status"].astype(str).str[:20]
            st.dataframe(sig_hist[["timestamp", "type", "status"]], hide_index=True, width="stretch", height=280)
        else:
            st.info("No signals yet.")

    with c2:
        st.markdown('<div class="section-title">Chain activity pulse</div>', unsafe_allow_html=True)
        activity_rows = []
        if not polkadot_activity.empty:
            top = polkadot_activity.iloc[0]
            activity_rows.append({"Chain": "Polkadot", "TX": fmt_num(top.get("tx_count", 0)), "TPS": f"{float(top.get('tps', 0)):.2f}", "Score": f"{float(top.get('activity_score', 0)):.1f}"})
        if not base_activity.empty:
            top = base_activity.iloc[0]
            activity_rows.append({"Chain": "Base L2", "TX": fmt_num(top.get("tx_count", 0)), "TPS": f"{float(top.get('tps', 0)):.2f}", "Score": f"{float(top.get('activity_score', 0)):.1f}"})
        if activity_rows:
            st.dataframe(pd.DataFrame(activity_rows), hide_index=True, width="stretch")
        else:
            st.info("No chain activity data.")

    # ── Bottom: Operator Brief ─────────────────────────────────────────────────
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="panel">
        <div class="section-title">Operator brief</div>
        <div class="helper">
            AsyncSignals ingests on-chain data from Solana, EVM, Base L2, and Polkadot ecosystems into Oracle-backed persistence.
            Use the Whale Tracker for flow inspection, the Polkadot tab for parachain telemetry, the Base L2 tab for L2 signals, and the Signal Ledger for execution history.
            Deep narrative summaries are available in the <strong>AI Context</strong> tab.
        </div>
        <div class="small-note">Cross-chain flow: {fmt_usd(total_whale_usd)} | EVM: {fmt_usd(evm_whale_usd)} | SOL: {fmt_usd(sol_whale_usd)} | XCM: {fmt_usd(polkadot_xcm_usd)} | Base: {fmt_usd(base_whale_usd)} | Signals: {len(signals)}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Whale Tracker ─────────────────────────────────────────────────────────────
with tab_whales:
    st.markdown('<div class="section-title">Whale tracker</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="helper">Raw token amount is stored in <span class="mono">amount</span>. USD-converted transfer value is stored in <span class="mono">raw_qty</span>. Polkadot XCM flows are shown in their own lens.</div>',
        unsafe_allow_html=True
    )

    sub_sol, sub_cross, sub_polkadot_xcm = st.tabs(["SOL Spotlight", "Cross-Chain View", "Polkadot XCM"])

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

    with sub_polkadot_xcm:
        if not polkadot_xcm.empty:
            xcm_display = polkadot_xcm.copy()
            xcm_export = xcm_display.copy()
            xcm_display["value_usd"] = xcm_display["value_usd"].map(fmt_usd)
            xcm_display["latency_seconds"] = xcm_display["latency_seconds"].map(lambda x: f"{float(x):.1f}s" if x else "-")
            xcm_display["origin_account"] = xcm_display["origin_account"].map(short_addr)
            xcm_display["dest_account"] = xcm_display["dest_account"].map(short_addr)
            xcm_display["origin_para_id"] = xcm_display["origin_para_id"].astype(str)
            xcm_display["dest_para_id"] = xcm_display["dest_para_id"].astype(str)

            st.download_button(
                "Export Polkadot XCM transfers",
                data=build_export_bytes(xcm_export),
                file_name="asyncsignals_polkadot_xcm.csv",
                mime="text/csv"
            )
            st.dataframe(xcm_display, width="stretch", hide_index=True)
        else:
            st.info("No Polkadot XCM transfers available.")

# ── Signal Ledger ─────────────────────────────────────────────────────────────
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

# ── AI Context ────────────────────────────────────────────────────────────────
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

# ── News Context ──────────────────────────────────────────────────────────────
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

# ── Market Surface ────────────────────────────────────────────────────────────
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

# ── Polkadot ──────────────────────────────────────────────────────────────────
with tab_polkadot:
    st.markdown('<div class="section-title">Polkadot telemetry</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="helper">Parachain activity, staking economics, treasury allocation, governance urgency, XCM routes, and derived signals.</div>',
        unsafe_allow_html=True
    )

    if polkadot_rpc.empty or polkadot_activity.empty:
        st.warning("Polkadot telemetry tables are empty or unavailable.")
    else:
        rpc = polkadot_rpc.iloc[0]
        active_chains = int(polkadot_activity["chain_name"].nunique()) if not polkadot_activity.empty else 0
        xcm_24h = int(polkadot_xcm_summary["total_messages"].sum()) if not polkadot_xcm_summary.empty else 0
        max_urgency = int(polkadot_opengov["urgency_score"].max()) if not polkadot_opengov.empty else 0

        p1, p2, p3, p4 = st.columns(4)
        with p1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Latest Block</div>
                <div class="kpi-value">{fmt_num(rpc.get('latest_block_number_int', 0))}</div>
                <div class="kpi-delta">Extrinsics: {fmt_num(rpc.get('extrinsics_in_latest_block', 0))}</div>
            </div>
            """, unsafe_allow_html=True)
        with p2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Active Parachains</div>
                <div class="kpi-value">{active_chains}</div>
                <div class="kpi-delta">From latest activity window</div>
            </div>
            """, unsafe_allow_html=True)
        with p3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">XCM 24h Messages</div>
                <div class="kpi-value">{fmt_num(xcm_24h)}</div>
                <div class="kpi-delta">Cross-chain message volume</div>
            </div>
            """, unsafe_allow_html=True)
        with p4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Max Gov Urgency</div>
                <div class="kpi-value">{max_urgency}</div>
                <div class="kpi-delta">OpenGov referendum pressure</div>
            </div>
            """, unsafe_allow_html=True)

        sub_ov, sub_stake, sub_tgov, sub_xcm, sub_ext, sub_der = st.tabs([
            "Overview", "Staking & Validators", "Treasury & Gov", "XCM Explorer", "Extrinsics", "Derived Signals"
        ])

        # ── Overview ──────────────────────────────────────────────────────────
        with sub_ov:
            st.markdown('<div class="section-title">Chain activity leaders</div>', unsafe_allow_html=True)
            c1, c2 = st.columns([2, 1])
            with c1:
                if not polkadot_activity.empty:
                    act = polkadot_activity.head(15).copy()
                    fig = px.bar(
                        act,
                        x="chain_name",
                        y="tx_count",
                        color="alert_level",
                        color_discrete_map={"high": "#ff6b7a", "medium": "#ffb84d", "low": "#14f195"},
                        title="Daily transactions by chain",
                        labels={"chain_name": "Chain", "tx_count": "TX Count"}
                    )
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e9f1f7"),
                        margin=dict(l=10, r=10, t=40, b=10),
                        height=320,
                        xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                        yaxis=dict(gridcolor="rgba(255,255,255,0.06)")
                    )
                    st.plotly_chart(fig, width="stretch")
                else:
                    st.info("No activity data.")
            with c2:
                st.markdown('<div class="panel">', unsafe_allow_html=True)
                st.markdown('<div class="section-title">Activity scores</div>', unsafe_allow_html=True)
                for _, row in polkadot_activity.head(6).iterrows():
                    st.markdown(f"""
                    <div style="margin-bottom:0.6rem;">
                        <div style="display:flex; justify-content:space-between;">
                            <span>{row['chain_name']}</span>
                            <span>{row['activity_score']:.1f}</span>
                        </div>
                        <div style="height:4px; background:rgba(255,255,255,0.06); border-radius:2px; margin-top:4px;">
                            <div style="width:min(100%, {max(5, row['activity_score'] / 5)}%); height:4px; background:{'#ff6b7a' if row['alert_level']=='high' else '#ffb84d' if row['alert_level']=='medium' else '#14f195'}; border-radius:2px;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="section-title">Chain activity detail</div>', unsafe_allow_html=True)
            act_table = polkadot_activity.copy()
            act_table["tx_count"] = act_table["tx_count"].map(fmt_num)
            act_table["tps"] = act_table["tps"].map(lambda x: f"{float(x):.3f}")
            act_table["total_fees_usd"] = act_table["total_fees_usd"].map(fmt_usd)
            act_table["activity_score"] = act_table["activity_score"].map(lambda x: f"{float(x):.1f}")
            st.dataframe(act_table, width="stretch", hide_index=True)

        # ── Staking ─────────────────────────────────────────────────────────
        with sub_stake:
            s1, s2, s3, s4 = st.columns(4)
            total_staked = polkadot_staking["staked_dot"].sum() if not polkadot_staking.empty else 0
            total_pools = polkadot_staking["staked_dot_in_pools"].sum() if not polkadot_staking.empty else 0
            total_unbonding = polkadot_staking["unbonding_dot"].sum() if not polkadot_staking.empty else 0
            min_stake = polkadot_staking["minimum_nominator_active_stake"].max() if not polkadot_staking.empty else 0

            with s1:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Total Staked DOT</div>
                    <div class="kpi-value">{fmt_num(total_staked)}</div>
                </div>
                """, unsafe_allow_html=True)
            with s2:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">In Pools</div>
                    <div class="kpi-value">{fmt_num(total_pools)}</div>
                </div>
                """, unsafe_allow_html=True)
            with s3:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Unbonding</div>
                    <div class="kpi-value">{fmt_num(total_unbonding)}</div>
                </div>
                """, unsafe_allow_html=True)
            with s4:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Min Active Stake</div>
                    <div class="kpi-value">{fmt_num(min_stake)}</div>
                </div>
                """, unsafe_allow_html=True)

            c1, c2 = st.columns([2, 1])
            with c1:
                if not polkadot_validators.empty:
                    val = polkadot_validators.copy()
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        name="Active",
                        x=val["chain_name"],
                        y=val["number_of_active_validators"],
                        marker_color="#14f195"
                    ))
                    fig.add_trace(go.Bar(
                        name="Waiting",
                        x=val["chain_name"],
                        y=val["number_of_waiting_validators"],
                        marker_color="#ffb84d"
                    ))
                    fig.update_layout(
                        barmode="group",
                        title="Validator set pressure",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e9f1f7"),
                        margin=dict(l=10, r=10, t=40, b=10),
                        height=300,
                        xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                        yaxis=dict(gridcolor="rgba(255,255,255,0.06)")
                    )
                    st.plotly_chart(fig, width="stretch")
                else:
                    st.info("No validator data.")
            with c2:
                st.markdown('<div class="panel">', unsafe_allow_html=True)
                st.markdown('<div class="section-title">Staking overview</div>', unsafe_allow_html=True)
                for _, row in polkadot_staking.head(5).iterrows():
                    st.markdown(f"""
                    <div class="small-note" style="margin-bottom:0.5rem;">
                        <strong>{row['chain_name']}</strong><br>
                        Validators: {fmt_num(row['number_of_validators'])} | Nominators: {fmt_num(row['number_of_nominators'])} | Pools: {fmt_num(row['number_of_pools'])}
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="section-title">Staking detail</div>', unsafe_allow_html=True)
            stake_table = polkadot_staking.copy()
            for c in ["staked_dot", "staked_dot_in_pools", "unbonding_dot", "minimum_nominator_active_stake"]:
                stake_table[c] = stake_table[c].map(fmt_num)
            for c in ["number_of_addresses_staking", "number_of_nominators", "number_of_pool_members", "number_of_pools", "number_of_validators"]:
                stake_table[c] = stake_table[c].map(fmt_num)
            st.dataframe(stake_table, width="stretch", hide_index=True)

        # ── Treasury & Gov ────────────────────────────────────────────────────
        with sub_tgov:
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown('<div class="section-title">Treasury allocation</div>', unsafe_allow_html=True)
                if not polkadot_treasury.empty:
                    tlatest = polkadot_treasury.groupby("asset_symbol")["balance_usd"].sum().reset_index()
                    fig = px.pie(
                        tlatest,
                        values="balance_usd",
                        names="asset_symbol",
                        hole=0.45,
                        title="Treasury by asset"
                    )
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e9f1f7"),
                        margin=dict(l=10, r=10, t=40, b=10),
                        height=300
                    )
                    st.plotly_chart(fig, width="stretch")
                else:
                    st.info("No treasury data.")

            with c2:
                st.markdown('<div class="section-title">OpenGov urgency</div>', unsafe_allow_html=True)
                if not polkadot_opengov.empty:
                    for _, row in polkadot_opengov.head(6).iterrows():
                        color = "#ff6b7a" if row["urgency_score"] >= 70 else "#ffb84d" if row["urgency_score"] >= 40 else "#14f195"
                        st.markdown(f"""
                        <div style="margin-bottom:0.6rem;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span class="small-note">#{row['referendum_index']} {row['origin_name']}</span>
                                <span style="color:{color}; font-weight:700;">{int(row['urgency_score'])}</span>
                            </div>
                            <div style="height:4px; background:rgba(255,255,255,0.06); border-radius:2px; margin-top:4px;">
                                <div style="width:min(100%, {max(5, row['urgency_score'])}%); height:4px; background:{color}; border-radius:2px;"></div>
                            </div>
                            <div class="small-note">{row['outcome_status']} | Turnout: {fmt_num(row['turnout_total'])}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No governance data.")

            st.markdown('<div class="section-title">Treasury detail</div>', unsafe_allow_html=True)
            treas_table = polkadot_treasury.copy()
            treas_table["balance_usd"] = treas_table["balance_usd"].map(fmt_usd)
            treas_table["balance_token"] = treas_table["balance_token"].map(fmt_num)
            treas_table["treasury_share_pct"] = treas_table["treasury_share_pct"].map(lambda x: f"{float(x):.2f}%" if x else "-")
            st.dataframe(treas_table, width="stretch", hide_index=True)

            st.markdown('<div class="section-title">OpenGov detail</div>', unsafe_allow_html=True)
            gov_table = polkadot_opengov.copy()
            for c in ["ayes", "nays", "support_value", "turnout_total", "approval_margin"]:
                gov_table[c] = gov_table[c].map(fmt_num)
            gov_table["urgency_score"] = gov_table["urgency_score"].map(lambda x: int(x))
            st.dataframe(gov_table, width="stretch", hide_index=True)

        # ── XCM Explorer ──────────────────────────────────────────────────────
        with sub_xcm:
            st.markdown('<div class="section-title">XCM summary</div>', unsafe_allow_html=True)
            if not polkadot_xcm_summary.empty:
                x1, x2, x3, x4 = st.columns(4)
                xs = polkadot_xcm_summary.iloc[0]
                with x1:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">Success Rate</div>
                        <div class="kpi-value">{float(xs.get('success_rate', 0)):.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                with x2:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">Avg Latency</div>
                        <div class="kpi-value">{float(xs.get('avg_latency_seconds', 0)):.1f}s</div>
                    </div>
                    """, unsafe_allow_html=True)
                with x3:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">Unmatched</div>
                        <div class="kpi-value">{fmt_num(xs.get('unmatched_messages', 0))}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with x4:
                    pending = len(polkadot_xcm[polkadot_xcm["route_status"].astype(str).str.contains("pending|partial", case=False)]) if not polkadot_xcm.empty else 0
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">Pending Routes</div>
                        <div class="kpi-value">{fmt_num(pending)}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No XCM summary data.")

            st.markdown('<div class="section-title">Recent XCM transfers</div>', unsafe_allow_html=True)
            if not polkadot_xcm.empty:
                xcm_disp = polkadot_xcm.copy()
                xcm_disp["value_usd"] = xcm_disp["value_usd"].map(fmt_usd)
                xcm_disp["latency_seconds"] = xcm_disp["latency_seconds"].map(lambda x: f"{float(x):.1f}s" if x else "-")
                xcm_disp["origin_account"] = xcm_disp["origin_account"].map(short_addr)
                xcm_disp["dest_account"] = xcm_disp["dest_account"].map(short_addr)
                xcm_disp["signal_score"] = xcm_disp["signal_score"].map(lambda x: int(x))
                st.dataframe(xcm_disp, width="stretch", hide_index=True)
            else:
                st.info("No XCM transfers.")

        # ── Extrinsics ────────────────────────────────────────────────────────
        with sub_ext:
            st.markdown('<div class="section-title">Recent extrinsics</div>', unsafe_allow_html=True)
            if not polkadot_extrinsics.empty:
                ext = polkadot_extrinsics.copy()
                ext["success_flag"] = ext["success_flag"].map(lambda x: "✅ Success" if x in [1, "1", True, "true"] else "❌ Failed")
                ext["signer_address"] = ext["signer_address"].map(short_addr)
                ext["extrinsic_hash"] = ext["extrinsic_hash"].map(short_addr)
                st.dataframe(ext, width="stretch", hide_index=True)
            else:
                st.info("No extrinsics available.")

        # ── Derived Signals ───────────────────────────────────────────────────
        with sub_der:
            st.markdown('<div class="section-title">Derived signals</div>', unsafe_allow_html=True)
            if not polkadot_derived.empty:
                for _, row in polkadot_derived.iterrows():
                    sev = str(row.get("severity", "")).lower()
                    color = "#ff6b7a" if sev == "high" else "#ffb84d" if sev == "medium" else "#14f195"
                    st.markdown(f"""
                    <div class="panel" style="border-left: 4px solid {color};">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                            <span class="section-title" style="margin:0;">{row['title']}</span>
                            {severity_badge(sev)}
                        </div>
                        <div class="small-note">{row['chain_name']} | {row['signal_family']} | Score: {int(row['score'])}</div>
                        <div style="margin-top:0.5rem;">{row['description']}</div>
                        <div class="small-note" style="margin-top:0.4rem;">Ref: {row['reference_id']} | Date: {row['signal_date']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No derived signals available.")


# ── Base L2 ─────────────────────────────────────────────────────────────────────
with tab_base:
    st.markdown('<div class="section-title">Base L2 telemetry</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="helper">Base chain activity, whale transfers, gas pressure, and derived signals from Oracle-backed ingestion.</div>',
        unsafe_allow_html=True
    )

    if base_rpc.empty or base_activity.empty:
        st.warning("Base telemetry tables are empty or unavailable.")
    else:
        rpc = base_rpc.iloc[0]
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Latest Block</div>
                <div class="kpi-value">{fmt_num(rpc.get('latest_block_number', 0))}</div>
                <div class="kpi-delta">Gas used: {fmt_num(rpc.get('gas_used_total', 0))}</div>
            </div>
            """, unsafe_allow_html=True)
        with b2:
            tps_val = float(rpc.get('tps_1min', 0)) if rpc.get('tps_1min') else 0
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">TPS (1m)</div>
                <div class="kpi-value">{tps_val:.1f}</div>
                <div class="kpi-delta">Base sequencer throughput</div>
            </div>
            """, unsafe_allow_html=True)
        with b3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Whale Flow</div>
                <div class="kpi-value">{fmt_usd(base_whale_usd)}</div>
                <div class="kpi-delta">{len(base_whales)} large transfers</div>
            </div>
            """, unsafe_allow_html=True)
        with b4:
            derived_count = len(base_derived)
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Derived Signals</div>
                <div class="kpi-value">{derived_count}</div>
                <div class="kpi-delta">Active intelligence layer</div>
            </div>
            """, unsafe_allow_html=True)

        sub_base_ov, sub_base_whales, sub_base_der = st.tabs([
            "Overview", "Whales", "Derived Signals"
        ])

        with sub_base_ov:
            st.markdown('<div class="section-title">Chain activity</div>', unsafe_allow_html=True)
            if not base_activity.empty:
                act = base_activity.copy()
                act["tx_count"] = act["tx_count"].map(fmt_num)
                act["tps"] = act["tps"].map(lambda x: f"{float(x):.3f}")
                act["total_fees_usd"] = act["total_fees_usd"].map(fmt_usd)
                act["activity_score"] = act["activity_score"].map(lambda x: f"{float(x):.1f}")
                st.dataframe(act, width="stretch", hide_index=True)
            else:
                st.info("No Base activity data.")

            st.markdown('<div class="section-title">RPC snapshot</div>', unsafe_allow_html=True)
            if not base_rpc.empty:
                rpc_table = base_rpc.copy()
                rpc_table["latest_block_number"] = rpc_table["latest_block_number"].map(fmt_num)
                rpc_table["tps_1min"] = rpc_table["tps_1min"].map(lambda x: f"{float(x):.2f}" if x else "-")
                rpc_table["base_fee_gwei"] = rpc_table["base_fee_gwei"].map(lambda x: f"{float(x):.4f}" if x else "-")
                st.dataframe(rpc_table, width="stretch", hide_index=True)
            else:
                st.info("No Base RPC snapshot.")

        with sub_base_whales:
            st.markdown('<div class="section-title">Base whale transfers</div>', unsafe_allow_html=True)
            if not base_whales.empty:
                bw = base_whales.copy()
                bw_export = bw.copy()
                bw["value_usd"] = bw["value_usd"].map(fmt_usd)
                bw["from_address"] = bw["from_address"].map(short_addr)
                bw["to_address"] = bw["to_address"].map(short_addr)
                bw["block_number"] = bw["block_number"].map(fmt_num)
                st.download_button(
                    "Export Base whale rows",
                    data=build_export_bytes(bw_export),
                    file_name="asyncsignals_base_whales.csv",
                    mime="text/csv"
                )
                st.dataframe(bw, width="stretch", hide_index=True)
            else:
                st.info("No Base whale transfers available.")

        with sub_base_der:
            st.markdown('<div class="section-title">Base derived signals</div>', unsafe_allow_html=True)
            if not base_derived.empty:
                for _, row in base_derived.iterrows():
                    sev = str(row.get("severity", "")).lower()
                    color = "#ff6b7a" if sev == "high" else "#ffb84d" if sev == "medium" else "#14f195"
                    st.markdown(f"""
                    <div class="panel" style="border-left: 4px solid {color};">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                            <span class="section-title" style="margin:0;">{row['title']}</span>
                            <span class="status-badge base-severity-{sev}">{sev.upper()}</span>
                        </div>
                        <div class="small-note">{row['signal_family']} | Score: {int(row['score'])}</div>
                        <div style="margin-top:0.5rem;">{row['description']}</div>
                        <div class="small-note" style="margin-top:0.4rem;">Ref: {row['reference_id']} | Date: {row['signal_date']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No Base derived signals available.")

# ── Alerts Access ───────────────────────────────────────────────────────────────
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
            <div class="small-note">Recommended demo flow: Mission Control → Whale Tracker → Polkadot → Signal Ledger → AI Context.</div>
        </div>
        """, unsafe_allow_html=True)



st.caption("AsyncSignals | Oracle-backed, multi-chain telemetry console")
