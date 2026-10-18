"""Extraction des données éCO2mix temps réel de RTE, via l'API Opendatasoft de l'ODRÉ."""

import json
from datetime import date

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DATASET = "eco2mix-national-tr"
EXPORT_URL = (
    f"https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/{DATASET}/exports/json"
)


def build_params(start: date, end: date) -> dict[str, str]:
    """Paramètres de la requête : les lignes dont date_heure est dans [start, end[."""
    where = f"date_heure >= date'{start.isoformat()}' AND date_heure < date'{end.isoformat()}'"
    return {"where": where, "order_by": "date_heure", "timezone": "UTC"}


def make_session() -> requests.Session:
    """Session HTTP qui réessaie jusqu'à 3 fois (pauses croissantes) si le serveur
    répond 429 (trop de requêtes) ou 5xx (erreur du serveur)."""
    retry = Retry(total=3, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_eco2mix(start: date, end: date, session: requests.Session | None = None) -> list[dict]:
    """Télécharge les enregistrements éCO2mix entre start (inclus) et end (exclu)."""
    session = session or make_session()
    response = session.get(EXPORT_URL, params=build_params(start, end), timeout=60)
    response.raise_for_status()  # lève une exception si le code HTTP est 4xx ou 5xx
    records = response.json()
    if not isinstance(records, list):
        raise ValueError(f"Réponse inattendue de l'API : {str(records)[:200]}")
    return records


def to_raw_rows(records: list[dict], loaded_at: str) -> list[dict]:
    """Une ligne par enregistrement : le JSON complet (payload) et l'heure du chargement."""
    rows = []
    for record in records:
        rows.append({"payload": json.dumps(record, ensure_ascii=False), "_loaded_at": loaded_at})
    return rows