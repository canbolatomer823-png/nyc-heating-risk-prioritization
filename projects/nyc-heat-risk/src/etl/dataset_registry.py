from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    dataset_id: str
    url: str
    notes: str


OFFICIAL_DATASETS = [
    DatasetSpec(
        name="311 Service Requests from 2010 to Present",
        dataset_id="erm2-nwe9",
        url="https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-Present/erm2-nwe9/about_data",
        notes="Primary request-level source for heat and hot water complaints.",
    ),
    DatasetSpec(
        name="Housing Maintenance Code Complaints and Problems",
        dataset_id="ygpa-z7cr",
        url="https://data.cityofnewyork.us/Housing-Development/Housing-Maintenance-Code-Complaints-and-Problems/ygpa-z7cr/about_data",
        notes="Use for complaint/problem code refinement and complaint normalization.",
    ),
    DatasetSpec(
        name="Buildings Subject to HPD Jurisdiction",
        dataset_id="kj4p-ruqc",
        url="https://data.cityofnewyork.us/Housing-Development/Buildings-Subject-to-HPD-Jurisdiction/kj4p-ruqc",
        notes="Core building table for joins and building metadata.",
    ),
    DatasetSpec(
        name="Multiple Dwelling Registrations",
        dataset_id="tesw-yqqr",
        url="https://data.cityofnewyork.us/Housing-Development/Multiple-Dwelling-Registrations/tesw-yqqr",
        notes="Registration status and management metadata.",
    ),
    DatasetSpec(
        name="Housing Maintenance Code Violations",
        dataset_id="wvxf-dwi5",
        url="https://data.cityofnewyork.us/Housing-Development/Housing-Maintenance-Code-Violations/wvxf-dwi5",
        notes="Historical violations for building-level risk features.",
    ),
    DatasetSpec(
        name="Buildings Selected for the Heat Sensor Program (HSP)",
        dataset_id="h4mf-f24e",
        url="https://data.cityofnewyork.us/Housing-Development/Buildings-Selected-for-the-Heat-Sensor-Program-HSP/h4mf-f24e",
        notes="Useful as an official high-risk signal.",
    ),
    DatasetSpec(
        name="NOAA Global Surface Summary of the Day (GSOD)",
        dataset_id="gsod",
        url="https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc%3AC00516/html",
        notes="Daily weather driver used through official NOAA open data distribution.",
    ),
    DatasetSpec(
        name="NOAA GHCN Daily",
        dataset_id="ghcn-daily",
        url="https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily",
        notes="Station inventory and alternative daily weather archive.",
    ),
    DatasetSpec(
        name="Community Resilience Estimates",
        dataset_id="cre",
        url="https://www.census.gov/programs-surveys/community-resilience-estimates.html",
        notes="Area-level vulnerability signal for equity-aware prioritization.",
    ),
]


def dataset_index() -> dict[str, DatasetSpec]:
    return {dataset.dataset_id: dataset for dataset in OFFICIAL_DATASETS}
