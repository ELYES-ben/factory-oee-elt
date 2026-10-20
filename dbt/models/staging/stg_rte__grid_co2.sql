-- Intensité carbone du réseau électrique français, un enregistrement par quart d'heure.
with source as (

    select payload, _loaded_at
    from {{ source('raw', 'rte_eco2mix') }}

),

parsed as (

    select
        safe_cast(json_value(payload, '$.date_heure') as timestamp) as slot_start,
        safe_cast(json_value(payload, '$.taux_co2') as float64) as grid_co2_g_per_kwh,
        safe_cast(json_value(payload, '$.consommation') as float64) as consumption_mw,
        _loaded_at
    from source

)

select *
from parsed
where slot_start is not null
-- filet de sécurité : si un quart d'heure apparaît deux fois, on garde la version la plus récente
qualify row_number() over (partition by slot_start order by _loaded_at desc) = 1