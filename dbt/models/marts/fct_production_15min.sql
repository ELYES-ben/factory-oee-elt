-- Grain : une ligne par machine et par quart d'heure d'ouverture.
-- Ajoute à la production : l'équipe, l'énergie consommée et le CO2 émis.
with production as (

    select * from {{ ref('stg_mes__production') }}

),

machines as (

    select * from {{ ref('dim_machines') }}

),

reasons as (

    select * from {{ ref('dim_downtime_reasons') }}

),

-- Intensité CO2 moyenne par heure : couvre aussi les quarts d'heure sans valeur publiée.
grid_co2_hourly as (

    select
        timestamp_trunc(slot_start, hour) as hour_start,
        avg(grid_co2_g_per_kwh) as grid_co2_g_per_kwh
    from {{ ref('stg_rte__grid_co2') }}
    where grid_co2_g_per_kwh is not null
    group by hour_start

),

joined as (

    select
        p.production_slot_id,
        p.machine_id,
        m.machine_name,
        p.slot_start,
        datetime(p.slot_start, 'Europe/Paris') as slot_start_paris,
        date(p.slot_start, 'Europe/Paris') as production_date,
        extract(hour from datetime(p.slot_start, 'Europe/Paris')) as hour_paris,
        p.run_minutes,
        p.downtime_minutes,
        p.downtime_reason,
        r.reason_label,
        r.owner_team,
        p.parts_produced,
        p.good_parts,
        p.parts_scrapped,
        m.ideal_cycle_time_s,
        -- énergie (kWh) = puissance (kW) x durée (h), en marche puis à l'arrêt
        (m.power_kw * p.run_minutes + m.idle_power_kw * p.downtime_minutes) / 60 as energy_kwh,
        c.grid_co2_g_per_kwh
    from production as p
    inner join machines as m on p.machine_id = m.machine_id
    left join reasons as r on p.downtime_reason = r.downtime_reason
    left join grid_co2_hourly as c on timestamp_trunc(p.slot_start, hour) = c.hour_start

)

select
    *,
    case
        when hour_paris between 5 and 12 then 'Matin'
        when hour_paris between 13 and 20 then 'Après-midi'
        else 'Nuit'
    end as shift,
    energy_kwh * grid_co2_g_per_kwh / 1000 as co2_kg
from joined
