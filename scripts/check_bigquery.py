"""Vérifie que Python peut se connecter à BigQuery avec la clé du compte de service."""

import os

from google.cloud import bigquery

project_id = os.environ["GCP_PROJECT_ID"]

client = bigquery.Client(project=project_id)

query = "SELECT 'BigQuery OK' AS message, CURRENT_TIMESTAMP() AS heure"
rows = client.query(query).result()

for row in rows:
    print(f"{row.message} – projet {project_id} – heure {row.heure}")
