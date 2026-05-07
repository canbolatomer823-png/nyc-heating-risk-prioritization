-- Sanity checks before modeling.

-- 1. Complaint coverage by borough
select
    borough,
    count(*) as request_count
from stg_311_heat_requests
group by borough
order by request_count desc;

-- 2. Buildings with the highest complaint burden
select
    building_bbl,
    count(*) as total_complaints
from stg_311_heat_requests
where bbl is not null
group by building_bbl
order by total_complaints desc
limit 25;

-- 3. Weather joins with missing temperature
select
    count(*) as missing_weather_rows
from fct_building_day_heat_risk
where tmin is null;

-- 4. Class balance for the surge target
select
    surge_flag,
    count(*) as row_count
from fct_building_day_heat_risk
group by surge_flag;

-- 5. Top vulnerable areas by average risk
select
    community_district,
    avg(next_day_complaint_count) as avg_next_day_count,
    avg(cre_vulnerability_score) as avg_cre_score
from fct_building_day_heat_risk
group by community_district
order by avg_next_day_count desc
limit 20;
