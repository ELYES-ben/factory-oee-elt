-- Production des machines, une ligne par machine et par quart d'heure d'ouverture.
with source as (

    select * from {{ source('raw', 'mes_production_15min') }}

)

select
    concat(machine_id, '|', format_timestamp('%Y-%m-%dT%H:%M', slot_start)) as production_slot_id,
    machine_id,
    slot_start,
    run_minutes,
    15 - run_minutes as downtime_minutes,
    downtime_reason,
    parts_produced,
    parts_produced - parts_scrapped as good_parts,
    parts_scrapped,
    _loaded_at
from source