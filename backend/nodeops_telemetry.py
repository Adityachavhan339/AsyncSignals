import os
import json
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from datetime import timedelta

import httpx
import oracledb
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN", "asyncsignalsdatabase_medium")
WALLET_DIR = os.getenv("WALLET_DIR", "/home/daniel/wallet")

TS_FORMAT = "%Y-%m-%d %H:%M:%S"

# Minimal runbook mapping — 3 codes to prove concept
RUNBOOK_MAP = {
    "NODE_OVERLOADED": {
        "severity": "high",
        "advice": "Increase CPU/memory resources or reduce concurrent job count in node config.",
        "category": "resource",
    },
    "RPC_UNAVAILABLE": {
        "severity": "critical",
        "advice": "Failover to backup RPC endpoint. Check network connectivity and RPC provider status.",
        "category": "connectivity",
    },
    "NONCE_TOO_LOW": {
        "severity": "medium",
        "advice": "Clear local mempool queue and reset node nonce tracker. Verify no stuck transactions.",
        "category": "transaction",
    },
    "REPLACEMENT_UNDERPRICED": {
        "severity": "medium",
        "advice": "Increase gas bump parameters in TOML config. Current replacement gas is below network threshold.",
        "category": "gas",
    },
    "INSUFFICIENT_FUNDS": {
        "severity": "critical",
        "advice": "Top up node wallet with native gas token. Review gas spend vs reward ratio.",
        "category": "financial",
    },
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


def resolve_runbook(error_code: str) -> Optional[Dict]:
    """Lookup runbook advice for a given error code."""
    return RUNBOOK_MAP.get(error_code)


def ingest_telemetry(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest a single node telemetry payload and return enriched record."""
    node_id = str(payload.get("node_id", "unknown"))
    chain = str(payload.get("chain", "unknown"))
    ts = payload.get("ts") or utc_now_str()
    jobs_ok = int(payload.get("jobs_ok", 0))
    jobs_failed = int(payload.get("jobs_failed", 0))
    avg_latency_ms = float(payload.get("avg_latency_ms", 0.0))
    gas_spent_native = float(payload.get("gas_spent_native", 0.0))
    rewards_token = float(payload.get("rewards_token", 0.0))
    error_code = str(payload.get("error_code", "")) or None

    total_jobs = jobs_ok + jobs_failed
    success_rate = (jobs_ok / total_jobs * 100) if total_jobs > 0 else 100.0

    runbook = resolve_runbook(error_code) if error_code else None

    record = {
        "node_id": node_id,
        "chain": chain,
        "ts": ts,
        "jobs_ok": jobs_ok,
        "jobs_failed": jobs_failed,
        "success_rate": round(success_rate, 2),
        "avg_latency_ms": round(avg_latency_ms, 2),
        "gas_spent_native": round(gas_spent_native, 6),
        "rewards_token": round(rewards_token, 6),
        "error_code": error_code,
        "runbook_severity": runbook["severity"] if runbook else None,
        "runbook_advice": runbook["advice"] if runbook else None,
        "runbook_category": runbook["category"] if runbook else None,
    }
    return record


def write_telemetry(records: List[Dict]):
    if not records:
        log("No NodeOps telemetry to write")
        return

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.executemany(
            """
            INSERT INTO NODEOPS_METRICS (
                NODE_ID, CHAIN, TS, JOBS_OK, JOBS_FAILED, SUCCESS_RATE,
                AVG_LATENCY_MS, GAS_SPENT_NATIVE, REWARDS_TOKEN, ERROR_CODE,
                RUNBOOK_SEVERITY, RUNBOOK_ADVICE, RUNBOOK_CATEGORY
            ) VALUES (
                :1, :2, TO_TIMESTAMP(:3, 'YYYY-MM-DD HH24:MI:SS'), :4, :5, :6,
                :7, :8, :9, :10, :11, :12, :13
            )
            """,
            [
                (r["node_id"], r["chain"], r["ts"], r["jobs_ok"], r["jobs_failed"],
                 r["success_rate"], r["avg_latency_ms"], r["gas_spent_native"],
                 r["rewards_token"], r["error_code"], r["runbook_severity"],
                 r["runbook_advice"], r["runbook_category"])
                for r in records
            ]
        )
        conn.commit()
        log(f"Wrote {len(records)} NodeOps telemetry rows")
    except Exception as e:
        conn.rollback()
        log(f"NodeOps DB write failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def generate_demo_data(node_count: int = 3, records_per_node: int = 10) -> List[Dict]:
    """Generate simulated telemetry for demo/grant review purposes."""
    import random
    chains = ["ethereum", "avalanche", "base"]
    error_pool = [None, "NODE_OVERLOADED", "RPC_UNAVAILABLE", "NONCE_TOO_LOW", 
                  "REPLACEMENT_UNDERPRICED", "INSUFFICIENT_FUNDS"]

    records = []
    base_time = datetime.now(UTC)

    for n in range(node_count):
        node_id = f"node-{n+1:02d}"
        chain = chains[n % len(chains)]
        for i in range(records_per_node):
            ts = (base_time - timedelta(hours=i)).strftime(TS_FORMAT)
            jobs_ok = random.randint(80, 200)
            jobs_failed = random.randint(0, 15)
            error = random.choice(error_pool)
            if error and random.random() < 0.3:
                jobs_failed += random.randint(5, 20)

            payload = {
                "node_id": node_id,
                "chain": chain,
                "ts": ts,
                "jobs_ok": jobs_ok,
                "jobs_failed": jobs_failed,
                "avg_latency_ms": round(random.uniform(50, 800), 2),
                "gas_spent_native": round(random.uniform(0.01, 0.5), 6),
                "rewards_token": round(random.uniform(0.5, 5.0), 6),
                "error_code": error,
            }
            records.append(ingest_telemetry(payload))

    return records


def export_metrics_csv(node_id: Optional[str] = None, window_hours: int = 24) -> str:
    """Export metrics to CSV string for ops/finance teams."""
    import csv
    import io

    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    cutoff_str = cutoff.strftime(TS_FORMAT)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        if node_id:
            cursor.execute(
                """SELECT * FROM NODEOPS_METRICS 
                   WHERE NODE_ID = :1 AND TS >= TO_TIMESTAMP(:2, 'YYYY-MM-DD HH24:MI:SS')
                   ORDER BY TS DESC""",
                [node_id, cutoff_str]
            )
        else:
            cursor.execute(
                """SELECT * FROM NODEOPS_METRICS 
                   WHERE TS >= TO_TIMESTAMP(:1, 'YYYY-MM-DD HH24:MI:SS')
                   ORDER BY TS DESC""",
                [cutoff_str]
            )

        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([str(c) if c is not None else "" for c in row])

        return output.getvalue()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    log("NodeOps worker demo starting")
    demo = generate_demo_data(node_count=3, records_per_node=10)
    write_telemetry(demo)
    log("Demo data ingested")

    csv_out = export_metrics_csv(window_hours=24)
    log(f"CSV export length: {len(csv_out)} chars")
