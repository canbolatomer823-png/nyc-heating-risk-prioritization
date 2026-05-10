-- Feature mart for building-day heat risk modeling.
-- Expected upstream tables:
--   stg_311_heat_requests
--   stg_hpd_buildings
--   stg_hpd_violations
--   stg_hpd_registrations
--   stg_noaa_daily
--   stg_cre_area

with complaints_by_day as (
    select
        coalesce(bbl, building_bbl) as building_bbl,
        complaint_date,
        count(*) as complaint_count
    from stg_311_heat_requests r
    left join stg_hpd_buildings b
        on upper(r.incident_address) = upper(b.house_number || ' ' || b.street_name)
    group by 1, 2
),
violations_by_day as (
    select
        building_bbl,
        violation_date,
        count(*) as violation_count
    from stg_hpd_violations
    group by 1, 2
),
building_calendar as (
    select
        b.building_bbl,
        d.calendar_date,
        b.boro,
        b.zip_code,
        b.unit_count,
        b.community_district,
        coalesce(r.registration_active_flag, 0) as registration_active_flag
    from stg_hpd_buildings b
    join dim_calendar d
        on d.calendar_date between date '2024-10-01' and date '2025-05-31'
    left join stg_hpd_registrations r
        on b.building_bbl = r.building_bbl
),
joined as (
    select
        c.building_bbl,
        c.calendar_date,
        c.boro,
        c.zip_code,
        c.unit_count,
        c.community_district,
        c.registration_active_flag,
        coalesce(q.complaint_count, 0) as complaint_count,
        coalesce(v.violation_count, 0) as violation_count,
        w.tmin,
        w.tmax,
        w.prcp,
        a.cre_vulnerability_score
    from building_calendar c
    left join complaints_by_day q
        on c.building_bbl = q.building_bbl
       and c.calendar_date = q.complaint_date
    left join violations_by_day v
        on c.building_bbl = v.building_bbl
       and c.calendar_date = v.violation_date
    left join stg_noaa_daily w
        on c.calendar_date = w.observation_date
    left join stg_cre_area a
        on c.community_district = a.community_district
)
select
    building_bbl,
    calendar_date,
    boro,
    zip_code,
    unit_count,
    community_district,
    registration_active_flag,
    complaint_count,
    lead(complaint_count, 1, 0) over (
        partition by building_bbl
        order by calendar_date
    ) as next_day_complaint_count,
    case
        when lead(complaint_count, 1, 0) over (
            partition by building_bbl
            order by calendar_date
        ) >= 3 then 1
        else 0
    end as surge_flag,
    sum(complaint_count) over (
        partition by building_bbl
        order by calendar_date
        rows between 6 preceding and current row
    ) as rolling_7d_complaints,
    violation_count,
    tmin,
    tmax,
    prcp,
    case
        when tmin < 32 then 1
        else 0
    end as cold_shock_indicator,
    cre_vulnerability_score
from joined;
