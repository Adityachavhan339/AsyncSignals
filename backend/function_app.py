import os
import asyncio
import logging
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

import httpx
import oracledb
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

COINGECKO_KEY = os.getenv("COINGECKO_KEY")
NEWSDATA_KEY = os.getenv("NEWSDATA_KEY")
ALCHEMY_KEY = os.getenv("ALCHEMY_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SOLANA_DRPC_URL = os.getenv("SOLANA_DRPC_URL")

SOL_MINT = "So11111111111111111111111111111111111111112"
SIGNAL_TS_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_connection():
    return oracledb.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dsn="asyncsignalsdatabase_medium",
        config_dir="/home/daniel/wallet",
        wallet_location="/home/daniel/wallet",
        wallet_password=os.getenv("DB_PASSWORD"),
    )


def utc_now_str() -> str:
    return datetime.now(UTC).strftime(SIGNAL_TS_FORMAT)


def blocktime_to_str(block_time: Optional[int]) -> str:
    if not block_time:
        return utc_now_str()
    return datetime.fromtimestamp(block_time, UTC).strftime(SIGNAL_TS_FORMAT)

class AsyncSignalBot:
    def __init__(self):
        self.headers_cg = {"x-cg-demo-api-key": COINGECKO_KEY} if COINGECKO_KEY else {}
        self.headers_news = {"X-ACCESS-KEY": NEWSDATA_KEY} if NEWSDATA_KEY else {}

    def save_to_db(self, table: str, data: List[Dict[str, Any]]):
        if not data:
            return

        conn = get_connection()
        cursor = conn.cursor()

        try:
            if table in {"prices", "news", "whales", "paprika"}:
                cursor.execute(f"DELETE FROM {table}")

            if table == "prices":
                cursor.executemany(
                    """
                    INSERT INTO prices (symbol, current_price, market_cap, price_change_percentage_24h)
                    VALUES (:1, :2, :3, :4)
                    """,
                    [
                        (
                            str(row.get("symbol", "")).lower()[:20],
                            float(row.get("current_price") or 0),
                            float(row.get("market_cap") or 0),
                            float(row.get("price_change_percentage_24h") or 0),
                        )
                        for row in data
                    ],
                )

            elif table == "news":
                cursor.executemany(
                    """
                    INSERT INTO news (title, source_id, pubDate, description, link)
                    VALUES (:1, :2, :3, :4, :5)
                    """,
                    [
                        (
                            str(row.get("title", ""))[:500],
                            str(row.get("source_id", ""))[:100],
                            str(row.get("pubDate", ""))[:100],
                            str(row.get("description", "")),
                            str(row.get("link", ""))[:500],
                        )
                        for row in data
                    ],
                )

            elif table == "whales":
                cursor.executemany(
                    """
                    INSERT INTO whales (time, asset, amount, raw_qty, from_address, to_address)
                    VALUES (:1, :2, :3, :4, :5, :6)
                    """,
                    [
                        (
                            str(row.get("time") or row.get("timestamp") or utc_now_str())[:100],
                            str(row.get("asset", "")).upper()[:20],
                            float(row.get("amount") or 0),
                            float(row.get("raw_qty") or row.get("value_usd") or 0),
                            str(row.get("from_address", "Unknown"))[:50],
                            str(row.get("to_address", "Unknown"))[:50],
                        )
                        for row in data
                    ],
                )

            elif table == "paprika":
                cursor.executemany(
                    """
                    INSERT INTO paprika (symbol, name, price)
                    VALUES (:1, :2, :3)
                    """,
                    [
                        (
                            str(row.get("Symbol", "")).upper()[:20],
                            str(row.get("Name", ""))[:100],
                            float(row.get("Price") or 0),
                        )
                        for row in data
                    ],
                )

            elif table == "ai_summaries":
                cursor.executemany(
                    """
                    INSERT INTO ai_summaries (asset, summary, timestamp)
                    VALUES (:1, :2, :3)
                    """,
                    [
                        (
                            str(row.get("asset", "")).upper()[:20],
                            str(row.get("summary", ""))[:4000],
                            str(row.get("timestamp", utc_now_str()))[:50],
                        )
                        for row in data
                    ],
                )

            elif table == "signals":
                cursor.executemany(
                    """
                    INSERT INTO signals (type, msg, timestamp, entry_price, exit_price, status)
                    VALUES (:1, :2, :3, :4, :5, :6)
                    """,
                    [
                        (
                            str(row.get("type", ""))[:100],
                            str(row.get("msg", ""))[:500],
                            str(row.get("timestamp", utc_now_str()))[:50],
                            float(row.get("entry_price") or 0),
                            float(row.get("exit_price") or 0),
                            str(row.get("status", "Pending"))[:50],
                        )
                        for row in data
                    ],
                )

            conn.commit()
            print(f"Inserted into {table}: {len(data)} rows")

        except Exception as e:
            conn.rollback()
            logging.exception(f"DB write failed for {table}: {e}")
        finally:
            cursor.close()
            conn.close()

    def check_db_counts(self):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            for table in ["prices", "news", "whales", "signals", "ai_summaries", "paprika"]:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                print(f"{table}: {cursor.fetchone()[0]}")
        except Exception as e:
            logging.exception(f"COUNT CHECK FAILED: {e}")
        finally:
            cursor.close()
            conn.close()

    async def fetch_prices_cg(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 50,
            "page": 1,
            "sparkline": False,
            "x_cg_demo_api_key": COINGECKO_KEY,
        }
        try:
            resp = await client.get(url, params=params, headers=self.headers_cg)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logging.warning(f"CoinGecko fetch failed: {e}")
            return []

    async def fetch_prices_paprika(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        url = "https://api.coinpaprika.com/v1/tickers"
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (AsyncSignalBot/2.0)",
        }
        try:
            resp = await client.get(url, params={"limit": "50"}, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                return []
            return [
                {
                    "Symbol": str(coin.get("symbol", "")).upper(),
                    "Name": coin.get("name"),
                    "Price": float(coin.get("quotes", {}).get("USD", {}).get("price", 0) or 0),
                }
                for coin in data
            ]
        except Exception as e:
            logging.warning(f"CoinPaprika fetch failed: {e}")
            return []

    async def fetch_crypto_news(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        url = "https://newsdata.io/api/1/news"
        params = {
            "apikey": NEWSDATA_KEY,
            "q": "crypto OR bitcoin OR ethereum OR solana",
            "language": "en",
        }
        try:
            resp = await client.get(url, params=params, headers=self.headers_news)
            resp.raise_for_status()
            return resp.json().get("results", [])[:25]
        except Exception as e:
            logging.warning(f"News fetch failed: {e}")
            return []

    def build_price_lookup(self, prices: List[Dict[str, Any]], paprika: List[Dict[str, Any]]) -> Dict[str, float]:
        lookup = {}
        for p in prices:
            sym = str(p.get("symbol", "")).upper().strip()
            if sym:
                lookup[sym] = float(p.get("current_price") or 0)

        for p in paprika:
            sym = str(p.get("Symbol", "")).upper().strip()
            if sym and sym not in lookup:
                lookup[sym] = float(p.get("Price") or 0)

        stablecoins = ["USDT", "USDC", "DAI", "USDE", "FDUSD", "USDD", "PYUSD", "TUSD"]
        for s in stablecoins:
            lookup[s] = 1.0

        return lookup

    async def fetch_evm_whales(self, client: httpx.AsyncClient, price_lookup: Dict[str, float]) -> List[Dict[str, Any]]:
        if not ALCHEMY_KEY:
            logging.warning("ALCHEMY_KEY missing. Skipping EVM whales.")
            return []

        url = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}"

        try:
            latest_block_resp = await client.post(
                url,
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
            )
            latest_block_resp.raise_for_status()
            latest_block_hex = latest_block_resp.json().get("result", "0x0")
            latest_block_number = int(latest_block_hex, 16)

            recent_blocks = 600
            from_block_hex = hex(max(latest_block_number - recent_blocks, 0))

            payload = {
                "id": 1,
                "jsonrpc": "2.0",
                "method": "alchemy_getAssetTransfers",
                "params": [{
                    "fromBlock": from_block_hex,
                    "toBlock": latest_block_hex,
                    "category": ["external", "erc20"],
                    "withMetadata": True,
                    "excludeZeroValue": True,
                    "maxCount": "0x3E8",
                    "order": "desc"
                }]
            }

            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            transfers = resp.json().get("result", {}).get("transfers", [])

            whale_data = []
            for tx in transfers:
                asset = str(tx.get("asset", "")).upper().strip()
                amount = float(tx.get("value") or 0)
                token_price = price_lookup.get(asset, 0.0)
                usd_value = amount * token_price

                valid_transfer = (
                    (asset in ["ETH", "WETH"] and amount >= 5) or
                    (asset in ["BTC", "WBTC"] and amount >= 0.5) or
                    (usd_value >= 25000)
                )

                if valid_transfer:
                    whale_data.append({
                        "time": str(tx.get("metadata", {}).get("blockTimestamp") or utc_now_str()),
                        "asset": asset,
                        "amount": amount,
                        "raw_qty": usd_value,
                        "from_address": str(tx.get("from", "Unknown")),
                        "to_address": str(tx.get("to", "Unknown")),
                    })

            return whale_data[:60]

        except Exception as e:
            logging.exception(f"Alchemy EVM whale fetch failed: {e}")
            return []

    async def fetch_solana_signatures(self, client: httpx.AsyncClient, limit: int = 20) -> List[Dict[str, Any]]:
        if not SOLANA_DRPC_URL:
            logging.warning("SOLANA_DRPC_URL missing. Skipping Solana.")
            return []

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [SOL_MINT, {"limit": limit}],
        }

        try:
            resp = await client.post(SOLANA_DRPC_URL, json=payload, timeout=20.0)
            resp.raise_for_status()
            return resp.json().get("result", []) or []
        except Exception as e:
            logging.warning(f"Solana signatures fetch failed: {e}")
            return []

    async def fetch_solana_tx(self, client: httpx.AsyncClient, signature: str) -> Optional[Dict[str, Any]]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0,
                },
            ],
        }
        try:
            resp = await client.post(SOLANA_DRPC_URL, json=payload, timeout=25.0)
            resp.raise_for_status()
            return resp.json().get("result")
        except Exception as e:
            logging.warning(f"Solana tx fetch failed for {signature[:14]}...: {e}")
            return None

    def extract_solana_whales_from_tx(self, tx: Dict[str, Any], sol_usd_price: float) -> List[Dict[str, Any]]:
        if not tx:
            return []

        out = []
        block_time = blocktime_to_str(tx.get("blockTime"))
        transaction = tx.get("transaction", {})
        message = transaction.get("message", {})
        account_keys_raw = message.get("accountKeys", [])
        meta = tx.get("meta", {}) or {}

        account_keys = []
        for k in account_keys_raw:
            if isinstance(k, dict):
                account_keys.append(k.get("pubkey"))
            else:
                account_keys.append(k)

        instructions = message.get("instructions", []) or []
        for ins in instructions:
            if ins.get("program") == "system":
                parsed = ins.get("parsed", {})
                if parsed.get("type") == "transfer":
                    info = parsed.get("info", {})
                    lamports = float(info.get("lamports") or 0)
                    sol_amount = lamports / 1_000_000_000
                    usd_value = sol_amount * sol_usd_price
                    if sol_amount >= 1 or usd_value >= 100:   
                        out.append({
                            "time": block_time,
                            "asset": "SOL",
                            "amount": round(sol_amount, 9),
                            "raw_qty": round(usd_value, 2),
                            "from_address": str(info.get("source", "Unknown")),
                            "to_address": str(info.get("destination", "Unknown")),
                        })

        pre_token_balances = meta.get("preTokenBalances", []) or []
        post_token_balances = meta.get("postTokenBalances", []) or []

        pre_map = {}
        for item in pre_token_balances:
            if item.get("mint") != SOL_MINT:
                continue
            idx = item.get("accountIndex")
            owner = item.get("owner", "Unknown")
            amount = float(item.get("uiTokenAmount", {}).get("uiAmountString") or 0)
            pre_map[idx] = {"owner": owner, "amount": amount}

        post_map = {}
        for item in post_token_balances:
            if item.get("mint") != SOL_MINT:
                continue
            idx = item.get("accountIndex")
            owner = item.get("owner", "Unknown")
            amount = float(item.get("uiTokenAmount", {}).get("uiAmountString") or 0)
            post_map[idx] = {"owner": owner, "amount": amount}

        token_deltas = []
        for idx in set(pre_map.keys()) | set(post_map.keys()):
            pre_amt = pre_map.get(idx, {}).get("amount", 0.0)
            post_amt = post_map.get(idx, {}).get("amount", 0.0)
            delta = round(post_amt - pre_amt, 9)
            owner = post_map.get(idx, {}).get("owner") or pre_map.get(idx, {}).get("owner") or "Unknown"
            if abs(delta) > 0:
                token_deltas.append({"index": idx, "owner": owner, "delta": delta})

        senders = [x for x in token_deltas if x["delta"] < 0]
        receivers = [x for x in token_deltas if x["delta"] > 0]

        senders = sorted(senders, key=lambda x: abs(x["delta"]), reverse=True)
        receivers = sorted(receivers, key=lambda x: abs(x["delta"]), reverse=True)

        pair_count = min(len(senders), len(receivers), 3)
        for i in range(pair_count):
            amount = min(abs(senders[i]["delta"]), abs(receivers[i]["delta"]))
            usd_value = amount * sol_usd_price
            if amount >= 1 or usd_value >= 100:
                row = {
                    "time": block_time,
                    "asset": "SOL",
                    "amount": round(amount, 9),
                    "raw_qty": round(usd_value, 2),
                    "from_address": str(senders[i]["owner"]),
                    "to_address": str(receivers[i]["owner"]),
                }
                duplicate = any(
                    r["asset"] == row["asset"]
                    and r["from_address"] == row["from_address"]
                    and r["to_address"] == row["to_address"]
                    and abs(float(r["amount"]) - float(row["amount"])) < 1e-9
                    for r in out
                )
                if not duplicate:
                    out.append(row)
        
        return out

    async def fetch_solana_whales(self, client: httpx.AsyncClient, sol_usd_price: float) -> List[Dict[str, Any]]:
        signatures = await self.fetch_solana_signatures(client, limit=18)
        if not signatures:
            return []

        sig_values = [s.get("signature") for s in signatures if s.get("signature")]
        txs = await asyncio.gather(*[self.fetch_solana_tx(client, s) for s in sig_values])

        all_rows = []
        seen = set()

        for tx in txs:
            rows = self.extract_solana_whales_from_tx(tx, sol_usd_price)
            for row in rows:
                key = (
                    row["time"],
                    row["asset"],
                    round(float(row["amount"]), 9),
                    row["from_address"],
                    row["to_address"],
                )
                if key not in seen:
                    seen.add(key)
                    all_rows.append(row)

        all_rows = sorted(all_rows, key=lambda x: float(x.get("raw_qty", 0)), reverse=True)
        return all_rows[:40]

    def get_last_alert_prices(self) -> Dict[str, float]:
        last_alert_prices = {"DANGER": 0.0, "OPPORTUNITY": 0.0}
        conn = None
        try:
            conn = get_connection()
            df_recent = pd.read_sql(
                """
                SELECT type, entry_price
                FROM (
                    SELECT type, entry_price
                    FROM signals
                    WHERE type IN ('🚨 DANGER', '🚀 OPPORTUNITY')
                    ORDER BY timestamp DESC
                )
                FETCH FIRST 20 ROWS ONLY
                """,
                conn,
            )

            if not df_recent.empty:
                df_recent.columns = [c.lower() for c in df_recent.columns]

                danger_rows = df_recent[df_recent["type"].astype(str).str.contains("DANGER", na=False)]
                if not danger_rows.empty:
                    last_alert_prices["DANGER"] = float(danger_rows.iloc[0]["entry_price"] or 0)

                opp_rows = df_recent[df_recent["type"].astype(str).str.contains("OPPORTUNITY", na=False)]
                if not opp_rows.empty:
                    last_alert_prices["OPPORTUNITY"] = float(opp_rows.iloc[0]["entry_price"] or 0)

        except Exception as e:
            logging.warning(f"Recent alert lookup skipped: {e}")
        finally:
            if conn:
                conn.close()

        return last_alert_prices

    def generate_signals(
        self,
        news: List[Dict[str, Any]],
        whales: List[Dict[str, Any]],
        prices: List[Dict[str, Any]],
        last_alert_prices: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        if last_alert_prices is None:
            last_alert_prices = {"DANGER": 0.0, "OPPORTUNITY": 0.0}

        if not prices:
            return []

        btc_price = 0.0
        btc_change = 0.0
        sol_price = 0.0

        for p in prices:
            sym = str(p.get("symbol", "")).lower()
            if sym == "btc":
                btc_price = float(p.get("current_price") or 0)
                btc_change = float(p.get("price_change_percentage_24h") or 0)
            elif sym == "sol":
                sol_price = float(p.get("current_price") or 0)

        top_headline = "No breaking news detected."
        if news:
            top_headline = str(news[0].get("title", "No breaking news detected.")).strip()

        total_whale_usd = sum(float(w.get("raw_qty") or 0) for w in whales)
        sol_whale_usd = sum(float(w.get("raw_qty") or 0) for w in whales if str(w.get("asset", "")).upper() == "SOL")
        whale_count = len(whales)
        sol_whale_count = sum(1 for w in whales if str(w.get("asset", "")).upper() == "SOL")

        danger_delta = 100.0
        if last_alert_prices["DANGER"] > 0:
            danger_delta = abs(((btc_price - last_alert_prices["DANGER"]) / last_alert_prices["DANGER"]) * 100)

        opp_delta = 100.0
        if last_alert_prices["OPPORTUNITY"] > 0:
            opp_delta = abs(((btc_price - last_alert_prices["OPPORTUNITY"]) / last_alert_prices["OPPORTUNITY"]) * 100)

        signals = []

        if btc_change <= -0.75 and total_whale_usd >= 250000 and danger_delta >= 0.5:
            signals.append({
                "type": "🚨 DANGER",
                "msg": f"BTC down {btc_change:.2f}% with ${total_whale_usd:,.0f} whale flow. Top story: {top_headline}",
            })
        elif btc_change >= 0.75 and total_whale_usd >= 250000 and opp_delta >= 0.5:
            signals.append({
                "type": "🚀 OPPORTUNITY",
                "msg": f"BTC up {btc_change:.2f}% with ${total_whale_usd:,.0f} whale flow. Top story: {top_headline}",
            })

        if sol_whale_count >= 2 and sol_whale_usd >= 10000 and sol_price > 0:
            signals.append({
                "type": "🟣 SOL FLOW",
                "msg": f"{sol_whale_count} real SOL transfers detected totaling ${sol_whale_usd:,.0f}. SOL spot: ${sol_price:,.2f}",
            })
        elif whale_count >= 5 and total_whale_usd >= 500000:
            signals.append({
                "type": "🐋 WHALE VOLATILITY",
                "msg": f"{whale_count} whale transfers detected totaling ${total_whale_usd:,.0f} USD",
            })

        return signals

    async def broadcast_signals(self, client: httpx.AsyncClient, signals: List[Dict[str, Any]]):
        if not TELEGRAM_BOT_TOKEN or not signals:
            return

        def get_subscribers():
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT chat_id FROM subscribers")
                rows = cursor.fetchall()
                return [r[0] for r in rows]
            finally:
                cursor.close()
                conn.close()

        chat_ids = get_subscribers()

        for chat_id in chat_ids:
            for sig in signals:
                if sig.get("type") in ["🚨 DANGER", "🚀 OPPORTUNITY", "🐋 WHALE VOLATILITY", "🟣 SOL FLOW"]:
                    text = f"*{sig.get('type')}*\n\n{sig.get('msg')}"
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                            json={
                                "chat_id": chat_id,
                                "text": text,
                                "parse_mode": "Markdown",
                            },
                            timeout=15.0,
                        )
                    except Exception as e:
                        logging.warning(f"Telegram send failed: {e}")

    def update_performance_history(self, current_btc_price: float):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT type, timestamp, entry_price, status
                FROM (
                    SELECT type, timestamp, entry_price, status
                    FROM signals
                    ORDER BY timestamp DESC
                )
                FETCH FIRST 50 ROWS ONLY
                """
            )
            rows = cursor.fetchall()

            for sig_type, ts, entry_price, current_status in rows:
                sig_type_original = str(sig_type or "")
                current_status = str(current_status or "Pending").strip()
                sig_type = sig_type_original.upper()
                entry_price = float(entry_price or 0)

                if entry_price == 0:
                    continue
                if "✅" in current_status or "❌" in current_status or "⚪" in current_status:
                    continue

                price_diff = ((current_btc_price - entry_price) / entry_price) * 100
                new_status = None

                if "DANGER" in sig_type:
                    if price_diff <= -0.5:
                        new_status = f"✅ Success ({price_diff:.2f}%)"
                    elif price_diff >= 0.5:
                        new_status = f"❌ Failed (+{price_diff:.2f}%)"

                elif "OPPORTUNITY" in sig_type:
                    if price_diff >= 0.5:
                        new_status = f"✅ Success (+{price_diff:.2f}%)"
                    elif price_diff <= -0.5:
                        new_status = f"❌ Failed ({price_diff:.2f}%)"

                elif "WHALE" in sig_type or "SOL FLOW" in sig_type:
                    new_status = f"⚪ Observed ({price_diff:+.2f}%)"

                if new_status and new_status != current_status:
                    cursor.execute(
                        """
                        UPDATE signals
                        SET status = :1, exit_price = :2
                        WHERE timestamp = :3 AND type = :4
                        """,
                        (new_status[:50], current_btc_price, str(ts), sig_type_original),
                    )

            conn.commit()

        except Exception as e:
            logging.warning(f"Signal history update failed: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    logging.info("AsyncSignals backend starting...")

    bot = AsyncSignalBot()

    limits = httpx.Limits(max_keepalive_connections=10, max_connections=25)
    timeout = httpx.Timeout(30.0, connect=15.0)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        prices_task = bot.fetch_prices_cg(client)
        paprika_task = bot.fetch_prices_paprika(client)
        news_task = bot.fetch_crypto_news(client)

        prices, paprika, news = await asyncio.gather(prices_task, paprika_task, news_task)
        price_lookup = bot.build_price_lookup(prices, paprika)

        evm_whales_task = bot.fetch_evm_whales(client, price_lookup)
        sol_usd = price_lookup.get("SOL", 0.0)
        sol_whales_task = bot.fetch_solana_whales(client, sol_usd)

        evm_whales, sol_whales = await asyncio.gather(evm_whales_task, sol_whales_task)

        all_whales = evm_whales + sol_whales
        all_whales = sorted(all_whales, key=lambda x: float(x.get("raw_qty", 0)), reverse=True)[:100]

        last_alert_prices = bot.get_last_alert_prices()
        signals = bot.generate_signals(news, all_whales, prices, last_alert_prices)

        btc_price = price_lookup.get("BTC", 0.0)
        now_ts = utc_now_str()

        for sig in signals:
            sig["timestamp"] = now_ts
            sig["entry_price"] = btc_price
            sig["exit_price"] = btc_price
            sig["status"] = "Pending"

        logging.info(f"Prices fetched: {len(prices)}")
        logging.info(f"Paprika fetched: {len(paprika)}")
        logging.info(f"News fetched: {len(news)}")
        logging.info(f"EVM whales: {len(evm_whales)}")
        logging.info(f"SOL whales: {len(sol_whales)}")
        logging.info(f"Signals generated: {len(signals)}")

        bot.save_to_db("prices", prices)
        bot.save_to_db("paprika", paprika)
        bot.save_to_db("news", news)
        bot.save_to_db("whales", all_whales)
        if signals:
            bot.save_to_db("signals", signals)

        bot.check_db_counts()

        if btc_price > 0:
            bot.update_performance_history(btc_price)

        await bot.broadcast_signals(client, signals)

    logging.info("AsyncSignals backend finished.")


if __name__ == "__main__":
    asyncio.run(main())
