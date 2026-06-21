import asyncio
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
import oracledb
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN", "asyncsignalsdatabase_medium")
WALLET_DIR = os.getenv("WALLET_DIR", "/home/daniel/wallet")

SUI_GRAPHQL_URL = os.getenv("ANKR_SUI_URL") or os.getenv("SUI_GRAPHQL_URL", "https://rpc.ankr.com/http/sui_graphql")
COINGECKO_KEY = os.getenv("COINGECKO_KEY")

TS_FORMAT = "%Y-%m-%d %H:%M:%S"

# Thresholds: lower for testing, raise for production
WHALE_THRESHOLD_SUI = 500.0      # 100 SUI (was 5000)
WHALE_THRESHOLD_USD = 100.0       # $100 (was $10000)

# Protocol detection by package address prefix (first 6 chars after 0x) or name
PROTOCOL_PATTERNS = {
    "cetus":      ["cetus", "1eabed"],           
    "deepbook":   ["deepbook", "2c8d60", "deep"],
    "scallop":    ["scallop"],
    "navi":       ["naviprotocol", "navi"],
    "suilend":    ["suilend"],
    "bucket":     ["bucket"],
    "turbos":     ["turbos"],
    "flowx":      ["flowx"],
    "kriya":      ["kriya"],
    "aftermath":  ["aftermath"],
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


def short_addr(addr: str) -> str:
    if len(addr) <= 14:
        return addr
    return f"{addr[:6]}...{addr[-6:]}"


async def fetch_sui_price(client: httpx.AsyncClient) -> float:
    if not COINGECKO_KEY:
        return 0.65
    try:
        headers = {"x-cg-demo-api-key": COINGECKO_KEY}
        resp = await client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "sui", "vs_currencies": "usd"},
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("sui", {}).get("usd", 0.65)
    except Exception as e:
        log(f"CoinGecko SUI price failed: {e}")
        return 0.65


async def graphql_query(client: httpx.AsyncClient, query: str, variables: Optional[Dict] = None) -> Dict:
    payload = {"query": query, "variables": variables or {}}
    resp = await client.post(
        SUI_GRAPHQL_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        error_msgs = [e.get("message", "") for e in data["errors"]]
        raise RuntimeError(f"GraphQL errors: {error_msgs}")
    return data.get("data", {})


async def fetch_recent_transactions(client: httpx.AsyncClient, limit: int = 50) -> List[Dict]:
    """Fetch recent transactions using verified Ankr Sui GraphQL schema."""
    query = """
    query RecentTransactions($limit: Int!) {
        transactions(last: $limit) {
            nodes {
                digest
                sender {
                    address
                }
                effects {
                    timestamp
                    gasEffects {
                        gasSummary {
                            computationCost
                            storageCost
                            storageRebate
                            nonRefundableStorageFee
                        }
                    }
                    objectChanges {
                        nodes {
                            address
                            idCreated
                            idDeleted
                            inputState {
                                asMoveObject {
                                    contents {
                                        type {
                                            repr
                                        }
                                    }
                                }
                            }
                            outputState {
                                asMoveObject {
                                    contents {
                                        type {
                                            repr
                                        }
                                    }
                                }
                            }
                        }
                    }
                    balanceChanges {
                        nodes {
                            owner {
                                address
                            }
                            amount
                            coinType {
                                repr
                            }
                        }
                    }
                }
            }
        }
    }
    """
    data = await graphql_query(client, query, {"limit": limit})
    nodes = data.get("transactions", {}).get("nodes", [])
    return nodes if isinstance(nodes, list) else []


def extract_object_type(obj_change: Dict) -> str:
    """Extract the Move object type string from an object change."""
    output = obj_change.get("outputState", {})
    if output and isinstance(output, dict):
        move_obj = output.get("asMoveObject", {})
        if move_obj and isinstance(move_obj, dict):
            contents = move_obj.get("contents", {})
            if contents and isinstance(contents, dict):
                type_info = contents.get("type", {})
                if type_info and isinstance(type_info, dict):
                    return type_info.get("repr", "")

    input_state = obj_change.get("inputState", {})
    if input_state and isinstance(input_state, dict):
        move_obj = input_state.get("asMoveObject", {})
        if move_obj and isinstance(move_obj, dict):
            contents = move_obj.get("contents", {})
            if contents and isinstance(contents, dict):
                type_info = contents.get("type", {})
                if type_info and isinstance(type_info, dict):
                    return type_info.get("repr", "")
    return ""


def detect_protocol_tag(object_type: str, coin_type: str) -> Optional[str]:
    """Tag a transaction with a protocol based on object/coin type heuristics."""
    text = f"{object_type or ''} {coin_type or ''}".lower()
    for protocol, patterns in PROTOCOL_PATTERNS.items():
        for pat in patterns:
            if pat in text:
                return protocol
    return None


def normalize_whale_events(txs: List[Dict], sui_price: float) -> List[Dict]:
    """Distill raw GraphQL transactions into whale events."""
    events = []
    for tx in txs:
        digest = tx.get("digest", "")
        sender = ""
        sender_obj = tx.get("sender")
        if isinstance(sender_obj, dict):
            sender = sender_obj.get("address", "")

        effects = tx.get("effects", {}) or {}
        ts_raw = effects.get("timestamp")
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).strftime(TS_FORMAT) if ts_raw else utc_now_str()

        # --- Balance changes (gas fees, simple transfers) ---
        balance_changes = []
        bc_nodes = effects.get("balanceChanges", {})
        if isinstance(bc_nodes, dict):
            balance_changes = bc_nodes.get("nodes", [])

        for bc in balance_changes:
            amount_raw = bc.get("amount")
            if amount_raw is None:
                continue
            try:
                amount = float(amount_raw) / 1e9  # MIST -> SUI
            except Exception:
                continue

            coin_type = ""
            ct = bc.get("coinType")
            if isinstance(ct, dict):
                coin_type = ct.get("repr", "")

            owner = ""
            owner_obj = bc.get("owner")
            if isinstance(owner_obj, dict):
                owner = owner_obj.get("address", "")

            is_sui = "sui" in coin_type.lower() or coin_type == "0x2::sui::SUI"
            if is_sui:
                usd_value = abs(amount) * sui_price
            else:
                # For non-SUI coins, rough estimate
                usd_value = abs(amount) * 1.0

            # Whale threshold check
            if not (abs(amount) >= WHALE_THRESHOLD_SUI or usd_value >= WHALE_THRESHOLD_USD):
                continue

            # Protocol tag from object changes
            protocol_tag = None
            obj_changes = []
            oc_nodes = effects.get("objectChanges", {})
            if isinstance(oc_nodes, dict):
                obj_changes = oc_nodes.get("nodes", [])

            for oc in obj_changes:
                obj_type = extract_object_type(oc)
                protocol_tag = detect_protocol_tag(obj_type, coin_type)
                if protocol_tag:
                    break

            direction = "in" if amount > 0 else "out"
            from_addr = sender if amount < 0 else owner
            to_addr = owner if amount < 0 else sender

            events.append({
                "tx_hash": digest,
                "timestamp": ts,
                "from_addr": from_addr or "-",
                "to_addr": to_addr or "-",
                "token": coin_type.split("::")[-1] if "::" in coin_type else ("SUI" if is_sui else "UNKNOWN"),
                "amount": round(abs(amount), 9),
                "usd_value": round(usd_value, 2),
                "protocol_tag": protocol_tag or "unknown",
                "direction": direction,
            })

        # --- Object changes: detect protocol interactions even without balance changes ---
        obj_changes = []
        oc_nodes = effects.get("objectChanges", {})
        if isinstance(oc_nodes, dict):
            obj_changes = oc_nodes.get("nodes", [])

        for oc in obj_changes:
            obj_type = extract_object_type(oc)
            if not obj_type:
                continue

            protocol_tag = detect_protocol_tag(obj_type, "")
            if not protocol_tag:
                continue

            # Only log if we haven't already logged this tx+protocol combo
            already_logged = any(
                e["tx_hash"] == digest and e["protocol_tag"] == protocol_tag
                for e in events
            )
            if already_logged:
                continue

            # Object-level protocol interaction (no amount, just protocol tag)
            events.append({
                "tx_hash": digest,
                "timestamp": ts,
                "from_addr": sender or "-",
                "to_addr": "-",
                "token": "OBJECT",
                "amount": 0.0,
                "usd_value": 0.0,
                "protocol_tag": protocol_tag,
                "direction": "mutate",
            })

    # Sort by USD value descending, dedupe
    seen = set()
    unique = []
    for e in sorted(events, key=lambda x: x["usd_value"], reverse=True):
        key = (e["tx_hash"], e["token"], e["direction"], e["from_addr"], e["to_addr"], e["protocol_tag"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique[:100]


def compute_top_whales(events: List[Dict], window_hours: int = 168) -> List[Dict]:
    """Rolling 7D top whale addresses."""
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    from collections import defaultdict
    stats = defaultdict(lambda: {"total_in": 0.0, "total_out": 0.0, "protocols": set(), "tx_count": 0})

    for e in events:
        try:
            et = datetime.strptime(e["timestamp"], TS_FORMAT).replace(tzinfo=UTC)
        except Exception:
            continue
        if et < cutoff:
            continue

        addr = e["from_addr"] if e["direction"] == "out" else e["to_addr"]
        if addr == "-":
            addr = e["from_addr"]
        stats[addr]["tx_count"] += 1
        if e["direction"] == "in":
            stats[addr]["total_in"] += e["usd_value"]
        elif e["direction"] == "out":
            stats[addr]["total_out"] += e["usd_value"]
        stats[addr]["protocols"].add(e["protocol_tag"])

    out = []
    for addr, s in sorted(stats.items(), key=lambda x: x[1]["total_in"] + x[1]["total_out"], reverse=True):
        out.append({
            "address": addr,
            "total_in_usd": round(s["total_in"], 2),
            "total_out_usd": round(s["total_out"], 2),
            "net_flow_usd": round(s["total_in"] - s["total_out"], 2),
            "protocols_touched": len(s["protocols"]),
            "protocol_list": ",".join(sorted(s["protocols"])),
            "tx_count": s["tx_count"],
        })
    return out[:50]


def compute_protocol_exposure(events: List[Dict], window_hours: int = 168) -> List[Dict]:
    """Volume per protocol over rolling window."""
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    from collections import defaultdict
    exposure = defaultdict(lambda: {"volume_usd": 0.0, "tx_count": 0})

    for e in events:
        try:
            et = datetime.strptime(e["timestamp"], TS_FORMAT).replace(tzinfo=UTC)
        except Exception:
            continue
        if et < cutoff:
            continue
        proto = e.get("protocol_tag") or "unknown"
        exposure[proto]["volume_usd"] += e["usd_value"]
        exposure[proto]["tx_count"] += 1

    return [
        {"protocol": k, "volume_usd": round(v["volume_usd"], 2), "tx_count": v["tx_count"]}
        for k, v in sorted(exposure.items(), key=lambda x: x[1]["volume_usd"], reverse=True)
    ]


def write_sui_events(events: List[Dict]):
    if not events:
        log("No Sui whale events to write")
        return

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM SUI_WHALE_EVENTS")
        cursor.executemany(
            """
            INSERT INTO SUI_WHALE_EVENTS (
                TX_HASH, EVENT_TIMESTAMP, FROM_ADDR, TO_ADDR, TOKEN, AMOUNT, USD_VALUE, PROTOCOL_TAG, DIRECTION
            ) VALUES (:1, TO_TIMESTAMP(:2, 'YYYY-MM-DD HH24:MI:SS'), :3, :4, :5, :6, :7, :8, :9)
            """,
            [
                (e["tx_hash"], e["timestamp"], e["from_addr"], e["to_addr"], e["token"],
                 e["amount"], e["usd_value"], e["protocol_tag"], e["direction"])
                for e in events
            ]
        )
        conn.commit()
        log(f"Wrote {len(events)} Sui whale events")
    except Exception as e:
        conn.rollback()
        log(f"Sui DB write failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def write_sui_top_whales(top_whales: List[Dict]):
    if not top_whales:
        return
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM SUI_TOP_WHALES")
        cursor.executemany(
            """
            INSERT INTO SUI_TOP_WHALES (
                ADDRESS, TOTAL_IN_USD, TOTAL_OUT_USD, NET_FLOW_USD, PROTOCOLS_TOUCHED, PROTOCOL_LIST, TX_COUNT, COMPUTED_AT
            ) VALUES (:1, :2, :3, :4, :5, :6, :7, CURRENT_TIMESTAMP)
            """,
            [
                (w["address"], w["total_in_usd"], w["total_out_usd"], w["net_flow_usd"],
                 w["protocols_touched"], w["protocol_list"], w["tx_count"])
                for w in top_whales
            ]
        )
        conn.commit()
        log(f"Wrote {len(top_whales)} Sui top whales")
    finally:
        cursor.close()
        conn.close()


def write_sui_protocol_exposure(exposure: List[Dict]):
    if not exposure:
        return
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM SUI_PROTOCOL_EXPOSURE")
        cursor.executemany(
            """
            INSERT INTO SUI_PROTOCOL_EXPOSURE (
                PROTOCOL, VOLUME_USD, TX_COUNT, COMPUTED_AT
            ) VALUES (:1, :2, :3, CURRENT_TIMESTAMP)
            """,
            [(e["protocol"], e["volume_usd"], e["tx_count"]) for e in exposure]
        )
        conn.commit()
        log(f"Wrote {len(exposure)} protocol exposure rows")
    finally:
        cursor.close()
        conn.close()


async def main():
    log("Sui worker starting")
    log("GraphQL endpoint: [REDACTED]")

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(30.0, connect=15.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        sui_price = await fetch_sui_price(client)
        log(f"SUI price: ${sui_price}")

        txs = await fetch_recent_transactions(client, limit=50)
        log(f"Fetched {len(txs)} transactions")

        events = normalize_whale_events(txs, sui_price)
        log(f"Normalized {len(events)} whale events")

        top_whales = compute_top_whales(events)
        exposure = compute_protocol_exposure(events)

        write_sui_events(events)
        write_sui_top_whales(top_whales)
        write_sui_protocol_exposure(exposure)

        log(f"Top whales: {len(top_whales)}")
        log(f"Protocol exposure: {len(exposure)}")

    log("Sui worker finished")


if __name__ == "__main__":
    asyncio.run(main())
