-- Un TRS est un pourcentage : il doit rester entre 0 et 1 (0 % et 100 %).
select *
from {{ ref('fct_oee_daily') }}
where oee < 0 or oee > 1
