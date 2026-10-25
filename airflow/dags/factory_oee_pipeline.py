"""DAG quotidien : API RTE + simulateur MES -> BigQuery (raw) -> dbt (staging, marts, tests)."""

from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

PROJECT_DIR = "/opt/project"  # le dépôt, monté par docker-compose.override.yaml
VENV_BIN = "/opt/pipeline_venv/bin"  # l'environnement Python créé par le Dockerfile

with DAG(
    dag_id="factory_oee_pipeline",
    description="Ingestion, fraîcheur des sources, puis dbt build",
    schedule="0 5 * * *",  # tous les jours à 5 h UTC (6 h ou 7 h à Paris)
    start_date=datetime(2026, 10, 1),
    catchup=False,  # ne pas rattraper les jours passés
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["portfolio", "elt"],
) as dag:
    extract_load = BashOperator(
        task_id="extract_load",
        bash_command=f"cd {PROJECT_DIR} && {VENV_BIN}/python -m ingestion.main --days 30",
    )

    check_freshness = BashOperator(
        task_id="check_source_freshness",
        bash_command=f"cd {PROJECT_DIR}/dbt && {VENV_BIN}/dbt source freshness --target prod",
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"cd {PROJECT_DIR}/dbt && {VENV_BIN}/dbt build --target prod",
    )

    extract_load >> check_freshness >> dbt_build
