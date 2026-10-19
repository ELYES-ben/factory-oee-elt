import csv
from datetime import UTC, date, datetime
from pathlib import Path

from ingestion.mes_simulator import MACHINES, day_slots, simulate, simulate_machine_day

SEED_MACHINES = Path(__file__).resolve().parents[1] / "dbt" / "seeds" / "machines.csv"


def test_un_jour_normal_compte_96_quarts_d_heure():
    assert len(day_slots(date(2026, 10, 14))) == 96


def test_les_changements_d_heure_sont_geres():
    assert len(day_slots(date(2026, 3, 29))) == 92  # passage à l'heure d'été : journée de 23 h
    assert len(day_slots(date(2026, 10, 25))) == 100  # passage à l'heure d'hiver : journée de 25 h


def test_le_meme_jour_donne_les_memes_donnees():
    day = date(2026, 10, 14)
    assert simulate_machine_day(MACHINES[0], day) == simulate_machine_day(MACHINES[0], day)


def test_l_usine_est_fermee_le_dimanche():
    assert simulate_machine_day(MACHINES[0], date(2026, 10, 18)) == []


def test_les_valeurs_sont_coherentes():
    rows = simulate(date(2026, 10, 12), date(2026, 10, 16), now=datetime(2026, 10, 17, tzinfo=UTC))
    assert len(rows) > 0
    for row in rows:
        assert 0 <= row["run_minutes"] <= 15
        assert 0 <= row["parts_scrapped"] <= row["parts_produced"]
        assert (row["downtime_reason"] is None) == (row["run_minutes"] == 15)


def test_aucun_quart_d_heure_dans_le_futur():
    now = datetime(2026, 10, 14, 10, 7, tzinfo=UTC)
    rows = simulate(date(2026, 10, 14), date(2026, 10, 14), now=now)
    assert max(row["slot_start"] for row in rows) == "2026-10-14T09:45:00+00:00"


def test_le_simulateur_et_le_seed_dbt_ont_les_memes_machines():
    with SEED_MACHINES.open(encoding="utf-8") as f:
        seed = {row["machine_id"]: float(row["ideal_cycle_time_s"]) for row in csv.DictReader(f)}
    assert seed == {m.machine_id: m.ideal_cycle_time_s for m in MACHINES}
