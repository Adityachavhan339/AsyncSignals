import os
import asyncio
import logging
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

import httpx
import oracledb
from dotenv import load_dotenv

load_dotenv()

HELIUS_RPC = os.getenv("SOLANA_DRPC_URL")
QUICKNODE_RPC = os.getenv("QUICKNODE_RPC_URL")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
WALLET_DIR = os.getenv("WALLET_DIR", "/home/ubuntu/wallet")
DB_DSN = os.getenv("DB_DSN", "asyncsignalsdatabase_low")


WHALE_THRESHOLD_SOL = 1.0
WHALE_THRESHOLD_USD = 500.0
MEGA_WHALE_THRESHOLD_SOL = 50.0
MEGA_WHALE_THRESHOLD_USD = 5_000.0


REAL_WATCH_ADDRESSES = [
    "CbrKVVDv6irzm4SYv8YnhJkN6wCTnYw9S7SqdwavCrRt",
    "EmutJdbKJ55hUyth15bar8ZxDCchR44udAXWYg9eLLDL",
    "4RiaWctnGNdEhyWz2DjFfoV5p2nuPwMPQ74QMa6Tbioh",
    "DY7yDm3TS3K696YgGQE2jSSreYd6dFHPbvdonR2a5Gfh",
    "4uEX6TQgZ3Zn4iXcjMDSnvEgEHpERa2YsguvCUNajx2B",
    "2R9YrpeXNXyne2gPrC3tKwJosScsuausNTmZ16LYfaFD",
]


PROTOCOL_MAP = {
    "JUP6LkbZbjS1jKKtdU6jq5p2faT7gHM7UNPFKQf6zxx": "Jupiter Aggregator",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium AMM",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca Whirlpools",
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "Pump.fun",
    "DjVE6JNzY9HYFkUv6j4BNG6X6zfM2cQm3B7iQY5N6tx": "Meteora DLMM",
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPjx": "Lifinity",
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp7VTaTb9V2HYJrA": "Raydium CLMM",
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHK11Qufs4r0": "Cropper AMM",
    "SSwpkEEcbUqx4vtoEByFjSkhKdCT862DNVb52nZg1UZ": "Saros AMM",
    "11111111111111111111111111111111": "System Program",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": "SPL Token",
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb": "Token-2022",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL": "Associated Token",
    "ComputeBudget111111111111111111111111111111": "Compute Budget",
    "So11111111111111111111111111111111111111112": "Wrapped SOL",
}


SOL_MINT = "So11111111111111111111111111111111111111112"

TRACKED_MINTS = {
    SOL_MINT: "SOL",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
    "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj": "stSOL",
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So": "mSOL",
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": "BONK",
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn": "JitoSOL",
    "bSo13r4TkiE4KumL71LsHTPpL2euBYLFxA2KoF1upYw": "bSOL",
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3": "PYTH",
    "7vfCXTUXx5WJV5J5dF62GV3qVn8Db3pW1pM8vR2r1Q2": "JUP",
}

TOKEN_DECIMALS = {
    "SOL": 9, "USDC": 6, "USDT": 6, "stSOL": 9, "mSOL": 9,
    "BONK": 5, "JitoSOL": 9, "bSOL": 9, "PYTH": 6, "JUP": 6,
}


class RedactedLogger(logging.Filter):
    def filter(self, record):
        msg = str(record.getMessage())
        if "api-key=" in msg:
            parts = msg.split("api-key=")
            if len(parts) > 1:
                rest = parts[1].split("&")[0].split('"')[0].split(" ")[0]
                record.msg = msg.replace(rest, "[REDACTED]")
        if "api.helius" in msg or "quicknode" in msg:
            record.msg = "[RPC call]"
        return True

httpx_logger = logging.getLogger("httpx")
httpx_logger.addFilter(RedactedLogger())
httpx_logger.setLevel(logging.WARNING)


def get_connection():
    return oracledb.connect(
        user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN,
        config_dir=WALLET_DIR, wallet_location=WALLET_DIR, wallet_password=DB_PASSWORD,
    )


def utc_now_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════════════════
# SOLANA COLLECTOR
# ═══════════════════════════════════════════════════════════════════════════

class SolanaCollector:
    def __init__(self):
        self.primary_rpc = HELIUS_RPC
        self.backup_rpc = QUICKNODE_RPC
        self.current_rpc = self.primary_rpc
        self.semaphore = asyncio.Semaphore(6)
        self.token_prices = {}
        self.protocol_volumes = defaultdict(float)
        self.protocol_tx_counts = defaultdict(int)

    def _get_rpc(self) -> str:
        return self.current_rpc or self.primary_rpc or self.backup_rpc

    def _switch_rpc(self):
        self.current_rpc = self.backup_rpc if (self.current_rpc == self.primary_rpc and self.backup_rpc) else self.primary_rpc

    async def _rpc_call(self, client: httpx.AsyncClient, payload: dict, timeout: float = 25.0) -> Optional[dict]:
        async with self.semaphore:
            for attempt in range(3):
                rpc = self._get_rpc()
                if not rpc:
                    return None
                try:
                    resp = await client.post(rpc, json=payload, timeout=timeout)
                    if resp.status_code == 429:
                        wait = 2 ** attempt
                        await asyncio.sleep(wait)
                        if attempt == 1:
                            self._switch_rpc()
                        continue
                    resp.raise_for_status()
                    result = resp.json()
                    if result.get("error"):
                        err = result.get("error", {})
                        if isinstance(err, dict) and err.get("code") in (-32001, -32602, -32004):
                            return {"result": None, "_empty": True}
                        logging.warning(f"RPC error: {err}")
                        return None
                    return result
                except httpx.TimeoutException:
                    logging.warning(f"RPC timeout (attempt {attempt + 1})")
                    if attempt == 1:
                        self._switch_rpc()
                    await asyncio.sleep(1.5)
                except Exception as e:
                    logging.warning(f"RPC error: {e}")
                    if attempt == 1:
                        self._switch_rpc()
                    await asyncio.sleep(1)
            return None

    
    async def _fetch_signatures(self, client: httpx.AsyncClient, address: str, limit: int = 50) -> List[dict]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [address, {"limit": limit, "commitment": "confirmed"}],
        }
        result = await self._rpc_call(client, payload)
        if result and result.get("result"):
            return result["result"]
        return []

    async def _fetch_transaction(self, client: httpx.AsyncClient, signature: str) -> Optional[Dict[str, Any]]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0,
                    "commitment": "confirmed",
                },
            ],
        }
        result = await self._rpc_call(client, payload, timeout=30.0)
        return result.get("result") if result else None

    
    async def discover_whales_from_program(self, client: httpx.AsyncClient, program_id: str, limit: int = 30) -> List[str]:
        sigs = await self._fetch_signatures(client, program_id, limit)
        if not sigs:
            return []

        candidate_wallets = defaultdict(float)
        tasks = [self._fetch_transaction(client, s["signature"]) for s in sigs[:limit]]
        txs = await asyncio.gather(*tasks, return_exceptions=True)

        for tx in txs:
            if isinstance(tx, Exception) or not tx:
                continue
            meta = tx.get("meta", {}) or {}
            pre_balances = meta.get("preBalances", [])
            post_balances = meta.get("postBalances", [])

            account_keys_raw = tx.get("transaction", {}).get("message", {}).get("accountKeys", [])
            key_list = []
            for k in account_keys_raw:
                if isinstance(k, dict):
                    key_list.append(k.get("pubkey", ""))
                elif isinstance(k, str):
                    key_list.append(k)
                else:
                    key_list.append(str(k))

            for i, (pre, post) in enumerate(zip(pre_balances, post_balances)):
                if i >= len(key_list):
                    continue
                addr = key_list[i]
                change = abs(post - pre) / 1e9
                if change >= 0.5:
                    candidate_wallets[addr] += change

            pre_tokens = meta.get("preTokenBalances", []) or []
            post_tokens = meta.get("postTokenBalances", []) or []
            for p in post_tokens:
                owner = p.get("owner", "")
                mint = p.get("mint", "")
                if mint in TRACKED_MINTS and owner:
                    pre_amt = 0
                    for pr in pre_tokens:
                        if pr.get("accountIndex") == p.get("accountIndex") and pr.get("mint") == mint:
                            ui = pr.get("uiTokenAmount", {})
                            pre_amt = float(ui.get("uiAmountString") or ui.get("amount", "0") or 0)
                            break
                    post_amt = float(p.get("uiTokenAmount", {}).get("uiAmountString") or p.get("uiTokenAmount", {}).get("amount", "0") or 0)
                    delta = abs(post_amt - pre_amt)
                    if delta >= 50:
                        candidate_wallets[owner] += delta

        sorted_wallets = sorted(candidate_wallets.items(), key=lambda x: x[1], reverse=True)
        return [addr for addr, vol in sorted_wallets[:20] if vol >= 5]

  
    async def discover_top_token_holders(self, client: httpx.AsyncClient, mint: str, min_balance: float = 1000.0) -> List[str]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenLargestAccounts",
            "params": [mint],
        }
        result = await self._rpc_call(client, payload)
        if not result or not result.get("result"):
            return []

        value = result["result"].get("value", [])
        holders = []

        for item in value:
            address = item.get("address", "")
            ui_amount = item.get("uiAmount", 0)
            if ui_amount >= min_balance:
                owner_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getAccountInfo",
                    "params": [address, {"encoding": "jsonParsed"}],
                }
                owner_result = await self._rpc_call(client, owner_payload)
                if owner_result and owner_result.get("result"):
                    account_data = owner_result["result"].get("value", {})
                    parsed = account_data.get("data", {}).get("parsed", {})
                    info = parsed.get("info", {})
                    owner = info.get("owner", "")
                    if owner and len(owner) == 44:
                        holders.append(owner)

        return holders[:10]

    
    def _identify_protocol(self, tx: Dict[str, Any]) -> Optional[str]:
        instructions = tx.get("transaction", {}).get("message", {}).get("instructions", []) or []
        for ins in instructions:
            pid = ins.get("programId", "") if isinstance(ins, dict) else ""
            if pid in PROTOCOL_MAP:
                return PROTOCOL_MAP[pid]
        account_keys_raw = tx.get("transaction", {}).get("message", {}).get("accountKeys", []) or []
        for key in account_keys_raw:
            addr = key.get("pubkey", "") if isinstance(key, dict) else key
            if addr in PROTOCOL_MAP:
                return PROTOCOL_MAP[addr]
        return None

    def extract_transfers(self, tx: Dict[str, Any], sol_price: float, source_address: str) -> List[Dict[str, Any]]:
        if not tx:
            return []

        out = []
        block_time = tx.get("blockTime")
        ts = datetime.fromtimestamp(block_time, UTC).strftime("%Y-%m-%d %H:%M:%S") if block_time else utc_now_str()
        meta = tx.get("meta", {}) or {}
        transaction = tx.get("transaction", {})
        message = transaction.get("message", {})
        instructions = message.get("instructions", []) or []
        tx_hash = transaction.get("signatures", [""])[0] if isinstance(transaction, dict) else ""
        fee_lamports = meta.get("fee", 0)
        compute_units = meta.get("computeUnitsConsumed", 0)
        protocol = self._identify_protocol(tx)

        account_keys_raw = message.get("accountKeys", [])
        key_list = []
        for k in account_keys_raw:
            if isinstance(k, dict):
                key_list.append(k.get("pubkey", ""))
            elif isinstance(k, str):
                key_list.append(k)
            else:
                key_list.append(str(k))

      
        for ins in instructions:
            if not isinstance(ins, dict):
                continue
            prog_id = ins.get("programId", "")
            parsed = ins.get("parsed", {})
            if not parsed:
                continue

            ptype = parsed.get("type", "")
            info = parsed.get("info", {})

           
            if prog_id == "11111111111111111111111111111111" and ptype == "transfer":
                lamports = float(info.get("lamports") or 0)
                sol_amount = lamports / 1e9
                usd_value = sol_amount * sol_price
                if sol_amount >= WHALE_THRESHOLD_SOL or usd_value >= WHALE_THRESHOLD_USD:
                    from_addr = str(info.get("source", "Unknown"))
                    to_addr = str(info.get("destination", "Unknown"))
                    out.append(self._build_transfer_record(
                        ts, "SOL", sol_amount, usd_value, from_addr, to_addr,
                        tx_hash, "system_transfer", protocol, fee_lamports, compute_units, source_address
                    ))

            
            elif prog_id in ("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                             "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb") and "transfer" in str(ptype).lower():
                amount_raw = info.get("amount") or info.get("tokenAmount", {}).get("amount", "0")
                try:
                    amount_raw = float(amount_raw)
                except (ValueError, TypeError):
                    continue
                mint = info.get("mint", "")
                if not mint and "tokenAmount" in info:
                    mint = info.get("tokenAmount", {}).get("mint", "")
                if mint not in TRACKED_MINTS:
                    continue
                asset = TRACKED_MINTS[mint]
                decimals = TOKEN_DECIMALS.get(asset, 9)
                amount = amount_raw / (10 ** decimals)
                token_price = self.token_prices.get(asset, 1.0 if asset in ("USDC", "USDT") else sol_price)
                usd_value = amount * token_price

                threshold_sol_equiv = WHALE_THRESHOLD_SOL if asset == "SOL" else WHALE_THRESHOLD_USD / max(token_price, 0.001)
                if amount >= threshold_sol_equiv or usd_value >= WHALE_THRESHOLD_USD:
                    from_addr = str(info.get("source", info.get("authority", "Unknown")))
                    to_addr = str(info.get("destination", "Unknown"))
                    out.append(self._build_transfer_record(
                        ts, asset, amount, usd_value, from_addr, to_addr,
                        tx_hash, "spl_transfer", protocol, fee_lamports, compute_units, source_address
                    ))

            
            elif "transferChecked" in str(ptype):
                amount_raw = info.get("tokenAmount", {}).get("amount", "0")
                try:
                    amount_raw = float(amount_raw)
                except (ValueError, TypeError):
                    continue
                mint = info.get("mint", "")
                if mint not in TRACKED_MINTS:
                    continue
                asset = TRACKED_MINTS[mint]
                decimals = TOKEN_DECIMALS.get(asset, 9)
                amount = amount_raw / (10 ** decimals)
                token_price = self.token_prices.get(asset, 1.0 if asset in ("USDC", "USDT") else sol_price)
                usd_value = amount * token_price
                if usd_value >= WHALE_THRESHOLD_USD:
                    from_addr = str(info.get("source", info.get("authority", "Unknown")))
                    to_addr = str(info.get("destination", "Unknown"))
                    out.append(self._build_transfer_record(
                        ts, asset, amount, usd_value, from_addr, to_addr,
                        tx_hash, "spl_transfer_checked", protocol, fee_lamports, compute_units, source_address
                    ))

       
        pre_balances = meta.get("preBalances", [])
        post_balances = meta.get("postBalances", [])
        for i, (pre, post) in enumerate(zip(pre_balances, post_balances)):
            if i >= len(key_list):
                continue
            addr = key_list[i]
            change = (post - pre) / 1e9
            if abs(change) >= WHALE_THRESHOLD_SOL:
                counterparties = []
                for j, (pre2, post2) in enumerate(zip(pre_balances, post_balances)):
                    if j == i or j >= len(key_list):
                        continue
                    change2 = (post2 - pre2) / 1e9
                    if change > 0 and change2 < 0:
                        counterparties.append((key_list[j], abs(change2)))
                    elif change < 0 and change2 > 0:
                        counterparties.append((key_list[j], abs(change2)))

                if counterparties:
                    counterparties.sort(key=lambda x: x[1], reverse=True)
                    counterparty = counterparties[0][0]
                    if change > 0:
                        from_addr, to_addr = counterparty, addr
                    else:
                        from_addr, to_addr = addr, counterparty
                    usd_value = abs(change) * sol_price
                    already = any(
                        t["tx_hash"] == tx_hash and t["asset"] == "SOL" and
                        abs(t["amount"] - abs(change)) < 0.001 and
                        ((t["from_address"] == from_addr and t["to_address"] == to_addr) or
                         (t["from_address"] == to_addr and t["to_address"] == from_addr))
                        for t in out
                    )
                    if not already:
                        out.append(self._build_transfer_record(
                            ts, "SOL", abs(change), usd_value, from_addr, to_addr,
                            tx_hash, "balance_change", protocol, fee_lamports, compute_units, source_address
                        ))

       
        pre_tokens = meta.get("preTokenBalances", []) or []
        post_tokens = meta.get("postTokenBalances", []) or []

        owner_deltas = defaultdict(lambda: {"pre": 0.0, "post": 0.0, "mint": ""})
        for pt in pre_tokens:
            mint = pt.get("mint", "")
            if mint not in TRACKED_MINTS:
                continue
            owner = pt.get("owner", "")
            if not owner:
                continue
            ui = pt.get("uiTokenAmount", {})
            amt = float(ui.get("uiAmountString") or ui.get("amount", "0") or 0)
            owner_deltas[(owner, mint)]["pre"] = amt
            owner_deltas[(owner, mint)]["mint"] = mint

        for pt in post_tokens:
            mint = pt.get("mint", "")
            if mint not in TRACKED_MINTS:
                continue
            owner = pt.get("owner", "")
            if not owner:
                continue
            ui = pt.get("uiTokenAmount", {})
            amt = float(ui.get("uiAmountString") or ui.get("amount", "0") or 0)
            owner_deltas[(owner, mint)]["post"] = amt
            owner_deltas[(owner, mint)]["mint"] = mint

        senders = []
        receivers = []
        for (owner, mint), data in owner_deltas.items():
            delta = data["post"] - data["pre"]
            if abs(delta) < 0.0001:
                continue
            asset = TRACKED_MINTS.get(mint, "SPL")
            token_price = self.token_prices.get(asset, 1.0 if asset in ("USDC", "USDT") else sol_price)
            usd_delta = abs(delta) * token_price
            if usd_delta >= WHALE_THRESHOLD_USD:
                if delta < 0:
                    senders.append({"owner": owner, "amount": abs(delta), "asset": asset, "mint": mint, "usd": usd_delta})
                else:
                    receivers.append({"owner": owner, "amount": abs(delta), "asset": asset, "mint": mint, "usd": usd_delta})

        senders.sort(key=lambda x: x["amount"], reverse=True)
        receivers.sort(key=lambda x: x["amount"], reverse=True)
        paired_senders = set()
        paired_receivers = set()

        for s in senders:
            for r in receivers:
                if r["asset"] != s["asset"]:
                    continue
                if r["owner"] == s["owner"]:
                    continue
                if id(s) in paired_senders or id(r) in paired_receivers:
                    continue
                amt = min(s["amount"], r["amount"])
                usd = amt * (s["usd"] / s["amount"])
                already = any(
                    t["tx_hash"] == tx_hash and t["asset"] == s["asset"] and
                    abs(t["amount"] - amt) < 0.001
                    for t in out
                )
                if not already:
                    out.append(self._build_transfer_record(
                        ts, s["asset"], amt, usd, s["owner"], r["owner"],
                        tx_hash, "spl_balance_delta", protocol, fee_lamports, compute_units, source_address
                    ))
                paired_senders.add(id(s))
                paired_receivers.add(id(r))
                break

       
        for (owner, mint), data in owner_deltas.items():
            delta = data["post"] - data["pre"]
            if abs(delta) < 0.0001:
                continue
            asset = TRACKED_MINTS.get(mint, "SPL")
            token_price = self.token_prices.get(asset, 1.0 if asset in ("USDC", "USDT") else sol_price)
            usd_delta = abs(delta) * token_price
            if usd_delta >= MEGA_WHALE_THRESHOLD_USD:
                already = any(
                    t["tx_hash"] == tx_hash and t["asset"] == asset and
                    abs(t["amount"] - abs(delta)) < 0.001
                    for t in out
                )
                if not already:
                    from_addr = owner if delta < 0 else "mint/burn/unknown"
                    to_addr = owner if delta > 0 else "mint/burn/unknown"
                    out.append(self._build_transfer_record(
                        ts, asset, abs(delta), usd_delta, from_addr, to_addr,
                        tx_hash, "unpaired_delta", protocol, fee_lamports, compute_units, source_address
                    ))

        return out

    def _build_transfer_record(self, ts, asset, amount, usd_value, from_addr, to_addr,
                               tx_hash, source, protocol, fee_lamports, compute_units, watch_source) -> Dict[str, Any]:
        from_tier = "mega_whale" if usd_value >= MEGA_WHALE_THRESHOLD_USD else "institutional" if usd_value >= WHALE_THRESHOLD_USD else "retail"
        to_tier = from_tier
        impact_score = min(100, (usd_value / 10000) * 5)
        liquidity_pressure = "extreme" if usd_value >= 1_000_000 else "high" if usd_value >= 100_000 else "medium" if usd_value >= 10_000 else "low"
        slippage = round(0.05 + (usd_value / 100_000) * 0.2, 2) if asset == "SOL" else 0.0

        return {
            "time": ts,
            "asset": asset,
            "amount": round(amount, 9),
            "raw_qty": round(usd_value, 2),
            "from_address": from_addr,
            "to_address": to_addr,
            "tx_hash": tx_hash,
            "source": source,
            "protocol": protocol or "unknown",
            "from_tier": from_tier,
            "to_tier": to_tier,
            "from_type": "unknown",
            "to_type": "unknown",
            "risk_flag": "high_impact" if usd_value >= MEGA_WHALE_THRESHOLD_USD else "medium_impact" if usd_value >= WHALE_THRESHOLD_USD else "none",
            "impact_score": round(impact_score, 1),
            "liquidity_pressure": liquidity_pressure,
            "slippage_estimate": slippage,
            "fee_sol": round(fee_lamports / 1e9, 9),
            "compute_units": compute_units or 0,
            "watch_source": watch_source,
        }

  
    async def fetch_whales_from_address(self, client: httpx.AsyncClient, address: str, sol_price: float, limit: int = 30) -> List[Dict[str, Any]]:
        sigs = await self._fetch_signatures(client, address, limit)
        if not sigs:
            logging.warning(f"No signatures for {address[:20]}...")
            return []

        valid_sigs = [s["signature"] for s in sigs if not s.get("err")]
        if not valid_sigs:
            logging.warning(f"All {len(sigs)} txs failed for {address[:20]}...")
            return []

        tasks = [self._fetch_transaction(client, sig) for sig in valid_sigs[:limit]]
        txs = await asyncio.gather(*tasks, return_exceptions=True)

        whales = []
        seen_hashes = set()
        for tx in txs:
            if isinstance(tx, Exception) or not tx:
                continue
            tx_hash = ""
            tx_data = tx.get("transaction", {}) if isinstance(tx.get("transaction"), dict) else tx
            if isinstance(tx_data, dict):
                sigs_list = tx_data.get("signatures", [])
                if sigs_list:
                    tx_hash = sigs_list[0]
            if not tx_hash and isinstance(tx, dict):
                tx_hash = tx.get("signature", "")
            if not tx_hash:
                continue
            if tx_hash in seen_hashes:
                continue
            seen_hashes.add(tx_hash)
            transfers = self.extract_transfers(tx, sol_price, address)
            for t in transfers:
                whales.append(t)
                proto = t.get("protocol", "unknown")
                self.protocol_volumes[proto] += t["raw_qty"]
                self.protocol_tx_counts[proto] += 1

        logging.info(f"Address {address[:20]}... found {len(whales)} whale transfers from {len(valid_sigs)} valid txs")
        return whales

   
    async def fetch_all_whales(self, client: httpx.AsyncClient, sol_price: float) -> List[Dict[str, Any]]:
        all_whales = []
        seen = set()

        
        watch_addrs = [a for a in REAL_WATCH_ADDRESSES if len(a) == 44]
        if watch_addrs:
            logging.info(f"Watching {len(watch_addrs)} user-provided addresses...")
            tasks = [self.fetch_whales_from_address(client, addr, sol_price, limit=30) for addr in watch_addrs]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for whales in results:
                if isinstance(whales, Exception):
                    logging.error(f"Error in whale fetch: {whales}")
                    continue
                for w in whales:
                    key = (w["time"], w["asset"], w["amount"], w["from_address"], w["to_address"], w["tx_hash"])
                    if key not in seen:
                        seen.add(key)
                        all_whales.append(w)

       
        if len(all_whales) < 10:
            discovery_programs = [
                ("JUP6LkbZbjS1jKKtdU6jq5p2faT7gHM7UNPFKQf6zxx", "Jupiter"),
                ("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8", "Raydium"),
                ("whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc", "Orca"),
                ("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P", "Pump.fun"),
            ]

            for prog_id, name in discovery_programs:
                if len(all_whales) >= 20:
                    break
                logging.info(f"Discovery mode: scanning {name}...")
                try:
                    discovered = await self.discover_whales_from_program(client, prog_id, limit=25)
                except Exception as e:
                    logging.warning(f"Discovery from {name} failed: {e}")
                    continue
                if discovered:
                    logging.info(f"Discovered {len(discovered)} candidates from {name}")
                    disc_tasks = [self.fetch_whales_from_address(client, addr, sol_price, limit=15) for addr in discovered[:8]]
                    disc_results = await asyncio.gather(*disc_tasks, return_exceptions=True)
                    for whales in disc_results:
                        if isinstance(whales, Exception):
                            continue
                        for w in whales:
                            key = (w["time"], w["asset"], w["amount"], w["from_address"], w["to_address"], w["tx_hash"])
                            if key not in seen:
                                seen.add(key)
                                all_whales.append(w)

      
        if len(all_whales) < 10:
            logging.info("Discovery mode: scanning top USDC holders...")
            try:
                usdc_holders = await self.discover_top_token_holders(client, "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", min_balance=5000)
            except Exception as e:
                logging.warning(f"USDC holder discovery failed: {e}")
                usdc_holders = []
            if usdc_holders:
                logging.info(f"Discovered {len(usdc_holders)} USDC whale holders")
                disc_tasks = [self.fetch_whales_from_address(client, addr, sol_price, limit=15) for addr in usdc_holders[:8]]
                disc_results = await asyncio.gather(*disc_tasks, return_exceptions=True)
                for whales in disc_results:
                    if isinstance(whales, Exception):
                        continue
                    for w in whales:
                        key = (w["time"], w["asset"], w["amount"], w["from_address"], w["to_address"], w["tx_hash"])
                        if key not in seen:
                            seen.add(key)
                            all_whales.append(w)

        all_whales.sort(key=lambda x: x["raw_qty"], reverse=True)
        return all_whales[:200]

   
    async def fetch_sol_price(self, client: httpx.AsyncClient) -> float:
        try:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "solana", "vs_currencies": "usd"},
                timeout=10.0,
            )
            resp.raise_for_status()
            price = resp.json().get("solana", {}).get("usd", 0.0)
            if price:
                self.token_prices["SOL"] = price
                self.token_prices["stSOL"] = price * 1.05
                self.token_prices["mSOL"] = price * 1.08
                self.token_prices["JitoSOL"] = price * 1.06
                self.token_prices["bSOL"] = price * 1.04
                return price
        except Exception as e:
            logging.warning(f"CoinGecko failed: {e}")
        return 70.0

    
    def save_whales(self, whales: List[Dict[str, Any]]):
        if not whales:
            logging.info("No Solana whales to save")
            return
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM SOL_WHALE_EVENTS")
            cursor.executemany(
                """
                INSERT INTO SOL_WHALE_EVENTS (
                    tx_hash, event_timestamp, token, amount, usd_value,
                    from_address, to_address, protocol, from_tier, to_tier,
                    from_type, to_type, risk_flag, impact_score,
                    liquidity_pressure, slippage_estimate, fee_sol,
                    compute_units, watch_source, direction
                ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15, :16, :17, :18, :19, :20)
                """,
                [
                    (
                        str(w.get("tx_hash", ""))[:100],
                        str(w.get("time", utc_now_str()))[:50],
                        str(w.get("asset", "SOL")).upper()[:20],
                        float(w.get("amount", 0)),
                        float(w.get("raw_qty", 0)),
                        str(w.get("from_address", "Unknown"))[:50],
                        str(w.get("to_address", "Unknown"))[:50],
                        str(w.get("protocol", "unknown"))[:50],
                        str(w.get("from_tier", "unknown"))[:20],
                        str(w.get("to_tier", "unknown"))[:20],
                        str(w.get("from_type", "unknown"))[:20],
                        str(w.get("to_type", "unknown"))[:20],
                        str(w.get("risk_flag", "none"))[:20],
                        float(w.get("impact_score", 0)),
                        str(w.get("liquidity_pressure", "low"))[:20],
                        float(w.get("slippage_estimate", 0)),
                        float(w.get("fee_sol", 0)),
                        int(w.get("compute_units", 0) or 0),
                        str(w.get("watch_source", ""))[:50],
                        f"{str(w.get('from_address', ''))[:20]}... -> {str(w.get('to_address', ''))[:20]}...",
                    )
                    for w in whales
                ],
            )
            conn.commit()
            logging.info(f"Saved {len(whales)} whale events to DB")
        except Exception as e:
            logging.error(f"Save whales failed: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def save_protocol_analytics(self):
        if not self.protocol_volumes:
            return
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM SOL_PROTOCOL_ANALYTICS")
            total_vol = sum(self.protocol_volumes.values())
            rows = []
            for proto, vol in self.protocol_volumes.items():
                tx_count = self.protocol_tx_counts.get(proto, 0)
                dominance = round((vol / total_vol) * 100, 2) if total_vol > 0 else 0
                rows.append((
                    proto[:50], round(vol, 2), tx_count,
                    round(vol / max(tx_count, 1), 2), tx_count, dominance
                ))
            cursor.executemany(
                """
                INSERT INTO SOL_PROTOCOL_ANALYTICS (
                    protocol, volume_usd_24h, tx_count, avg_tx_size,
                    whale_count, dominance_pct, computed_at
                ) VALUES (:1, :2, :3, :4, :5, :6, CURRENT_TIMESTAMP)
                """, rows
            )
            conn.commit()
            logging.info(f"Saved {len(rows)} protocol analytics rows")
        except Exception as e:
            logging.error(f"Save protocol analytics failed: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def save_market_intelligence(self, whales: List[Dict[str, Any]]):
        if not whales:
            return
        total_volume = sum(w["raw_qty"] for w in whales)
        sol_volume = sum(w["raw_qty"] for w in whales if w["asset"] == "SOL")
        stable_volume = sum(w["raw_qty"] for w in whales if w["asset"] in ("USDC", "USDT"))
        mega_whales = sum(1 for w in whales if w["raw_qty"] >= MEGA_WHALE_THRESHOLD_USD)
        high_impact = sum(1 for w in whales if w.get("impact_score", 0) >= 50)
        sorted_whales = sorted(whales, key=lambda x: x["raw_qty"], reverse=True)
        top_5_pct = sum(w["raw_qty"] for w in sorted_whales[:5]) / max(total_volume, 1) * 100
        avg_impact = sum(w.get("impact_score", 0) for w in whales) / max(len(whales), 1)
        dominant = max(self.protocol_volumes.keys(), key=lambda k: self.protocol_volumes[k], default="unknown")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM SOL_MARKET_INTELLIGENCE")
            cursor.execute(
                """
                INSERT INTO SOL_MARKET_INTELLIGENCE (
                    computed_at, total_whale_volume_usd, sol_volume_usd, stable_volume_usd,
                    whale_count, mega_whale_count, high_impact_count,
                    top_5_concentration_pct, avg_impact_score, dominant_protocol,
                    market_stress_index, signal_label
                ) VALUES (CURRENT_TIMESTAMP, :1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11)
                """,
                (
                    round(total_volume, 2), round(sol_volume, 2), round(stable_volume, 2),
                    len(whales), mega_whales, high_impact,
                    round(top_5_pct, 2), round(avg_impact, 2), dominant[:50],
                    round(min(100, high_impact * 10 + top_5_pct / 2), 2),
                    "institutional_flow_active" if total_volume > 500_000 else "normal_flow",
                )
            )
            conn.commit()
            logging.info(f"Saved market intelligence: {len(whales)} whales, ${total_volume:,.0f} volume")
        except Exception as e:
            logging.error(f"Save market intelligence failed: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def ensure_tables(self):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            tables = {
                "SOL_WHALE_EVENTS": """
                    CREATE TABLE SOL_WHALE_EVENTS (
                        tx_hash VARCHAR2(100), event_timestamp VARCHAR2(50),
                        token VARCHAR2(20), amount NUMBER, usd_value NUMBER,
                        from_address VARCHAR2(50), to_address VARCHAR2(50),
                        protocol VARCHAR2(50), from_tier VARCHAR2(20), to_tier VARCHAR2(20),
                        from_type VARCHAR2(20), to_type VARCHAR2(20), risk_flag VARCHAR2(20),
                        impact_score NUMBER, liquidity_pressure VARCHAR2(20),
                        slippage_estimate NUMBER, fee_sol NUMBER, compute_units NUMBER,
                        watch_source VARCHAR2(50), direction VARCHAR2(100)
                    )""",
                "SOL_PROTOCOL_ANALYTICS": """
                    CREATE TABLE SOL_PROTOCOL_ANALYTICS (
                        protocol VARCHAR2(50), volume_usd_24h NUMBER, tx_count NUMBER,
                        avg_tx_size NUMBER, whale_count NUMBER, dominance_pct NUMBER, computed_at TIMESTAMP
                    )""",
                "SOL_MARKET_INTELLIGENCE": """
                    CREATE TABLE SOL_MARKET_INTELLIGENCE (
                        computed_at TIMESTAMP, total_whale_volume_usd NUMBER, sol_volume_usd NUMBER,
                        stable_volume_usd NUMBER, whale_count NUMBER, mega_whale_count NUMBER,
                        high_impact_count NUMBER, top_5_concentration_pct NUMBER, avg_impact_score NUMBER,
                        dominant_protocol VARCHAR2(50), market_stress_index NUMBER, signal_label VARCHAR2(50)
                    )""",
            }
            for table_name, ddl in tables.items():
                cursor.execute(f"SELECT COUNT(*) FROM user_tables WHERE table_name = '{table_name}'")
                if cursor.fetchone()[0] == 0:
                    cursor.execute(ddl)
                    logging.info(f"Created {table_name}")
            conn.commit()
        except Exception as e:
            logging.error(f"Table creation failed: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    logging.info("=" * 60)
    logging.info("ASYNCSIGNALS SOLANA — REAL WHALE INTELLIGENCE")
    logging.info("=" * 60)

    collector = SolanaCollector()
    collector.ensure_tables()

    limits = httpx.Limits(max_keepalive_connections=8, max_connections=16)
    timeout = httpx.Timeout(30.0, connect=15.0)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        sol_price = await collector.fetch_sol_price(client)
        logging.info(f"SOL spot price: ${sol_price}")
        logging.info(f"Thresholds: {WHALE_THRESHOLD_SOL} SOL / ${WHALE_THRESHOLD_USD:,.0f} USD")
        logging.info(f"Mega: {MEGA_WHALE_THRESHOLD_SOL} SOL / ${MEGA_WHALE_THRESHOLD_USD:,.0f} USD")
        logging.info("-" * 60)

        whales = await collector.fetch_all_whales(client, sol_price)

        logging.info("-" * 60)
        logging.info(f"TOTAL WHALES CAPTURED: {len(whales)}")

        proto_breakdown = defaultdict(lambda: {"count": 0, "volume": 0.0})
        for w in whales:
            proto = w.get("protocol", "unknown")
            proto_breakdown[proto]["count"] += 1
            proto_breakdown[proto]["volume"] += w["raw_qty"]
        logging.info("PROTOCOL BREAKDOWN:")
        for proto, stats in sorted(proto_breakdown.items(), key=lambda x: x[1]["volume"], reverse=True)[:10]:
            logging.info(f"  {proto}: {stats['count']} txs, ${stats['volume']:,.0f}")

        tier_counts = defaultdict(int)
        for w in whales:
            tier_counts[w.get("from_tier", "unknown")] += 1
        logging.info("TIER BREAKDOWN:")
        for tier, count in sorted(tier_counts.items(), key=lambda x: x[1], reverse=True):
            logging.info(f"  {tier}: {count}")

        logging.info("-" * 60)
        logging.info("TOP 10 FLOWS:")
        for i, w in enumerate(whales[:10], 1):
            flag = "🚨" if w.get("risk_flag") == "high_impact" else "⚡" if w.get("impact_score", 0) > 30 else "  "
            logging.info(
                f"  {flag} #{i} {w['asset']} ${w['raw_qty']:,.0f} | "
                f"{w['from_address'][:16]}... -> {w['to_address'][:16]}... | "
                f"{w.get('protocol', 'unknown')} | src={w['source']}"
            )

        collector.save_whales(whales)
        collector.save_protocol_analytics()
        collector.save_market_intelligence(whales)

        logging.info("-" * 60)
        logging.info("Collection complete.")
        logging.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
