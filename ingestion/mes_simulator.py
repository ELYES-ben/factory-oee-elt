"""Simulateur du MES d'une ligne de faisceaux électriques automobiles.

Un MES (Manufacturing Execution System) enregistre ce que font les machines d'une usine.
Ici, chaque machine produit une ligne par quart d'heure d'ouverture de l'usine :
- run_minutes : minutes de marche dans le quart d'heure (0 à 15) ;
- downtime_reason : cause de l'arrêt quand la machine n'a pas tourné 15 minutes ;
- parts_produced / parts_scrapped : pièces produites et pièces rebutées.

Le hasard est initialisé avec (jour, machine) : simuler deux fois le même jour
donne exactement les mêmes chiffres, donc le chargement peut être rejoué sans risque.
"""

import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
SLOT = timedelta(minutes=15)
SHIFT_START_HOURS = (5, 13, 21)  # début des équipes du matin, de l'après-midi et de nuit


@dataclass(frozen=True)
class Machine:
    machine_id: str
    ideal_cycle_time_s: float  # temps de cycle théorique, en secondes par pièce
    breakdown_prob: float  # probabilité qu'une panne commence pendant un quart d'heure
    scrap_rate: float  # part moyenne de pièces rebutées


# Les temps de cycle doivent être identiques à ceux de dbt/seeds/machines.csv (un test le vérifie).
MACHINES = (
    Machine("CUT-01", ideal_cycle_time_s=2.0, breakdown_prob=0.010, scrap_rate=0.010),
    Machine("CUT-02", ideal_cycle_time_s=2.0, breakdown_prob=0.025, scrap_rate=0.015),
    Machine("WELD-01", ideal_cycle_time_s=6.0, breakdown_prob=0.015, scrap_rate=0.008),
    Machine("TEST-01", ideal_cycle_time_s=45.0, breakdown_prob=0.008, scrap_rate=0.030),
)


def day_slots(day: date) -> list[datetime]:
    """Débuts (en UTC) des quarts d'heure d'une journée de Paris : 96, ou 92 et 100
    les jours de changement d'heure."""
    start = datetime.combine(day, time(0), tzinfo=PARIS).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time(0), tzinfo=PARIS).astimezone(UTC)
    return [start + i * SLOT for i in range(int((end - start) / SLOT))]


def is_open(local: datetime) -> bool:
    """L'usine tourne en 3 x 8 du lundi 5 h au samedi 5 h (heure de Paris)."""
    weekday, hour = local.weekday(), local.hour  # weekday : lundi = 0 ... dimanche = 6
    if weekday == 0:
        return hour >= 5
    if weekday <= 4:
        return True
    if weekday == 5:
        return hour < 5
    return False


def simulate_machine_day(machine: Machine, day: date) -> list[dict]:
    """Toutes les lignes MES d'une machine pour une journée de Paris."""
    rng = random.Random(f"{day.isoformat()}|{machine.machine_id}")
    rows = []
    reason = None
    slots_left = 0  # quarts d'heure d'arrêt restants (panne ou manque matière en cours)
    for slot_start in day_slots(day):
        local = slot_start.astimezone(PARIS)
        if not is_open(local):
            continue
        if slots_left > 0:  # l'arrêt en cours continue, avec la même cause
            run_minutes = 0
            slots_left -= 1
        elif local.minute == 0 and local.hour in SHIFT_START_HOURS:
            reason, run_minutes = "CHANGEOVER", rng.randint(5, 10)
        elif rng.random() < machine.breakdown_prob:
            reason, run_minutes = "BREAKDOWN", rng.randint(0, 12)
            slots_left = rng.randint(1, 8)  # la réparation dure de 15 min à 2 h
        elif rng.random() < 0.004:
            reason, run_minutes = "MATERIAL_SHORTAGE", rng.randint(0, 10)
            slots_left = rng.randint(0, 2)
        else:
            reason, run_minutes = None, 15
        speed = rng.uniform(0.82, 0.97)  # micro-arrêts et ralentissements : perte de performance
        produced = int(run_minutes * 60 / machine.ideal_cycle_time_s * speed)
        scrapped = min(produced, round(produced * machine.scrap_rate * rng.uniform(0.3, 1.7)))
        rows.append(
            {
                "machine_id": machine.machine_id,
                "slot_start": slot_start.isoformat(),
                "run_minutes": run_minutes,
                "downtime_reason": reason if run_minutes < 15 else None,
                "parts_produced": produced,
                "parts_scrapped": scrapped,
            }
        )
    return rows


def simulate(start: date, end: date, now: datetime | None = None) -> list[dict]:
    """Lignes MES de toutes les machines, du jour start au jour end inclus.
    Les quarts d'heure qui ne sont pas encore terminés à l'instant now sont ignorés."""
    now = now or datetime.now(UTC)
    rows = []
    day = start
    while day <= end:
        for machine in MACHINES:
            for row in simulate_machine_day(machine, day):
                if datetime.fromisoformat(row["slot_start"]) + SLOT <= now:
                    rows.append(row)
        day += timedelta(days=1)
    return rows
