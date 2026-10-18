"""Chargement de lignes Python dans BigQuery (dataset raw), avec des jobs de chargement."""

from google.cloud import bigquery

RAW_DATASET = "raw"
LOCATION = "EU"

RTE_TABLE = "rte_eco2mix"
RTE_SCHEMA = [
    bigquery.SchemaField("payload", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("_loaded_at", "TIMESTAMP", mode="REQUIRED"),
]

MES_TABLE = "mes_production_15min"
MES_SCHEMA = [
    bigquery.SchemaField("machine_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("slot_start", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("run_minutes", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("downtime_reason", "STRING"),
    bigquery.SchemaField("parts_produced", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("parts_scrapped", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("_loaded_at", "TIMESTAMP", mode="REQUIRED"),
]


def make_client(project_id: str) -> bigquery.Client:
    """Client BigQuery. Les identifiants sont lus dans GOOGLE_APPLICATION_CREDENTIALS."""
    return bigquery.Client(project=project_id, location=LOCATION)


def ensure_raw_dataset(client: bigquery.Client) -> None:
    """Crée le dataset raw s'il n'existe pas encore (sans erreur s'il existe déjà)."""
    dataset = bigquery.Dataset(f"{client.project}.{RAW_DATASET}")
    dataset.location = LOCATION
    client.create_dataset(dataset, exists_ok=True)


def replace_table(
    client: bigquery.Client, table: str, rows: list[dict], schema: list[bigquery.SchemaField]
) -> int:
    """Remplace tout le contenu de raw.<table> par rows et renvoie le nombre de lignes chargées."""
    if not rows:
        raise ValueError(f"Aucune ligne à charger dans {table} : chargement annulé.")
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    destination = f"{client.project}.{RAW_DATASET}.{table}"
    job = client.load_table_from_json(rows, destination, job_config=job_config)
    job.result()  # attend la fin du job ; lève une exception si BigQuery refuse les données
    return job.output_rows