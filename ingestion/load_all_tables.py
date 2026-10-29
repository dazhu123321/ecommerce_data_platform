
import time
from datetime import datetime

from load_table import TABLE_CONFIG, load_table


# 按业务依赖顺序执行：先维度表，再订单相关表
TABLES_TO_LOAD = [
    "users",
    "products",
    "orders",
    "order_items",
]


def main():
    pipeline_start = time.perf_counter()
    pipeline_started_at = datetime.now()

    results = []

    print("=" * 60)
    print("ECOMMERCE DATA PLATFORM - LOAD PIPELINE")
    print(f"Started at: {pipeline_started_at:%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    for table_name in TABLES_TO_LOAD:
        table_start = time.perf_counter()
        started_at = datetime.now()

        print(f"\n[{table_name.upper()}] Starting load...")

        try:
            rows_loaded = load_table(table_name)

            results.append({
                "table": table_name,
                "status": "SUCCESS",
                "rows": rows_loaded,
                "duration_seconds": round(
                    time.perf_counter() - table_start, 2
                ),
                "error": None,
            })

        except Exception as exc:
            results.append({
                "table": table_name,
                "status": "FAILED",
                "rows": None,
                "duration_seconds": round(
                    time.perf_counter() - table_start, 2
                ),
                "error": str(exc),
            })

            print(f"[{table_name.upper()}] FAILED: {exc}")
            # 继续执行其他表，最后统一报告失败结果

    total_duration = round(
        time.perf_counter() - pipeline_start, 2
    )

    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)

    for result in results:
        rows = (
            f"{result['rows']:,}"
            if result["rows"] is not None
            else "-"
        )

        print(
            f"{result['table']:15} "
            f"{result['status']:8} "
            f"rows={rows:>10} "
            f"duration={result['duration_seconds']}s"
        )

        if result["error"]:
            print(f"  Error: {result['error']}")

    success_count = sum(
        result["status"] == "SUCCESS"
        for result in results
    )
    failed_count = len(results) - success_count

    print("-" * 60)
    print(f"Tables: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Total duration: {total_duration}s")

    if failed_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
