import json
from datetime import date
from unittest.mock import Mock

import pytest

from ingestion.rte_api import build_params, fetch_eco2mix, to_raw_rows


def fake_session(payload):
    """Fausse session HTTP : renvoie payload sans appeler Internet."""
    response = Mock()
    response.json.return_value = payload
    session = Mock()
    session.get.return_value = response
    return session


def test_les_parametres_filtrent_les_dates():
    params = build_params(date(2026, 10, 1), date(2026, 10, 3))
    assert params["where"] == "date_heure >= date'2026-10-01' AND date_heure < date'2026-10-03'"
    assert params["timezone"] == "UTC"


def test_fetch_renvoie_les_enregistrements():
    records = [{"date_heure": "2026-10-01T00:00:00+00:00", "taux_co2": 21}]
    session = fake_session(records)
    assert fetch_eco2mix(date(2026, 10, 1), date(2026, 10, 2), session=session) == records


def test_fetch_refuse_une_reponse_qui_n_est_pas_une_liste():
    session = fake_session({"error_code": "ODSQLError", "message": "..."})
    with pytest.raises(ValueError):
        fetch_eco2mix(date(2026, 10, 1), date(2026, 10, 2), session=session)


def test_to_raw_rows_garde_tout_le_json():
    record = {"date_heure": "2026-10-01T00:00:00+00:00", "taux_co2": 21}
    rows = to_raw_rows([record], loaded_at="2026-10-16T06:00:00+00:00")
    assert json.loads(rows[0]["payload"]) == record
    assert rows[0]["_loaded_at"] == "2026-10-16T06:00:00+00:00"
