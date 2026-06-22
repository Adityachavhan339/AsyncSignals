import asyncio
import math
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
import oracledb
from dotenv import load_dotenv

load_dotenv()

ALCHEMY_KEY = os.getenv("ALCHEMY_KEY")
CHAINSTACK_BASE_URL = os.getenv("CHAINSTACK_BASE_URL")
BLOCKPI_BASE_URL = os.getenv("BLOCKPI_BASE_URL")
NODEREAL_BASE_URL = os.getenv("NODEREAL_BASE_URL")
BLOCKREQ_BASE_URL = os.getenv("BLOCKREQ_BASE_URL")
COINGECKO_KEY = os.getenv("COINGECKO_KEY")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN", "asyncsignalsdatabase_medium")
WALLET_DIR = os.getenv("WALLET_DIR", "/home/daniel/wallet")

BASE_ALCHEMY_URL = f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}" if ALCHEMY_KEY else None

TS_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_DERIVED_SIGNALS = 40

# ─── Token pricing whitelist ──────────────────────────────────────────────
# Only tokens we can reliably price. Everything else is skipped.
KNOWN_NATIVE = {"ETH", "BASE"}
KNOWN_WRAPPED = {"WETH", "WBTC", "CBETH"}
KNOWN_STABLES = {"USDC", "USDT", "DAI", "USDE", "PYUSD", "USDZ", "AUSD"}
TRACKED_TOKENS = KNOWN_NATIVE | KNOWN_WRAPPED | KNOWN_STABLES

# CoinGecko ID mapping for price lookups
COINGECKO_IDS = {
    "ETH": "ethereum",
    "WETH": "weth",
    "WBTC": "wrapped-bitcoin",
    "CBETH": "coinbase-wrapped-staked-eth",
}


def get_connection():
    return oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        config_dir=WALLET_DIR,
        wallet_location=WALLET_DIR,
        wallet_password=DB_PASSWORD,
    )


def utc_now_str() -> str:
    return datetime.now(UTC).strftime(TS_FORMAT)


def log(msg: str):
    print(f"[{utc_now_str()}] {msg}", flush=True)


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
        if isinstance(value, str):
            if value.startswith("0x") or value.startswith("0X"):
                return int(value, 16)
            return int(float(value))
        return int(value)
    except Exception:
        return None


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


@dataclass
class BaseRpcSnapshot:
    captured_at: str
    latest_block_number: int
    latest_block_hash: str
    latest_block_timestamp: Optional[int]
    avg_block_time_seconds: Optional[float]
    tps_1min: Optional[float]
    gas_used_total: Optional[int]
    base_fee_gwei: Optional[float]


@dataclass
class BaseChainActivity:
    date: str
    chain_name: str
    tx_count: int
    tps: float
    total_fees_eth: float
    total_fees_usd: float
    activity_score: float
    alert_level: str


@dataclass
class BaseEcosystemMetrics:
    snapshot_date: str
    eth_price_usd: Optional[float]
    tvl_proxy: Optional[float]
    stablecoin_proxy: Optional[float]


@dataclass
class BaseTransferSignal:
    timestamp: str
    asset_symbol: str
    value_usd: Optional[float]
    from_address: str
    to_address: str
    tx_hash: str
    block_number: Optional[int]
    transfer_type: str


@dataclass
class BaseDerivedSignal:
    signal_date: str
    signal_family: str
    signal_key: str
    severity: str
    score: int
    title: str
    description: str
    metric_value_1: Optional[float]
    metric_value_2: Optional[float]
    metric_value_3: Optional[float]
    reference_id: str


async def alchemy_post(client: httpx.AsyncClient, payload: Dict[str, Any]) -> Any:
    if not BASE_ALCHEMY_URL:
        raise ValueError("Missing ALCHEMY_KEY")
    resp = await client.post(
        BASE_ALCHEMY_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=25.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Alchemy RPC error: {data['error']}")
    return data.get("result")


async def chainstack_post(client: httpx.AsyncClient, method: str, params: list = None) -> Any:
    if not CHAINSTACK_BASE_URL:
        raise ValueError("Missing CHAINSTACK_BASE_URL")
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    resp = await client.post(
        CHAINSTACK_BASE_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=25.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"ChainStack error: {data['error']}")
    return data.get("result")


async def blockpi_post(client: httpx.AsyncClient, method: str, params: list = None) -> Any:
    if not BLOCKPI_BASE_URL:
        raise ValueError("Missing BLOCKPI_BASE_URL")
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    resp = await client.post(
        BLOCKPI_BASE_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=25.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"BlockPI error: {data['error']}")
    return data.get("result")


async def nodereal_post(client: httpx.AsyncClient, method: str, params: list = None) -> Any:
    if not NODEREAL_BASE_URL:
        raise ValueError("Missing NODEREAL_BASE_URL")
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    resp = await client.post(
        NODEREAL_BASE_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=25.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"NodeReal error: {data['error']}")
    return data.get("result")


async def blockreq_post(client: httpx.AsyncClient, method: str, params: list = None) -> Any:
    if not BLOCKREQ_BASE_URL:
        raise ValueError("Missing BLOCKREQ_BASE_URL")
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    resp = await client.post(
        BLOCKREQ_BASE_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=25.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"BlockReq error: {data['error']}")
    return data.get("result")


async def fetch_coingecko_eth_price(client: httpx.AsyncClient) -> Optional[float]:
    if not COINGECKO_KEY:
        return None
    try:
        headers = {"x-cg-demo-api-key": COINGECKO_KEY} if COINGECKO_KEY else {}
        resp = await client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "ethereum", "vs_currencies": "usd"},
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("ethereum", {}).get("usd")
    except Exception as e:
        log(f"CoinGecko ETH price failed: {e}")
        return None


async def fetch_coingecko_prices(client: httpx.AsyncClient, ids: List[str]) -> Dict[str, float]:
    """Fetch USD prices for multiple CoinGecko IDs. Returns {id: price}."""
    if not COINGECKO_KEY or not ids:
        return {}
    try:
        headers = {"x-cg-demo-api-key": COINGECKO_KEY}
        ids_str = ",".join(ids)
        resp = await client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": ids_str, "vs_currencies": "usd"},
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return {k: v.get("usd") for k, v in data.items() if v and v.get("usd")}
    except Exception as e:
        log(f"CoinGecko batch price fetch failed: {e}")
        return {}


async def fetch_alchemy_block_data(client: httpx.AsyncClient) -> Dict[str, Any]:
    log("Fetching Alchemy Base block data")
    block_num_hex = await alchemy_post(client, {"method": "eth_blockNumber", "params": []})
    block_num = int(block_num_hex, 16)
    block = await alchemy_post(client, {
        "method": "eth_getBlockByNumber",
        "params": [block_num_hex, False]
    }) or {}
    fee_history = await alchemy_post(client, {
        "method": "eth_feeHistory",
        "params": [10, block_num_hex, [10, 50, 90]]
    }) or {}
    return {
        "block_number": block_num,
        "block_hash": block.get("hash"),
        "timestamp": block.get("timestamp"),
        "gas_used": block.get("gasUsed"),
        "gas_limit": block.get("gasLimit"),
        "base_fee_per_gas": block.get("baseFeePerGas"),
        "transactions_count": len(block.get("transactions", [])),
        "fee_history": fee_history,
    }


async def fetch_chainstack_block(client: httpx.AsyncClient) -> Dict[str, Any]:
    log("Fetching ChainStack Base block")
    try:
        block = await chainstack_post(client, "eth_getBlockByNumber", ["latest", False])
        return {
            "block_number": int(block.get("number", "0x0"), 16) if block else None,
            "block_hash": block.get("hash") if block else None,
            "timestamp": int(block.get("timestamp", "0x0"), 16) if block else None,
        }
    except Exception as e:
        log(f"ChainStack block fetch failed: {e}")
        return {}


async def fetch_blockpi_trace_block(client: httpx.AsyncClient, block_num_hex: str) -> Dict[str, Any]:
    log("Fetching BlockPI trace block")
    try:
        traces = await blockpi_post(client, "trace_block", [block_num_hex])
        if not isinstance(traces, list):
            return {"traces": [], "contracts_created": 0}
        log(f"BlockPI trace returned {len(traces)} traces")
        contracts_created = 0
        for trace in traces:
            if not isinstance(trace, dict):
                continue
            action = trace.get("action", {})
            if isinstance(action, dict):
                if action.get("type") in ["create", "CREATE"]:
                    contracts_created += 1
                if action.get("init") and not action.get("to"):
                    contracts_created += 1
            result = trace.get("result", {})
            if isinstance(result, dict) and result.get("address"):
                contracts_created += 1
        return {"traces": traces, "contracts_created": contracts_created}
    except Exception as e:
        log(f"BlockPI trace failed: {e}")
        return {"traces": [], "contracts_created": 0}


async def fetch_nodereal_block(client: httpx.AsyncClient) -> Dict[str, Any]:
    log("Fetching NodeReal Base block")
    try:
        block = await nodereal_post(client, "eth_getBlockByNumber", ["latest", True])
        txs = block.get("transactions", []) if isinstance(block, dict) else []
        contracts_created = 0
        for tx in txs:
            if isinstance(tx, dict) and not tx.get("to"):
                contracts_created += 1
        return {
            "block_number": int(block.get("number", "0x0"), 16) if block else None,
            "block_hash": block.get("hash") if block else None,
            "timestamp": int(block.get("timestamp", "0x0"), 16) if block else None,
            "transactions_count": len(txs),
            "contracts_created": contracts_created,
        }
    except Exception as e:
        log(f"NodeReal block fetch failed: {e}")
        return {}


BASE_BRIDGE_L1 = "0x49048044D57e1C92A77f79988d21Fa8fAF74E97e"
BASE_BRIDGE_L2 = "0x4200000000000000000000000000000000000010"
UNISWAP_V3_FACTORY = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
AERODROME_ROUTER = "0xcF77a3Ba9A73CA43934ef2c5aE8c60371E7f8c8A"

async def fetch_blockreq_bridge_logs(client: httpx.AsyncClient, from_block: str, to_block: str) -> Dict[str, Any]:
    log("Fetching BlockReq bridge logs")
    try:
        deposit_topic = "0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c"
        withdrawal_topic = "0x7fcf532c15f0a6db0bd6d0e038bea71d30d807c357da43f2b3a92d2173c50d0c"
        deposits = await blockreq_post(client, "eth_getLogs", [{
            "fromBlock": from_block,
            "toBlock": to_block,
            "address": BASE_BRIDGE_L2,
            "topics": [deposit_topic],
        }])
        withdrawals = await blockreq_post(client, "eth_getLogs", [{
            "fromBlock": from_block,
            "toBlock": to_block,
            "address": BASE_BRIDGE_L2,
            "topics": [withdrawal_topic],
        }])
        deposit_count = len(deposits) if isinstance(deposits, list) else 0
        withdrawal_count = len(withdrawals) if isinstance(withdrawals, list) else 0
        log(f"BlockReq bridge: {deposit_count} deposits, {withdrawal_count} withdrawals")
        return {
            "deposits": deposit_count,
            "withdrawals": withdrawal_count,
            "net_flow": deposit_count - withdrawal_count,
        }
    except Exception as e:
        log(f"BlockReq bridge logs failed: {e}")
        return {"deposits": 0, "withdrawals": 0, "net_flow": 0}


async def fetch_blockreq_dex_logs(client: httpx.AsyncClient, from_block: str, to_block: str) -> Dict[str, Any]:
    log("Fetching BlockReq DEX swap logs")
    try:
        swap_topic = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
        swaps = await blockreq_post(client, "eth_getLogs", [{
            "fromBlock": from_block,
            "toBlock": to_block,
            "topics": [swap_topic],
        }])
        swap_count = len(swaps) if isinstance(swaps, list) else 0
        log(f"BlockReq DEX: {swap_count} swap events")
        return {"swap_count": swap_count}
    except Exception as e:
        log(f"BlockReq DEX logs failed: {e}")
        return {"swap_count": 0}


async def fetch_alchemy_whales(client: httpx.AsyncClient, eth_price: float) -> List[BaseTransferSignal]:
    """
    Fetch whale transfers from Alchemy.
    Only tracks tokens with known prices. Skips unknown ERC-20s to avoid
    fake 'trillion dollar' values from meme coins with massive supply.
    """
    log("Fetching Alchemy Base whales")
    if not ALCHEMY_KEY:
        return []

    # Fetch wrapped token prices (WBTC, etc.) in one call
    cg_ids = [COINGECKO_IDS.get(t) for t in KNOWN_WRAPPED if COINGECKO_IDS.get(t)]
    cg_prices = await fetch_coingecko_prices(client, cg_ids)
    token_prices = {
        "ETH": eth_price,
        "WETH": eth_price,
        "BASE": eth_price,
    }
    for token, cg_id in COINGECKO_IDS.items():
        price = cg_prices.get(cg_id)
        if price:
            token_prices[token] = price

    latest_resp = await alchemy_post(client, {"method": "eth_blockNumber", "params": []})
    latest_num = int(latest_resp, 16)
    from_num = max(latest_num - 600, 0)
    payload = {
        "id": 1,
        "jsonrpc": "2.0",
        "method": "alchemy_getAssetTransfers",
        "params": [{
            "fromBlock": hex(from_num),
            "toBlock": latest_resp,
            "category": ["external", "erc20"],
            "withMetadata": True,
            "excludeZeroValue": True,
            "maxCount": "0x3E8",
            "order": "desc"
        }]
    }
    resp = await client.post(BASE_ALCHEMY_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=25.0)
    resp.raise_for_status()
    data = resp.json()
    transfers = data.get("result", {}).get("transfers", [])

    whale_data = []
    skipped_unknown = 0
    skipped_small = 0

    for tx in transfers:
        asset = str(tx.get("asset", "")).upper().strip() or "ETH"

        # ─── SKIP unknown tokens ─────────────────────────────────────────
        if asset not in TRACKED_TOKENS:
            skipped_unknown += 1
            continue

        amount = float(tx.get("value") or 0)

        # ─── Calculate USD value ─────────────────────────────────────────
        if asset in KNOWN_STABLES:
            usd_value = amount  # 1:1 peg assumption
        elif asset in KNOWN_NATIVE or asset in KNOWN_WRAPPED:
            token_price = token_prices.get(asset, eth_price)
            usd_value = amount * token_price
        else:
            # Shouldn't reach here, but safety fallback
            skipped_unknown += 1
            continue

        # ─── Whale threshold: $15,000 minimum ────────────────────────────
        if usd_value < 15000:
            skipped_small += 1
            continue

        whale_data.append(BaseTransferSignal(
            timestamp=str(tx.get("metadata", {}).get("blockTimestamp") or utc_now_str()),
            asset_symbol=asset,
            value_usd=round(usd_value, 2) if usd_value > 0 else None,
            from_address=str(tx.get("from", "Unknown")),
            to_address=str(tx.get("to", "Unknown")),
            tx_hash=str(tx.get("hash", "Unknown")),
            block_number=as_int(tx.get("blockNum")),
            transfer_type=str(tx.get("category", "external")).lower(),
        ))

    # Deduplicate
    seen = set()
    unique = []
    for w in sorted(whale_data, key=lambda x: x.value_usd or 0, reverse=True):
        key = (w.timestamp, w.asset_symbol, w.from_address, w.to_address, w.tx_hash)
        if key not in seen:
            seen.add(key)
            unique.append(w)

    log(f"Whales: {len(unique)} tracked, {skipped_unknown} unknown tokens skipped, {skipped_small} below threshold skipped")
    return unique[:60]


def normalize_rpc_snapshot(alchemy_data: Dict[str, Any], chainstack_data: Dict[str, Any], nodereal_data: Dict[str, Any]) -> BaseRpcSnapshot:
    block_num = alchemy_data.get("block_number") or chainstack_data.get("block_number") or nodereal_data.get("block_number")
    block_hash = alchemy_data.get("block_hash") or chainstack_data.get("block_hash") or nodereal_data.get("block_hash")
    timestamp = alchemy_data.get("timestamp")
    if timestamp is None:
        timestamp = chainstack_data.get("timestamp") or nodereal_data.get("timestamp")
    tx_count = alchemy_data.get("transactions_count", 0) or nodereal_data.get("transactions_count", 0)
    tps = None
    if timestamp and tx_count:
        tps = tx_count / 2.0
    base_fee_gwei = None
    base_fee_hex = alchemy_data.get("base_fee_per_gas")
    if base_fee_hex:
        try:
            base_fee_wei = int(base_fee_hex, 16) if isinstance(base_fee_hex, str) else int(base_fee_hex)
            base_fee_gwei = base_fee_wei / 1e9
        except Exception:
            pass
    return BaseRpcSnapshot(
        captured_at=utc_now_str(),
        latest_block_number=as_int(block_num) or 0,
        latest_block_hash=block_hash or "-",
        latest_block_timestamp=as_int(timestamp),
        avg_block_time_seconds=2.0,
        tps_1min=tps,
        gas_used_total=as_int(alchemy_data.get("gas_used")),
        base_fee_gwei=base_fee_gwei,
    )


def normalize_chain_activity(alchemy_data: Dict[str, Any], nodereal_data: Dict[str, Any], eth_price: float) -> BaseChainActivity:
    tx_count = alchemy_data.get("transactions_count", 0) or nodereal_data.get("transactions_count", 0)
    gas_used = as_int(alchemy_data.get("gas_used")) or 0
    base_fee = alchemy_data.get("base_fee_per_gas")
    fees_eth = 0.0
    if base_fee and gas_used:
        try:
            base_fee_wei = int(base_fee, 16) if isinstance(base_fee, str) else int(base_fee)
            fees_eth = (gas_used * base_fee_wei) / 1e18
        except Exception:
            pass
    fees_usd = fees_eth * eth_price if eth_price else 0.0
    score = math.log10(max(tx_count, 1)) * 60 + math.log10(max(fees_usd, 1)) * 40
    alert = "high" if score >= 400 else "medium" if score >= 200 else "low"
    return BaseChainActivity(
        date=datetime.now(UTC).strftime("%Y-%m-%d"),
        chain_name="base",
        tx_count=tx_count,
        tps=round((tx_count / 2.0), 3) if tx_count else 0.0,
        total_fees_eth=round(fees_eth, 6),
        total_fees_usd=round(fees_usd, 2),
        activity_score=round(score, 2),
        alert_level=alert,
    )


def normalize_ecosystem_metrics(eth_price: Optional[float], total_whale_usd: float) -> BaseEcosystemMetrics:
    return BaseEcosystemMetrics(
        snapshot_date=datetime.now(UTC).strftime("%Y-%m-%d"),
        eth_price_usd=eth_price,
        tvl_proxy=total_whale_usd * 100 if total_whale_usd > 0 else None,
        stablecoin_proxy=None,
    )


def build_derived_signals(
    rpc: BaseRpcSnapshot,
    activity: BaseChainActivity,
    ecosystem: BaseEcosystemMetrics,
    transfers: List[BaseTransferSignal],
    nodereal_data: Dict[str, Any],
    contracts_from_traces: int,
    bridge_data: Dict[str, Any],
    dex_data: Dict[str, Any],
) -> List[BaseDerivedSignal]:
    out: List[BaseDerivedSignal] = []
    if rpc.tps_1min and rpc.tps_1min > 15:
        out.append(BaseDerivedSignal(
            signal_date=activity.date,
            signal_family="sequencer",
            signal_key=f"base:tps:{activity.date}",
            severity="medium" if rpc.tps_1min < 30 else "high",
            score=min(100, int(rpc.tps_1min * 3)),
            title="Base sequencer throughput spike",
            description=f"Base processed {rpc.tps_1min:.1f} TPS in recent blocks.",
            metric_value_1=rpc.tps_1min,
            metric_value_2=rpc.avg_block_time_seconds,
            metric_value_3=rpc.gas_used_total,
            reference_id=f"base:{rpc.latest_block_number}",
        ))
    if rpc.base_fee_gwei and rpc.base_fee_gwei > 0.1:
        out.append(BaseDerivedSignal(
            signal_date=activity.date,
            signal_family="fee_pressure",
            signal_key=f"base:gas:{activity.date}",
            severity="low" if rpc.base_fee_gwei < 0.5 else "medium",
            score=min(100, int(rpc.base_fee_gwei * 100)),
            title="Base gas fee elevation",
            description=f"Base fee at {rpc.base_fee_gwei:.4f} gwei indicates network demand shift.",
            metric_value_1=rpc.base_fee_gwei,
            metric_value_2=activity.total_fees_eth,
            metric_value_3=activity.total_fees_usd,
            reference_id=f"base:{rpc.latest_block_number}",
        ))
    total_whale_usd = sum(t.value_usd or 0 for t in transfers)
    if total_whale_usd > 1_000_000:
        out.append(BaseDerivedSignal(
            signal_date=activity.date,
            signal_family="whale_flow",
            signal_key=f"base:whales:{activity.date}",
            severity="medium" if total_whale_usd < 10_000_000 else "high",
            score=min(100, int(total_whale_usd / 100_000)),
            title="Base whale flow detected",
            description=f"${total_whale_usd/1e6:.2f}M in large transfers on Base.",
            metric_value_1=total_whale_usd,
            metric_value_2=float(len(transfers)),
            metric_value_3=None,
            reference_id=f"base:{activity.date}",
        ))
    if activity.tx_count > 5000:
        out.append(BaseDerivedSignal(
            signal_date=activity.date,
            signal_family="activity",
            signal_key=f"base:activity:{activity.date}",
            severity="low" if activity.tx_count < 15000 else "medium",
            score=min(100, int(activity.tx_count / 200)),
            title="Base network activity surge",
            description=f"{activity.tx_count} transactions in recent observation window.",
            metric_value_1=float(activity.tx_count),
            metric_value_2=activity.tps,
            metric_value_3=activity.total_fees_usd,
            reference_id=f"base:{activity.date}",
        ))
    contracts_created = nodereal_data.get("contracts_created", 0) if isinstance(nodereal_data, dict) else 0
    if contracts_created >= 0:
        out.append(BaseDerivedSignal(
            signal_date=activity.date,
            signal_family="builder_velocity",
            signal_key=f"base:contracts:{activity.date}",
            severity="low" if contracts_created < 3 else "medium" if contracts_created < 10 else "high",
            score=min(100, max(contracts_created * 10, 1)),
            title="Base builder velocity signal",
            description=f"{contracts_created} new contracts created in latest block (NodeReal + BlockPI traces).",
            metric_value_1=float(contracts_created),
            metric_value_2=float(activity.tx_count),
            metric_value_3=None,
            reference_id=f"base:{rpc.latest_block_number}",
        ))
    bridge_net = bridge_data.get("net_flow", 0) if isinstance(bridge_data, dict) else 0
    swap_count = dex_data.get("swap_count", 0) if isinstance(dex_data, dict) else 0
    if bridge_net != 0:
        out.append(BaseDerivedSignal(
            signal_date=activity.date,
            signal_family="bridge_flow",
            signal_key=f"base:bridge:{activity.date}",
            severity="medium" if abs(bridge_net) < 50 else "high",
            score=min(100, abs(bridge_net)),
            title="Base bridge flow detected",
            description=f"Bridge net flow: {bridge_net:+d} (deposits - withdrawals) in last 100 blocks.",
            metric_value_1=float(bridge_net),
            metric_value_2=float(bridge_data.get("deposits", 0)) if isinstance(bridge_data, dict) else 0,
            metric_value_3=float(bridge_data.get("withdrawals", 0)) if isinstance(bridge_data, dict) else 0,
            reference_id=f"base:{rpc.latest_block_number}",
        ))
    if swap_count > 0:
        out.append(BaseDerivedSignal(
            signal_date=activity.date,
            signal_family="dex_activity",
            signal_key=f"base:dex:{activity.date}",
            severity="low" if swap_count < 100 else "medium" if swap_count < 500 else "high",
            score=min(100, swap_count // 10),
            title="Base DEX activity detected",
            description=f"{swap_count} swap events detected in last 100 blocks via BlockReq.",
            metric_value_1=float(swap_count),
            metric_value_2=None,
            metric_value_3=None,
            reference_id=f"base:{rpc.latest_block_number}",
        ))
    severity_rank = {"high": 3, "medium": 2, "low": 1}
    out.sort(key=lambda x: (severity_rank.get(x.severity, 0), x.score), reverse=True)
    return out[:MAX_DERIVED_SIGNALS]


def replace_table(cursor, table_name: str):
    cursor.execute(f"DELETE FROM {table_name}")


def insert_many(cursor, sql: str, rows: List[Any]):
    if rows:
        cursor.executemany(sql, rows)


def write_to_oracle(
    rpc: BaseRpcSnapshot,
    activity: BaseChainActivity,
    ecosystem: BaseEcosystemMetrics,
    transfers: List[BaseTransferSignal],
    derived: List[BaseDerivedSignal],
):
    log("Writing Base data to Oracle")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        replace_table(cursor, "BASE_RPC_SNAPSHOT")
        cursor.execute("""
            INSERT INTO BASE_RPC_SNAPSHOT (
                CAPTURED_AT, LATEST_BLOCK_NUMBER, LATEST_BLOCK_HASH,
                LATEST_BLOCK_TIMESTAMP, AVG_BLOCK_TIME_SECONDS, TPS_1MIN,
                GAS_USED_TOTAL, BASE_FEE_GWEI
            ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8)
        """, (
            parse_timestamp(rpc.captured_at),
            as_int(rpc.latest_block_number),
            rpc.latest_block_hash,
            as_int(rpc.latest_block_timestamp),
            as_float(rpc.avg_block_time_seconds),
            as_float(rpc.tps_1min),
            as_int(rpc.gas_used_total),
            as_float(rpc.base_fee_gwei),
        ))
        replace_table(cursor, "BASE_CHAIN_ACTIVITY_DAILY")
        cursor.execute("""
            INSERT INTO BASE_CHAIN_ACTIVITY_DAILY (
                ACTIVITY_DATE, CHAIN_NAME, TX_COUNT, TPS,
                TOTAL_FEES_ETH, TOTAL_FEES_USD, ACTIVITY_SCORE, ALERT_LEVEL
            ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8)
        """, (
            parse_date(activity.date),
            activity.chain_name,
            as_int(activity.tx_count),
            as_float(activity.tps),
            as_float(activity.total_fees_eth),
            as_float(activity.total_fees_usd),
            as_float(activity.activity_score),
            activity.alert_level,
        ))
        replace_table(cursor, "BASE_ECOSYSTEM_DAILY")
        cursor.execute("""
            INSERT INTO BASE_ECOSYSTEM_DAILY (
                SNAPSHOT_DATE, ETH_PRICE_USD, TVL_PROXY, STABLECOIN_PROXY
            ) VALUES (:1, :2, :3, :4)
        """, (
            parse_date(ecosystem.snapshot_date),
            as_float(ecosystem.eth_price_usd),
            as_float(ecosystem.tvl_proxy),
            as_float(ecosystem.stablecoin_proxy),
        ))
        replace_table(cursor, "BASE_TRANSFER_SIGNALS")
        insert_many(cursor, """
            INSERT INTO BASE_TRANSFER_SIGNALS (
                TIMESTAMP, ASSET_SYMBOL, VALUE_USD, FROM_ADDRESS,
                TO_ADDRESS, TX_HASH, BLOCK_NUMBER, TRANSFER_TYPE
            ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8)
        """, [
            (
                parse_timestamp(t.timestamp),
                t.asset_symbol,
                as_float(t.value_usd),
                t.from_address,
                t.to_address,
                t.tx_hash,
                as_int(t.block_number),
                t.transfer_type,
            )
            for t in transfers
        ])
        replace_table(cursor, "BASE_DERIVED_SIGNALS")
        insert_many(cursor, """
            INSERT INTO BASE_DERIVED_SIGNALS (
                SIGNAL_DATE, SIGNAL_FAMILY, SIGNAL_KEY, SEVERITY,
                SCORE, TITLE, DESCRIPTION, METRIC_VALUE_1,
                METRIC_VALUE_2, METRIC_VALUE_3, REFERENCE_ID
            ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11)
        """, [
            (
                parse_date(d.signal_date),
                d.signal_family,
                d.signal_key,
                d.severity,
                as_int(d.score),
                d.title,
                d.description,
                as_float(d.metric_value_1),
                as_float(d.metric_value_2),
                as_float(d.metric_value_3),
                d.reference_id,
            )
            for d in derived
        ])
        conn.commit()
        log("Oracle write complete")
    except Exception as e:
        conn.rollback()
        log(f"Oracle write failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


async def main():
    log("Base collector starting")
    log(f"Alchemy configured: {bool(ALCHEMY_KEY)}")
    log(f"ChainStack configured: {bool(CHAINSTACK_BASE_URL)}")
    log(f"BlockPI configured: {bool(BLOCKPI_BASE_URL)}")
    log(f"NodeReal configured: {bool(NODEREAL_BASE_URL)}")
    log(f"BlockReq configured: {bool(BLOCKREQ_BASE_URL)}")
    log(f"CoinGecko configured: {bool(COINGECKO_KEY)}")

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(30.0, connect=15.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        eth_price = await fetch_coingecko_eth_price(client)
        if not eth_price:
            eth_price = 3500.0
            log(f"Using fallback ETH price: {eth_price}")
        else:
            log(f"ETH price: ${eth_price}")

        alchemy_task = fetch_alchemy_block_data(client)
        chainstack_task = fetch_chainstack_block(client)
        nodereal_task = fetch_nodereal_block(client)
        alchemy_data, chainstack_data, nodereal_data = await asyncio.gather(
            alchemy_task, chainstack_task, nodereal_task, return_exceptions=True,
        )

        for name, data in [("alchemy", alchemy_data), ("chainstack", chainstack_data), ("nodereal", nodereal_data)]:
            if isinstance(data, Exception):
                log(f"{name} fetch failed: {data}")
                if name == "alchemy":
                    alchemy_data = {}
                elif name == "chainstack":
                    chainstack_data = {}
                elif name == "nodereal":
                    nodereal_data = {}

        block_num_hex = hex(alchemy_data.get("block_number", 0)) if alchemy_data.get("block_number") else "latest"
        blockpi_task = fetch_blockpi_trace_block(client, block_num_hex)
        blockpi_data = await blockpi_task
        if isinstance(blockpi_data, Exception):
            log(f"BlockPI traces failed: {blockpi_data}")
            blockpi_data = {"traces": [], "contracts_created": 0}
        blockpi_traces = blockpi_data.get("traces", []) if isinstance(blockpi_data, dict) else []
        contracts_from_traces = blockpi_data.get("contracts_created", 0) if isinstance(blockpi_data, dict) else 0
        log(f"BlockPI detected {contracts_from_traces} contract creations")

        transfers = await fetch_alchemy_whales(client, eth_price)
        from_block = hex(max(alchemy_data.get("block_number", 0) - 100, 0))
        to_block = "latest"
        bridge_task = fetch_blockreq_bridge_logs(client, from_block, to_block)
        dex_task = fetch_blockreq_dex_logs(client, from_block, to_block)
        bridge_data, dex_data = await asyncio.gather(
            bridge_task, dex_task, return_exceptions=True,
        )
        if isinstance(bridge_data, Exception):
            log(f"BlockReq bridge failed: {bridge_data}")
            bridge_data = {"deposits": 0, "withdrawals": 0, "net_flow": 0}
        if isinstance(dex_data, Exception):
            log(f"BlockReq DEX failed: {dex_data}")
            dex_data = {"swap_count": 0}
        log(f"Bridge net flow: {bridge_data.get('net_flow', 0)}, DEX swaps: {dex_data.get('swap_count', 0)}")
        rpc = normalize_rpc_snapshot(alchemy_data, chainstack_data, nodereal_data)
        activity = normalize_chain_activity(alchemy_data, nodereal_data, eth_price)
        ecosystem = normalize_ecosystem_metrics(eth_price, sum(t.value_usd or 0 for t in transfers))
        derived = build_derived_signals(rpc, activity, ecosystem, transfers, nodereal_data, contracts_from_traces, bridge_data, dex_data)
        write_to_oracle(rpc, activity, ecosystem, transfers, derived)

        log(f"Base block: {rpc.latest_block_number}")
        log(f"Base TPS: {rpc.tps_1min}")
        log(f"Base whales: {len(transfers)}")
        log(f"Base derived signals: {len(derived)}")

    log("Base collector finished")


if __name__ == "__main__":
    asyncio.run(main())
