FROM apache/airflow:3.3.2

# Notre pipeline (client BigQuery + dbt) vit dans son propre environnement Python,
# séparé de celui d'Airflow, pour éviter les conflits de versions entre les deux.
USER root
COPY requirements-pipeline.txt /tmp/requirements-pipeline.txt
RUN python -m venv /opt/pipeline_venv \
    && /opt/pipeline_venv/bin/pip install --no-cache-dir -r /tmp/requirements-pipeline.txt
USER airflow
