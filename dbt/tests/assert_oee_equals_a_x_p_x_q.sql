-- Le TRS doit être égal à disponibilité x performance x qualité (à l'arrondi près).
select *
from {{ ref('fct_oee_daily') }}
where abs(oee - availability * performance * quality) > 0.001
