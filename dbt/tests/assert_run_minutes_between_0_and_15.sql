-- Un quart d'heure dure 15 minutes : une machine ne peut pas tourner plus, ni moins de 0.
-- Le test échoue si cette requête renvoie au moins une ligne.
select *
from {{ ref('stg_mes__production') }}
where run_minutes < 0 or run_minutes > 15