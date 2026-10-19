"""Ingestion : API RTE et simulateur MES -> BigQuery (dataset raw).

Usage : python -m ingestion.main --days 30
"""

import argparse
import logging
import os
from datetime import UTC, datetime, timedelta

from ingestion import bq_loader, mes_simulator, rte_api

log = logging.getLogger("ingestion")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Charge les données brutes dans BigQuery.")
    parser.add_argument("--days", type=int, default=30, help="jours à recharger (défaut : 30)")
    parser.add_argument("--source", choices=("all", "rte", "mes"), default="all")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        raise SystemExit("GCP_PROJECT_ID manquant. Lance d'abord : export GCP_PROJECT_ID=<id>")

    now = datetime.now(UTC)
    loaded_at = now.isoformat()
    today = now.astimezone(mes_simulator.PARIS).date()
    start = today - timedelta(days=args.days - 1)

    client = bq_loader.make_client(project_id)
    bq_loader.ensure_raw_dataset(client)

    if args.source in ("all", "rte"):
        # Un jour de marge de chaque côté : une journée de Paris commence la veille en UTC.
        records = rte_api.fetch_eco2mix(start - timedelta(days=1), today + timedelta(days=1))
        rows = rte_api.to_raw_rows(records, loaded_at)
        n = bq_loader.replace_table(client, bq_loader.RTE_TABLE, rows, bq_loader.RTE_SCHEMA)
        log.info("raw.%s : %s lignes chargées", bq_loader.RTE_TABLE, n)

    if args.source in ("all", "mes"):
        rows = mes_simulator.simulate(start, today, now=now)
        for row in rows:
            row["_loaded_at"] = loaded_at
        n = bq_loader.replace_table(client, bq_loader.MES_TABLE, rows, bq_loader.MES_SCHEMA)
        log.info("raw.%s : %s lignes chargées", bq_loader.MES_TABLE, n)


if __name__ == "__main__":
    main()