-- Staging query for heat-related 311 requests.
-- Validate exact field names against the downloaded schema before running.

with base_requests as (
    select
        unique_key,
        cast(created_date as timestamp) as created_ts,
        cast(date_trunc('day', cast(created_date as timestamp)) as date) as complaint_date,
        upper(coalesce(complaint_type, '')) as complaint_type,
        upper(coalesce(descriptor, '')) as descriptor,
        incident_address,
        borough,
        bbl,
        latitude,
        longitude
    from raw_311_requests
),
heat_requests as (
    select *
    from base_requests
    where complaint_type like '%HEAT%'
       or descriptor like '%HEAT%'
       or descriptor like '%HOT WATER%'
)
select
    unique_key,
    complaint_date,
    created_ts,
    complaint_type,
    descriptor,
    incident_address,
    borough,
    bbl,
    latitude,
    longitude
from heat_requests;
