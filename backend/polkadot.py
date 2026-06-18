import asyncio
import math
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
import oracledb
from dotenv import load_dotenv

load_dotenv()

DOTLAKE_API_PARITY_KEY = os.getenv("DOTLAKE_API_PARITY_KEY")
PUBLICNODE_POLKADOT_URL = os.getenv("PUBLICNODE_POLKADOT_URL")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN", "asyncsignalsdatabase_medium")
WALLET_DIR = os.getenv("WALLET_DIR", "/home/daniel/wallet")

DOTLAKE_BASE = "https://api.data.parity.io"
TS_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_FETCH_LIMIT = 60
MAX_DERIVED_SIGNALS = 40


def get_connection():
    return oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        config_dir=WALLET_DIR,
        wallet_location=WALLET_DIR,
        wallet_password=DB_PASSWORD,
    )


@dataclass
class RpcSnapshot:
    captured_at: str
    latest_block_number_hex: str
    latest_block_number_int: int
    latest_block_hash: str
    finalized_head: str
    extrinsics_in_latest_block: int


@dataclass
class DailyChainActivity:
    date: str
    relay_chain: str
    chain: str
    tx_count: int
    tps: float
    total_fees_native: float
    total_fees_usd: float
    total_fees_usd_30d: Optional[float]
    activity_score: float
    alert_level: str


@dataclass
class DailyStakingParticipation:
    date: str
    relay_chain: str
    chain: str
    minimum_nominator_active_stake: Optional[float]
    number_of_addresses_staking: Optional[int]
    number_of_nominators: Optional[int]
    number_of_pool_members: Optional[int]
    number_of_pools: Optional[int]
    number_of_validators: Optional[int]
    staked_dot: Optional[float]
    staked_dot_in_pools: Optional[float]
    unbonding_dot: Optional[float]


@dataclass
class ExtrinsicFeedItem:
    timestamp: str
    chain: str
    block_number: str
    extrinsic_hash: str
    domain: str
    pallet: str
    method: str
    signer: str
    success: bool
    summary: str


@dataclass
class ValidatorMonthly:
    month: str
    relay_chain: str
    chain: str
    number_of_nominators: Optional[int]
    number_of_active_validators: Optional[int]
    number_of_waiting_validators: Optional[int]
    waiting_ratio_pct: Optional[float]


@dataclass
class TreasuryBalance:
    month: str
    relay_chain: str
    chain: str
    asset: str
    balance_token: float
    balance_usd: float
    treasury_share_pct: Optional[float]


@dataclass
class OpenGovSignal:
    start_date: str
    end_date: Optional[str]
    relay_chain: str
    chain: str
    referendum_index: Optional[int]
    origin_name: str
    track_id: Optional[str]
    outcome_status: str
    ayes: Optional[float]
    nays: Optional[float]
    support_value: Optional[float]
    turnout_total: Optional[float]
    approval_margin: Optional[float]
    urgency_score: int
    signal_label: str


@dataclass
class XCMSummarySnapshot:
    relay_chain: str
    window_hours: int
    total_messages: int
    completed_messages: int
    failed_messages: int
    matched_messages: int
    success_rate: Optional[float]
    avg_latency_seconds: Optional[float]
    median_latency_seconds: Optional[float]
    p95_latency_seconds: Optional[float]
    unmatched_messages: int


@dataclass
class XCMTransferSignal:
    origin_timestamp: str
    relay_chain: str
    origin_chain: str
    dest_chain: str
    origin_para_id: str
    dest_para_id: str
    xcm_type: str
    xcm_version: str
    message_hash: str
    message_id: str
    origin_account: str
    dest_account: str
    asset_symbol: str
    value_usd: Optional[float]
    origin_block_number: str
    outcome: str
    match_status: str
    latency_seconds: Optional[float]
    route_status: str
    signal_score: int


@dataclass
class DerivedSignal:
    signal_date: str
    signal_family: str
    signal_key: str
    relay_chain: str
    chain: str
    severity: str
    score: int
    title: str
    description: str
    metric_value_1: Optional[float]
    metric_value_2: Optional[float]
    metric_value_3: Optional[float]
    reference_id: str


def utc_now_str() -> str:
    return datetime.now(UTC).strftime(TS_FORMAT)


def log(msg: str):
    print(f"[{utc_now_str()}] {msg}", flush=True)


def short_text(value: Any, limit: int = 140) -> str:
    if value is None:
        return "-"
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def as_float(value: Any) -> Optional[float]:
    try:
        if value in [None, "", "NaT"]:
            return None
        return float(value)
    except Exception:
        return None


def as_int(value: Any) -> Optional[int]:
    try:
        if value in [None, "", "NaT"]:
            return None
        return int(float(value))
    except Exception:
        return None


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return value in [1, "1", "true", "True", "TRUE", "yes", "Yes"]


def first_present(row: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    for key in keys:
        if key in row and row.get(key) not in [None, "", "NaT"]:
            return row.get(key)
    return default


def safe_list(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ["data", "results", "items", "rows", "records", "referenda"]:
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        if all(not isinstance(v, (list, dict)) for v in data.values()):
            return [data]
    return []


def filter_relay_chain(rows: List[Dict[str, Any]], relay_chain: str = "polkadot") -> List[Dict[str, Any]]:
    rows_with_relay = [r for r in rows if r.get("relay_chain") not in [None, "", "NaT"]]
    if not rows_with_relay:
        return rows
    filtered = [r for r in rows if str(r.get("relay_chain", "")).lower() == relay_chain.lower()]
    return filtered if filtered else rows


def latest_value(rows: List[Dict[str, Any]], key: str) -> Optional[str]:
    values = [str(r.get(key)) for r in rows if r.get(key) not in [None, "", "NaT"]]
    return max(values) if values else None


def parse_date(value: Optional[str]):
    if value in [None, "", "-", "None", "NaT"]:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(text, fmt)
            if fmt == "%Y-%m":
                return datetime(dt.year, dt.month, 1)
            return dt
        except Exception:
            continue
    return None


def parse_timestamp(value: Optional[str]):
    if value in [None, "", "-", "None", "NaT"]:
        return None
    text = str(value).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    return None


def dotlake_headers() -> Dict[str, str]:
    if not DOTLAKE_API_PARITY_KEY:
        raise ValueError("Missing DOTLAKE_API_PARITY_KEY")
    return {
        "Authorization": f"Bearer {DOTLAKE_API_PARITY_KEY}",
        "Accept": "application/json",
        "User-Agent": "AsyncSignals-Polkadot/6.0",
    }


async def polkadot_rpc(client: httpx.AsyncClient, method: str, params: Optional[list] = None):
    if not PUBLICNODE_POLKADOT_URL:
        raise ValueError("Missing PUBLICNODE_POLKADOT_URL")
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    resp = await client.post(
        PUBLICNODE_POLKADOT_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=25.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data.get("result")


async def dotlake_get(client: httpx.AsyncClient, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{DOTLAKE_BASE}{path}"
    resp = await client.get(
        url,
        params=params or {},
        headers=dotlake_headers(),
        timeout=30.0,
        follow_redirects=True,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"{path} -> HTTP {resp.status_code} | {short_text(resp.text, 300)}")
    if "application/json" not in resp.headers.get("content-type", "").lower():
        raise RuntimeError(f"{path} -> non-json response")
    return resp.json()


async def fetch_publicnode_basics(client: httpx.AsyncClient) -> RpcSnapshot:
    log("Fetching PublicNode RPC basics")
    header = await polkadot_rpc(client, "chain_getHeader")
    finalized_head = await polkadot_rpc(client, "chain_getFinalizedHead")
    latest_hash = await polkadot_rpc(client, "chain_getBlockHash")
    latest_block = await polkadot_rpc(client, "chain_getBlock", [latest_hash])

    latest_block_number_hex = header.get("number", "0x0") if isinstance(header, dict) else "0x0"
    latest_block_number_int = int(latest_block_number_hex, 16)

    return RpcSnapshot(
        captured_at=utc_now_str(),
        latest_block_number_hex=latest_block_number_hex,
        latest_block_number_int=latest_block_number_int,
        latest_block_hash=latest_hash,
        finalized_head=finalized_head,
        extrinsics_in_latest_block=len(latest_block.get("block", {}).get("extrinsics", []))
        if isinstance(latest_block, dict)
        else 0,
    )


async def fetch_dotlake_data(client: httpx.AsyncClient) -> Dict[str, Any]:
    log("Fetching Dotlake datasets")
    start_7 = (datetime.now(UTC).date() - timedelta(days=7)).isoformat()
    start_30 = (datetime.now(UTC).date() - timedelta(days=30)).isoformat()
    end_today = datetime.now(UTC).date().isoformat()

    endpoints = {
        "daily_tps": ("/api/daily-tps", {"relay_chain": "polkadot", "start_date": start_7, "end_date": end_today}),
        "daily_fees": ("/api/daily-fees", {"relay_chain": "polkadot", "start_date": start_7, "end_date": end_today}),
        "staking_participation": (
            "/api/daily-staking-participation",
            {"relay_chain": "polkadot", "chain": "polkadot", "start_date": start_30, "end_date": end_today},
        ),
        "recent_extrinsics": (
            "/api/explorer/recent-extrinsics",
            {"relay_chain": "polkadot", "limit": DEFAULT_FETCH_LIMIT, "exclude_domains": "System,Consensus"},
        ),
        "active_validators": ("/api/monthly-active-validators", {"relay_chain": "polkadot", "chain": "polkadot"}),
        "treasury_balances": ("/api/monthly-treasury-balances", {"relay_chain": "polkadot"}),
        "opengov_results": ("/api/monthly-opengov-participation", {"relay_chain": "polkadot", "chain": "polkadot"}),
        "xcm_summary": ("/api/xcm-summary", {"relay_chain": "polkadot"}),
        "xcm_transfers": ("/api/xcm-transfers", {"relay_chain": "polkadot", "limit": DEFAULT_FETCH_LIMIT}),
    }

    out: Dict[str, Any] = {}
    for label, (path, params) in endpoints.items():
        try:
            data = await dotlake_get(client, path, params=params)
            out[label] = {"ok": True, "data": data, "path": path, "params": params}
            log(f"[OK] {label}")
        except Exception as e:
            out[label] = {"ok": False, "error": repr(e), "path": path, "params": params}
            log(f"[FAIL] {label}: {e}")
    return out


def compute_activity_score(tx_count: int, fees_usd: float, tps: float) -> float:
    score = math.log10(tx_count + 1) * 50 + math.log10(max(fees_usd, 0.0) + 1) * 30 + math.log10(max(tps, 0.0) + 1) * 20
    return round(score, 2)


def activity_alert_level(score: float) -> str:
    if score >= 450:
        return "high"
    if score >= 250:
        return "medium"
    return "low"


def normalize_chain_activity(tps_data: Any, fees_data: Any) -> List[DailyChainActivity]:
    tps_rows = filter_relay_chain(safe_list(tps_data), "polkadot")
    fee_rows = filter_relay_chain(safe_list(fees_data), "polkadot")

    latest_tps_date = latest_value(tps_rows, "date")
    latest_fee_date = latest_value(fee_rows, "date")
    if latest_tps_date:
        tps_rows = [r for r in tps_rows if str(r.get("date")) == latest_tps_date]
    if latest_fee_date:
        fee_rows = [r for r in fee_rows if str(r.get("date")) == latest_fee_date]

    fee_index = {}
    for row in fee_rows:
        key = (str(row.get("relay_chain", "")), str(row.get("chain", "")), str(row.get("date", "")))
        fee_index[key] = row

    normalized: List[DailyChainActivity] = []
    for row in tps_rows:
        try:
            key = (str(row.get("relay_chain", "")), str(row.get("chain", "")), str(row.get("date", "")))
            fee_row = fee_index.get(key, {})
            tx_count = as_int(first_present(row, ["num_transactions_combined", "tx_count"])) or 0
            tps = as_float(first_present(row, ["transactions_per_second", "tps"])) or 0.0
            total_fees_native = as_float(first_present(fee_row, ["total_fees", "total_fees_native"])) or 0.0
            total_fees_usd = as_float(first_present(fee_row, ["total_fees_usd"])) or 0.0
            total_fees_usd_30d = as_float(first_present(fee_row, ["total_fees_usd_30d"]))
            score = compute_activity_score(tx_count, total_fees_usd, tps)
            normalized.append(
                DailyChainActivity(
                    date=str(first_present(row, ["date"], "-")),
                    relay_chain=str(first_present(row, ["relay_chain"], "-")),
                    chain=str(first_present(row, ["chain"], "-")),
                    tx_count=tx_count,
                    tps=round(tps, 6),
                    total_fees_native=round(total_fees_native, 6),
                    total_fees_usd=round(total_fees_usd, 6),
                    total_fees_usd_30d=round(total_fees_usd_30d, 6) if total_fees_usd_30d is not None else None,
                    activity_score=score,
                    alert_level=activity_alert_level(score),
                )
            )
        except Exception as e:
            log(f"normalize_chain_activity row skipped: {e}")

    normalized.sort(key=lambda x: x.activity_score, reverse=True)
    return normalized[:15]


def normalize_staking_participation(data: Any) -> List[DailyStakingParticipation]:
    rows = filter_relay_chain(safe_list(data), "polkadot")
    rows = [r for r in rows if str(r.get("chain", "")).lower() == "polkadot"] or rows

    normalized: List[DailyStakingParticipation] = []
    for row in rows:
        try:
            normalized.append(
                DailyStakingParticipation(
                    date=str(first_present(row, ["date"], "-")),
                    relay_chain=str(first_present(row, ["relay_chain"], "-")),
                    chain=str(first_present(row, ["chain"], "-")),
                    minimum_nominator_active_stake=as_float(first_present(row, ["minimum_nominator_active_stake"])),
                    number_of_addresses_staking=as_int(first_present(row, ["number_of_addresses_staking"])),
                    number_of_nominators=as_int(first_present(row, ["number_of_nominators"])),
                    number_of_pool_members=as_int(first_present(row, ["number_of_pool_members"])),
                    number_of_pools=as_int(first_present(row, ["number_of_pools"])),
                    number_of_validators=as_int(first_present(row, ["number_of_validators"])),
                    staked_dot=as_float(first_present(row, ["staked_DOT", "staked_dot"])),
                    staked_dot_in_pools=as_float(first_present(row, ["staked_DOT_in_pools", "staked_dot_in_pools"])),
                    unbonding_dot=as_float(first_present(row, ["unbonding_DOT", "unbonding_dot"])),
                )
            )
        except Exception as e:
            log(f"normalize_staking_participation row skipped: {e}")

    normalized.sort(key=lambda x: x.date, reverse=True)
    return normalized[:15]


def normalize_recent_extrinsics(data: Any) -> List[ExtrinsicFeedItem]:
    rows = safe_list(data)
    normalized: List[ExtrinsicFeedItem] = []
    for row in rows:
        try:
            normalized.append(
                ExtrinsicFeedItem(
                    timestamp=str(first_present(row, ["timestamp", "event_time"], "-")),
                    chain=str(first_present(row, ["chain"], "-")),
                    block_number=str(first_present(row, ["block_number"], "-")),
                    extrinsic_hash=str(first_present(row, ["extrinsic_hash"], "-")),
                    domain=str(first_present(row, ["domain", "domain_name"], "-")),
                    pallet=str(first_present(row, ["pallet", "pallet_name", "ex_pallet"], "-")),
                    method=str(first_present(row, ["method", "method_name", "ex_method"], "-")),
                    signer=str(first_present(row, ["signer", "signer_address"], "-")) or "-",
                    success=as_bool(first_present(row, ["success", "success_flag"])),
                    summary=str(first_present(row, ["summary", "summary_text"], "-")),
                )
            )
        except Exception as e:
            log(f"normalize_recent_extrinsics row skipped: {e}")

    normalized.sort(key=lambda x: x.timestamp, reverse=True)
    return normalized[:40]


def normalize_active_validators(data: Any) -> List[ValidatorMonthly]:
    rows = filter_relay_chain(safe_list(data), "polkadot")
    rows = [r for r in rows if str(r.get("chain", "")).lower() == "polkadot"] or rows

    normalized: List[ValidatorMonthly] = []
    for row in rows:
        try:
            active = as_int(first_present(row, ["number_of_active_validators"]))
            waiting = as_int(first_present(row, ["number_of_waiting_validators"]))
            waiting_ratio = round((waiting / active) * 100, 2) if active and waiting is not None and active > 0 else None
            normalized.append(
                ValidatorMonthly(
                    month=str(first_present(row, ["month"], "-")),
                    relay_chain=str(first_present(row, ["relay_chain"], "-")),
                    chain=str(first_present(row, ["chain"], "-")),
                    number_of_nominators=as_int(first_present(row, ["number_of_nominators"])),
                    number_of_active_validators=active,
                    number_of_waiting_validators=waiting,
                    waiting_ratio_pct=waiting_ratio,
                )
            )
        except Exception as e:
            log(f"normalize_active_validators row skipped: {e}")

    normalized.sort(key=lambda x: x.month, reverse=True)
    return normalized[:6]


def normalize_treasury_balances(data: Any) -> List[TreasuryBalance]:
    rows = filter_relay_chain(safe_list(data), "polkadot")
    latest_month = latest_value(rows, "month")
    if latest_month:
        rows = [r for r in rows if str(r.get("month")) == latest_month]

    total_usd = sum(as_float(first_present(r, ["balance_usd"])) or 0.0 for r in rows)
    normalized: List[TreasuryBalance] = []
    for row in rows:
        try:
            balance_usd = as_float(first_present(row, ["balance_usd"])) or 0.0
            share = round((balance_usd / total_usd) * 100, 2) if total_usd > 0 else None
            normalized.append(
                TreasuryBalance(
                    month=str(first_present(row, ["month"], "-")),
                    relay_chain=str(first_present(row, ["relay_chain"], "-")),
                    chain=str(first_present(row, ["chain"], "-")),
                    asset=str(first_present(row, ["asset", "asset_symbol"], "-")),
                    balance_token=round(as_float(first_present(row, ["balance_token"])) or 0.0, 6),
                    balance_usd=round(balance_usd, 6),
                    treasury_share_pct=share,
                )
            )
        except Exception as e:
            log(f"normalize_treasury_balances row skipped: {e}")

    normalized.sort(key=lambda x: x.balance_usd, reverse=True)
    return normalized[:12]


def normalize_opengov_results(data: Any) -> List[OpenGovSignal]:
    rows = safe_list(data)
    rows = [r for r in rows if str(r.get("relay_chain", "")).lower() == "polkadot"] or rows
    normalized: List[OpenGovSignal] = []

    for row in rows:
        try:
            start_date = str(first_present(row, ["start_date", "date", "month"], "-"))
            end_date = first_present(row, ["end_date"])
            relay_chain = str(first_present(row, ["relay_chain"], "polkadot"))
            chain = str(first_present(row, ["chain", "chain_name"], "polkadot"))
            referendum_index = as_int(first_present(row, ["referendum_index", "number_of_referenda"]))
            origin_name = str(first_present(row, ["origin_name", "vote_type", "origin"], "-"))
            track_id = first_present(row, ["track_id", "track"])
            outcome_status = str(first_present(row, ["outcome_status", "outcome"], "monthly_summary"))
            ayes = as_float(first_present(row, ["ayes"]))
            nays = as_float(first_present(row, ["nays"]))
            support_value = as_float(first_present(row, ["support_value", "support"]))
            turnout_total = as_float(first_present(row, ["turnout_total", "number_of_voters"]))
            approval_margin = as_float(first_present(row, ["approval_margin"]))
            if approval_margin is None and ayes is not None and nays is not None:
                approval_margin = round(ayes - nays, 6)

            urgency_score = as_int(first_present(row, ["urgency_score"]))
            signal_label = str(first_present(row, ["signal_label"], "governance_event"))

            if urgency_score is None:
                if turnout_total is None:
                    turnout_total = (ayes or 0.0) + (nays or 0.0)
                urgency_score = min(100, int(math.log10((turnout_total or 0.0) + 1) * 20))
                signal_label = "monthly_participation"

            normalized.append(
                OpenGovSignal(
                    start_date=start_date,
                    end_date=str(end_date) if end_date not in [None, "", "NaT"] else None,
                    relay_chain=relay_chain,
                    chain=chain,
                    referendum_index=referendum_index,
                    origin_name=origin_name,
                    track_id=str(track_id) if track_id not in [None, "", "NaT"] else None,
                    outcome_status=outcome_status,
                    ayes=ayes,
                    nays=nays,
                    support_value=support_value,
                    turnout_total=turnout_total,
                    approval_margin=approval_margin,
                    urgency_score=urgency_score,
                    signal_label=signal_label,
                )
            )
        except Exception as e:
            log(f"normalize_opengov_results row skipped: {e}")

    normalized.sort(key=lambda x: (x.start_date, x.urgency_score), reverse=True)
    return normalized[:50]


def normalize_xcm_summary(data: Any) -> List[XCMSummarySnapshot]:
    rows = filter_relay_chain(safe_list(data), "polkadot")
    normalized: List[XCMSummarySnapshot] = []
    for row in rows:
        try:
            total_messages = as_int(first_present(row, ["total_messages"])) or 0
            matched_messages = as_int(first_present(row, ["matched_messages"])) or 0
            normalized.append(
                XCMSummarySnapshot(
                    relay_chain=str(first_present(row, ["relay_chain"], "-")),
                    window_hours=as_int(first_present(row, ["window_hours"])) or 0,
                    total_messages=total_messages,
                    completed_messages=as_int(first_present(row, ["completed_messages"])) or 0,
                    failed_messages=as_int(first_present(row, ["failed_messages"])) or 0,
                    matched_messages=matched_messages,
                    success_rate=as_float(first_present(row, ["success_rate"])),
                    avg_latency_seconds=as_float(first_present(row, ["avg_latency_seconds"])),
                    median_latency_seconds=as_float(first_present(row, ["median_latency_seconds"])),
                    p95_latency_seconds=as_float(first_present(row, ["p95_latency_seconds"])),
                    unmatched_messages=max(total_messages - matched_messages, 0),
                )
            )
        except Exception as e:
            log(f"normalize_xcm_summary row skipped: {e}")

    normalized.sort(key=lambda x: x.window_hours, reverse=True)
    return normalized[:3]


def xcm_transfer_profile(match_status: str, latency_seconds: Optional[float], dest_chain: str) -> Tuple[str, int]:
    match_l = (match_status or "").lower()
    if match_l == "matched":
        return "confirmed_route", 86
    if match_l == "sent_only":
        if latency_seconds is not None and latency_seconds > 300:
            return "stale_unmatched_route", 90
        if dest_chain and dest_chain != "-":
            return "pending_route", 74
        return "partial_route", 68
    return "unknown_route", 58


def normalize_xcm_transfers(data: Any) -> List[XCMTransferSignal]:
    rows = filter_relay_chain(safe_list(data), "polkadot")
    normalized: List[XCMTransferSignal] = []
    for row in rows:
        try:
            match_status = str(first_present(row, ["match_status"], "-"))
            latency_seconds = as_float(first_present(row, ["latency_seconds"]))
            dest_chain = str(first_present(row, ["dest_chain"], "")) or ""
            route_status, signal_score = xcm_transfer_profile(match_status, latency_seconds, dest_chain)
            normalized.append(
                XCMTransferSignal(
                    origin_timestamp=str(first_present(row, ["origin_timestamp"], "-")),
                    relay_chain=str(first_present(row, ["relay_chain"], "-")),
                    origin_chain=str(first_present(row, ["origin_chain"], "-")),
                    dest_chain=dest_chain or "-",
                    origin_para_id=str(first_present(row, ["origin_para_id"], "-")),
                    dest_para_id=str(first_present(row, ["dest_para_id"], "-")),
                    xcm_type=str(first_present(row, ["xcm_type"], "-")),
                    xcm_version=str(first_present(row, ["xcm_version"], "-")),
                    message_hash=str(first_present(row, ["message_hash"], "-")),
                    message_id=str(first_present(row, ["message_id"], "-")),
                    origin_account=str(first_present(row, ["origin_account"], "-")) or "-",
                    dest_account=str(first_present(row, ["dest_account"], "-")) or "-",
                    asset_symbol=str(first_present(row, ["asset_symbol"], "-")) or "-",
                    value_usd=as_float(first_present(row, ["value_usd"])),
                    origin_block_number=str(first_present(row, ["origin_block_number"], "-")),
                    outcome=str(first_present(row, ["outcome", "outcome_status"], "-")),
                    match_status=match_status,
                    latency_seconds=latency_seconds,
                    route_status=route_status,
                    signal_score=signal_score,
                )
            )
        except Exception as e:
            log(f"normalize_xcm_transfers row skipped: {e}")

    normalized.sort(key=lambda x: (x.origin_timestamp, x.signal_score), reverse=True)
    return normalized[:40]


def build_derived_signals(
    chain_activity: List[DailyChainActivity],
    staking: List[DailyStakingParticipation],
    validators: List[ValidatorMonthly],
    treasury: List[TreasuryBalance],
    opengov: List[OpenGovSignal],
    xcm_summary: List[XCMSummarySnapshot],
    xcm_transfers: List[XCMTransferSignal],
) -> List[DerivedSignal]:
    out: List[DerivedSignal] = []

    for row in chain_activity[:15]:
        severity = "high" if row.activity_score >= 450 else "medium" if row.activity_score >= 250 else "low"
        out.append(
            DerivedSignal(
                signal_date=row.date,
                signal_family="chain_activity",
                signal_key=f"{row.chain}:{row.date}",
                relay_chain=row.relay_chain,
                chain=row.chain,
                severity=severity,
                score=int(round(row.activity_score)),
                title=f"Chain activity spike on {row.chain}",
                description=(
                    f"{row.chain} recorded {row.tx_count} transactions, {row.tps} TPS, "
                    f"and ${row.total_fees_usd:.2f} in daily fees."
                ),
                metric_value_1=float(row.tx_count),
                metric_value_2=row.tps,
                metric_value_3=row.total_fees_usd,
                reference_id=f"{row.chain}:{row.date}",
            )
        )

    for row in opengov[:12]:
        sev = "high" if row.urgency_score >= 90 else "medium" if row.urgency_score >= 70 else "low"
        turnout = float(row.turnout_total or 0.0)
        margin = row.approval_margin
        support = row.support_value
        if row.referendum_index is not None:
            title = f"OpenGov referendum #{row.referendum_index} update"
            signal_key = f"opengov:{row.start_date}:{row.referendum_index}"
            reference_id = f"{row.start_date}:{row.referendum_index}"
            description = f"{row.origin_name} referendum #{row.referendum_index} is {row.outcome_status} with turnout {turnout:.2f}."
        else:
            title = f"OpenGov {row.origin_name} participation update"
            signal_key = f"opengov:{row.start_date}:{row.origin_name}"
            reference_id = f"{row.start_date}:{row.origin_name}"
            description = f"{row.origin_name} OpenGov participation recorded turnout {turnout:.2f} on {row.start_date}."

        out.append(
            DerivedSignal(
                signal_date=row.start_date,
                signal_family="governance",
                signal_key=signal_key,
                relay_chain=row.relay_chain,
                chain=row.chain,
                severity=sev,
                score=row.urgency_score,
                title=title,
                description=description,
                metric_value_1=turnout,
                metric_value_2=margin,
                metric_value_3=support,
                reference_id=reference_id,
            )
        )

    for row in treasury[:8]:
        if row.treasury_share_pct is not None and row.treasury_share_pct >= 15:
            severity = "high" if row.treasury_share_pct >= 50 else "medium"
            out.append(
                DerivedSignal(
                    signal_date=row.month,
                    signal_family="treasury",
                    signal_key=f"treasury:{row.asset}:{row.month}",
                    relay_chain=row.relay_chain,
                    chain=row.chain,
                    severity=severity,
                    score=int(round(row.treasury_share_pct)),
                    title=f"Treasury concentration in {row.asset}",
                    description=(
                        f"{row.asset} represents {row.treasury_share_pct}% of reported treasury "
                        f"value with ${row.balance_usd:.2f} balance."
                    ),
                    metric_value_1=row.balance_usd,
                    metric_value_2=row.treasury_share_pct,
                    metric_value_3=row.balance_token,
                    reference_id=f"{row.asset}:{row.month}",
                )
            )

    for row in validators[:4]:
        if row.waiting_ratio_pct is not None:
            severity = "high" if row.waiting_ratio_pct >= 100 else "medium" if row.waiting_ratio_pct >= 50 else "low"
            out.append(
                DerivedSignal(
                    signal_date=row.month,
                    signal_family="validator_pressure",
                    signal_key=f"validators:{row.month}",
                    relay_chain=row.relay_chain,
                    chain=row.chain,
                    severity=severity,
                    score=int(round(row.waiting_ratio_pct)),
                    title="Validator queue pressure",
                    description=(
                        f"{row.number_of_waiting_validators} waiting validators versus "
                        f"{row.number_of_active_validators} active validators."
                    ),
                    metric_value_1=float(row.number_of_waiting_validators or 0),
                    metric_value_2=float(row.number_of_active_validators or 0),
                    metric_value_3=row.waiting_ratio_pct,
                    reference_id=row.month,
                )
            )

    for row in staking[:10]:
        if row.minimum_nominator_active_stake is not None:
            sev = "medium" if row.minimum_nominator_active_stake >= 200 else "low"
            out.append(
                DerivedSignal(
                    signal_date=row.date,
                    signal_family="staking_access",
                    signal_key=f"staking:{row.date}",
                    relay_chain=row.relay_chain,
                    chain=row.chain,
                    severity=sev,
                    score=int(round(row.minimum_nominator_active_stake)),
                    title="Minimum active nominator stake",
                    description=(
                        f"Minimum active nominator stake is {row.minimum_nominator_active_stake} DOT "
                        f"with {row.number_of_nominators} nominators and {row.number_of_validators} validators."
                    ),
                    metric_value_1=row.minimum_nominator_active_stake,
                    metric_value_2=float(row.number_of_nominators or 0),
                    metric_value_3=float(row.number_of_validators or 0),
                    reference_id=row.date,
                )
            )

    for row in xcm_summary[:2]:
        if row.unmatched_messages > 0:
            sev = "high" if row.unmatched_messages >= 100 else "medium"
            out.append(
                DerivedSignal(
                    signal_date=utc_now_str().split(" ")[0],
                    signal_family="xcm_health",
                    signal_key=f"xcm_summary:{row.window_hours}",
                    relay_chain=row.relay_chain,
                    chain="xcm",
                    severity=sev,
                    score=min(100, row.unmatched_messages),
                    title="Unmatched XCM routes detected",
                    description=(
                        f"{row.unmatched_messages} unmatched messages out of {row.total_messages} "
                        f"in the last {row.window_hours} hours."
                    ),
                    metric_value_1=float(row.unmatched_messages),
                    metric_value_2=float(row.total_messages),
                    metric_value_3=row.avg_latency_seconds,
                    reference_id=f"{row.relay_chain}:{row.window_hours}",
                )
            )

    pending_count = sum(1 for row in xcm_transfers if row.route_status in ["pending_route", "partial_route"])
    if pending_count > 0:
        out.append(
            DerivedSignal(
                signal_date=utc_now_str().split(" ")[0],
                signal_family="xcm_flow",
                signal_key="xcm_pending_routes",
                relay_chain="polkadot",
                chain="xcm",
                severity="medium" if pending_count < 10 else "high",
                score=min(100, pending_count * 5),
                title="Pending XCM routes in recent feed",
                description=f"{pending_count} recent XCM transfers are pending or partial.",
                metric_value_1=float(pending_count),
                metric_value_2=None,
                metric_value_3=None,
                reference_id="recent_xcm",
            )
        )

    severity_rank = {"high": 3, "medium": 2, "low": 1}
    out.sort(key=lambda x: (severity_rank.get(x.severity, 0), x.score, x.signal_date), reverse=True)
    return out[:MAX_DERIVED_SIGNALS]


def build_store(rpc_snapshot: RpcSnapshot, datasets: Dict[str, Any]) -> Dict[str, Any]:
    chain_activity = []
    staking = []
    extrinsic_feed = []
    validators = []
    treasury = []
    opengov = []
    xcm_summary = []
    xcm_transfers = []

    if datasets.get("daily_tps", {}).get("ok") and datasets.get("daily_fees", {}).get("ok"):
        chain_activity = normalize_chain_activity(datasets["daily_tps"]["data"], datasets["daily_fees"]["data"])
    if datasets.get("staking_participation", {}).get("ok"):
        staking = normalize_staking_participation(datasets["staking_participation"]["data"])
    if datasets.get("recent_extrinsics", {}).get("ok"):
        extrinsic_feed = normalize_recent_extrinsics(datasets["recent_extrinsics"]["data"])
    if datasets.get("active_validators", {}).get("ok"):
        validators = normalize_active_validators(datasets["active_validators"]["data"])
    if datasets.get("treasury_balances", {}).get("ok"):
        treasury = normalize_treasury_balances(datasets["treasury_balances"]["data"])
    if datasets.get("opengov_results", {}).get("ok"):
        opengov = normalize_opengov_results(datasets["opengov_results"]["data"])
    if datasets.get("xcm_summary", {}).get("ok"):
        xcm_summary = normalize_xcm_summary(datasets["xcm_summary"]["data"])
    if datasets.get("xcm_transfers", {}).get("ok"):
        xcm_transfers = normalize_xcm_transfers(datasets["xcm_transfers"]["data"])

    derived = build_derived_signals(chain_activity, staking, validators, treasury, opengov, xcm_summary, xcm_transfers)

    return {
        "rpc_snapshot": asdict(rpc_snapshot),
        "daily_chain_activity": [asdict(x) for x in chain_activity],
        "staking_daily": [asdict(x) for x in staking],
        "extrinsic_feed": [asdict(x) for x in extrinsic_feed],
        "validator_monthly": [asdict(x) for x in validators],
        "treasury_monthly": [asdict(x) for x in treasury],
        "opengov_signals": [asdict(x) for x in opengov],
        "xcm_summary": [asdict(x) for x in xcm_summary],
        "xcm_transfer_signals": [asdict(x) for x in xcm_transfers],
        "derived_signals": [asdict(x) for x in derived],
    }


def replace_table(cursor, table_name: str):
    cursor.execute(f"DELETE FROM {table_name}")


def insert_one(cursor, sql: str, params: Tuple[Any, ...]):
    cursor.execute(sql, params)


def insert_many(cursor, sql: str, rows: List[Tuple[Any, ...]]):
    if rows:
        cursor.executemany(sql, rows)


def write_store_to_oracle(store: Dict[str, Any]):
    log("Writing normalized store to Oracle")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for table_name in [
            "POLKADOT_RPC_SNAPSHOT",
            "POLKADOT_CHAIN_ACTIVITY_DAILY",
            "POLKADOT_STAKING_DAILY",
            "POLKADOT_EXTRINSIC_SUPPLEMENTARY_FEED",
            "POLKADOT_VALIDATOR_MONTHLY",
            "POLKADOT_TREASURY_MONTHLY",
            "POLKADOT_OPENGOV_SIGNALS",
            "POLKADOT_XCM_SUMMARY",
            "POLKADOT_XCM_TRANSFER_SIGNALS",
            "POLKADOT_DERIVED_SIGNALS",
        ]:
            replace_table(cursor, table_name)

        rpc = store["rpc_snapshot"]
        insert_one(
            cursor,
            """
            INSERT INTO POLKADOT_RPC_SNAPSHOT (
                CAPTURED_AT,
                LATEST_BLOCK_NUMBER_HEX,
                LATEST_BLOCK_NUMBER_INT,
                LATEST_BLOCK_HASH,
                FINALIZED_HEAD,
                EXTRINSICS_IN_LATEST_BLOCK
            ) VALUES (:1, :2, :3, :4, :5, :6)
            """,
            (
                parse_timestamp(rpc.get("captured_at")),
                rpc.get("latest_block_number_hex"),
                rpc.get("latest_block_number_int"),
                rpc.get("latest_block_hash"),
                rpc.get("finalized_head"),
                rpc.get("extrinsics_in_latest_block"),
            ),
        )

        insert_many(
            cursor,
            """
            INSERT INTO POLKADOT_CHAIN_ACTIVITY_DAILY (
                ACTIVITY_DATE, RELAY_CHAIN, CHAIN_NAME, TX_COUNT, TPS,
                TOTAL_FEES_NATIVE, TOTAL_FEES_USD, TOTAL_FEES_USD_30D,
                ACTIVITY_SCORE, ALERT_LEVEL
            ) VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10)
            """,
            [
                (
                    parse_date(r.get("date")),
                    r.get("relay_chain"),
                    r.get("chain"),
                    r.get("tx_count"),
                    r.get("tps"),
                    r.get("total_fees_native"),
                    r.get("total_fees_usd"),
                    r.get("total_fees_usd_30d"),
                    r.get("activity_score"),
                    r.get("alert_level"),
                )
                for r in store.get("daily_chain_activity", [])
            ],
        )

        insert_many(
            cursor,
            """
            INSERT INTO POLKADOT_STAKING_DAILY (
                STAKING_DATE, RELAY_CHAIN, CHAIN_NAME,
                MINIMUM_NOMINATOR_ACTIVE_STAKE, NUMBER_OF_ADDRESSES_STAKING,
                NUMBER_OF_NOMINATORS, NUMBER_OF_POOL_MEMBERS, NUMBER_OF_POOLS,
                NUMBER_OF_VALIDATORS, STAKED_DOT, STAKED_DOT_IN_POOLS, UNBONDING_DOT
            ) VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12)
            """,
            [
                (
                    parse_date(r.get("date")),
                    r.get("relay_chain"),
                    r.get("chain"),
                    r.get("minimum_nominator_active_stake"),
                    r.get("number_of_addresses_staking"),
                    r.get("number_of_nominators"),
                    r.get("number_of_pool_members"),
                    r.get("number_of_pools"),
                    r.get("number_of_validators"),
                    r.get("staked_dot"),
                    r.get("staked_dot_in_pools"),
                    r.get("unbonding_dot"),
                )
                for r in store.get("staking_daily", [])
            ],
        )

        insert_many(
            cursor,
            """
            INSERT INTO POLKADOT_EXTRINSIC_SUPPLEMENTARY_FEED (
                EVENT_TIME, CHAIN_NAME, BLOCK_NUMBER, EXTRINSIC_HASH,
                DOMAIN_NAME, PALLET_NAME, METHOD_NAME, SIGNER_ADDRESS,
                SUCCESS_FLAG, SUMMARY_TEXT
            ) VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10)
            """,
            [
                (
                    parse_timestamp(r.get("timestamp")),
                    r.get("chain"),
                    r.get("block_number"),
                    r.get("extrinsic_hash"),
                    r.get("domain"),
                    r.get("pallet"),
                    r.get("method"),
                    r.get("signer"),
                    1 if r.get("success") else 0,
                    r.get("summary"),
                )
                for r in store.get("extrinsic_feed", [])
            ],
        )

        insert_many(
            cursor,
            """
            INSERT INTO POLKADOT_VALIDATOR_MONTHLY (
                MONTH_DATE, RELAY_CHAIN, CHAIN_NAME,
                NUMBER_OF_NOMINATORS, NUMBER_OF_ACTIVE_VALIDATORS,
                NUMBER_OF_WAITING_VALIDATORS, WAITING_RATIO_PCT
            ) VALUES (:1,:2,:3,:4,:5,:6,:7)
            """,
            [
                (
                    parse_date(r.get("month")),
                    r.get("relay_chain"),
                    r.get("chain"),
                    r.get("number_of_nominators"),
                    r.get("number_of_active_validators"),
                    r.get("number_of_waiting_validators"),
                    r.get("waiting_ratio_pct"),
                )
                for r in store.get("validator_monthly", [])
            ],
        )

        insert_many(
            cursor,
            """
            INSERT INTO POLKADOT_TREASURY_MONTHLY (
                MONTH_DATE, RELAY_CHAIN, CHAIN_NAME, ASSET_SYMBOL,
                BALANCE_TOKEN, BALANCE_USD, TREASURY_SHARE_PCT
            ) VALUES (:1,:2,:3,:4,:5,:6,:7)
            """,
            [
                (
                    parse_date(r.get("month")),
                    r.get("relay_chain"),
                    r.get("chain"),
                    r.get("asset"),
                    r.get("balance_token"),
                    r.get("balance_usd"),
                    r.get("treasury_share_pct"),
                )
                for r in store.get("treasury_monthly", [])
            ],
        )

        insert_many(
            cursor,
            """
            INSERT INTO POLKADOT_OPENGOV_SIGNALS (
                START_DATE, END_DATE, RELAY_CHAIN, CHAIN_NAME, REFERENDUM_INDEX,
                ORIGIN_NAME, TRACK_ID, OUTCOME_STATUS, AYES, NAYS,
                SUPPORT_VALUE, TURNOUT_TOTAL, APPROVAL_MARGIN, URGENCY_SCORE, SIGNAL_LABEL
            ) VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12,:13,:14,:15)
            """,
            [
                (
                    parse_date(r.get("start_date")),
                    parse_date(r.get("end_date")),
                    r.get("relay_chain"),
                    r.get("chain"),
                    r.get("referendum_index"),
                    r.get("origin_name"),
                    r.get("track_id"),
                    r.get("outcome_status"),
                    r.get("ayes"),
                    r.get("nays"),
                    r.get("support_value"),
                    r.get("turnout_total"),
                    r.get("approval_margin"),
                    r.get("urgency_score"),
                    r.get("signal_label"),
                )
                for r in store.get("opengov_signals", [])
            ],
        )

        insert_many(
            cursor,
            """
            INSERT INTO POLKADOT_XCM_SUMMARY (
                RELAY_CHAIN, WINDOW_HOURS, TOTAL_MESSAGES, COMPLETED_MESSAGES,
                FAILED_MESSAGES, MATCHED_MESSAGES, SUCCESS_RATE,
                AVG_LATENCY_SECONDS, MEDIAN_LATENCY_SECONDS, P95_LATENCY_SECONDS,
                UNMATCHED_MESSAGES
            ) VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11)
            """,
            [
                (
                    r.get("relay_chain"),
                    r.get("window_hours"),
                    r.get("total_messages"),
                    r.get("completed_messages"),
                    r.get("failed_messages"),
                    r.get("matched_messages"),
                    r.get("success_rate"),
                    r.get("avg_latency_seconds"),
                    r.get("median_latency_seconds"),
                    r.get("p95_latency_seconds"),
                    r.get("unmatched_messages"),
                )
                for r in store.get("xcm_summary", [])
            ],
        )

        insert_many(
            cursor,
            """
            INSERT INTO POLKADOT_XCM_TRANSFER_SIGNALS (
                ORIGIN_TIMESTAMP, RELAY_CHAIN, ORIGIN_CHAIN, DEST_CHAIN,
                ORIGIN_PARA_ID, DEST_PARA_ID, XCM_TYPE, XCM_VERSION,
                MESSAGE_HASH, MESSAGE_ID, ORIGIN_ACCOUNT, DEST_ACCOUNT,
                ASSET_SYMBOL, VALUE_USD, ORIGIN_BLOCK_NUMBER, OUTCOME_STATUS,
                MATCH_STATUS, LATENCY_SECONDS, ROUTE_STATUS, SIGNAL_SCORE
            ) VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12,:13,:14,:15,:16,:17,:18,:19,:20)
            """,
            [
                (
                    parse_timestamp(r.get("origin_timestamp")),
                    r.get("relay_chain"),
                    r.get("origin_chain"),
                    r.get("dest_chain"),
                    r.get("origin_para_id"),
                    r.get("dest_para_id"),
                    r.get("xcm_type"),
                    r.get("xcm_version"),
                    r.get("message_hash"),
                    r.get("message_id"),
                    r.get("origin_account"),
                    r.get("dest_account"),
                    r.get("asset_symbol"),
                    r.get("value_usd"),
                    r.get("origin_block_number"),
                    r.get("outcome"),
                    r.get("match_status"),
                    r.get("latency_seconds"),
                    r.get("route_status"),
                    r.get("signal_score"),
                )
                for r in store.get("xcm_transfer_signals", [])
            ],
        )

        insert_many(
            cursor,
            """
            INSERT INTO POLKADOT_DERIVED_SIGNALS (
                SIGNAL_DATE, SIGNAL_FAMILY, SIGNAL_KEY, RELAY_CHAIN, CHAIN_NAME,
                SEVERITY, SCORE, TITLE, DESCRIPTION, METRIC_VALUE_1,
                METRIC_VALUE_2, METRIC_VALUE_3, REFERENCE_ID
            ) VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12,:13)
            """,
            [
                (
                    parse_date(r.get("signal_date")),
                    r.get("signal_family"),
                    r.get("signal_key"),
                    r.get("relay_chain"),
                    r.get("chain"),
                    r.get("severity"),
                    r.get("score"),
                    r.get("title"),
                    r.get("description"),
                    r.get("metric_value_1"),
                    r.get("metric_value_2"),
                    r.get("metric_value_3"),
                    r.get("reference_id"),
                )
                for r in store.get("derived_signals", [])
            ],
        )

        conn.commit()
        log("Oracle write complete")
    except Exception as e:
        conn.rollback()
        log(f"Oracle write failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def print_summary(rpc_snapshot: RpcSnapshot, store: Dict[str, Any], datasets: Dict[str, Any]):
    print("\n=== PUBLICNODE SUMMARY ===")
    print(asdict(rpc_snapshot))
    print("\n=== NORMALIZED COUNTS ===")
    for key, value in store.items():
        print(f"{key}: {len(value) if isinstance(value, list) else 1}")
    print("\n=== FETCH STATUS ===")
    for label, payload in datasets.items():
        print(f"{label}: {'OK' if payload.get('ok') else 'FAIL'}")


async def main():
    log("Polkadot parser starting")
    log(f"DOTLAKE_API_PARITY_KEY set: {bool(DOTLAKE_API_PARITY_KEY)}")
    log(f"PUBLICNODE_POLKADOT_URL set: {bool(PUBLICNODE_POLKADOT_URL)}")

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(30.0, connect=15.0)
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        rpc_snapshot = await fetch_publicnode_basics(client)
        datasets = await fetch_dotlake_data(client)
        store = build_store(rpc_snapshot, datasets)
        write_store_to_oracle(store)
        print_summary(rpc_snapshot, store, datasets)

    log("Polkadot parser finished")


if __name__ == "__main__":
    asyncio.run(main())
