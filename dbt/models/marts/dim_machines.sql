-- Une ligne par machine : le référentiel (seed) enrichi de la cadence théorique.
select
    machine_id,
    machine_name,
    process_step,
    step_order,
    ideal_cycle_time_s,
    3600 / ideal_cycle_time_s as ideal_parts_per_hour,
    power_kw,
    idle_power_kw,
    is_line_output
from {{ ref('machines') }}