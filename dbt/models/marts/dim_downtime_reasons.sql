-- Une ligne par cause d'arrêt, avec l'équipe qui doit agir.
select
    downtime_reason,
    reason_label,
    owner_team,
    is_planned
from {{ ref('downtime_reasons') }}