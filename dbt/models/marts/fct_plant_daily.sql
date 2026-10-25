-- Grain : une ligne par jour de production. Indicateurs de l'usine entière.
with oee as (

    select * from {{ ref('fct_oee_daily') }}

),

machines as (

    select * from {{ ref('dim_machines') }}

),

daily as (

    select
        o.production_date,
        sum(if(m.is_line_output, o.good_parts, 0)) as harnesses_produced,
        avg(o.oee) as avg_oee,
        sum(o.energy_kwh) as energy_kwh,
        sum(o.co2_kg) as co2_kg
    from oee as o
    inner join machines as m on o.machine_id = m.machine_id
    group by o.production_date

)

select
    production_date,
    harnesses_produced,
    round(avg_oee, 4) as avg_oee,
    round(energy_kwh, 1) as energy_kwh,
    round(co2_kg, 2) as co2_kg,
    round(safe_divide(energy_kwh, harnesses_produced), 3) as kwh_per_harness,
    round(safe_divide(co2_kg * 1000, harnesses_produced), 1) as co2_g_per_harness
from daily
