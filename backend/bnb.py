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

# ─── ENV ──────────────────────────────────────────────────────────────────────
DWELLIR_BSC_URL = os.getenv("DWELLIR_BSC_URL")
ANKR_BSC_URL = os.getenv("ANKR_BSC_URL")
INFURA_BSC_URL = os.getenv("INFURA_BSC_URL")
GETBLOCK_BSC_URL = os.getenv("GETBLOCK_BSC_URL")
BLOCKPI_BSC_URL = os.getenv("BLOCKPI_BSC_URL")
ALCHEMY_BSC_URL = os.getenv("ALCHEMY_BSC_URL")
CMC_API_KEY = os.getenv("CMC_API_KEY")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN", "asyncsignalsdatabase_medium")
WALLET_DIR = os.getenv("WALLET_DIR", "/home/daniel/wallet")

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
TS_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_DERIVED_SIGNALS = 40
WHALE_THRESHOLD_USD = 25_000
BSC_BLOCK_TIME = 3.0

# BSC token contracts (BEP-20) — ONLY these are tracked
BSC_TOKENS = {
    "USDT": "0x55d398326f99059fF775485246999027B3197955",
    "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
    "FDUSD": "0xc5f0f7b66764F6ec8C8Dff7bD68340bD14e8f3bE",
}

# ─── Token pricing whitelist ────────────────────────────────────────────────
# Only tokens we can reliably price. Everything else is skipped.
KNOWN_NATIVE = {"BNB", "WBNB"}
KNOWN_STABLES = {"USDT", "USDC", "FDUSD", "BUSD", "DAI", "USDE", "PYUSD", "USDZ"}
KNOWN_WRAPPED = {"BTC", "WBTC", "ETH", "WETH"}
TRACKED_TOKENS = KNOWN_NATIVE | KNOWN_STABLES | KNOWN_WRAPPED

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

PCS_V2_PAIRS = [
    "0x0eD7e52944161450477ee417DE9Cd3a859b14fD0",
    "0x16b9a82891338f9bA80E2D6970FcdA1b8D67a9DD",
    "0xF45cd219aEF1F10796bF33aAae9f0BdC2848e5bb",
    "0x74E4716E431f45807BD19F907DD71d9b49E5C0E5",
    "0x61EB789d75A95CAa3fF50ed7E47b96c132fE08d3",
]
GET_RESERVES_SELECTOR = "0x0902f1ac"

GECKOTERMINAL_BASE_URL = "https://api.geckoterminal.com/api/v2"

# ─── UTILS ────────────────────────────────────────────────────────────────────
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


def decode_log_value(hex_str: str) -> int:
    try:
        return int(hex_str, 16) if hex_str else 0
    except Exception:
        return 0


# ─── DATACLASSES ───────────────────────────────────────────────────────────────
@dataclass
class BnbRpcSnapshot:
    captured_at: str
    latest_block_number: int
    latest_block_hash: str
    latest_block_timestamp: Optional[int]
    avg_block_time_seconds: Optional[float]
    tps_1min: Optional[float]
    gas_used_total: Optional[int]
    gas_price_gwei: Optional[float]
    tx_count: Optional[int]
    validator_address: Optional[str]


@dataclass
class BnbWhaleEvent:
    timestamp: str
    asset_symbol: str
    token_contract: Optional[str]
    value_raw: Optional[float]
    value_usd: Optional[float]
    from_address: str
    to_address: str
    tx_hash: str
    block_number: Optional[int]
    transfer_type: str


@dataclass
class BnbDexPool:
    snapshot_date: str
    pool_id: str
    token0_symbol: str
    token1_symbol: str
    token0_contract: str
    token1_contract: str
    tvl_usd: Optional[float]
    volume_24h_usd: Optional[float]
    tx_count_24h: Optional[int]
    token0_price: Optional[float]
    token1_price: Optional[float]
    price_change_24h: Optional[float]


@dataclass
class BnbYieldRiskScore:
    score_date: str
    pool_id: str
    pool_name: str
    risk_score: int
    risk_flag: str
    explanation: str
    tvl_change_24h: Optional[float]
    whale_net_flow: Optional[float]
    volatility_flag: Optional[float]
    computed_at: str


@dataclass
class BnbValidatorSnapshot:
    captured_at: str
    block_number: int
    validator_address: str
    validator_name: Optional[str]
    missed_blocks_count: Optional[int]
    staking_apr: Optional[float]
    is_active: int


@dataclass
class BnbGasForecast:
    forecast_at: str
    current_gas_price_gwei: Optional[float]
    avg_gas_50_blocks: Optional[float]
    std_dev_gas: Optional[float]
    forecast_1h_gwei: Optional[float]
    congestion_level: str


@dataclass
class BnbDerivedSignal:
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


# ─── RPC HELPERS ───────────────────────────────────────────────────────────────
async def dwellir_post(client: httpx.AsyncClient, method: str, params: list = None) -> Any:
    if not DWELLIR_BSC_URL:
        raise ValueError("Missing DWELLIR_BSC_URL")
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    resp = await client.post(
        DWELLIR_BSC_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=25.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Dwellir RPC error: {data['error']}")
    return data.get("result")


async def rpc_post_with_fallback(client: httpx.AsyncClient, method: str, params: list = None) -> Any:
    try:
        return await dwellir_post(client, method, params)
    except Exception as e:
        if "403" in str(e) or "Forbidden" in str(e):
            log(f"Dwellir blocked {method}, trying Ankr fallback")
        else:
            log(f"Dwellir {method} failed: {e}, trying Ankr")
    if ANKR_BSC_URL:
        try:
            log(f"Trying Ankr for {method}")
            return await generic_rpc_post(client, ANKR_BSC_URL, method, params)
        except Exception as e:
            log(f"Ankr {method} failed: {e}")
    if INFURA_BSC_URL:
        try:
            log(f"Trying Infura for {method}")
            return await generic_rpc_post(client, INFURA_BSC_URL, method, params)
        except Exception as e:
            log(f"Infura {method} failed: {e}")
    if BLOCKPI_BSC_URL:
        try:
            log(f"Trying BlockPi for {method}")
            return await generic_rpc_post(client, BLOCKPI_BSC_URL, method, params)
        except Exception as e:
            log(f"BlockPi {method} failed: {e}")
    if GETBLOCK_BSC_URL:
        try:
            log(f"Trying Getblock for {method}")
            return await generic_rpc_post(client, GETBLOCK_BSC_URL, method, params)
        except Exception as e:
            log(f"Getblock {method} failed: {e}")
    raise RuntimeError(f"All RPC providers failed for {method}")


async def generic_rpc_post(client: httpx.AsyncClient, url: str, method: str, params: list = None) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    resp = await client.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=25.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"RPC error: {data['error']}")
    return data.get("result")


async def alchemy_bsc_post(client: httpx.AsyncClient, payload: Dict[str, Any]) -> Any:
    if not ALCHEMY_BSC_URL:
        raise ValueError("Missing ALCHEMY_BSC_URL")
    resp = await client.post(
        ALCHEMY_BSC_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=25.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Alchemy BSC error: {data['error']}")
    return data.get("result")


# ─── ALCHEMY BSC WHALES (PATCHED) ─────────────────────────────────────────────
async def fetch_alchemy_bsc_whales(client: httpx.AsyncClient, bnb_price: float) -> List[BnbWhaleEvent]:
    """
    Fetch whale transfers from Alchemy BSC.
    Only tracks tokens with known prices. Skips unknown BEP-20s.
    """
    log("Fetching Alchemy BSC whales")
    if not ALCHEMY_BSC_URL:
        return []

    latest_resp = await alchemy_bsc_post(client, {"method": "eth_blockNumber", "params": []})
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
    resp = await client.post(ALCHEMY_BSC_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=25.0)
    resp.raise_for_status()
    data = resp.json()
    transfers = data.get("result", {}).get("transfers", [])

    whale_data = []
    skipped_unknown = 0
    skipped_small = 0

    for tx in transfers:
        asset = str(tx.get("asset", "")).upper().strip() or "BNB"

        # ─── SKIP unknown tokens ─────────────────────────────────────────
        if asset not in TRACKED_TOKENS:
            skipped_unknown += 1
            continue

        amount = float(tx.get("value") or 0)

        # ─── Calculate USD value ─────────────────────────────────────────
        if asset in KNOWN_STABLES:
            usd_value = amount
        elif asset in KNOWN_NATIVE:
            usd_value = amount * bnb_price
        elif asset in KNOWN_WRAPPED:
            usd_value = amount * bnb_price  # rough proxy
        else:
            skipped_unknown += 1
            continue

        # ─── Whale threshold: $25,000 minimum ───────────────────────────
        if usd_value < WHALE_THRESHOLD_USD:
            skipped_small += 1
            continue

        whale_data.append(BnbWhaleEvent(
            timestamp=str(tx.get("metadata", {}).get("blockTimestamp") or utc_now_str()),
            asset_symbol=asset,
            token_contract=None,
            value_raw=amount,
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

    log(f"Alchemy BSC whales: {len(unique)} tracked, {skipped_unknown} unknown skipped, {skipped_small} below threshold")
    return unique[:60]


# ─── CMC BNB PRICE ───────────────────────────────────────────────────────────
async def fetch_cmc_bnb_price(client: httpx.AsyncClient) -> Optional[float]:
    if not CMC_API_KEY:
        return None
    try:
        resp = await client.get(
            "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest",
            params={"symbol": "BNB", "convert": "USD"},
            headers={"X-CMC_PRO_API_KEY": CMC_API_KEY},
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("BNB", {}).get("quote", {}).get("USD", {}).get("price")
    except Exception as e:
        log(f"CMC BNB price failed: {e}")
        return None


# ─── FETCH: BLOCK DATA ─────────────────────────────────────────────────────────
async def fetch_dwellir_block_data(client: httpx.AsyncClient) -> Dict[str, Any]:
    log("Fetching Dwellir BSC block data")
    block_num_hex = await rpc_post_with_fallback(client, "eth_blockNumber", [])
    block_num = int(block_num_hex, 16)
    block = await rpc_post_with_fallback(client, "eth_getBlockByNumber", [block_num_hex, False]) or {}
    fee_history = await rpc_post_with_fallback(client, "eth_feeHistory", [10, block_num_hex, [10, 50, 90]]) or {}
    return {
        "block_number": block_num,
        "block_hash": block.get("hash"),
        "timestamp": block.get("timestamp"),
        "gas_used": block.get("gasUsed"),
        "gas_limit": block.get("gasLimit"),
        "gas_price": block.get("gasPrice"),
        "base_fee_per_gas": block.get("baseFeePerGas"),
        "transactions_count": len(block.get("transactions", [])),
        "miner": block.get("miner"),
        "fee_history": fee_history,
    }


async def fetch_drpc_block(client: httpx.AsyncClient) -> Dict[str, Any]:
    log("dRPC removed, using fallback block fetch")
    try:
        block = await rpc_post_with_fallback(client, "eth_getBlockByNumber", ["latest", False])
        return {
            "block_number": int(block.get("number", "0x0"), 16) if block else None,
            "block_hash": block.get("hash") if block else None,
            "timestamp": int(block.get("timestamp", "0x0"), 16) if block else None,
            "miner": block.get("miner") if block else None,
        }
    except Exception as e:
        log(f"Fallback block fetch failed: {e}")
        return {}


# ─── FETCH: TOKEN TRANSFERS (RPC LOGS) ─────────────────────────────────────────
async def fetch_token_transfer_logs(
    client: httpx.AsyncClient,
    token_address: str,
    from_block: str,
    to_block: str,
) -> List[Dict[str, Any]]:
    log(f"Fetching transfer logs for {token_address}")
    try:
        logs = await rpc_post_with_fallback(client, "eth_getLogs", [{
            "fromBlock": from_block,
            "toBlock": to_block,
            "address": token_address,
            "topics": [TRANSFER_TOPIC],
        }])
        if not isinstance(logs, list):
            return []
        return logs
    except Exception as e:
        log(f"Token log fetch failed for {token_address}: {e}")
        return []


# ─── FETCH: BNB NATIVE WHALES ──────────────────────────────────────────────────
async def fetch_bnb_native_whales(
    client: httpx.AsyncClient, from_block: int, to_block: int, bnb_price: float
) -> List[BnbWhaleEvent]:
    log("Fetching BNB native whale transactions")
    whales = []
    threshold_wei = int((WHALE_THRESHOLD_USD / max(bnb_price, 1.0)) * 1e18)
    for block_num in range(from_block, to_block + 1):
        try:
            block = await rpc_post_with_fallback(client, "eth_getBlockByNumber", [hex(block_num), True])
            if not block:
                continue
            txs = block.get("transactions", [])
            ts = int(block.get("timestamp", "0x0"), 16) if block.get("timestamp") else 0
            dt = datetime.fromtimestamp(ts, UTC).strftime(TS_FORMAT) if ts else utc_now_str()
            for tx in txs:
                if not isinstance(tx, dict):
                    continue
                val = int(tx.get("value", "0x0"), 16) if isinstance(tx.get("value"), str) else 0
                if val >= threshold_wei:
                    usd = (val / 1e18) * bnb_price
                    whales.append(BnbWhaleEvent(
                        timestamp=dt,
                        asset_symbol="BNB",
                        token_contract=None,
                        value_raw=val / 1e18,
                        value_usd=round(usd, 2),
                        from_address=str(tx.get("from", "Unknown")),
                        to_address=str(tx.get("to", "Unknown")),
                        tx_hash=str(tx.get("hash", "Unknown")),
                        block_number=block_num,
                        transfer_type="native",
                    ))
        except Exception as e:
            log(f"BNB whale scan block {block_num} failed: {e}")
            continue
    return whales


# ─── FETCH: PANCAKESWAP POOLS ──────────────────────────────────────────────────
async def fetch_pools_via_rpc(client: httpx.AsyncClient) -> List[BnbDexPool]:
    """Fallback: call getReserves() on known PancakeSwap v2 pairs via RPC."""
    log("Fetching pools via RPC getReserves fallback")
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    out = []
    for pair_addr in PCS_V2_PAIRS:
        try:
            result = await rpc_post_with_fallback(client, "eth_call", [{
                "to": pair_addr,
                "data": GET_RESERVES_SELECTOR,
            }, "latest"])
            if not result or result == "0x":
                continue
            raw = result[2:] if result.startswith("0x") else result
            if len(raw) < 64:
                continue
            reserve0 = int(raw[0:64], 16) / 1e18
            reserve1 = int(raw[64:128], 16) / 1e18
            tvl_proxy = (reserve0 + reserve1) * 1.0
            out.append(BnbDexPool(
                snapshot_date=today,
                pool_id=pair_addr,
                token0_symbol="?",
                token1_symbol="?",
                token0_contract="",
                token1_contract="",
                tvl_usd=tvl_proxy,
                volume_24h_usd=None,
                tx_count_24h=None,
                token0_price=None,
                token1_price=None,
                price_change_24h=None,
            ))
        except Exception as e:
            log(f"RPC pool fallback {pair_addr} failed: {e}")
            continue
    return out


async def geckoterminal_get_pools(client: httpx.AsyncClient) -> Any:
    url = f"{GECKOTERMINAL_BASE_URL}/networks/bsc/pools"
    params = {
        "include": "base_token,quote_token",
        "order": "h24_volume_usd_desc",
        "page": "1",
    }
    headers = {
        "Accept": "application/json;version=20230203",
    }
    await asyncio.sleep(0.5)
    resp = await client.get(url, params=params, headers=headers, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


async def fetch_pancakeswap_pools(client: httpx.AsyncClient) -> List[BnbDexPool]:
    log("Fetching BSC pools via GeckoTerminal")
    for attempt in range(3):
        try:
            data = await geckoterminal_get_pools(client)
            pools = data.get("data", [])
            included = {item.get("id"): item for item in data.get("included", [])}
            today = datetime.now(UTC).strftime("%Y-%m-%d")
            out = []

            for p in pools:
                attrs = p.get("attributes", {}) or {}
                rels = p.get("relationships", {}) or {}

                base_token_id = rels.get("base_token", {}).get("data", {}).get("id")
                quote_token_id = rels.get("quote_token", {}).get("data", {}).get("id")
                base_token = included.get(base_token_id, {}).get("attributes", {}) or {}
                quote_token = included.get(quote_token_id, {}).get("attributes", {}) or {}

                pool_id = attrs.get("address", "")
                volume = attrs.get("volume_usd", {}) or {}
                txns = attrs.get("transactions", {}) or {}
                price_change = attrs.get("price_change_percentage", {}) or {}

                h24_txns = txns.get("h24", {}) or {}
                tx_count = (h24_txns.get("buys", 0) or 0) + (h24_txns.get("sells", 0) or 0)

                out.append(BnbDexPool(
                    snapshot_date=today,
                    pool_id=pool_id,
                    token0_symbol=base_token.get("symbol", "?"),
                    token1_symbol=quote_token.get("symbol", "?"),
                    token0_contract=base_token.get("address", ""),
                    token1_contract=quote_token.get("address", ""),
                    tvl_usd=as_float(attrs.get("reserve_in_usd")),
                    volume_24h_usd=as_float(volume.get("h24")),
                    tx_count_24h=tx_count,
                    token0_price=as_float(attrs.get("base_token_price_usd")),
                    token1_price=as_float(attrs.get("quote_token_price_usd")),
                    price_change_24h=as_float(price_change.get("h24")),
                ))
            return out
        except Exception as e:
            log(f"GeckoTerminal pool fetch attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
    return await fetch_pools_via_rpc(client)


# ─── FETCH: VALIDATOR DATA ─────────────────────────────────────────────────────
async def fetch_validator_data(client: httpx.AsyncClient, latest_block: int) -> List[BnbValidatorSnapshot]:
    log("Fetching BSC validator data")
    validators: Dict[str, Dict] = {}
    sample_size = min(200, latest_block)
    from_block = max(latest_block - sample_size, 0)
    for block_num in range(from_block, latest_block + 1):
        try:
            block = await rpc_post_with_fallback(client, "eth_getBlockByNumber", [hex(block_num), False])
            if not block:
                continue
            miner = block.get("miner")
            if not miner:
                continue
            if miner not in validators:
                validators[miner] = {"count": 0, "name": None}
            validators[miner]["count"] += 1
        except Exception as e:
            log(f"Validator scan block {block_num} failed: {e}")
            continue

    expected_per_validator = sample_size / max(len(validators), 1)
    out = []
    for addr, info in validators.items():
        missed = max(0, int(expected_per_validator - info["count"]))
        out.append(BnbValidatorSnapshot(
            captured_at=utc_now_str(),
            block_number=latest_block,
            validator_address=addr,
            validator_name=info["name"],
            missed_blocks_count=missed,
            staking_apr=None,
            is_active=1 if info["count"] > 0 else 0,
        ))
    return out


# ─── FETCH: GAS HISTORY ────────────────────────────────────────────────────────
async def fetch_gas_history(client: httpx.AsyncClient, latest_block: int) -> BnbGasForecast:
    log("Fetching BSC gas history")
    prices = []
    sample = min(50, latest_block)
    for i in range(sample):
        try:
            block = await rpc_post_with_fallback(client, "eth_getBlockByNumber", [hex(latest_block - i), False])
            if not block:
                continue
            gp = block.get("gasPrice")
            if gp:
                gwei = int(gp, 16) / 1e9 if isinstance(gp, str) else gp / 1e9
                prices.append(gwei)
        except Exception:
            continue

    if not prices:
        try:
            gp = await rpc_post_with_fallback(client, "eth_gasPrice", [])
            prices = [int(gp, 16) / 1e9 if isinstance(gp, str) else gp / 1e9]
        except Exception:
            prices = [5.0]

    avg = sum(prices) / len(prices) if prices else 5.0
    std = math.sqrt(sum((p - avg) ** 2 for p in prices) / len(prices)) if prices else 0.0
    forecast = avg + (prices[0] - prices[-1]) if len(prices) > 1 else avg

    congestion = "low"
    if forecast > 10:
        congestion = "medium"
    if forecast > 20:
        congestion = "high"

    return BnbGasForecast(
        forecast_at=utc_now_str(),
        current_gas_price_gwei=prices[0] if prices else avg,
        avg_gas_50_blocks=round(avg, 4),
        std_dev_gas=round(std, 4),
        forecast_1h_gwei=round(forecast, 4),
        congestion_level=congestion,
    )


# ─── NORMALIZE ─────────────────────────────────────────────────────────────────
def normalize_rpc_snapshot(
    dwellir_data: Dict[str, Any], drpc_data: Dict[str, Any]
) -> BnbRpcSnapshot:
    block_num = dwellir_data.get("block_number") or drpc_data.get("block_number")
    block_hash = dwellir_data.get("block_hash") or drpc_data.get("block_hash")
    timestamp = dwellir_data.get("timestamp")
    if timestamp is None:
        timestamp = drpc_data.get("timestamp")
    tx_count = dwellir_data.get("transactions_count", 0)
    tps = tx_count / BSC_BLOCK_TIME if tx_count else None
    gas_price_gwei = None
    gp = dwellir_data.get("gas_price") or dwellir_data.get("base_fee_per_gas")
    if gp:
        try:
            gas_price_gwei = int(gp, 16) / 1e9 if isinstance(gp, str) else gp / 1e9
        except Exception:
            pass
    return BnbRpcSnapshot(
        captured_at=utc_now_str(),
        latest_block_number=as_int(block_num) or 0,
        latest_block_hash=block_hash or "-",
        latest_block_timestamp=as_int(timestamp),
        avg_block_time_seconds=BSC_BLOCK_TIME,
        tps_1min=tps,
        gas_used_total=as_int(dwellir_data.get("gas_used")),
        gas_price_gwei=gas_price_gwei,
        tx_count=as_int(tx_count),
        validator_address=dwellir_data.get("miner") or drpc_data.get("miner"),
    )


# ─── BUILD WHALES FROM LOGS ────────────────────────────────────────────────────
def build_whales_from_logs(
    logs: List[Dict], token_symbol: str, token_address: str, token_price: float, decimals: int = 18
) -> List[BnbWhaleEvent]:
    whales = []
    for log in logs:
        try:
            topics = log.get("topics", [])
            if len(topics) < 3:
                continue
            from_addr = "0x" + topics[1][-40:]
            to_addr = "0x" + topics[2][-40:]
            raw_val = decode_log_value(log.get("data", "0x0"))
            val_token = raw_val / (10 ** decimals)
            usd = val_token * token_price
            if usd >= WHALE_THRESHOLD_USD:
                block_num = as_int(log.get("blockNumber"))
                ts = utc_now_str()
                whales.append(BnbWhaleEvent(
                    timestamp=ts,
                    asset_symbol=token_symbol,
                    token_contract=token_address,
                    value_raw=val_token,
                    value_usd=round(usd, 2),
                    from_address=from_addr,
                    to_address=to_addr,
                    tx_hash=log.get("transactionHash", "Unknown"),
                    block_number=block_num,
                    transfer_type="erc20",
                ))
        except Exception:
            continue
    return whales


# ─── COMPUTE RISK SCORES ────────────────────────────────────────────────────────
def compute_risk_scores(
    pools: List[BnbDexPool], whales: List[BnbWhaleEvent], conn: oracledb.Connection
) -> List[BnbYieldRiskScore]:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    scores = []
    cursor = conn.cursor()
    for pool in pools:
        tvl_change = None
        try:
            cursor.execute(
                "SELECT TVL_USD FROM BNB_DEX_POOLS_DAILY WHERE POOL_ID = :1 AND SNAPSHOT_DATE = :2",
                (pool.pool_id, (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")),
            )
            row = cursor.fetchone()
            if row and row[0] and pool.tvl_usd:
                tvl_change = ((pool.tvl_usd - row[0]) / row[0]) * 100
        except Exception:
            pass

        whale_net = 0.0
        for w in whales:
            if w.token_contract in (pool.token0_contract, pool.token1_contract):
                whale_net += w.value_usd or 0

        vol_flag = None
        if pool.tvl_usd and pool.tvl_usd > 0 and pool.volume_24h_usd:
            vol_flag = pool.volume_24h_usd / pool.tvl_usd

        score = 30
        if tvl_change is not None:
            score += abs(tvl_change) * 2
        if whale_net > 1_000_000:
            score += 20
        elif whale_net > 100_000:
            score += 10
        if vol_flag and vol_flag > 1.0:
            score += 15
        if pool.tvl_usd and pool.tvl_usd < 100_000:
            score += 20

        score = min(100, max(0, int(score)))
        flag = "stable"
        if score >= 40:
            flag = "watch"
        if score >= 70:
            flag = "high"

        explanation = f"TVL=${pool.tvl_usd or 0:.0f}"
        if tvl_change is not None:
            explanation += f", TVL_chg={tvl_change:.1f}%"
        vol_str = f"{vol_flag:.2f}" if vol_flag is not None else "N/A"
        explanation += f", whale_flow=${whale_net:.0f}, vol_ratio={vol_str}"

        scores.append(BnbYieldRiskScore(
            score_date=today,
            pool_id=pool.pool_id,
            pool_name=f"{pool.token0_symbol}/{pool.token1_symbol}",
            risk_score=score,
            risk_flag=flag,
            explanation=explanation,
            tvl_change_24h=tvl_change,
            whale_net_flow=whale_net,
            volatility_flag=vol_flag,
            computed_at=utc_now_str(),
        ))
    cursor.close()
    return scores


# ─── BUILD DERIVED SIGNALS ─────────────────────────────────────────────────────
def build_derived_signals(
    rpc: BnbRpcSnapshot,
    whales: List[BnbWhaleEvent],
    pools: List[BnbDexPool],
    gas: BnbGasForecast,
    validators: List[BnbValidatorSnapshot],
) -> List[BnbDerivedSignal]:
    out: List[BnbDerivedSignal] = []
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    if rpc.tps_1min and rpc.tps_1min > 10:
        out.append(BnbDerivedSignal(
            signal_date=today,
            signal_family="sequencer",
            signal_key=f"bnb:tps:{today}",
            severity="medium" if rpc.tps_1min < 25 else "high",
            score=min(100, int(rpc.tps_1min * 4)),
            title="BNB Chain throughput spike",
            description=f"BNB processed {rpc.tps_1min:.1f} TPS in recent blocks.",
            metric_value_1=rpc.tps_1min,
            metric_value_2=rpc.avg_block_time_seconds,
            metric_value_3=rpc.gas_used_total,
            reference_id=f"bnb:{rpc.latest_block_number}",
        ))

    if rpc.gas_price_gwei and rpc.gas_price_gwei > 5:
        out.append(BnbDerivedSignal(
            signal_date=today,
            signal_family="fee_pressure",
            signal_key=f"bnb:gas:{today}",
            severity="low" if rpc.gas_price_gwei < 10 else "medium" if rpc.gas_price_gwei < 20 else "high",
            score=min(100, int(rpc.gas_price_gwei * 5)),
            title="BNB Chain gas fee elevation",
            description=f"Gas price at {rpc.gas_price_gwei:.2f} gwei indicates network demand shift.",
            metric_value_1=rpc.gas_price_gwei,
            metric_value_2=rpc.tx_count,
            metric_value_3=None,
            reference_id=f"bnb:{rpc.latest_block_number}",
        ))

    total_whale_usd = sum(w.value_usd or 0 for w in whales)
    if total_whale_usd > 500_000:
        out.append(BnbDerivedSignal(
            signal_date=today,
            signal_family="whale_flow",
            signal_key=f"bnb:whales:{today}",
            severity="medium" if total_whale_usd < 5_000_000 else "high",
            score=min(100, int(total_whale_usd / 50_000)),
            title="BNB Chain whale flow detected",
            description=f"${total_whale_usd/1e6:.2f}M in large transfers on BNB Chain.",
            metric_value_1=total_whale_usd,
            metric_value_2=float(len(whales)),
            metric_value_3=None,
            reference_id=f"bnb:{today}",
        ))

    if gas.congestion_level in ("medium", "high"):
        out.append(BnbDerivedSignal(
            signal_date=today,
            signal_family="gas_forecast",
            signal_key=f"bnb:gasforecast:{today}",
            severity=gas.congestion_level,
            score=min(100, int(gas.forecast_1h_gwei or 0) * 5),
            title="BNB Chain gas congestion forecast",
            description=f"Forecasted gas: {gas.forecast_1h_gwei:.2f} gwei ({gas.congestion_level}).",
            metric_value_1=gas.current_gas_price_gwei,
            metric_value_2=gas.forecast_1h_gwei,
            metric_value_3=gas.std_dev_gas,
            reference_id=f"bnb:{rpc.latest_block_number}",
        ))

    bad_validators = [v for v in validators if v.missed_blocks_count and v.missed_blocks_count > 5]
    if bad_validators:
        out.append(BnbDerivedSignal(
            signal_date=today,
            signal_family="validator_health",
            signal_key=f"bnb:validators:{today}",
            severity="medium" if len(bad_validators) < 3 else "high",
            score=min(100, len(bad_validators) * 15),
            title="BNB Chain validator health alert",
            description=f"{len(bad_validators)} validators showing missed block anomalies.",
            metric_value_1=float(len(bad_validators)),
            metric_value_2=float(len(validators)),
            metric_value_3=None,
            reference_id=f"bnb:{rpc.latest_block_number}",
        ))

    high_risk_pools = [p for p in pools if p.tvl_usd and p.tvl_usd < 50_000]
    if high_risk_pools:
        out.append(BnbDerivedSignal(
            signal_date=today,
            signal_family="dex_risk",
            signal_key=f"bnb:dexrisk:{today}",
            severity="low" if len(high_risk_pools) < 3 else "medium",
            score=min(100, len(high_risk_pools) * 10),
            title="BNB Chain low-TVL DEX pool alert",
            description=f"{len(high_risk_pools)} PancakeSwap pools below $50k TVL.",
            metric_value_1=float(len(high_risk_pools)),
            metric_value_2=None,
            metric_value_3=None,
            reference_id=f"bnb:{today}",
        ))

    severity_rank = {"high": 3, "medium": 2, "low": 1}
    out.sort(key=lambda x: (severity_rank.get(x.severity, 0), x.score), reverse=True)
    return out[:MAX_DERIVED_SIGNALS]


# ─── ORACLE WRITE ──────────────────────────────────────────────────────────────
def replace_table(cursor, table_name: str):
    cursor.execute(f"DELETE FROM {table_name}")


def insert_many(cursor, sql: str, rows: List[Any]):
    if rows:
        cursor.executemany(sql, rows)


def write_to_oracle(
    rpc: BnbRpcSnapshot,
    whales: List[BnbWhaleEvent],
    pools: List[BnbDexPool],
    risk_scores: List[BnbYieldRiskScore],
    validators: List[BnbValidatorSnapshot],
    gas: BnbGasForecast,
    derived: List[BnbDerivedSignal],
):
    log("Writing BNB data to Oracle")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        replace_table(cursor, "BNB_RPC_SNAPSHOT")
        cursor.execute("""
            INSERT INTO BNB_RPC_SNAPSHOT (
                CAPTURED_AT, LATEST_BLOCK_NUMBER, LATEST_BLOCK_HASH,
                LATEST_BLOCK_TIMESTAMP, AVG_BLOCK_TIME_SECONDS, TPS_1MIN,
                GAS_USED_TOTAL, GAS_PRICE_GWEI, TX_COUNT, VALIDATOR_ADDRESS
            ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10)
        """, (
            parse_timestamp(rpc.captured_at),
            as_int(rpc.latest_block_number),
            rpc.latest_block_hash,
            as_int(rpc.latest_block_timestamp),
            as_float(rpc.avg_block_time_seconds),
            as_float(rpc.tps_1min),
            as_int(rpc.gas_used_total),
            as_float(rpc.gas_price_gwei),
            as_int(rpc.tx_count),
            rpc.validator_address,
        ))

        replace_table(cursor, "BNB_WHALE_EVENTS")
        insert_many(cursor, """
            INSERT INTO BNB_WHALE_EVENTS (
                TIMESTAMP, ASSET_SYMBOL, TOKEN_CONTRACT, VALUE_RAW,
                VALUE_USD, FROM_ADDRESS, TO_ADDRESS, TX_HASH, BLOCK_NUMBER, TRANSFER_TYPE
            ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10)
        """, [
            (
                parse_timestamp(w.timestamp),
                w.asset_symbol,
                w.token_contract,
                as_float(w.value_raw),
                as_float(w.value_usd),
                w.from_address,
                w.to_address,
                w.tx_hash,
                as_int(w.block_number),
                w.transfer_type,
            )
            for w in whales
        ])

        replace_table(cursor, "BNB_DEX_POOLS_DAILY")
        insert_many(cursor, """
            INSERT INTO BNB_DEX_POOLS_DAILY (
                SNAPSHOT_DATE, POOL_ID, TOKEN0_SYMBOL, TOKEN1_SYMBOL,
                TOKEN0_CONTRACT, TOKEN1_CONTRACT, TVL_USD, VOLUME_24H_USD,
                TX_COUNT_24H, TOKEN0_PRICE, TOKEN1_PRICE, PRICE_CHANGE_24H
            ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12)
        """, [
            (
                parse_date(p.snapshot_date),
                p.pool_id,
                p.token0_symbol,
                p.token1_symbol,
                p.token0_contract,
                p.token1_contract,
                as_float(p.tvl_usd),
                as_float(p.volume_24h_usd),
                as_int(p.tx_count_24h),
                as_float(p.token0_price),
                as_float(p.token1_price),
                as_float(p.price_change_24h),
            )
            for p in pools
        ])

        replace_table(cursor, "BNB_YIELD_RISK_SCORES")
        insert_many(cursor, """
            INSERT INTO BNB_YIELD_RISK_SCORES (
                SCORE_DATE, POOL_ID, POOL_NAME, RISK_SCORE, RISK_FLAG,
                EXPLANATION, TVL_CHANGE_24H, WHALE_NET_FLOW, VOLATILITY_FLAG, COMPUTED_AT
            ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10)
        """, [
            (
                parse_date(r.score_date),
                r.pool_id,
                r.pool_name,
                as_int(r.risk_score),
                r.risk_flag,
                r.explanation,
                as_float(r.tvl_change_24h),
                as_float(r.whale_net_flow),
                as_float(r.volatility_flag),
                parse_timestamp(r.computed_at),
            )
            for r in risk_scores
        ])

        replace_table(cursor, "BNB_VALIDATOR_SNAPSHOT")
        insert_many(cursor, """
            INSERT INTO BNB_VALIDATOR_SNAPSHOT (
                CAPTURED_AT, BLOCK_NUMBER, VALIDATOR_ADDRESS, VALIDATOR_NAME,
                MISSED_BLOCKS_COUNT, STAKING_APR, IS_ACTIVE
            ) VALUES (:1, :2, :3, :4, :5, :6, :7)
        """, [
            (
                parse_timestamp(v.captured_at),
                as_int(v.block_number),
                v.validator_address,
                v.validator_name,
                as_int(v.missed_blocks_count),
                as_float(v.staking_apr),
                v.is_active,
            )
            for v in validators
        ])

        replace_table(cursor, "BNB_GAS_FORECAST")
        cursor.execute("""
            INSERT INTO BNB_GAS_FORECAST (
                FORECAST_AT, CURRENT_GAS_PRICE_GWEI, AVG_GAS_50_BLOCKS,
                STD_DEV_GAS, FORECAST_1H_GWEI, CONGESTION_LEVEL
            ) VALUES (:1, :2, :3, :4, :5, :6)
        """, (
            parse_timestamp(gas.forecast_at),
            as_float(gas.current_gas_price_gwei),
            as_float(gas.avg_gas_50_blocks),
            as_float(gas.std_dev_gas),
            as_float(gas.forecast_1h_gwei),
            gas.congestion_level,
        ))

        replace_table(cursor, "BNB_DERIVED_SIGNALS")
        insert_many(cursor, """
            INSERT INTO BNB_DERIVED_SIGNALS (
                SIGNAL_DATE, SIGNAL_FAMILY, SIGNAL_KEY, SEVERITY, SCORE,
                TITLE, DESCRIPTION, METRIC_VALUE_1, METRIC_VALUE_2, METRIC_VALUE_3, REFERENCE_ID
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


# ─── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    log("BNB collector starting")
    log(f"Dwellir configured: {bool(DWELLIR_BSC_URL)}")
    log(f"Ankr configured: {bool(ANKR_BSC_URL)}")
    log(f"Infura configured: {bool(INFURA_BSC_URL)}")
    log(f"BlockPi configured: {bool(BLOCKPI_BSC_URL)}")
    log(f"Alchemy BSC configured: {bool(ALCHEMY_BSC_URL)}")
    log(f"Getblock configured: {bool(GETBLOCK_BSC_URL)}")
    log(f"GeckoTerminal configured: True (no key needed)")
    log(f"CMC configured: {bool(CMC_API_KEY)}")

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(30.0, connect=15.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        # ── Prices ──
        bnb_price = await fetch_cmc_bnb_price(client)
        if not bnb_price:
            bnb_price = 600.0
            log(f"Using fallback BNB price: ${bnb_price}")
        else:
            log(f"BNB price: ${bnb_price}")

        # Only track tokens we can price (stables at $1)
        token_prices: Dict[str, float] = {}
        for symbol in BSC_TOKENS.keys():
            if symbol in KNOWN_STABLES:
                token_prices[symbol] = 1.0
                log(f"{symbol} price: $1.00 (stable)")
            else:
                log(f"{symbol} skipped: not in known pricing whitelist")

        # ── RPC Blocks ──
        dwellir_task = fetch_dwellir_block_data(client)
        drpc_task = fetch_drpc_block(client)
        dwellir_data, drpc_data = await asyncio.gather(
            dwellir_task, drpc_task, return_exceptions=True
        )
        for name, data in [("dwellir", dwellir_data), ("drpc", drpc_data)]:
            if isinstance(data, Exception):
                log(f"{name} fetch failed: {data}")
                if name == "dwellir":
                    dwellir_data = {}
                elif name == "drpc":
                    drpc_data = {}

        latest_block = dwellir_data.get("block_number") or drpc_data.get("block_number") or 0

        # ── Whale Detection ──
        from_block_logs = hex(max(latest_block - 50, 0))
        to_block_logs = "latest"
        all_whales: List[BnbWhaleEvent] = []

        # Alchemy already covers BNB + all tracked ERC-20s in one call
        alchemy_whales = await fetch_alchemy_bsc_whales(client, bnb_price)
        all_whales.extend(alchemy_whales)
        log(f"Alchemy BSC whales: {len(alchemy_whales)}")

        # Supplement with RPC logs for specific stablecoins (Alchemy may miss some)
        for symbol, addr in BSC_TOKENS.items():
            price = token_prices.get(symbol)
            if price is None:
                log(f"Skipping {symbol}: no price available")
                continue

            logs = await fetch_token_transfer_logs(client, addr, from_block_logs, to_block_logs)
            if logs:
                whales = build_whales_from_logs(logs, symbol, addr, price, decimals=18)
                all_whales.extend(whales)
                log(f"{symbol} RPC log whales: {len(whales)}")
            else:
                log(f"{symbol}: no RPC log whales found")
            await asyncio.sleep(0.3)

        # BNB native whales (last 10 blocks to limit RPC load)
        native_whales = await fetch_bnb_native_whales(
            client, max(latest_block - 10, 0), latest_block, bnb_price
        )
        all_whales.extend(native_whales)
        log(f"BNB native whale events: {len(native_whales)}")

        # Deduplicate whales
        seen = set()
        unique_whales = []
        for w in sorted(all_whales, key=lambda x: x.value_usd or 0, reverse=True):
            key = (w.timestamp, w.asset_symbol, w.from_address, w.to_address, w.tx_hash)
            if key not in seen:
                seen.add(key)
                unique_whales.append(w)
        all_whales = unique_whales[:100]

        # ── PancakeSwap Pools ──
        pools = await fetch_pancakeswap_pools(client)
        log(f"PancakeSwap pools fetched: {len(pools)}")

        # ── Validator Data ──
        validators = await fetch_validator_data(client, latest_block)
        log(f"Validators tracked: {len(validators)}")

        # ── Gas Forecast ──
        gas = await fetch_gas_history(client, latest_block)
        log(f"Gas forecast: {gas.forecast_1h_gwei} gwei ({gas.congestion_level})")

        # ── Normalize ──
        rpc = normalize_rpc_snapshot(dwellir_data, drpc_data)

        # ── Risk Scores ──
        conn = get_connection()
        try:
            risk_scores = compute_risk_scores(pools, all_whales, conn)
        finally:
            conn.close()
        log(f"Risk scores computed: {len(risk_scores)}")

        # ── Derived Signals ──
        derived = build_derived_signals(rpc, all_whales, pools, gas, validators)
        log(f"Derived signals: {len(derived)}")

        # ── Write ──
        write_to_oracle(rpc, all_whales, pools, risk_scores, validators, gas, derived)

        log(f"BNB block: {rpc.latest_block_number}")
        log(f"BNB TPS: {rpc.tps_1min}")
        log(f"BNB whales: {len(all_whales)}")
        log(f"BNB pools: {len(pools)}")
        log(f"BNB validators: {len(validators)}")
        log(f"BNB derived signals: {len(derived)}")

    log("BNB collector finished")


if __name__ == "__main__":
    asyncio.run(main())
