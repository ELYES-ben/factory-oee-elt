
-- : requêtes d'exploration des tables brutes (console BigQuery).--  : requêtes d'exploration des tables brutes (console BigQuery).
-- Lance-les une par une : sélectionne une requête puis Ctrl+Entrée.

-- Q1. Volume et période couverte par chaque table brute
select
  'rte_eco2mix' as table_brute,
  count(*) as nb_lignes,
  min(json_value(payload, '$.date_heure')) as premiere,
  max(json_value(payload, '$.date_heure')) as derniere
from raw.rte_eco2mix
union all
select
  'mes_production_15min',
  count(*),
  cast(min(slot_start) as string),
  cast(max(slot_start) as string)
from raw.mes_production_15min;

-- Q2. Lire le JSON et typer les colonnes
select
  safe_cast(json_value(payload, '$.date_heure') as timestamp) as slot_start,
  datetime(safe_cast(json_value(payload, '$.date_heure') as timestamp), 'Europe/Paris') as slot_start_paris,
  safe_cast(json_value(payload, '$.taux_co2') as float64) as grid_co2_g_per_kwh,
  safe_cast(json_value(payload, '$.consommation') as float64) as consumption_mw
from raw.rte_eco2mix
order by slot_start desc
limit 20;

-- Q3. À quelle heure l'électricité française est-elle la moins carbonée ?
with co2 as (
  select
    safe_cast(json_value(payload, '$.date_heure') as timestamp) as slot_start,
    safe_cast(json_value(payload, '$.taux_co2') as float64) as grid_co2
  from raw.rte_eco2mix
)
select
  extract(hour from datetime(slot_start, 'Europe/Paris')) as heure_paris,
  round(avg(grid_co2), 1) as co2_moyen_g_par_kwh,
  count(grid_co2) as nb_valeurs
from co2
where grid_co2 is not null
group by heure_paris
order by heure_paris;

-- Q4. Production, rebuts et quarts d'heure de panne par machine
select
  machine_id,
  sum(parts_produced) as pieces_produites,
  sum(parts_scrapped) as pieces_rebutees,
  round(100 * sum(parts_scrapped) / sum(parts_produced), 2) as taux_rebut_pct,
  countif(downtime_reason = 'BREAKDOWN') as quarts_d_heure_en_panne
from raw.mes_production_15min
group by machine_id
order by machine_id;

-- Q5. Pareto des causes d'arrêt : minutes perdues, part et part cumulée
with arrets as (
  select
    downtime_reason,
    sum(15 - run_minutes) as minutes_arret
  from raw.mes_production_15min
  where downtime_reason is not null
  group by downtime_reason
)
select
  downtime_reason,
  minutes_arret,
  round(100 * minutes_arret / sum(minutes_arret) over (), 1) as part_pct,
  round(100 * sum(minutes_arret) over (order by minutes_arret desc) / sum(minutes_arret) over (), 1) as part_cumulee_pct
from arrets
order by minutes_arret desc;

-- Q6. TRS par machine et par jour (heure de Paris)
with machines as (
  select * from unnest([
    struct('CUT-01' as machine_id, 2.0 as ideal_cycle_time_s),
    struct('CUT-02' as machine_id, 2.0 as ideal_cycle_time_s),
    struct('WELD-01' as machine_id, 6.0 as ideal_cycle_time_s),
    struct('TEST-01' as machine_id, 45.0 as ideal_cycle_time_s)
  ])
),
daily as (
  select
    date(p.slot_start, 'Europe/Paris') as jour,
    p.machine_id,
    count(*) * 15 as minutes_ouverture,
    sum(p.run_minutes) as minutes_marche,
    sum(p.parts_produced) as pieces_produites,
    sum(p.parts_produced - p.parts_scrapped) as pieces_bonnes,
    sum(p.parts_produced * m.ideal_cycle_time_s) / 60 as minutes_nettes,
    sum((p.parts_produced - p.parts_scrapped) * m.ideal_cycle_time_s) / 60 as minutes_utiles
  from raw.mes_production_15min as p
  inner join machines as m on p.machine_id = m.machine_id
  group by jour, p.machine_id
)
select
  jour,
  machine_id,
  round(safe_divide(minutes_marche, minutes_ouverture), 3) as disponibilite,
  round(safe_divide(minutes_nettes, minutes_marche), 3) as performance,
  round(safe_divide(pieces_bonnes, pieces_produites), 3) as qualite,
  round(safe_divide(minutes_utiles, minutes_ouverture), 3) as trs
from daily
order by jour desc, machine_id;

-- Q7. Énergie et CO2 de l'usine par jour
with machines as (
  select * from unnest([
    struct('CUT-01' as machine_id, 7.5 as power_kw, 1.5 as idle_power_kw),
    struct('CUT-02' as machine_id, 7.5 as power_kw, 1.5 as idle_power_kw),
    struct('WELD-01' as machine_id, 4.0 as power_kw, 0.8 as idle_power_kw),
    struct('TEST-01' as machine_id, 2.5 as power_kw, 0.5 as idle_power_kw)
  ])
),
co2_par_heure as (
  select
    timestamp_trunc(safe_cast(json_value(payload, '$.date_heure') as timestamp), hour) as heure,
    avg(safe_cast(json_value(payload, '$.taux_co2') as float64)) as grid_co2
  from raw.rte_eco2mix
  group by heure
),
slots as (
  select
    date(p.slot_start, 'Europe/Paris') as jour,
    (m.power_kw * p.run_minutes + m.idle_power_kw * (15 - p.run_minutes)) / 60 as kwh,
    c.grid_co2
  from raw.mes_production_15min as p
  inner join machines as m on p.machine_id = m.machine_id
  left join co2_par_heure as c on timestamp_trunc(p.slot_start, hour) = c.heure
)
select
  jour,
  round(sum(kwh), 1) as energie_kwh,
  round(sum(kwh * grid_co2) / 1000, 2) as co2_kg,
  countif(grid_co2 is null) as quarts_d_heure_sans_co2
from slots
group by jour
order by jour desc;

-- Q8. Fonctions de fenêtre : variation du TRS d'un jour à l'autre, et plus mauvais jour
with machines as (
  select * from unnest([
    struct('CUT-01' as machine_id, 2.0 as ideal_cycle_time_s),
    struct('CUT-02' as machine_id, 2.0 as ideal_cycle_time_s),
    struct('WELD-01' as machine_id, 6.0 as ideal_cycle_time_s),
    struct('TEST-01' as machine_id, 45.0 as ideal_cycle_time_s)
  ])
),
trs_jour as (
  select
    date(p.slot_start, 'Europe/Paris') as jour,
    p.machine_id,
    sum((p.parts_produced - p.parts_scrapped) * m.ideal_cycle_time_s) / 60 / (count(*) * 15) as trs
  from raw.mes_production_15min as p
  inner join machines as m on p.machine_id = m.machine_id
  group by jour, p.machine_id
)
select
  machine_id,
  jour,
  round(trs, 3) as trs,
  round(trs - lag(trs) over (partition by machine_id order by jour), 3) as variation_vs_veille,
  row_number() over (partition by machine_id order by trs) as rang_du_plus_mauvais
from trs_jour
order by machine_id, jour;

-- Q8 bis. Garder seulement le plus mauvais jour de chaque machine (QUALIFY)
-- Reprends Q8 et remplace son dernier SELECT par celui-ci :
-- select machine_id, jour, round(trs, 3) as trs
-- from trs_jour
-- where trs is not null
-- qualify row_number() over (partition by machine_id order by trs) = 1
-- order by machine_id;