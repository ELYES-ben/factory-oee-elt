-- Grain : une ligne par machine et par jour de production (heure de Paris).
-- TRS (OEE) = disponibilité x performance x qualité.
with slots as (

    select * from {{ ref('fct_production_15min') }}

),

daily as (

    select
        production_date,
        machine_id,
        count(*) * 15 as planned_minutes,
        sum(run_minutes) as run_minutes,
        sum(parts_produced) as parts_produced,
        sum(good_parts) as good_parts,
        sum(parts_scrapped) as parts_scrapped,
        -- temps utile : temps qu'il aurait fallu pour faire les pièces bonnes à la cadence idéale
        sum(good_parts * ideal_cycle_time_s) / 60 as valuable_minutes,
        sum(parts_produced * ideal_cycle_time_s) / 60 as net_minutes,
        sum(energy_kwh) as energy_kwh,
        sum(co2_kg) as co2_kg
    from slots
    group by production_date, machine_id

)

select
    concat(machine_id, '|', cast(production_date as string)) as oee_daily_id,
    production_date,
    machine_id,
    planned_minutes,
    run_minutes,
    parts_produced,
    good_parts,
    parts_scrapped,
    round(net_minutes, 2) as net_minutes,
    round(valuable_minutes, 2) as valuable_minutes,
    round(safe_divide(run_minutes, planned_minutes), 4) as availability,
    round(safe_divide(net_minutes, run_minutes), 4) as performance,
    round(safe_divide(good_parts, parts_produced), 4) as quality,
    round(safe_divide(valuable_minutes, planned_minutes), 4) as oee,
    round(energy_kwh, 2) as energy_kwh,
    round(co2_kg, 3) as co2_kg
from daily
