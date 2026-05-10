from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path("/Users/omer/aws-analytics-pipeline")
PROJECT = ROOT / "projects/nyc-heat-risk"
WINDOW = PROJECT / "data/windows/heat_season_2024_10_01_2025_05_31"
REPORTS = WINDOW / "reports"
ROOT_REPORTS = PROJECT / "reports"
DOCS_OUT = ROOT / "docs/index.html"
PROJECT_OUT = PROJECT / "outputs/shareable-site/index.html"
DOWNLOADS_OUT = Path("/Users/omer/Downloads/NYC_Heating_Risk_Interactive_Site_Omer_Canbolat.html")


def clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        return clean(value.item())
    if isinstance(value, dict):
        return {str(key): clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_priority_rows() -> list[dict[str, Any]]:
    frame = pd.read_csv(REPORTS / "inspection_priority_latest_day.csv", low_memory=False).head(50)
    raw_311_path = WINDOW / "raw/nyc_311_heat_requests_filtered.csv"
    if raw_311_path.exists():
        coords = pd.read_csv(raw_311_path, usecols=["bbl", "latitude", "longitude"], low_memory=False)
        coords["bbl_key"] = pd.to_numeric(coords["bbl"], errors="coerce").astype("Int64").astype(str)
        coords = (
            coords.dropna(subset=["latitude", "longitude"])
            .groupby("bbl_key", as_index=False)
            .agg(latitude=("latitude", "mean"), longitude=("longitude", "mean"), coordinate_sample_count=("latitude", "size"))
        )
        frame["bbl_key"] = pd.to_numeric(frame["building_bbl"], errors="coerce").astype("Int64").astype(str)
        frame = frame.merge(coords, on="bbl_key", how="left")
        frame["coordinate_source"] = "NYC 311 BBL geocoded complaint coordinates"
        frame = frame.drop(columns=["bbl_key"])
    rows: list[dict[str, Any]] = []
    for raw in frame.to_dict(orient="records"):
        row = clean(raw)
        for field in ("top_positive_contributors_json", "top_negative_contributors_json"):
            try:
                row[field] = json.loads(row.get(field) or "[]")
            except json.JSONDecodeError:
                row[field] = []
        rows.append(row)
    return rows


def load_monthly_profile() -> list[dict[str, Any]]:
    frame = pd.read_csv(REPORTS / "seasonal_anova_daily_metrics.csv")
    grouped = (
        frame.groupby(["month_key", "month_label"], as_index=False)
        .agg(
            days=("complaint_date", "count"),
            mean_complaints=("daily_total_complaints", "mean"),
            mean_positive_buildings=("daily_positive_buildings", "mean"),
            total_complaints=("daily_total_complaints", "sum"),
        )
        .sort_values("month_key")
    )
    return [clean(row) for row in grouped.round(4).to_dict(orient="records")]


def load_policy_rows() -> list[dict[str, Any]]:
    frame = pd.read_csv(REPORTS / "inspection_policy_simulation_summary.csv")
    fields = [
        "policy",
        "capacity",
        "mean_hits",
        "mean_precision",
        "mean_recall",
        "mean_lift",
        "random_mean_hits",
        "history_mean_hits",
        "delta_hits_vs_random",
        "delta_hits_vs_history",
    ]
    return [clean(row) for row in frame[fields].round(4).to_dict(orient="records")]


def build_app_data() -> dict[str, Any]:
    presentation = load_json(ROOT_REPORTS / "presentation_data.json", {})
    metadata = load_json(WINDOW / "models/logistic_regression_bundle.metadata.json", {})
    demo_health = load_json(ROOT_REPORTS / "demo_proof/health.json", {})
    demo_score = load_json(ROOT_REPORTS / "demo_proof/score_response.json", {})
    demo_priority = load_json(ROOT_REPORTS / "demo_proof/priorities_top5.json", {})
    aws_summary = load_json(ROOT_REPORTS / "aws_live_deploy/proof_summary.json", {})
    shutdown_summary = load_json(ROOT_REPORTS / "aws_shutdown/shutdown_summary.json", {})

    headline = presentation.get("headline_metrics", {})
    logistic = presentation.get("logistic_summary", {})
    ranking_50 = logistic.get("ranking_metrics", {}).get("50", {})
    anova = presentation.get("seasonal_anova", {})
    oot = presentation.get("oot_summary", {})

    methods = [
        {
            "id": "anova",
            "name": "ANOVA",
            "question": "Aylar arasında ortalama şikayet yükü gerçekten farklı mı?",
            "why": "Tahmin modeli değil; veri hikayesini istatistiksel olarak kanıtlamak için kullanıldı.",
            "formula": "H0: μOct = ... = μMay\\nF = MS_between / MS_within\\nη² = SS_between / SS_total",
            "result": f"F={anova.get('monthly_complaints_f', 33.6227):.2f}, p<0.0001, η²={anova.get('monthly_complaints_eta_sq', 0.5004):.3f}",
        },
        {
            "id": "logistic",
            "name": "Lojistik regresyon",
            "question": "Yarın bu binada şikayet olur mu?",
            "why": "Hedef 0/1 olduğu için ana operasyonel model olarak kullanıldı.",
            "formula": "Y(i,t+1) ~ Bernoulli(p)\\nlogit(p)=β0+βX\\np → Top-50",
            "result": f"AUC={logistic.get('test_roc_auc', 0.8036):.4f}, P@50={ranking_50.get('mean_precision_at_k', 0.2743):.4f}, Lift@50={ranking_50.get('mean_lift_at_k', 47.3438):.1f}x",
        },
        {
            "id": "nb",
            "name": "Negatif Binom",
            "question": "Yarın kaç şikayet beklenir?",
            "why": "Şikayet sayısı gibi aşırı değişken sayım verilerinde Poisson fazla katı kalır.",
            "formula": "Y_count ~ NB(μ, θ)\\nlog(μ)=β0+βX\\nVar(Y)>E(Y)",
            "result": "Sayım yönlü destek modeli; ana karar listesi lojistik sıralamadan gelir.",
        },
        {
            "id": "gee",
            "name": "GEE",
            "question": "Aynı bina birçok gün tekrar gözlenirse ne olur?",
            "why": "Bina içi tekrar gözlem bağımlılığını cluster mantığıyla kontrol eder.",
            "formula": "cluster = building_id\\nmarjinal etki + sağlam standart hata",
            "result": "Panel veri etkisi için tanısal/statistiksel destek sağlar.",
        },
        {
            "id": "glmm",
            "name": "GLMM",
            "question": "Her binanın kendine özgü başlangıç riski var mı?",
            "why": "Bina bazlı random intercept ile tekrar eden bina farklarını kontrol eder.",
            "formula": "random intercept: building_id\\nlogit(p_it)=βX_it + u_i",
            "result": "Ana başarı iddiası değil; tanısal mixed-effects kontrolüdür.",
        },
    ]

    return {
        "headline": clean(headline),
        "metrics": {
            "auc": logistic.get("test_roc_auc", 0.8036),
            "f1": logistic.get("test_f1", 0.1641),
            "precision": logistic.get("test_precision", 0.1946),
            "recall": logistic.get("test_recall", 0.1419),
            "p50": ranking_50.get("mean_precision_at_k", 0.2743),
            "lift50": ranking_50.get("mean_lift_at_k", 47.3438),
            "oot_auc": oot.get("metrics", {}).get("roc_auc", 0.8107),
            "oot_p50": oot.get("ranking_metrics", {}).get("50", {}).get("mean_precision_at_k", 0.6893),
            "threshold": metadata.get("threshold", 0.2),
            "scored_rows": sum(split.get("rows", 0) for split in metadata.get("metrics", {}).values()),
        },
        "priorityRows": load_priority_rows(),
        "monthlyProfile": load_monthly_profile(),
        "policyRows": load_policy_rows(),
        "methods": methods,
        "modelComparison": clean(presentation.get("model_comparison", [])),
        "weatherEffects": clean(presentation.get("weather_effects", [])),
        "boroughMix": clean(presentation.get("priority_borough_mix", [])),
        "dailyTrend": clean(presentation.get("daily_trend", [])),
        "evidence": {
            "health": clean(demo_health),
            "score": clean(demo_score),
            "priorities": clean(demo_priority),
            "aws": clean(aws_summary),
            "shutdown": clean(shutdown_summary),
        },
        "limits": [
            "Bu sistem otomatik ceza veya otomatik denetim kararı vermez.",
            "Model nedensellik iddiası kurmaz; operasyonel risk sıralaması üretir.",
            "AWS endpoint maliyet nedeniyle kalıcı açık tutulmaz; canlı deploy kanıtı ve kapatma kanıtı raporlanır.",
            "Equity weighting politika incelemesi gerektirir; burada şeffaf karar desteği olarak sunulur.",
        ],
    }


HTML_TEMPLATE = """<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NYC Heating Risk | İnteraktif Proje Deneyimi</title>
  <meta name="description" content="NYC resmi açık verileriyle ertesi gün ısınma/sıcak su şikayet riski ve denetim önceliği projesi.">
  <meta name="theme-color" content="#123d34">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='18' fill='%23123d34'/%3E%3Cpath d='M18 43c6-12 1-15 8-26 1 10 12 11 12 24 4-4 5-8 4-12 7 8 6 23-10 23-8 0-14-3-14-9z' fill='%23d85f42'/%3E%3C/svg%3E">
  <style>
    :root{
      --ink:#101814; --muted:#65746c; --paper:#fff8eb; --cream:#f5ead6;
      --forest:#123d34; --mint:#d8ece3; --brick:#d85f42; --gold:#d6a33d;
      --blue:#356985; --line:rgba(16,24,20,.14); --shadow:0 28px 80px rgba(24,35,29,.18);
    }
    *{box-sizing:border-box} html{scroll-behavior:smooth}
    body{margin:0;color:var(--ink);font-family:"Avenir Next","Gill Sans","Trebuchet MS",sans-serif;background:
      radial-gradient(circle at 12% 8%,rgba(216,95,66,.20),transparent 27%),
      radial-gradient(circle at 86% 4%,rgba(18,61,52,.18),transparent 26%),
      linear-gradient(135deg,#f7efdf 0%,#eaf1ea 48%,#fff8ea 100%);overflow-x:hidden}
    body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.21;background-image:
      linear-gradient(rgba(18,61,52,.16) 1px,transparent 1px),linear-gradient(90deg,rgba(18,61,52,.16) 1px,transparent 1px);background-size:52px 52px;mask-image:linear-gradient(to bottom,#000,transparent 82%)}
    a{color:inherit;text-decoration:none} button,input,select,textarea{font:inherit}
    .shell{width:min(1180px,calc(100% - 34px));margin:auto;padding:22px 0 64px;position:relative}
    .topbar{position:sticky;top:10px;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:18px;padding:9px 10px;border:1px solid var(--line);border-radius:999px;background:rgba(255,250,240,.88);backdrop-filter:blur(18px);box-shadow:0 12px 34px rgba(24,35,29,.10)}
    .brand{display:flex;align-items:center;gap:10px;font-weight:900;color:var(--forest);padding-left:8px}.brand-mark{width:34px;height:34px;border-radius:50%;background:conic-gradient(from 210deg,var(--brick),var(--gold),var(--forest),var(--brick));box-shadow:inset 0 0 0 5px rgba(255,255,255,.56)}
    .nav{display:flex;gap:5px;flex-wrap:wrap;flex:1;justify-content:flex-end}.nav button{border:0;border-radius:999px;background:transparent;color:var(--muted);font-weight:850;padding:9px 10px;cursor:pointer}.nav button.active{background:var(--forest);color:white}
    .hero{display:grid;grid-template-columns:1.04fr .96fr;gap:22px;min-height:610px;align-items:stretch}
    .panel{border:1px solid var(--line);border-radius:30px;background:rgba(255,250,240,.88);box-shadow:var(--shadow);backdrop-filter:blur(18px)}
    .hero-copy{padding:40px;display:flex;flex-direction:column;justify-content:space-between;overflow:hidden;position:relative}.hero-copy:after{content:"";position:absolute;right:-110px;bottom:-130px;width:330px;height:330px;border-radius:50%;background:radial-gradient(circle,rgba(216,95,66,.22),transparent 69%)}
    .kicker{display:inline-flex;width:max-content;gap:8px;align-items:center;border:1px solid rgba(18,61,52,.18);border-radius:999px;padding:9px 13px;background:#fffaf1;color:var(--forest);font-size:.78rem;font-weight:900;letter-spacing:.06em;text-transform:uppercase}
    h1,h2,h3,.serif{font-family:Georgia,"Times New Roman",serif} h1{margin:24px 0 18px;font-size:clamp(3rem,6.8vw,6.8rem);line-height:.88;letter-spacing:-.075em;max-width:820px}
    .lead{font-size:1.18rem;line-height:1.58;color:var(--muted);max-width:730px}.cta{display:flex;flex-wrap:wrap;gap:12px;margin-top:28px}.btn{border:0;border-radius:999px;padding:13px 17px;background:var(--forest);color:white;font-weight:900;cursor:pointer;box-shadow:0 16px 26px rgba(18,61,52,.2)}.btn.alt{background:#fffaf1;color:var(--forest);border:1px solid var(--line);box-shadow:none}
    .stage{padding:24px;display:grid;gap:16px;grid-template-rows:auto 1fr}.phone{border-radius:32px;background:#10211c;color:white;padding:18px;min-height:430px;position:relative;overflow:hidden}.phone:before{content:"";position:absolute;inset:12px;border:1px solid rgba(255,255,255,.16);border-radius:25px}.pulse{position:absolute;width:180px;height:180px;border-radius:50%;background:rgba(216,95,66,.28);filter:blur(4px);right:-30px;top:-30px;animation:pulse 3.2s ease-in-out infinite}
    .phone-inner{position:relative;z-index:2;display:grid;gap:14px}.mini-map{height:155px;border-radius:22px;background:linear-gradient(145deg,#193f35,#245f50);position:relative;overflow:hidden}.mini-map svg{position:absolute;inset:0;width:100%;height:100%;opacity:.95}.pin{position:absolute;width:13px;height:13px;border-radius:50%;background:var(--brick);box-shadow:0 0 0 7px rgba(216,95,66,.2);animation:pop 2s ease-in-out infinite}.pin.p2{left:60%;top:34%;animation-delay:.3s}.pin.p3{left:34%;top:58%;animation-delay:.8s}.pin.p1{left:48%;top:48%}
    .hero-metrics{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.metric{border:1px solid rgba(255,255,255,.12);border-radius:20px;padding:14px;background:rgba(255,255,255,.08)}.metric span{display:block;color:#bfd6ce;font-size:.76rem;text-transform:uppercase;font-weight:900;letter-spacing:.07em}.metric b{display:block;margin-top:8px;font-size:1.45rem}
    .section{display:none;margin-top:22px;padding:30px;scroll-margin-top:150px}.section.active{display:block;animation:rise .35s ease both}.section h2{font-size:clamp(2.05rem,4.2vw,3.75rem);line-height:.98;letter-spacing:-.055em;margin:0 0 10px}.section-lead{font-size:1.05rem;color:var(--muted);line-height:1.56;max-width:860px}
    .grid{display:grid;gap:16px}.cols-2{grid-template-columns:1fr 1fr}.cols-3{grid-template-columns:repeat(3,1fr)}.cols-4{grid-template-columns:repeat(4,1fr)}
    .card{border:1px solid var(--line);border-radius:24px;background:#fffaf1;padding:20px;min-height:150px;position:relative;overflow:hidden}.card h3{margin:0 0 8px;font-size:1.35rem}.card p{margin:0;color:var(--muted);line-height:1.48}.card .num{position:absolute;right:16px;bottom:-18px;color:rgba(216,95,66,.14);font-size:5rem;font-weight:950}
    .actor{cursor:pointer;transition:.18s ease}.actor:hover,.actor.active{transform:translateY(-4px);border-color:rgba(216,95,66,.55);box-shadow:0 20px 42px rgba(24,35,29,.12)}
    .flow{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:20px}.flow .card{min-height:180px}.flow .card:after{content:"→";position:absolute;right:-14px;top:46%;font-size:2rem;color:var(--brick)}.flow .card:last-child:after{content:""}
    .tour-layout{display:grid;grid-template-columns:1.05fr .95fr;gap:18px;margin-top:18px}.tour-board{background:linear-gradient(145deg,#10211c,#173f35);color:white}.tour-board p{color:#c8dcd4}.tour-steps{display:grid;gap:10px;margin-top:16px}.tour-step{text-align:left;border:1px solid rgba(255,255,255,.14);border-radius:22px;background:rgba(255,255,255,.07);color:white;padding:15px;cursor:pointer;transition:.18s}.tour-step:hover,.tour-step.active{transform:translateX(5px);border-color:rgba(255,248,235,.55);background:rgba(216,95,66,.22)}.tour-step b{display:block}.tour-step span{display:block;color:#bfd6ce;font-size:.82rem;margin-top:4px}.tour-detail{min-height:460px}.tour-time{display:inline-flex;border-radius:999px;background:var(--mint);color:var(--forest);font-weight:900;padding:7px 10px;font-size:.8rem;margin-bottom:12px}.tour-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}.tour-route{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:16px}.tour-dot{height:10px;border-radius:999px;background:#eadcc8}.tour-dot.active{background:linear-gradient(90deg,var(--forest),var(--brick))}
    .chart-wrap{border:1px solid var(--line);border-radius:28px;background:#fffaf1;padding:20px;min-height:420px}.bar-chart{display:flex;align-items:end;gap:12px;height:300px;padding-top:34px;border-bottom:1px solid var(--line)}.bar{flex:1;border:0;border-radius:16px 16px 0 0;background:linear-gradient(180deg,var(--brick),#efb05e);min-height:8px;position:relative;transition:.25s;cursor:pointer}.bar:hover,.bar.active{filter:saturate(1.25);transform:translateY(-4px);box-shadow:0 16px 28px rgba(216,95,66,.22)}.bar.active:after{content:"";position:absolute;left:50%;bottom:-10px;width:12px;height:12px;border-radius:50%;background:var(--forest);transform:translateX(-50%)}.bar label{position:absolute;bottom:-34px;left:50%;transform:translateX(-50%);font-size:.78rem;color:var(--muted);white-space:nowrap}.bar span{position:absolute;top:-26px;left:50%;transform:translateX(-50%);font-size:.8rem;font-weight:900}
    .method-tabs,.mode-tabs{display:flex;flex-wrap:wrap;gap:9px;margin:18px 0}.pill{border:1px solid var(--line);border-radius:999px;padding:10px 12px;background:#fffaf1;color:var(--muted);font-weight:900;cursor:pointer}.pill.active{background:var(--forest);color:white}
    .formula{white-space:pre-wrap;border-radius:20px;background:#13251f;color:#ecfff7;padding:18px;font-family:"SF Mono",Menlo,Consolas,monospace;line-height:1.55;min-height:132px}
    .stats-lab{display:grid;grid-template-columns:.92fr 1.08fr;gap:18px;margin-top:18px}.method-card{min-height:520px}.stat-workbench{min-height:520px;background:linear-gradient(145deg,#10211c,#173f35);color:white}.stat-workbench p{color:#c8dcd4}.workbench-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}.workbench-head span{border:1px solid rgba(255,255,255,.16);border-radius:999px;padding:7px 10px;color:#d8ece3;font-size:.78rem;font-weight:900;text-transform:uppercase;letter-spacing:.06em}.hypothesis-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}.hypothesis{border:1px solid var(--line);border-radius:20px;background:#fffdf6;padding:14px}.hypothesis b{display:block;color:var(--forest);margin-bottom:6px}.anova-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:18px}.month-detail{background:#10211c;color:white}.month-detail p{color:#c8dcd4}.stat-mini-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px}.stat-mini{border:1px solid rgba(255,255,255,.14);border-radius:18px;padding:13px;background:rgba(255,255,255,.07)}.stat-mini span{display:block;color:#bfd6ce;font-size:.72rem;text-transform:uppercase;font-weight:900}.stat-mini b{display:block;font-size:1.35rem;margin-top:7px}.sim-controls{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0}.dark-control{display:grid;gap:7px;color:#bfd6ce;font-size:.88rem;font-weight:850}.dark-control input{background:rgba(255,255,255,.92)}.stat-output{display:grid;grid-template-columns:170px 1fr;gap:16px;align-items:center;margin:14px 0}.stat-gauge{width:160px;height:160px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(var(--gold) 0deg,var(--brick) var(--sim-deg),rgba(255,255,255,.16) var(--sim-deg),rgba(255,255,255,.16) 360deg)}.stat-gauge b{width:112px;height:112px;border-radius:50%;display:grid;place-items:center;background:#10211c;color:#fff8eb;font-size:1.75rem}.effect-list{display:grid;gap:8px}.effect-row{display:grid;grid-template-columns:128px 1fr 48px;gap:8px;align-items:center;color:#d8ece3;font-size:.86rem}.effect-row .track{background:rgba(255,255,255,.14)}.cluster-viz{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin-top:14px}.cluster-day{border:1px solid rgba(255,255,255,.13);border-radius:16px;min-height:70px;padding:10px;background:rgba(255,255,255,.07);display:grid;align-content:end}.cluster-day b{color:#fff8eb}.cluster-day span{color:#bfd6ce;font-size:.74rem;font-weight:900}
    .explorer{display:grid;grid-template-columns:.72fr 1.28fr;gap:18px}.controls{display:grid;gap:13px}.control{display:grid;gap:7px;color:var(--muted);font-size:.9rem;font-weight:850}select,input,textarea{border:1px solid var(--line);border-radius:15px;background:white;color:var(--ink);padding:11px 12px;min-height:43px}input[type=range]{accent-color:var(--brick);padding:0}
    .results{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;max-height:650px;overflow:auto;padding-right:4px}.risk-card{cursor:pointer;transition:.18s ease;border-left:8px solid var(--brick)}.risk-card:hover,.risk-card.active{transform:translateY(-3px);box-shadow:0 18px 38px rgba(24,35,29,.13);border-color:rgba(216,95,66,.42)}.risk-top{display:flex;justify-content:space-between;gap:10px}.rank{font-size:1.5rem;color:var(--brick);font-weight:950}.risk-score{font-size:1.2rem;color:var(--forest);font-weight:950}.small{font-size:.9rem;color:var(--muted);line-height:1.42}
    .detail{position:sticky;top:88px}.contrib{display:grid;gap:8px;margin-top:12px}.contrib-row{display:grid;grid-template-columns:150px 1fr 55px;gap:8px;align-items:center;font-size:.86rem}.track{height:12px;border-radius:999px;background:#eadcc8;overflow:hidden}.fill{height:100%;border-radius:999px;background:var(--brick)}.fill.neg{background:var(--blue)}
    .policy-board{display:grid;grid-template-columns:.82fr 1.18fr;gap:18px}.policy-bars{display:grid;gap:12px}.policy-row{display:grid;grid-template-columns:135px 1fr 70px;gap:10px;align-items:center}.policy-track{height:30px;border-radius:999px;background:#eadcc8;overflow:hidden}.policy-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--forest),var(--brick));transition:.25s}
    .evidence-grid{display:grid;grid-template-columns:280px 1fr;gap:18px}.evidence-list{display:grid;gap:10px}.evidence-item{text-align:left;border:1px solid var(--line);border-radius:18px;background:#fffaf1;padding:14px;cursor:pointer}.evidence-item.active{background:var(--forest);color:white}.evidence-output-stack{display:grid;gap:14px}.evidence-summary{min-height:220px}.evidence-badge{display:inline-flex;border-radius:999px;background:#10211c;color:white;font-weight:900;padding:7px 10px;font-size:.78rem;margin-bottom:10px}.evidence-bullets{display:grid;gap:8px;margin-top:12px}.evidence-bullet{border-left:6px solid var(--forest);border-radius:15px;background:#fffdf6;padding:11px;color:var(--muted)}.evidence-bullet b{color:var(--forest)}pre{white-space:pre-wrap;word-break:break-word;border-radius:22px;background:#10211c;color:#eafff8;padding:18px;max-height:360px;overflow:auto}
    .footer{margin-top:24px;color:var(--muted);font-size:.9rem;text-align:center}.tag{display:inline-flex;border-radius:999px;padding:6px 9px;background:var(--mint);color:var(--forest);font-weight:900;font-size:.78rem;margin:3px}
    .progress-dock{position:fixed;right:14px;bottom:14px;z-index:30;border:1px solid var(--line);border-radius:24px;background:rgba(255,248,235,.92);box-shadow:0 18px 42px rgba(24,35,29,.16);padding:12px;min-width:220px;backdrop-filter:blur(12px)}
    .progress-dock b{display:block;color:var(--forest);font-size:.9rem}.progress-track{height:10px;border-radius:999px;background:#eadcc8;overflow:hidden;margin:9px 0}.progress-fill{height:100%;width:0;background:linear-gradient(90deg,var(--forest),var(--brick));transition:.25s}.progress-dock small{color:var(--muted)}
    .mission-board{display:grid;grid-template-columns:.9fr 1.1fr;gap:18px;margin-top:18px}.mission-choices{display:grid;gap:12px}.choice-card{border:1px solid var(--line);border-left:8px solid var(--gold);border-radius:24px;background:#fffaf1;padding:16px;text-align:left;cursor:pointer;transition:.18s}.choice-card:hover{transform:translateY(-3px);box-shadow:0 16px 32px rgba(24,35,29,.12)}.choice-card.correct{border-left-color:var(--forest);background:#edf7f2}.choice-card.wrong{border-left-color:var(--brick);background:#fff0ea}.mission-result{min-height:220px}.score-ring{width:154px;height:154px;border-radius:50%;display:grid;place-items:center;margin:10px auto 16px;background:conic-gradient(var(--brick) 0deg,var(--brick) var(--risk-deg),#eadcc8 var(--risk-deg),#eadcc8 360deg)}.score-ring span{width:116px;height:116px;border-radius:50%;display:grid;place-items:center;background:#fffaf1;font-size:1.7rem;font-weight:950;color:var(--forest)}
    .compare-layout{display:grid;grid-template-columns:300px 1fr;gap:18px}.compare-controls{display:grid;gap:12px}.compare-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.compare-card{border:1px solid var(--line);border-radius:26px;background:#fffaf1;padding:18px}.compare-meter{height:16px;border-radius:999px;background:#eadcc8;overflow:hidden;margin:8px 0 14px}.compare-meter div{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--gold),var(--brick))}
    .map-toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:18px 0 8px}.map-chip{border:1px solid var(--line);border-radius:999px;background:#fffaf1;color:var(--muted);padding:10px 13px;font-weight:950;cursor:pointer;transition:.18s}.map-chip:hover,.map-chip.active{background:var(--forest);color:white;transform:translateY(-2px);box-shadow:0 12px 24px rgba(24,35,29,.12)}.map-toolbar .control{min-width:190px;margin-left:auto}.nyc-map-layout{display:grid;grid-template-columns:1.18fr .82fr;gap:18px;margin-top:14px}.nyc-map-card{border:1px solid var(--line);border-radius:34px;background:radial-gradient(circle at 18% 20%,rgba(255,248,235,.16),transparent 25%),radial-gradient(circle at 72% 42%,rgba(216,95,66,.18),transparent 29%),linear-gradient(150deg,#071916,#123d34 56%,#1c594c);min-height:640px;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(255,255,255,.08),var(--shadow);position:relative}.nyc-map-card:before{content:"";position:absolute;left:0;right:0;bottom:0;height:110px;background:linear-gradient(to top,rgba(0,0,0,.34),transparent);pointer-events:none}.nyc-map-card:after{content:"Resmi 311 koordinatlarından yaklaşık şehir görünümü";position:absolute;left:22px;bottom:18px;color:#d8ece3;font-weight:850;font-size:.86rem;letter-spacing:.02em}.map-brief{min-height:640px;display:flex;flex-direction:column;gap:12px}.map-side-top{display:grid;grid-template-columns:1fr 150px;gap:12px;align-items:start}.map-side-top .score-ring{margin:0 auto}.borough-shape{fill:rgba(255,248,235,.09);stroke:rgba(255,248,235,.30);stroke-width:2}.borough-label{fill:rgba(216,236,227,.78);font-weight:950;font-size:20px;letter-spacing:.06em}.map-line{stroke:rgba(255,248,235,.08);stroke-width:1.5}.waterline{fill:none;stroke:rgba(216,236,227,.18);stroke-width:18;stroke-linecap:round}.bridge-line{stroke:rgba(255,248,235,.22);stroke-width:2.5;stroke-dasharray:5 9}.risk-dot{cursor:pointer;transition:.18s}.risk-dot circle:first-child{fill:rgba(216,95,66,.16);animation:mapPulse 2.8s ease-in-out infinite}.risk-dot circle:last-child{fill:var(--brick);stroke:#fff8eb;stroke-width:2;filter:drop-shadow(0 4px 8px rgba(0,0,0,.32))}.risk-dot.muted circle:first-child{fill:rgba(255,248,235,.06);animation:none}.risk-dot.muted circle:last-child{fill:#d6a33d;opacity:.64}.risk-dot:hover circle:last-child,.risk-dot.active circle:last-child{fill:var(--gold);r:10;opacity:1}.risk-dot text{fill:#fff8eb;font-size:10px;font-weight:950;paint-order:stroke;stroke:#10211c;stroke-width:3}.map-legend{fill:#bfd6ce;font-size:14px}.subway-line{fill:none;stroke-width:3.2;stroke-linecap:round;opacity:.24;stroke-dasharray:12 14;animation:dash 10s linear infinite}.map-badge{fill:rgba(255,248,235,.92);stroke:rgba(255,248,235,.22)}.map-badge-text{fill:#123d34;font-size:13px;font-weight:950}.selected-link{stroke:#fff8eb;stroke-width:2.5;stroke-dasharray:7 7;animation:dash 7s linear infinite}.selected-callout{fill:rgba(255,248,235,.96);stroke:rgba(255,248,235,.32)}.selected-callout-text{fill:#123d34;font-size:13px;font-weight:950}.map-glow{fill:rgba(216,95,66,.14);animation:mapPulse 2.2s ease-in-out infinite}.map-priority-list{display:grid;gap:8px;max-height:210px;overflow:auto;padding-right:4px}.map-mini-row{border:1px solid var(--line);border-radius:16px;background:#fffdf6;padding:10px;text-align:left;cursor:pointer;transition:.18s;font:inherit}.map-mini-row:hover,.map-mini-row.active{background:#edf7f2;border-color:rgba(18,61,52,.36);transform:translateY(-2px)}.map-mini-row b{display:flex;justify-content:space-between;gap:8px;color:var(--forest);font-size:.9rem}.map-mini-row b span{color:var(--forest);font-size:.9rem;margin-top:0}.map-mini-row>span{display:block;color:var(--muted);font-size:.78rem;margin-top:4px}.map-note{border-left:6px solid var(--gold);border-radius:16px;background:#fff4d8;padding:12px;color:var(--muted);font-size:.86rem}
    .tech-layout{display:grid;grid-template-columns:1.12fr .88fr;gap:18px;margin-top:18px}.tech-visual{background:linear-gradient(145deg,#10211c,#153f35 56%,#0d1714);color:white;min-height:620px}.tech-visual p{color:#c8dcd4}.tech-map{width:100%;height:auto;min-height:390px}.tech-node{fill:rgba(255,248,235,.1);stroke:rgba(255,248,235,.42);stroke-width:2}.tech-node.active{fill:rgba(216,95,66,.42);stroke:#fff8eb}.tech-node-label{fill:#fff8eb;font-weight:900;font-size:15px;text-anchor:middle}.tech-node-sub{fill:#bfd6ce;font-weight:800;font-size:11px;text-anchor:middle}.tech-flow{fill:none;stroke:rgba(255,248,235,.30);stroke-width:4;stroke-linecap:round;stroke-dasharray:12 12;animation:dash 9s linear infinite}.tech-packet{fill:#d85f42;filter:drop-shadow(0 0 8px rgba(216,95,66,.85))}.tech-card-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-top:16px}.tech-card{text-align:left;border:1px solid var(--line);border-radius:22px;background:#fffaf1;padding:16px;cursor:pointer;transition:.18s}.tech-card:hover,.tech-card.active{transform:translateY(-3px);border-color:rgba(216,95,66,.55);box-shadow:0 18px 34px rgba(24,35,29,.12)}.tech-card b{display:block;color:var(--forest);font-size:1.05rem}.tech-card span{display:block;color:var(--muted);font-size:.86rem;margin-top:5px}.tech-detail{min-height:620px}.tech-bullets{display:grid;gap:10px;margin-top:14px}.tech-bullet{border-left:6px solid var(--brick);border-radius:16px;background:#fffdf6;padding:13px}.tech-bullet b{display:block;color:var(--forest);margin-bottom:4px}.tech-bullet p{font-size:.9rem}.stack-ribbon{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px}.stack-ribbon .metric{background:#10211c;color:white}.cost-note{border-left:7px solid var(--gold);background:#fff4d8}
    .insight-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}.insight{border-radius:22px;padding:16px;background:#10211c;color:white;min-height:126px}.insight span{display:block;color:#bfd6ce;font-size:.75rem;text-transform:uppercase;font-weight:900;letter-spacing:.06em}.insight b{display:block;font-size:1.65rem;margin-top:8px}.sparkline{height:46px;margin-top:10px}
    .toast{position:fixed;left:50%;bottom:24px;z-index:60;transform:translate(-50%,20px);opacity:0;max-width:min(92vw,420px);border-radius:999px;background:#10211c;color:white;padding:12px 16px;box-shadow:0 18px 42px rgba(24,35,29,.24);font-weight:900;transition:.25s}.toast.show{transform:translate(-50%,0);opacity:1}
    .safe-note{border-left:7px solid var(--forest);background:#edf7f2}.mobile-hint{display:none;margin-top:10px;color:var(--muted)}
    @keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}@keyframes pulse{50%{transform:scale(1.16);opacity:.55}}@keyframes pop{50%{transform:scale(1.25)}}@keyframes mapPulse{50%{transform:scale(1.75);opacity:.08}}@keyframes dash{to{stroke-dashoffset:-120}}
    @media(max-width:980px){.hero,.cols-2,.explorer,.policy-board,.evidence-grid,.mission-board,.compare-layout,.nyc-map-layout,.stats-lab,.anova-grid,.tech-layout,.tour-layout{grid-template-columns:1fr}.flow,.cols-3,.cols-4,.insight-strip,.hypothesis-grid{grid-template-columns:repeat(2,1fr)}.results,.compare-grid{grid-template-columns:1fr}.detail{position:static}.topbar{border-radius:24px;align-items:flex-start;flex-direction:column}.nav button{padding:9px}.progress-dock{position:static;margin:14px 0}.mobile-hint{display:block}.nyc-map-card,.map-brief,.tech-visual,.tech-detail{min-height:auto}}
    @media(max-width:620px){.shell{width:min(100% - 22px,1220px);padding-top:12px}.hero-copy,.section{padding:20px}.panel{border-radius:24px}h1{font-size:2.9rem}.lead{font-size:1.02rem}.topbar{position:relative;top:auto}.nav{justify-content:flex-start;overflow-x:auto;flex-wrap:nowrap;width:100%;padding-bottom:4px}.nav button{white-space:nowrap}.flow,.cols-3,.cols-4,.hero-metrics,.insight-strip,.hypothesis-grid,.sim-controls,.stat-output,.stat-mini-grid,.tech-card-grid,.stack-ribbon,.tour-route,.map-side-top{grid-template-columns:1fr}.map-toolbar .control{margin-left:0;width:100%}.nyc-map-card{min-height:420px}.nyc-map-card:after{font-size:.74rem;left:16px}.phone{min-height:360px}.bar-chart{gap:6px;overflow-x:auto}.bar{min-width:42px}.bar span{font-size:.68rem}.bar label{font-size:.68rem}.choice-card,.card{border-radius:20px}.toast{bottom:12px;border-radius:20px}}
  </style>
</head>
<body>
<main class="shell">
  <header class="topbar">
    <a class="brand" href="#top"><span class="brand-mark"></span><span>NYC Heating Risk</span></a>
    <nav class="nav" aria-label="Site bölümleri">
      <button class="active" data-section="story">Hikaye</button>
      <button data-section="tour">Hızlı tur</button>
      <button data-section="map">Harita</button>
      <button data-section="stats">İstatistik</button>
      <button data-section="explorer">Risk</button>
      <button data-section="stack">Teknoloji</button>
      <button data-section="evidence">Kanıt</button>
    </nav>
  </header>

  <section id="top" class="hero">
    <div class="panel hero-copy">
      <div>
        <div class="kicker">Ömer Canbolat · 22050622 · IST-312</div>
        <h1>Şikayet gelmeden önce riskli binaları görün.</h1>
        <p class="lead">Bu interaktif site, NYC resmi açık verileriyle geliştirilen ısınma/sıcak su şikayet riski projesini sınıfın telefondan inceleyebilmesi için hazırlandı. Amaç: sınırlı denetim kapasitesini veriyle önceliklendirmek.</p>
        <div class="cta">
          <button class="btn" data-jump="tour">3 dakikalık hızlı tur</button>
          <button class="btn alt" data-jump="map">Haritayı aç</button>
          <button class="btn alt" data-jump="stats">İstatistik masası</button>
          <button class="btn alt" data-jump="evidence">Kanıtı göster</button>
        </div>
      </div>
      <p class="small"><b>Sınır:</b> Bu otomatik ceza sistemi değildir. Karar destek prototipidir; denetçiye önce nereye bakılabileceğini önerir.</p>
    </div>
    <aside class="panel stage">
      <div class="phone">
        <div class="pulse"></div>
        <div class="phone-inner">
          <div class="mini-map">
            <svg viewBox="0 0 400 180" role="img" aria-label="Soyut NYC risk haritası">
              <path d="M28 142 C98 80 134 112 188 48 C240 -8 290 82 370 34" fill="none" stroke="#d8ece3" stroke-width="15" stroke-linecap="round" opacity=".22"/>
              <path d="M30 146 C104 88 138 116 190 54 C242 0 292 88 372 40" fill="none" stroke="#f6ead5" stroke-width="3" stroke-linecap="round"/>
              <path d="M82 16 L112 160 M174 20 L154 164 M250 24 L236 164 M318 18 L338 166" stroke="#f6ead5" stroke-width="2" opacity=".35"/>
            </svg>
            <span class="pin p1"></span><span class="pin p2"></span><span class="pin p3"></span>
          </div>
          <div class="hero-metrics">
            <div class="metric"><span>Resmi şikayet</span><b id="heroComplaints">-</b></div>
            <div class="metric"><span>Bina-gün paneli</span><b id="heroRows">-</b></div>
            <div class="metric"><span>Test AUC</span><b id="heroAuc">-</b></div>
            <div class="metric"><span>Lift@50</span><b id="heroLift">-</b></div>
          </div>
        </div>
      </div>
    </aside>
  </section>

  <section id="tour" class="panel section">
    <h2>3 dakikalık hızlı tur: siteyi nereden okuyacağını bil.</h2>
    <p class="section-lead">Sınıfta zamanı az olan biri bu rotayı izlesin. Her adımda “neye bakacağım, ne anlayacağım?” sorusu cevaplanır.</p>
    <div class="tour-layout">
      <div class="card tour-board">
        <h3>Önerilen rota</h3>
        <p>Bu sırayı takip edersen proje önce problemden başlar, sonra harita, istatistik, risk çıktısı, teknoloji ve kanıtla kapanır.</p>
        <div class="tour-route" id="tourRoute"></div>
        <div class="tour-steps" id="tourSteps"></div>
      </div>
      <aside class="card tour-detail">
        <span class="tour-time" id="tourTime">0:00</span>
        <h3 id="tourTitle">Adım seç</h3>
        <p id="tourText"></p>
        <div class="tour-actions">
          <button class="btn" id="tourGo">Bu bölüme git</button>
          <button class="btn alt" id="tourNext">Sonraki adım</button>
        </div>
        <div class="card safe-note" style="margin-top:18px;min-height:auto">
          <h3>Tek cümlelik proje özeti</h3>
          <p>NYC resmi açık verileriyle ertesi gün ısınma/sıcak su şikayeti riski yüksek binaları tahmin edip denetim öncelik listesine çeviren karar destek prototipi.</p>
        </div>
        <div class="tour-actions">
          <button class="btn alt" data-jump="field">Saha brifingi</button>
          <button class="btn alt" data-jump="data">Veri haritası</button>
          <button class="btn alt" data-jump="compare">Bina karşılaştır</button>
          <button class="btn alt" data-jump="policy">Kapasite simülasyonu</button>
        </div>
      </aside>
    </div>
  </section>

  <section id="story" class="panel section active">
    <h2>Problem sadece veri problemi değil; insan ve kapasite problemi.</h2>
    <p class="section-lead">Aşağıdaki rollere tıkla. Aynı proje, kiracı, denetçi ve veri bilimci açısından farklı bir ihtiyacı karşılıyor.</p>
    <div class="grid cols-3" id="actorCards"></div>
    <div class="card" style="margin-top:16px"><h3 id="actorTitle">Sorun özeti</h3><p id="actorText"></p><span class="num">?</span></div>
    <div class="flow">
      <div class="card"><h3>1. Sorun</h3><p>Isınma/sıcak su problemi temel yaşam hizmetini etkiler.</p><span class="num">01</span></div>
      <div class="card"><h3>2. Veri</h3><p>311, HPD, NOAA ve Census CRE resmi açık verileri birleşir.</p><span class="num">02</span></div>
      <div class="card"><h3>3. Tahmin</h3><p>Her bina-gün için ertesi gün şikayet olasılığı üretilir.</p><span class="num">03</span></div>
      <div class="card"><h3>4. Sıralama</h3><p>Risk skoru büyükten küçüğe sıralanıp Top-50 liste olur.</p><span class="num">04</span></div>
      <div class="card"><h3>5. Karar desteği</h3><p>Denetçiye öncelik önerir, otomatik yaptırım üretmez.</p><span class="num">05</span></div>
    </div>
  </section>

  <section id="field" class="panel section">
    <h2>Saha brifingi: önce nereye gidileceğini veriyle savun.</h2>
    <p class="section-lead">Bu bölüm küçük bir karar provasıdır. Üç bina arasından birini seçince modelin hangi binayı neden öne aldığını ve seçimin hangi sinyallerle desteklendiğini görürsün.</p>
    <div class="mission-board">
      <div class="card safe-note">
        <h3>Brifing kuralı</h3>
        <p>Bir bina seç. Sistem seçimini modelin önerisiyle karşılaştırır. Amaç, geçmiş şikayet, son 7 gün sinyali, ihlal, kırılganlık ve risk olasılığının saha önceliğini nasıl değiştirdiğini görmek.</p>
        <div class="insight-strip" style="grid-template-columns:1fr 1fr;margin-bottom:0">
          <div class="insight"><span>Senaryo</span><b id="missionRound">1/3</b></div>
          <div class="insight"><span>Karar tipi</span><b>Öncelik</b></div>
        </div>
        <button class="btn" id="nextMission" style="margin-top:14px">Sonraki senaryo</button>
      </div>
      <div class="card mission-result">
        <div class="score-ring" id="missionRing" style="--risk-deg:0deg"><span id="missionRisk">?</span></div>
        <h3 id="missionTitle">Seçimini yap</h3>
        <p id="missionText">Modelin neden o binayı öne aldığı burada açıklanacak.</p>
      </div>
    </div>
    <div class="mission-choices" id="missionChoices" style="margin-top:16px"></div>
  </section>

  <section id="map" class="panel section">
    <h2>NYC risk haritası: seçilen bina şehirde nereye düşüyor?</h2>
    <p class="section-lead">Harita artık kalabalık bir nokta bulutu yerine öncelik odaklı çalışır: önce Top-10 temiz görünür, istersen Top-25 veya Top-50'ye geçebilirsin. Konumlar NYC 311 kayıtlarındaki BBL eşleşmeli latitude/longitude bilgisinden türetilmiştir; bu yüzden “yaklaşık resmi koordinatlı risk görünümü” olarak okunmalı.</p>
    <div class="map-toolbar" aria-label="Harita görünüm seçenekleri">
      <button class="map-chip active" data-map-limit="10">Top-10 net görünüm</button>
      <button class="map-chip" data-map-limit="25">Top-25</button>
      <button class="map-chip" data-map-limit="50">Top-50</button>
      <label class="control">İlçe filtresi
        <select id="mapBoroughFilter"><option value="Tümü">Tümü</option></select>
      </label>
    </div>
    <div class="nyc-map-layout">
      <div class="nyc-map-card">
        <svg id="nycRiskMap" viewBox="0 0 760 640" role="img" aria-label="Top-50 NYC heating risk map"></svg>
      </div>
      <aside class="card map-brief">
        <div class="map-side-top">
          <div>
            <h3 id="mapTitle">Bir risk noktasına dokun</h3>
            <p id="mapMeta" class="small">Nokta seçilince adres, ilçe, risk ve istatistiksel gerekçe burada görünür.</p>
          </div>
          <div class="score-ring" id="mapRing" style="--risk-deg:0deg"><span id="mapRisk">?</span></div>
        </div>
        <p id="mapWhy" class="small"></p>
        <div id="mapStats" class="grid cols-2"></div>
        <h3 style="margin-top:4px">Haritada görünen öncelikler</h3>
        <div id="mapPriorityList" class="map-priority-list"></div>
        <p class="map-note"><b>Harita dürüstlüğü:</b> Bu bir Google Maps yerine geçen kesin parsel haritası değildir; proje sunumu için resmi 311 koordinatlarıyla hazırlanmış şehir bağlamı görselleştirmesidir.</p>
      </aside>
    </div>
  </section>

  <section id="data" class="panel section">
    <h2>Veri haritası: dört resmi kaynak tek karar birimine bağlanıyor.</h2>
    <p class="section-lead">Kartlara tıklayınca kaynağın ne işe yaradığını gör. Kritik zaman mantığı: <b>X(i,t) → Y(i,t+1)</b>. Model bugünkü bilgiyle yarını tahmin eder, geleceği görmez.</p>
    <div class="grid cols-3" id="dataCards"></div>
    <div class="card" style="margin-top:16px"><h3 id="dataTitle"></h3><p id="dataText"></p><div id="dataTags"></div></div>
  </section>

  <section id="stats" class="panel section">
    <h2>İstatistik laboratuvarı: yöntem seç, ne için kullanıldığını gör.</h2>
    <p class="section-lead">Bu bölüm hocanın soracağı “hangi yöntemi neden kullandın?” sorusuna doğrudan cevap verir. Yönteme tıkla; hipotez, formül, proje içindeki görevi ve küçük etkileşimli örnek birlikte değişsin.</p>
    <div class="stats-lab">
      <div class="card method-card">
        <div class="method-tabs" id="methodTabs"></div>
        <h3 id="methodName"></h3>
        <p id="methodQuestion"></p>
        <p id="methodWhy" style="margin-top:10px"></p>
        <p class="small" id="methodResult" style="margin-top:12px"></p>
        <div class="hypothesis-grid" id="hypothesisGrid"></div>
        <div class="formula" id="methodFormula" style="margin-top:14px"></div>
      </div>
      <div class="card stat-workbench" id="statWorkbench"></div>
    </div>
    <div class="chart-wrap" style="margin-top:18px">
      <div class="mode-tabs"><button class="pill active" data-chart="complaints">Aylık ortalama şikayet</button><button class="pill" data-chart="buildings">Pozitif bina sayısı</button></div>
      <div class="anova-grid">
        <div>
          <div class="bar-chart" id="monthChart"></div>
          <p class="small" id="anovaCaption"></p>
        </div>
        <aside class="card month-detail">
          <h3 id="monthTitle">Ay seç</h3>
          <p id="monthText" class="small">Grafikteki aylardan birine tıklayınca ANOVA hikayesindeki yeri burada görünür.</p>
          <div class="stat-mini-grid" id="monthStats"></div>
        </aside>
      </div>
    </div>
  </section>

  <section id="explorer" class="panel section">
    <h2>Risk keşfi: sınıf kendi filtresini seçip binaları inceleyebilir.</h2>
    <p class="section-lead">Bu bölüm gerçek çıktıyı gösterir: bina, ilçe, risk, kırılganlık skoru ve “neden riskli?” açıklaması.</p>
    <div class="insight-strip">
      <div class="insight"><span>Top-50 ortalama risk</span><b id="avgTopRisk">-</b><svg class="sparkline" id="riskSpark"></svg></div>
      <div class="insight"><span>En yüksek risk</span><b id="maxTopRisk">-</b></div>
      <div class="insight"><span>İlçe çeşitliliği</span><b id="boroughCount">-</b></div>
      <div class="insight"><span>En yaygın sinyal</span><b>Geçmiş şikayet</b></div>
    </div>
    <div class="explorer">
      <aside class="card detail">
        <div class="controls">
          <label class="control">İlçe filtresi<select id="boroughFilter"></select></label>
          <label class="control">Arama<input id="searchBox" placeholder="Bina ID veya adres ara"></label>
          <label class="control">Minimum risk: <b id="riskLabel">0%</b><input id="riskFilter" type="range" min="0" max="100" value="0"></label>
          <label class="control">Gösterilecek kart sayısı<select id="limitFilter"><option>10</option><option selected>20</option><option>50</option></select></label>
        </div>
        <hr style="border:0;border-top:1px solid var(--line);margin:18px 0">
        <h3 id="detailTitle">Bir bina seç</h3>
        <p id="detailMeta" class="small">Kartlardan birine tıklayınca açıklama burada açılır.</p>
        <p id="detailWhy" class="small"></p>
        <div class="contrib" id="contribChart"></div>
      </aside>
      <div class="results" id="riskCards"></div>
    </div>
  </section>

  <section id="compare" class="panel section">
    <h2>İki binayı yan yana koy: neden biri önce geliyor?</h2>
    <p class="section-lead">Bu bölüm “neye göre önce gidilmeli?” sorusunu somutlaştırır. Risk, geçmiş şikayet, ihlal, kırılganlık ve model açıklamasını yan yana karşılaştır.</p>
    <div class="compare-layout">
      <div class="card compare-controls">
        <label class="control">Bina A<select id="compareA"></select></label>
        <label class="control">Bina B<select id="compareB"></select></label>
        <button class="btn" id="swapCompare">Yer değiştir</button>
        <p class="small">Öneri: yüksek riskli Bronx binası ile Manhattan binasını karşılaştır; riskin sadece ilçe değil geçmiş şikayet ve bina sinyalleriyle değiştiğini göreceksin.</p>
      </div>
      <div class="compare-grid" id="compareGrid"></div>
    </div>
  </section>

  <section id="policy" class="panel section">
    <h2>Karar simülasyonu: kapasite değişirse beklenen fayda nasıl değişir?</h2>
    <p class="section-lead">Denetim kapasitesini değiştir. Model, geçmişe dayalı basit seçim ve rastgele seçim beklenen isabet açısından karşılaştırılır.</p>
    <div class="policy-board">
      <div class="card">
        <label class="control">Günlük kapasite: <b id="capacityLabel">50</b> bina<input id="capacitySlider" type="range" min="10" max="100" step="5" value="50"></label>
        <p class="small" id="policyCaption"></p>
      </div>
      <div class="card"><div class="policy-bars" id="policyBars"></div></div>
    </div>
  </section>

  <section id="stack" class="panel section">
    <h2>Teknoloji zinciri: model sadece dosya değil, çalışan sisteme dönüştü.</h2>
    <p class="section-lead">Bu bölüm “Python, SQL, R, Docker, AWS ve Kubernetes neden kullanıldı?” sorusunu cevaplar. Amaç araç kalabalığı yapmak değil; her aracı gerçek bir proje problemini çözmek için kullanmaktır.</p>
    <div class="tech-layout">
      <div class="card tech-visual">
        <h3>Uçtan uca çalışma hattı</h3>
        <p>Veri dosyadan modele, model API’ye, API container’a, container da AWS/EKS ortamına taşınabilecek hale gelir.</p>
        <svg class="tech-map" id="techMap" viewBox="0 0 780 520" role="img" aria-label="Teknoloji mimarisi akışı"></svg>
        <div class="stack-ribbon">
          <div class="metric"><span>Yerel kanıt</span><b>API + dashboard</b></div>
          <div class="metric"><span>Paketleme</span><b>Docker</b></div>
          <div class="metric"><span>Canlı ortam</span><b>AWS/EKS</b></div>
          <div class="metric"><span>Paylaşım</span><b>Statik site</b></div>
        </div>
      </div>
      <aside class="card tech-detail">
        <h3 id="techTitle">Bir araca tıkla</h3>
        <p id="techRole" class="small">Kart seçilince bu aracın projedeki görevi burada açılır.</p>
        <div class="tech-bullets" id="techBullets"></div>
        <div class="card cost-note" style="margin-top:14px;min-height:auto">
          <h3>Maliyet ve dürüstlük notu</h3>
          <p>AWS kısmı maliyet nedeniyle sürekli açık tutulmaz. Sunum günü kısa süreli açılır, canlı çalıştığı kanıtlanır, sonra kapatılır. Bu yüzden proje “AWS’ye çıkabilir” iddiasını kanıt raporuyla destekler; boş yere ücret yazdırmaz.</p>
        </div>
      </aside>
    </div>
    <div class="tech-card-grid" id="techCards"></div>
  </section>

  <section id="evidence" class="panel section">
    <h2>Kanıt dolabı: çalışan sistemin parçaları.</h2>
    <p class="section-lead">Buradaki çıktılar statik örnek olarak gömüldü. Canlı derste aynı zincir local API, dashboard, demo-proof ve AWS proof raporlarıyla gösterilir.</p>
    <div class="evidence-grid">
      <div class="evidence-list" id="evidenceList"></div>
      <div class="evidence-output-stack">
        <div class="card evidence-summary">
          <span class="evidence-badge" id="evidenceBadge">Kanıt</span>
          <h3 id="evidenceHumanTitle">Bir kanıt seç</h3>
          <p id="evidenceHumanText"></p>
          <div class="evidence-bullets" id="evidenceHumanBullets"></div>
        </div>
        <h3 style="margin:0 0 -4px">Teknik çıktı: ham kanıt</h3>
        <pre id="evidenceOutput"></pre>
      </div>
    </div>
  </section>

  <p class="footer">NYC Heating Risk interaktif proje sitesi · Statik HTML olarak çalışır · AWS kaynağı oluşturmaz.</p>
</main>
<aside class="progress-dock" aria-live="polite">
  <b>Keşif ilerlemesi</b>
  <div class="progress-track"><div class="progress-fill" id="progressFill"></div></div>
  <small id="progressText">0 bölüm gezildi</small>
</aside>
<div class="toast" id="toast"></div>

<script id="app-data" type="application/json">__APP_DATA__</script>
<script>
const data = JSON.parse(document.getElementById('app-data').textContent);
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];
const fmt = (n, d=1) => Number(n == null ? 0 : n).toLocaleString('tr-TR', {maximumFractionDigits:d});
const pct = (n, d=1) => `${(Number(n == null ? 0 : n)*100).toFixed(d)}%`;
const escapeHtml = (value) => String(value == null ? '' : value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

const actors = [
  {title:'Kiracı açısından', icon:'ev', text:'Isınma veya sıcak su yoksa sorun doğrudan günlük hayatı etkiler. Proje bu sorunu görünür kılar; riskli binaların daha erken fark edilmesini hedefler.'},
  {title:'Denetçi açısından', icon:'liste', text:'Denetim ekibi her binaya aynı anda gidemez. Proje, sınırlı kapasiteyle önce hangi binalara bakılacağını sıralar.'},
  {title:'Veri bilimi açısından', icon:'model', text:'Geçmiş şikayet, hava, bina/ihlal bilgisi ve kırılganlık verisi birleştirilir; ertesi gün şikayet riski tahmin edilir.'}
];
const sources = [
  {title:'NYC 311', text:'Vatandaş hizmet talepleri. Isınma ve sıcak su şikayetleri hedef değişkenin temel kaynağıdır.', tags:['şikayet','hedef','resmi açık veri']},
  {title:'HPD', text:'New York konut bakım verileri. Bina, ihlal, kayıt ve ısı sensörü programı bilgisi sağlar.', tags:['bina','ihlal','bakım geçmişi']},
  {title:'NOAA', text:'Günlük hava verisi. Sıcaklık, soğukluk yükü, yağış ve rüzgar gibi çevresel sinyaller eklenir.', tags:['hava','soğukluk','günlük veri']},
  {title:'Census CRE', text:'Sosyal/çevresel kırılganlık göstergesi. Önceliklendirmede equity-aware katmanı destekler.', tags:['kırılganlık','tract','equity']},
  {title:'Bina-gün paneli', text:'Her satır bir binanın bir gününü temsil eder. Şikayet olmayan günler de tutulduğu için model normal günleri de öğrenir.', tags:['building-day','dense panel','8.7M+ satır']},
  {title:'Zaman kuralı', text:'X(i,t) bugüne kadar bilinen bilgidir; Y(i,t+1) ertesi gün şikayet hedefidir. Bu kural bilgi sızıntısını önler.', tags:['leakage audit','t → t+1','gerçek tahmin']}
];
const tourSteps = [
  {target:'story', time:'0:00 - 0:30', title:'Problem', text:'Önce gerçek insan problemini gör: denetim kapasitesi sınırlı, her binaya aynı anda gidilemiyor. Proje bu yüzden “yarın önce nereye bakılmalı?” sorusunu çözüyor.'},
  {target:'map', time:'0:30 - 1:00', title:'NYC haritası', text:'Top-50 riskli bina New York üzerinde yaklaşık resmi koordinatlarla görünür. Böylece model çıktısı soyut bir tablo değil, şehir üzerinde incelenebilir bir risk listesi olur.'},
  {target:'stats', time:'1:00 - 1:40', title:'İstatistik', text:'ANOVA aylar arasında fark var mı sorusunu, lojistik regresyon ise ertesi gün şikayet olasılığını açıklar. NB, GEE ve GLMM destekleyici istatistik kontrolleridir.'},
  {target:'explorer', time:'1:40 - 2:10', title:'Risk çıktısı', text:'Gerçek proje çıktısı burada: bina seç, risk olasılığını, neden riskli olduğunu ve hangi değişkenlerin kararı etkilediğini gör.'},
  {target:'stack', time:'2:10 - 2:40', title:'Teknoloji zinciri', text:'Python, SQL, R, FastAPI, Docker, AWS ve EKS araçları burada proje ihtiyacına bağlanır. Amaç araç göstermek değil, çalışan veri bilimi sistemi kurmaktır.'},
  {target:'evidence', time:'2:40 - 3:00', title:'Kanıt', text:'Son bölümde API sağlık kontrolü, Top-5 öncelik JSON’u, score endpoint örneği, AWS canlı deploy ve kapatma kanıtı gösterilir.'}
];
const techStack = [
  {id:'python', name:'Python', role:'ETL, feature üretimi ve model eğitimi', why:'Veri temizleme, 8.7M+ bina-gün paneli kurma, lojistik regresyon modelini eğitme ve raporları üretme işinin ana dili olarak kullanıldı.', used:'pandas, scikit-learn, statsmodels ve proje scriptleriyle resmi veriler işlenip model artefaktları üretildi.', proof:'train, analysis-suite, test ve demo-proof komutları bu hattı çalıştırıyor.'},
  {id:'sql', name:'SQL / SQLite', role:'Hızlı kayıt arama ve API lookup katmanı', why:'Dashboard veya API tek bina kaydını ararken milyonlarca satırlık CSV üzerinde yavaş arama yapmasın diye lookup veritabanı kullanıldı.', used:'record_lookup.sqlite ile /records/{building_id} endpoint’i hızlı cevap verebilir hale geldi.', proof:'API testleri lookup DB yolunu ve CSV’ye gereksiz düşülmediğini kontrol ediyor.'},
  {id:'r', name:'R', role:'İstatistiksel doğrulama ve lisans dersi uyumu', why:'Projenin sadece makine öğrenmesi değil, istatistiksel test ve modelleme tarafı da olduğunu göstermek için R analizi eklendi.', used:'ANOVA, mevsimsel fark, destekleyici istatistik çıktıları ve rapor hizalaması için kullanıldı.', proof:'r-analysis hedefi ve rapor çıktıları sunumdaki istatistik bölümünü destekliyor.'},
  {id:'fastapi', name:'FastAPI', role:'Modeli çalışan servis haline getirme', why:'Model dosyada kalırsa proje sadece notebook olur. FastAPI ile risk skoru, öncelik listesi, dashboard ve sağlık kontrolü endpoint olarak sunuldu.', used:'/health, /metadata, /priorities/latest, /records, /score, /dashboard ve /showcase uçları servis edildi.', proof:'local dashboard startup proof ve API testleri bu katmanın çalıştığını gösteriyor.'},
  {id:'docker', name:'Docker', role:'Çalışma ortamını paketleme', why:'“Benim bilgisayarımda çalışıyor” riskini azaltmak için API ve bağımlılıklar container mantığıyla paketlenebilir hale getirildi.', used:'Dockerfile API servis imajını üretir; aynı imaj yerelde ve AWS tarafında çalıştırılabilir.', proof:'class-demo-check Docker daemon erişimini ve demo zincirini kontrol ediyor.'},
  {id:'aws', name:'AWS', role:'Gerçek sunucu/deploy kanıtı', why:'Projeyi sadece yerelde değil, bulut ortamına çıkarılabilir bir karar destek servisi olarak göstermek için kullanıldı.', used:'S3 model/çıktı artefaktları, ECR container imajı, EKS uygulama çalıştırma ve Load Balancer dış erişim için kurgulandı.', proof:'aws_live_deploy_proof ve aws_shutdown_proof raporları canlı açma/kapatma kanıtını tutuyor.'},
  {id:'eks', name:'Kubernetes / EKS', role:'Container orkestrasyonu', why:'Docker tek başına imaj üretir; Kubernetes/EKS ise bu imajın sunucuda çalışmasını, servis olarak erişilmesini ve yönetilmesini sağlar.', used:'Kubernetes manifestleri API deployment ve service/load balancer zincirini tarif eder.', proof:'deploy-render, k8s-check ve release-dry-run AWS deploy zincirini doğrular.'},
  {id:'site', name:'GitHub Pages / Statik site', role:'Sınıfla güvenli paylaşım', why:'Herkesin telefondan açabileceği, AWS maliyeti oluşturmayan, tek HTML dosyasıyla çalışan proje anlatım yüzeyi gerekti.', used:'Bu interaktif site statik HTML olarak üretildi; QR veya link ile iOS/Android cihazlarda açılabilir.', proof:'docs/index.html ve Downloads kopyası aynı içeriği taşır; class-demo-check /showcase çıktısını kontrol eder.'}
];
const sectionIds = ['story','tour','field','map','data','stats','explorer','compare','policy','stack','evidence'];
let visitedSections = {};
try { visitedSections = JSON.parse(localStorage.getItem('nycHeatVisitedSections') || '{}'); } catch (e) { visitedSections = {}; }
let missionIndex = 0;
let currentChartKind = 'complaints';
let selectedMonthIndex = 0;
let tourIndex = 0;
let initializing = true;

function activate(sectionId){
  $$('.section').forEach(s => s.classList.toggle('active', s.id === sectionId));
  $$('.nav button').forEach(b => b.classList.toggle('active', b.dataset.section === sectionId));
  const section = document.getElementById(sectionId);
  if (section) {
    const topbar = $('.topbar');
    const offset = topbar ? topbar.getBoundingClientRect().height + 18 : 0;
    window.scrollTo({top: section.getBoundingClientRect().top + window.scrollY - offset, behavior:'smooth'});
  }
  markVisited(sectionId);
}
$$('[data-section]').forEach(btn => btn.addEventListener('click', () => activate(btn.dataset.section)));
$$('[data-jump]').forEach(btn => btn.addEventListener('click', () => activate(btn.dataset.jump)));

function markVisited(sectionId){
  if (initializing) return;
  if (!sectionIds.includes(sectionId)) return;
  visitedSections[sectionId] = true;
  try { localStorage.setItem('nycHeatVisitedSections', JSON.stringify(visitedSections)); } catch (e) {}
  updateProgress();
}
function updateProgress(){
  const count = sectionIds.filter(id => visitedSections[id]).length;
  const pctDone = Math.round(count / sectionIds.length * 100);
  $('#progressFill').style.width = `${pctDone}%`;
  $('#progressText').textContent = `${count}/${sectionIds.length} bölüm gezildi`;
}
function toast(message){
  const el = $('#toast');
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(window.__nycHeatToastTimer);
  window.__nycHeatToastTimer = setTimeout(() => el.classList.remove('show'), 1900);
}

function initHero(){
  $('#heroComplaints').textContent = fmt(data.headline.complaints, 0);
  $('#heroRows').textContent = fmt(data.headline.dense_rows, 0);
  $('#heroAuc').textContent = Number(data.metrics.auc).toFixed(3);
  $('#heroLift').textContent = `${Number(data.metrics.lift50).toFixed(1)}x`;
}

function initActors(){
  $('#actorCards').innerHTML = actors.map((a,i)=>`<article class="card actor ${i===0?'active':''}" data-actor="${i}"><h3>${a.title}</h3><p>${a.text}</p><span class="num">${i+1}</span></article>`).join('');
  function select(i){
    $$('.actor').forEach(c => c.classList.toggle('active', Number(c.dataset.actor)===i));
    $('#actorTitle').textContent = actors[i].title;
    $('#actorText').textContent = actors[i].text;
    markVisited('story');
  }
  $$('.actor').forEach(card => card.addEventListener('click', () => select(Number(card.dataset.actor))));
  select(0);
}

function initTour(){
  $('#tourRoute').innerHTML = tourSteps.map((_, i) => `<span class="tour-dot ${i===0?'active':''}"></span>`).join('');
  $('#tourSteps').innerHTML = tourSteps.map((step, i) => `
    <button class="tour-step ${i===0?'active':''}" data-tour="${i}">
      <b>${i+1}. ${escapeHtml(step.title)}</b>
      <span>${escapeHtml(step.time)} · ${escapeHtml(step.text.slice(0, 82))}...</span>
    </button>`).join('');
  $$('.tour-step').forEach(btn => btn.addEventListener('click', () => selectTour(Number(btn.dataset.tour))));
  $('#tourNext').addEventListener('click', () => selectTour((tourIndex + 1) % tourSteps.length));
  $('#tourGo').addEventListener('click', () => activate(tourSteps[tourIndex].target));
  selectTour(0, false);
}

function selectTour(index, shouldMark=true){
  tourIndex = Math.max(0, Math.min(index, tourSteps.length - 1));
  const step = tourSteps[tourIndex];
  $$('.tour-step').forEach(btn => btn.classList.toggle('active', Number(btn.dataset.tour) === tourIndex));
  $$('.tour-dot').forEach((dot, i) => dot.classList.toggle('active', i <= tourIndex));
  $('#tourTime').textContent = step.time;
  $('#tourTitle').textContent = `${tourIndex + 1}. ${step.title}`;
  $('#tourText').textContent = step.text;
  $('#tourGo').textContent = `${step.title} bölümüne git`;
  if (shouldMark) markVisited('tour');
}

function initDataCards(){
  $('#dataCards').innerHTML = sources.map((s,i)=>`<article class="card actor ${i===0?'active':''}" data-source="${i}"><h3>${s.title}</h3><p>${s.text}</p><span class="num">${String(i+1).padStart(2,'0')}</span></article>`).join('');
  function select(i){
    $$('#dataCards .actor').forEach(c => c.classList.toggle('active', Number(c.dataset.source)===i));
    const s = sources[i];
    $('#dataTitle').textContent = s.title;
    $('#dataText').textContent = s.text;
    $('#dataTags').innerHTML = s.tags.map(t => `<span class="tag">${t}</span>`).join('');
    markVisited('data');
  }
  $$('#dataCards .actor').forEach(card => card.addEventListener('click', () => select(Number(card.dataset.source))));
  select(0);
}

function initMethods(){
  $('#methodTabs').innerHTML = data.methods.map((m,i)=>`<button class="pill ${i===0?'active':''}" data-method="${m.id}">${m.name}</button>`).join('');
  function select(id){
    const method = data.methods.find(m => m.id === id) || data.methods[0];
    $$('#methodTabs .pill').forEach(p => p.classList.toggle('active', p.dataset.method === method.id));
    $('#methodName').textContent = method.name;
    $('#methodQuestion').textContent = method.question;
    $('#methodWhy').textContent = method.why;
    $('#methodResult').textContent = method.result;
    $('#methodFormula').textContent = method.formula;
    $('#hypothesisGrid').innerHTML = hypothesisFor(method.id);
    renderStatWorkbench(method);
    markVisited('stats');
  }
  $$('#methodTabs .pill').forEach(btn => btn.addEventListener('click', () => select(btn.dataset.method)));
  select(data.methods[0].id);
}

function hypothesisFor(id){
  const map = {
    anova: [
      ['H0', 'Ayların ortalama şikayet yükü aynıdır.'],
      ['H1', 'En az bir ayın ortalaması farklıdır.']
    ],
    logistic: [
      ['H0', 'Seçilen değişkenler ertesi gün şikayet olasılığını açıklamaz.'],
      ['H1', 'En az bir değişken şikayet olasılığını anlamlı biçimde değiştirir.']
    ],
    nb: [
      ['H0', 'Şikayet sayısı basit Poisson varsayımıyla yeterince açıklanır.'],
      ['H1', 'Varyans ortalamadan büyük olduğu için Negatif Binom daha uygundur.']
    ],
    gee: [
      ['H0', 'Aynı binanın tekrar eden günleri bağımsız kabul edilebilir.'],
      ['H1', 'Aynı binadaki günler ilişkili olduğu için cluster düzeltmesi gerekir.']
    ],
    glmm: [
      ['H0', 'Binaların kendine özgü başlangıç riskleri yoktur.'],
      ['H1', 'Bazı binalar gözlenmeyen özellikleri nedeniyle kalıcı olarak daha risklidir.']
    ]
  };
  return (map[id] || map.anova).map(([h,t]) => `<div class="hypothesis"><b>${h}</b><span>${t}</span></div>`).join('');
}

function renderStatWorkbench(method){
  if (method.id === 'logistic') return renderLogisticWorkbench(method);
  if (method.id === 'nb') return renderNbWorkbench(method);
  if (method.id === 'gee') return renderPanelWorkbench(method, 'GEE çalışma mantığı', 'Aynı bina birden çok gün gözlendiğinde standart hatalar fazla iyimser görünmesin diye bina düzeyinde cluster mantığı kullanılır.');
  if (method.id === 'glmm') return renderPanelWorkbench(method, 'GLMM çalışma mantığı', 'Her binaya ayrı bir başlangıç riski verilir. Böylece kronik sorunlu bina ile normal bina aynı kefeye konmaz.');
  return renderAnovaWorkbench(method);
}

function renderAnovaWorkbench(method){
  const eta = String(method.result.match(/η²=([0-9.]+)/)?.[1] || '0.500');
  $('#statWorkbench').innerHTML = `
    <div class="workbench-head"><h3>ANOVA karar ekranı</h3><span>Aylık fark testi</span></div>
    <p>Bu yöntemi tahmin yapmak için değil, “ısıtma sezonunda ayların şikayet yükü aynı mı?” sorusunu istatistiksel olarak savunmak için kullandım.</p>
    <div class="stat-mini-grid">
      <div class="stat-mini"><span>F istatistiği</span><b>33.62</b></div>
      <div class="stat-mini"><span>p değeri</span><b>&lt;0.0001</b></div>
      <div class="stat-mini"><span>Etki büyüklüğü</span><b>η²≈${eta}</b></div>
    </div>
    <div class="effect-list" style="margin-top:18px">
      <div class="effect-row"><span>Gruplar arası fark</span><div class="track"><div class="fill" style="width:88%"></div></div><b>yüksek</b></div>
      <div class="effect-row"><span>Grup içi oynama</span><div class="track"><div class="fill neg" style="width:42%"></div></div><b>var</b></div>
      <div class="effect-row"><span>Karar</span><div class="track"><div class="fill" style="width:96%"></div></div><b>H0 red</b></div>
    </div>
    <p class="small" style="margin-top:14px">Grafikte aylara tıklayınca seçilen ayın genel ortalamadan ne kadar ayrıldığını görebilirsin.</p>`;
}

function renderLogisticWorkbench(method){
  const row = data.priorityRows[0] || {};
  $('#statWorkbench').innerHTML = `
    <div class="workbench-head"><h3>Lojistik regresyon simülatörü</h3><span>Ana sıralama modeli</span></div>
    <p>Hedef değişken 0/1: “ertesi gün şikayet var mı?” Bu yüzden risk skoru olasılık olarak üretilir ve binalar bu olasılığa göre sıralanır.</p>
    <div class="sim-controls">
      <label class="dark-control">Geçmiş şikayet <b id="priorVal"></b><input id="statPrior" type="range" min="0" max="700" value="${Math.min(700, Number(row.cumulative_complaints_prior || 360))}"></label>
      <label class="dark-control">Son 7 gün şikayet <b id="sevenVal"></b><input id="statSeven" type="range" min="0" max="60" value="${Math.min(60, Number(row.rolling_7d_complaints || 8))}"></label>
      <label class="dark-control">Açık ihlal <b id="violVal"></b><input id="statViol" type="range" min="0" max="160" value="${Math.min(160, Number(row.open_linked_violation_count || 0))}"></label>
      <label class="dark-control">CRE kırılganlık <b id="creVal"></b><input id="statCre" type="range" min="0" max="100" value="${Math.round(Number(row.cre_vulnerability_index || .55)*100)}"></label>
    </div>
    <div class="stat-output">
      <div class="stat-gauge" id="simGauge" style="--sim-deg:0deg"><b id="simRisk">-</b></div>
      <div>
        <h3 id="simDecision">Risk yorumu</h3>
        <p id="simText"></p>
        <p class="small">Not: Bu panel yöntemin mantığını öğretmek için sadeleştirilmiş duyarlılık gösterimidir; gerçek Top-50 liste eğitimli model çıktısından gelir.</p>
      </div>
    </div>`;
  ['statPrior','statSeven','statViol','statCre'].forEach(id => document.getElementById(id).addEventListener('input', updateRiskSimulator));
  updateRiskSimulator();
}

function updateRiskSimulator(){
  const prior = Number($('#statPrior').value);
  const seven = Number($('#statSeven').value);
  const viol = Number($('#statViol').value);
  const cre = Number($('#statCre').value) / 100;
  $('#priorVal').textContent = fmt(prior,0);
  $('#sevenVal').textContent = fmt(seven,0);
  $('#violVal').textContent = fmt(viol,0);
  $('#creVal').textContent = fmt(cre,2);
  const z = -3.4 + (prior/700)*3.0 + (seven/60)*1.5 + (viol/160)*0.9 + cre*1.25;
  const p = 1 / (1 + Math.exp(-z));
  $('#simRisk').textContent = pct(p,0);
  $('#simGauge').style.setProperty('--sim-deg', `${p*360}deg`);
  $('#simDecision').textContent = p >= .70 ? 'Yüksek öncelik sinyali' : p >= .35 ? 'Orta risk sinyali' : 'Düşük/izleme sinyali';
  $('#simText').textContent = `Model mantığı: geçmiş şikayet ${fmt(prior,0)}, son 7 gün ${fmt(seven,0)}, açık ihlal ${fmt(viol,0)} ve CRE ${fmt(cre,2)} arttıkça logit değeri yükselir; bu da p olasılığını ve sıralamadaki önceliği artırır.`;
}

function renderNbWorkbench(method){
  $('#statWorkbench').innerHTML = `
    <div class="workbench-head"><h3>Negatif Binom sayım ekranı</h3><span>Kaç şikayet?</span></div>
    <p>Lojistik regresyon “şikayet olur mu?” sorusuna odaklanır. Negatif Binom ise “olursa beklenen şikayet sayısı ne kadar?” tarafını destekler.</p>
    <div class="sim-controls">
      <label class="dark-control">Beklenen ortalama μ <b id="nbMeanVal"></b><input id="nbMean" type="range" min="1" max="60" value="12"></label>
      <label class="dark-control">Dağılma θ <b id="nbThetaVal"></b><input id="nbTheta" type="range" min="2" max="60" value="10"></label>
    </div>
    <div class="stat-mini-grid">
      <div class="stat-mini"><span>Ortalama</span><b id="nbMeanOut">-</b></div>
      <div class="stat-mini"><span>Varyans</span><b id="nbVarOut">-</b></div>
      <div class="stat-mini"><span>Varyans / Ortalama</span><b id="nbRatioOut">-</b></div>
    </div>
    <p id="nbText" class="small" style="margin-top:14px"></p>`;
  ['nbMean','nbTheta'].forEach(id => document.getElementById(id).addEventListener('input', updateNbSimulator));
  updateNbSimulator();
}

function updateNbSimulator(){
  const mean = Number($('#nbMean').value);
  const theta = Number($('#nbTheta').value);
  const variance = mean + (mean*mean/theta);
  $('#nbMeanVal').textContent = fmt(mean,0);
  $('#nbThetaVal').textContent = fmt(theta,0);
  $('#nbMeanOut').textContent = fmt(mean,1);
  $('#nbVarOut').textContent = fmt(variance,1);
  $('#nbRatioOut').textContent = fmt(variance/mean,1) + 'x';
  $('#nbText').textContent = `Poisson modelinde varyans yaklaşık ortalamaya eşit kabul edilir. Burada varyans ortalamanın ${fmt(variance/mean,1)} katı; bu yüzden sayım şikayetleri için Negatif Binom daha esnek bir kontrol modeli olarak kullanılır.`;
}

function renderPanelWorkbench(method, title, text){
  const isGlmm = method.id === 'glmm';
  const days = [0,1,0,2,0,3,1];
  $('#statWorkbench').innerHTML = `
    <div class="workbench-head"><h3>${title}</h3><span>Panel veri kontrolü</span></div>
    <p>${text}</p>
    <div class="cluster-viz">
      ${days.map((v,i) => `<div class="cluster-day"><span>gün ${i+1}</span><b>${v} şikayet</b></div>`).join('')}
    </div>
    <div class="stat-mini-grid">
      <div class="stat-mini"><span>Birim</span><b>Bina-gün</b></div>
      <div class="stat-mini"><span>Cluster</span><b>building_id</b></div>
      <div class="stat-mini"><span>Rol</span><b>${isGlmm ? 'Tanısal' : 'Sağlam hata'}</b></div>
    </div>
    <p class="small" style="margin-top:14px">${isGlmm ? 'Sunumdaki net çizgi: ana ürün lojistik regresyon sıralamasıdır; GLMM, aynı binanın kalıcı farkını kontrol eden destekleyici tanısal katmandır.' : 'GEE, katsayıyı yorumlarken aynı binaya ait günlerin birbirinden tamamen bağımsızmış gibi davranılmasını engeller.'}</p>`;
}

function missionSets(){
  const rows = data.priorityRows;
  return [
    [rows[0], rows[8], rows[17]],
    [rows[2], rows[12], rows[26]],
    [rows[4], rows[18], rows[34]]
  ].map(set => set.filter(Boolean));
}
function initMission(){
  $('#nextMission').addEventListener('click', () => {
    missionIndex = (missionIndex + 1) % missionSets().length;
    renderMission();
  });
  renderMission();
}
function renderMission(){
  const sets = missionSets();
  const choices = sets[missionIndex] || [];
  $('#missionRound').textContent = `${missionIndex + 1}/${sets.length}`;
  $('#missionTitle').textContent = 'Önce hangi binaya gidilmeli?';
  $('#missionText').textContent = 'Kartlardan birini seç. Modelin en yüksek öncelik verdiği bina ve gerekçesi burada açılacak.';
  $('#missionRisk').textContent = '?';
  $('#missionRing').style.setProperty('--risk-deg', '0deg');
  $('#missionChoices').innerHTML = choices.map(row => `
    <button class="choice-card" data-choice="${escapeHtml(row.building_id)}">
      <div class="risk-top"><b>${escapeHtml(row.incident_address || 'Adres yok')}</b><span>${escapeHtml(row.borough)}</span></div>
      <p class="small">Geçmiş şikayet: ${fmt(row.cumulative_complaints_prior,0)} · açık ihlal: ${fmt(row.open_linked_violation_count,0)} · CRE: ${fmt(row.cre_vulnerability_index,3)}</p>
    </button>`).join('');
  $$('.choice-card').forEach(card => card.addEventListener('click', () => chooseMission(card.dataset.choice)));
}
function chooseMission(id){
  const choices = missionSets()[missionIndex] || [];
  const best = choices.slice().sort((a,b) => Number(a.inspection_priority_rank) - Number(b.inspection_priority_rank))[0];
  const selected = choices.find(row => String(row.building_id) === String(id));
  if (!best || !selected) return;
  const correct = String(best.building_id) === String(selected.building_id);
  $$('.choice-card').forEach(card => {
    const isBest = String(card.dataset.choice) === String(best.building_id);
    const isSelected = String(card.dataset.choice) === String(selected.building_id);
    card.classList.toggle('correct', isBest);
    card.classList.toggle('wrong', isSelected && !isBest);
  });
  if (correct) {
    toast('Seçimin modelin saha önceliğiyle aynı.');
  } else {
    toast('Model başka bir binayı daha önce incelenebilir görüyor.');
  }
  $('#missionRisk').textContent = pct(best.model_probability,0);
  $('#missionRing').style.setProperty('--risk-deg', `${Number(best.model_probability || 0) * 360}deg`);
  $('#missionTitle').textContent = `Model önerisi: ${best.incident_address}`;
  $('#missionText').textContent = `${best.why_risky} Öncelik sırası #${best.inspection_priority_rank}; risk ${pct(best.model_probability)}. Bu öneri otomatik karar değil, denetçiye sunulan öncelik sinyalidir.`;
  selectMapBuilding(best.building_id);
  markVisited('field');
}

function renderMonthChart(kind='complaints'){
  currentChartKind = kind;
  const key = kind === 'complaints' ? 'mean_complaints' : 'mean_positive_buildings';
  const max = Math.max(...data.monthlyProfile.map(row => Number(row[key] || 0)));
  $('#monthChart').innerHTML = data.monthlyProfile.map((row, index) => {
    const val = Number(row[key] || 0);
    const h = Math.max(8, val / max * 235);
    return `<button class="bar ${index === selectedMonthIndex ? 'active' : ''}" data-month="${index}" style="height:${h}px" aria-label="${escapeHtml(row.month_label)}"><span>${fmt(val,0)}</span><label>${escapeHtml(row.month_label.replace(' 202',''))}</label></button>`;
  }).join('');
  $$('#monthChart .bar').forEach(bar => bar.addEventListener('click', () => selectMonth(Number(bar.dataset.month))));
  $('#anovaCaption').textContent = kind === 'complaints'
    ? 'ANOVA sonucu: aylık ortalama şikayet yükü sabit değil. F=33.62, p<0.0001, η²≈0.50; yani fark sadece tesadüfi görünmüyor.'
    : 'Pozitif bina sayısı da aylar arasında anlamlı farklılaşıyor; en yoğun dönem kış penceresiyle çakışıyor.';
  selectMonth(Math.min(selectedMonthIndex, data.monthlyProfile.length - 1), false);
  markVisited('stats');
}
function selectMonth(index, shouldMark=true){
  selectedMonthIndex = Math.max(0, Math.min(index, data.monthlyProfile.length - 1));
  $$('#monthChart .bar').forEach(bar => bar.classList.toggle('active', Number(bar.dataset.month) === selectedMonthIndex));
  const row = data.monthlyProfile[selectedMonthIndex] || {};
  const key = currentChartKind === 'complaints' ? 'mean_complaints' : 'mean_positive_buildings';
  const label = currentChartKind === 'complaints' ? 'ortalama günlük şikayet' : 'ortalama pozitif bina';
  const values = data.monthlyProfile.map(r => Number(r[key] || 0));
  const grand = values.reduce((a,b) => a+b, 0) / Math.max(values.length, 1);
  const val = Number(row[key] || 0);
  const diff = val - grand;
  $('#monthTitle').textContent = `${row.month_label || 'Ay'} · ${label}`;
  $('#monthText').textContent = `${row.month_label || 'Seçilen ay'} değeri genel ortalamadan ${diff >= 0 ? 'yüksek' : 'düşük'}: ${fmt(Math.abs(diff),1)} fark. ANOVA bu aylık farkların toplamda istatistiksel olarak anlamlı olup olmadığını test eder.`;
  $('#monthStats').innerHTML = [
    ['Seçilen ay', fmt(val,1)],
    ['Genel ortalama', fmt(grand,1)],
    ['Toplam şikayet', fmt(row.total_complaints || 0,0)]
  ].map(([k,v]) => `<div class="stat-mini"><span>${k}</span><b>${v}</b></div>`).join('');
  if (shouldMark) markVisited('stats');
}
$$('[data-chart]').forEach(btn => btn.addEventListener('click', () => {
  $$('[data-chart]').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderMonthChart(btn.dataset.chart);
}));

function initExplorer(){
  const boroughs = ['Tümü', ...new Set(data.priorityRows.map(r => r.borough).filter(Boolean).sort())];
  $('#boroughFilter').innerHTML = boroughs.map(b => `<option value="${escapeHtml(b)}">${escapeHtml(b)}</option>`).join('');
  ['boroughFilter','searchBox','riskFilter','limitFilter'].forEach(id => document.getElementById(id).addEventListener('input', renderRiskCards));
  initRiskInsights();
  renderRiskCards();
}

function projectNyc(rowOrPoint){
  const lonMin = -74.27, lonMax = -73.68, latMin = 40.48, latMax = 40.92;
  const lon = Number(rowOrPoint.longitude);
  const lat = Number(rowOrPoint.latitude);
  const x = (lon - lonMin) / (lonMax - lonMin) * 760;
  const y = (latMax - lat) / (latMax - latMin) * 640;
  return {x, y};
}
function polygon(points){
  return points.map(([longitude, latitude]) => {
    const p = projectNyc({longitude, latitude});
    return `${p.x.toFixed(1)},${p.y.toFixed(1)}`;
  }).join(' ');
}
let activeMapLimit = 10;
let activeMapBorough = 'Tümü';
let activeMapBuildingId = null;
function initMap(){
  const boroughSelect = $('#mapBoroughFilter');
  if (boroughSelect) {
    const boroughs = ['Tümü', ...new Set(data.priorityRows.map(row => row.borough).filter(Boolean).sort())];
    boroughSelect.innerHTML = boroughs.map(b => `<option value="${escapeHtml(b)}">${escapeHtml(b)}</option>`).join('');
    boroughSelect.addEventListener('change', () => {
      activeMapBorough = boroughSelect.value;
      activeMapBuildingId = null;
      drawMap();
    });
  }
  $$('[data-map-limit]').forEach(btn => btn.addEventListener('click', () => {
    $$('[data-map-limit]').forEach(item => item.classList.remove('active'));
    btn.classList.add('active');
    activeMapLimit = Number(btn.dataset.mapLimit || 10);
    activeMapBuildingId = null;
    drawMap();
  }));
  drawMap();
}
function mapVisibleRows(){
  return data.priorityRows
    .filter(row => row.latitude && row.longitude)
    .filter(row => activeMapBorough === 'Tümü' || row.borough === activeMapBorough)
    .sort((a,b) => Number(a.inspection_priority_rank || 9999) - Number(b.inspection_priority_rank || 9999))
    .slice(0, activeMapLimit);
}
function drawMap(){
  const svg = $('#nycRiskMap');
  if (!svg) return;
  const shapes = [
    {name:'MANHATTAN', pts:[[-74.02,40.70],[-73.99,40.71],[-73.92,40.88],[-73.95,40.89]]},
    {name:'BRONX', pts:[[-73.94,40.78],[-73.76,40.80],[-73.75,40.91],[-73.93,40.91],[-73.96,40.84]]},
    {name:'QUEENS', pts:[[-73.96,40.55],[-73.70,40.55],[-73.70,40.79],[-73.84,40.80],[-73.96,40.70]]},
    {name:'BROOKLYN', pts:[[-74.05,40.56],[-73.85,40.56],[-73.84,40.72],[-74.03,40.73]]},
    {name:'STATEN', pts:[[-74.25,40.49],[-74.05,40.50],[-74.05,40.65],[-74.22,40.66]]}
  ];
  const subway = [
    [[-74.01,40.71],[-73.98,40.75],[-73.95,40.80],[-73.93,40.86]],
    [[-73.99,40.73],[-73.93,40.74],[-73.86,40.73],[-73.80,40.76]],
    [[-73.98,40.68],[-73.94,40.66],[-73.90,40.65],[-73.84,40.64]],
    [[-73.95,40.82],[-73.91,40.80],[-73.86,40.78],[-73.79,40.75]]
  ];
  const water = [
    [[-74.05,40.70],[-74.02,40.76],[-73.99,40.83],[-73.96,40.90]],
    [[-73.98,40.70],[-73.94,40.73],[-73.90,40.76],[-73.84,40.80]],
    [[-74.02,40.62],[-73.97,40.66],[-73.92,40.69],[-73.86,40.72]]
  ];
  const bridges = [
    [[-74.00,40.71],[-73.96,40.70]],
    [[-73.98,40.76],[-73.93,40.75]],
    [[-73.94,40.81],[-73.90,40.79]]
  ];
  const labels = [
    {name:'MANHATTAN', longitude:-73.97, latitude:40.78},
    {name:'BRONX', longitude:-73.86, latitude:40.86},
    {name:'QUEENS', longitude:-73.82, latitude:40.70},
    {name:'BROOKLYN', longitude:-73.94, latitude:40.63},
    {name:'STATEN', longitude:-74.14, latitude:40.57}
  ];
  const visibleRows = mapVisibleRows();
  const dots = visibleRows
    .map(row => {
      const p = projectNyc(row);
      const rank = Number(row.inspection_priority_rank || 999);
      const r = 4.5 + Number(row.model_probability || 0) * 4;
      const muted = rank > 10 ? ' muted' : '';
      const label = rank <= 10 ? `<text x="11" y="-9">#${rank}</text>` : '';
      return `<g class="risk-dot${muted}" data-map-id="${escapeHtml(row.building_id)}" transform="translate(${p.x.toFixed(1)} ${p.y.toFixed(1)})">
        <circle r="${(r*3.1).toFixed(1)}"></circle>
        <circle r="${r.toFixed(1)}"></circle>
        ${label}
      </g>`;
    }).join('');
  const guideLines = Array.from({length:7},(_,i)=>`<line class="map-line" x1="${i*118}" y1="0" x2="${i*118-190}" y2="640"></line>`).join('');
  svg.innerHTML = `
    <rect x="0" y="0" width="760" height="640" fill="transparent"></rect>
    ${guideLines}
    ${water.map(line => `<polyline class="waterline" points="${polygon(line)}"></polyline>`).join('')}
    ${shapes.map(s => `<polygon class="borough-shape" points="${polygon(s.pts)}"></polygon>`).join('')}
    ${bridges.map(line => `<polyline class="bridge-line" points="${polygon(line)}"></polyline>`).join('')}
    ${subway.map(line => `<polyline class="subway-line" points="${polygon(line)}" stroke="${line[0][0] < -74 ? '#d85f42' : '#d6a33d'}"></polyline>`).join('')}
    ${labels.map(label => { const p = projectNyc(label); return `<text class="borough-label" x="${p.x.toFixed(1)}" y="${p.y.toFixed(1)}">${label.name}</text>`; }).join('')}
    ${dots}
    <g id="activeMapLayer"></g>
    <rect class="map-badge" x="22" y="22" rx="17" ry="17" width="320" height="42"></rect>
    <text class="map-badge-text" x="42" y="49">${visibleRows.length} bina · ${escapeHtml(activeMapBorough)} · Top-${activeMapLimit}</text>
    <text class="map-legend" x="22" y="594">Nokta boyutu risk olasılığına göre artar · etiketler sadece en kritik binalarda gösterilir</text>
  `;
  $$('.risk-dot').forEach(dot => dot.addEventListener('click', () => selectMapBuilding(dot.dataset.mapId)));
  renderMapPriorityList(visibleRows);
  const selected = visibleRows.find(row => String(row.building_id) === String(activeMapBuildingId)) || visibleRows[0];
  if (selected) {
    selectMapBuilding(selected.building_id);
  } else {
    $('#mapTitle').textContent = 'Bu filtrede harita noktası yok';
    $('#mapMeta').textContent = 'Farklı ilçe veya daha geniş Top-N görünümü seç.';
    $('#mapRisk').textContent = '?';
    $('#mapRing').style.setProperty('--risk-deg', '0deg');
    $('#mapWhy').textContent = '';
    $('#mapStats').innerHTML = '';
    $('#mapPriorityList').innerHTML = '';
  }
}
function renderMapPriorityList(rows){
  const list = $('#mapPriorityList');
  if (!list) return;
  list.innerHTML = rows.slice(0, 10).map(row => `
    <button class="map-mini-row" data-map-list-id="${escapeHtml(row.building_id)}">
      <b><span>#${row.inspection_priority_rank} · ${escapeHtml(row.borough)}</span><span>${pct(row.model_probability,0)}</span></b>
      <span>${escapeHtml(row.incident_address || row.building_id)}</span>
    </button>
  `).join('');
  $$('[data-map-list-id]').forEach(btn => btn.addEventListener('click', () => selectMapBuilding(btn.dataset.mapListId)));
}
function selectMapBuilding(id){
  const row = data.priorityRows.find(item => String(item.building_id) === String(id));
  if (!row || !$('#mapTitle')) return;
  activeMapBuildingId = row.building_id;
  $$('.risk-dot').forEach(dot => dot.classList.toggle('active', String(dot.dataset.mapId) === String(id)));
  $$('[data-map-list-id]').forEach(btn => btn.classList.toggle('active', String(btn.dataset.mapListId) === String(id)));
  const layer = $('#activeMapLayer');
  if (layer && row.latitude && row.longitude) {
    const p = projectNyc(row);
    const labelX = p.x > 510 ? p.x - 240 : p.x + 38;
    const labelY = Math.max(86, Math.min(548, p.y - 46));
    layer.innerHTML = `
      <circle class="map-glow" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="44"></circle>
      <line class="selected-link" x1="${p.x.toFixed(1)}" y1="${p.y.toFixed(1)}" x2="${labelX.toFixed(1)}" y2="${labelY.toFixed(1)}"></line>
      <rect class="selected-callout" x="${labelX.toFixed(1)}" y="${(labelY-30).toFixed(1)}" rx="15" ry="15" width="214" height="60"></rect>
      <text class="selected-callout-text" x="${(labelX+16).toFixed(1)}" y="${(labelY-8).toFixed(1)}">#${row.inspection_priority_rank} · ${escapeHtml(row.borough)}</text>
      <text class="selected-callout-text" x="${(labelX+16).toFixed(1)}" y="${(labelY+14).toFixed(1)}">risk ${pct(row.model_probability,0)} · bina ${escapeHtml(row.building_id)}</text>
    `;
  }
  $('#mapTitle').textContent = `#${row.inspection_priority_rank} · ${row.incident_address}`;
  $('#mapMeta').textContent = `${row.borough} · bina ${row.building_id} · koordinat örnek sayısı ${fmt(row.coordinate_sample_count,0)}`;
  $('#mapRisk').textContent = pct(row.model_probability,0);
  $('#mapRing').style.setProperty('--risk-deg', `${Number(row.model_probability || 0) * 360}deg`);
  $('#mapWhy').textContent = row.why_risky || '';
  $('#mapStats').innerHTML = [
    ['Geçmiş şikayet', fmt(row.cumulative_complaints_prior,0)],
    ['Son 7 gün', fmt(row.rolling_7d_complaints,0)],
    ['Açık ihlal', fmt(row.open_linked_violation_count,0)],
    ['CRE kırılganlık', fmt(row.cre_vulnerability_index,3)],
    ['Enlem', fmt(row.latitude,4)],
    ['Boylam', fmt(row.longitude,4)]
  ].map(([k,v]) => `<div class="metric" style="color:white;background:#10211c"><span>${k}</span><b>${v}</b></div>`).join('');
  markVisited('map');
}
function initRiskInsights(){
  const risks = data.priorityRows.map(row => Number(row.model_probability || 0));
  const avg = risks.reduce((a,b) => a+b, 0) / Math.max(risks.length, 1);
  $('#avgTopRisk').textContent = pct(avg);
  $('#maxTopRisk').textContent = pct(Math.max(...risks));
  $('#boroughCount').textContent = new Set(data.priorityRows.map(row => row.borough).filter(Boolean)).size;
  const w = 220, h = 46;
  const max = Math.max(...risks, 1);
  const points = risks.slice(0, 35).map((value, index, arr) => {
    const x = arr.length === 1 ? 0 : index / (arr.length - 1) * w;
    const y = h - (value / max * (h - 8)) - 4;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  $('#riskSpark').setAttribute('viewBox', `0 0 ${w} ${h}`);
  $('#riskSpark').innerHTML = `<polyline points="${points}" fill="none" stroke="#d85f42" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/><line x1="0" y1="${h-4}" x2="${w}" y2="${h-4}" stroke="rgba(255,255,255,.25)" />`;
}
function filteredRows(){
  const borough = $('#boroughFilter').value;
  const q = $('#searchBox').value.toLowerCase().trim();
  const risk = Number($('#riskFilter').value)/100;
  const limit = Number($('#limitFilter').value);
  $('#riskLabel').textContent = `${$('#riskFilter').value}%`;
  return data.priorityRows.filter(row => {
    const hay = `${row.building_id} ${row.incident_address} ${row.borough}`.toLowerCase();
    return (borough === 'Tümü' || row.borough === borough) && (!q || hay.includes(q)) && Number(row.model_probability || 0) >= risk;
  }).slice(0, limit);
}
function renderRiskCards(){
  const rows = filteredRows();
  $('#riskCards').innerHTML = rows.length ? rows.map((row, i) => `
    <article class="card risk-card ${i===0?'active':''}" data-id="${escapeHtml(row.building_id)}">
      <div class="risk-top"><span class="rank">#${row.inspection_priority_rank}</span><span class="risk-score">${pct(row.model_probability)}</span></div>
      <h3>${escapeHtml(row.incident_address || 'Adres yok')}</h3>
      <p class="small">${escapeHtml(row.borough)} · bina ${escapeHtml(row.building_id)} · equity score ${fmt(row.equity_weighted_priority_score,3)}</p>
      <p class="small">${escapeHtml(row.why_risky)}</p>
    </article>`).join('') : '<article class="card"><h3>Kayıt yok</h3><p>Filtreyi gevşet.</p></article>';
  $$('.risk-card').forEach(card => card.addEventListener('click', () => selectRisk(card.dataset.id)));
  if (rows[0]) selectRisk(rows[0].building_id);
}
function selectRisk(id){
  const row = data.priorityRows.find(r => String(r.building_id) === String(id));
  if (!row) return;
  $$('.risk-card').forEach(card => card.classList.toggle('active', String(card.dataset.id) === String(id)));
  $('#detailTitle').textContent = `#${row.inspection_priority_rank} · ${row.incident_address}`;
  $('#detailMeta').textContent = `${row.borough} · bina ${row.building_id} · risk ${pct(row.model_probability)} · eşik ${pct(row.model_threshold,0)}`;
  $('#detailWhy').textContent = row.why_risky || '';
  selectMapBuilding(row.building_id);
  const positives = (row.top_positive_contributors_json || []).slice(0,5).map(x => ({...x, type:'pos'}));
  const negatives = (row.top_negative_contributors_json || []).slice(0,3).map(x => ({...x, type:'neg'}));
  const rows = [...positives, ...negatives];
  const max = Math.max(...rows.map(x => Math.abs(Number(x.contribution || 0))), 1);
  $('#contribChart').innerHTML = rows.map(x => {
    const w = Math.abs(Number(x.contribution || 0)) / max * 100;
    return `<div class="contrib-row"><span>${escapeHtml(x.label)}</span><div class="track"><div class="fill ${x.type==='neg'?'neg':''}" style="width:${w}%"></div></div><b>${Number(x.contribution || 0).toFixed(2)}</b></div>`;
  }).join('');
  markVisited('explorer');
}

function initCompare(){
  const options = data.priorityRows.map(row => `<option value="${escapeHtml(row.building_id)}">#${row.inspection_priority_rank} · ${escapeHtml(row.borough)} · ${escapeHtml(row.incident_address || row.building_id)}</option>`).join('');
  $('#compareA').innerHTML = options;
  $('#compareB').innerHTML = options;
  if (data.priorityRows[1]) $('#compareB').value = data.priorityRows[1].building_id;
  $('#compareA').addEventListener('change', renderCompare);
  $('#compareB').addEventListener('change', renderCompare);
  $('#swapCompare').addEventListener('click', () => {
    const a = $('#compareA').value;
    $('#compareA').value = $('#compareB').value;
    $('#compareB').value = a;
    renderCompare();
  });
  renderCompare();
}
function compareCard(row){
  if (!row) return '<div class="compare-card"><h3>Kayıt yok</h3></div>';
  const risk = Number(row.model_probability || 0);
  const fields = [
    ['Risk olasılığı', pct(risk)],
    ['Geçmiş şikayet', fmt(row.cumulative_complaints_prior,0)],
    ['Son 7 gün şikayet', fmt(row.rolling_7d_complaints,0)],
    ['Açık ihlal', fmt(row.open_linked_violation_count,0)],
    ['CRE kırılganlık', fmt(row.cre_vulnerability_index,3)]
  ];
  return `<article class="compare-card">
    <h3>#${row.inspection_priority_rank} · ${escapeHtml(row.incident_address || 'Adres yok')}</h3>
    <p class="small">${escapeHtml(row.borough)} · bina ${escapeHtml(row.building_id)}</p>
    <div class="compare-meter"><div style="width:${Math.max(2, risk*100)}%"></div></div>
    ${fields.map(([k,v]) => `<p class="small"><b>${k}:</b> ${v}</p>`).join('')}
    <p class="small" style="margin-top:10px"><b>Neden?</b> ${escapeHtml(row.why_risky || '')}</p>
  </article>`;
}
function renderCompare(){
  const a = data.priorityRows.find(row => String(row.building_id) === String($('#compareA').value));
  const b = data.priorityRows.find(row => String(row.building_id) === String($('#compareB').value));
  $('#compareGrid').innerHTML = compareCard(a) + compareCard(b);
  markVisited('compare');
}

function initPolicy(){
  $('#capacitySlider').addEventListener('input', renderPolicy);
  renderPolicy();
}
function renderPolicy(){
  const k = Number($('#capacitySlider').value);
  $('#capacityLabel').textContent = k;
  const rows = data.policyRows.filter(r => Number(r.capacity) === k);
  const order = ['model_probability','equity_weighted','history_baseline','random_expectation'];
  const labels = {model_probability:'Model skoru', equity_weighted:'Equity ağırlıklı', history_baseline:'Geçmiş bazlı', random_expectation:'Rastgele'};
  const max = Math.max(...rows.map(r => Number(r.mean_hits || 0)), 1);
  $('#policyBars').innerHTML = order.map(policy => {
    const row = rows.find(r => r.policy === policy) || {mean_hits:0, mean_precision:0, mean_lift:0};
    const w = Number(row.mean_hits || 0)/max*100;
    return `<div class="policy-row"><b>${labels[policy]}</b><div class="policy-track"><div class="policy-fill" style="width:${w}%"></div></div><span>${fmt(row.mean_hits,1)}</span></div>`;
  }).join('');
  const model = rows.find(r => r.policy === 'model_probability');
  $('#policyCaption').textContent = model ? `K=${k} için model ortalama ${fmt(model.mean_hits,1)} isabet, precision ${pct(model.mean_precision)}, lift ${fmt(model.mean_lift,1)}x üretir.` : '';
  markVisited('policy');
}

function initTech(){
  const nodes = [
    {id:'python', x:104, y:92, title:'Python', sub:'ETL + model'},
    {id:'sql', x:104, y:248, title:'SQL', sub:'lookup'},
    {id:'r', x:104, y:404, title:'R', sub:'istatistik'},
    {id:'fastapi', x:336, y:170, title:'FastAPI', sub:'servis'},
    {id:'docker', x:336, y:326, title:'Docker', sub:'imaj'},
    {id:'aws', x:574, y:140, title:'AWS', sub:'bulut'},
    {id:'eks', x:574, y:300, title:'EKS', sub:'orkestrasyon'},
    {id:'site', x:574, y:444, title:'Site', sub:'sınıf paylaşımı'}
  ];
  const links = [
    ['python','fastapi'], ['sql','fastapi'], ['r','python'], ['fastapi','docker'],
    ['docker','aws'], ['aws','eks'], ['fastapi','site'], ['eks','site']
  ];
  const byId = Object.fromEntries(nodes.map(n => [n.id, n]));
  $('#techMap').innerHTML = `
    <defs>
      <marker id="arrow" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto" markerUnits="strokeWidth">
        <path d="M0,0 L0,6 L8,3 z" fill="rgba(255,248,235,.48)"></path>
      </marker>
    </defs>
    ${links.map(([a,b]) => {
      const s = byId[a], t = byId[b];
      return `<path class="tech-flow" d="M${s.x+62} ${s.y} C${s.x+130} ${s.y}, ${t.x-130} ${t.y}, ${t.x-62} ${t.y}" marker-end="url(#arrow)"></path>`;
    }).join('')}
    <circle class="tech-packet" r="7">
      <animateMotion dur="7s" repeatCount="indefinite" path="M166 92 C234 92, 206 170, 274 170 C404 170, 444 140, 512 140 C640 140, 520 444, 574 444"></animateMotion>
    </circle>
    ${nodes.map(n => `
      <g class="tech-node-group" data-tech-node="${n.id}">
        <rect class="tech-node" x="${n.x-72}" y="${n.y-42}" rx="22" ry="22" width="144" height="84"></rect>
        <text class="tech-node-label" x="${n.x}" y="${n.y-6}">${n.title}</text>
        <text class="tech-node-sub" x="${n.x}" y="${n.y+18}">${n.sub}</text>
      </g>`).join('')}
    <text class="map-legend" x="32" y="502">Veri → model → API → container → bulut → sınıf paylaşımı</text>
  `;
  $('#techCards').innerHTML = techStack.map((tool, index) => `
    <button class="tech-card ${index===0?'active':''}" data-tech="${tool.id}">
      <b>${escapeHtml(tool.name)}</b>
      <span>${escapeHtml(tool.role)}</span>
    </button>`).join('');
  $$('.tech-card').forEach(card => card.addEventListener('click', () => selectTech(card.dataset.tech)));
  $$('.tech-node-group').forEach(node => node.addEventListener('click', () => selectTech(node.dataset.techNode)));
  selectTech(techStack[0].id);
}

function selectTech(id){
  const tool = techStack.find(item => item.id === id) || techStack[0];
  $$('.tech-card').forEach(card => card.classList.toggle('active', card.dataset.tech === tool.id));
  $$('.tech-node-group .tech-node').forEach(node => node.classList.remove('active'));
  const activeNode = document.querySelector(`[data-tech-node="${tool.id}"] .tech-node`);
  if (activeNode) activeNode.classList.add('active');
  $('#techTitle').textContent = tool.name;
  $('#techRole').textContent = tool.role;
  $('#techBullets').innerHTML = [
    ['Ne işe yarar?', tool.why],
    ['Bu projede nasıl kullandık?', tool.used],
    ['Çalıştığını nasıl kanıtlıyoruz?', tool.proof]
  ].map(([title, text]) => `<div class="tech-bullet"><b>${title}</b><p>${escapeHtml(text)}</p></div>`).join('');
  markVisited('stack');
}

function initEvidence(){
  const items = [
    {
      id:'health',
      title:'API sağlık kontrolü',
      badge:'Çalışan servis',
      humanTitle:'API ayakta ve artefaktları okuyabiliyor',
      humanText:'Bu çıktı yerel FastAPI servisinin çalıştığını, model ve öncelik dosyalarına erişebildiğini gösterir.',
      bullets:['/health endpoint status=ok döner.', 'Model tipi ve artefakt kaynağı kontrol edilir.', 'Dashboard/API sunum sırasında aynı servis üzerinden açılır.'],
      payload:data.evidence.health
    },
    {
      id:'priorities',
      title:'Top-5 öncelik JSON',
      badge:'Gerçek çıktı',
      humanTitle:'Modelin ürettiği öncelik listesi görülebiliyor',
      humanText:'Bu kanıt, sistemin sadece model eğitmediğini; sonuçta denetim için sıralı bina listesi ürettiğini gösterir.',
      bullets:['Her satır bina, tarih, risk ve öncelik sırası taşır.', 'Top-50 mantığının küçük örneği Top-5 olarak gösterilir.', 'Sınıfta “hangi binaya önce gidilmeli?” sorusunun cevabıdır.'],
      payload:data.evidence.priorities
    },
    {
      id:'score',
      title:'Score endpoint örneği',
      badge:'Tahmin servisi',
      humanTitle:'Yeni bir bina-gün kaydı risk skoruna çevriliyor',
      humanText:'Bu örnek, API’ye özellikler verildiğinde modelin olasılık, tahmin ve “neden riskli?” açıklaması döndürdüğünü gösterir.',
      bullets:['Girdi: bina-gün özellikleri.', 'Çıktı: olasılık, sınıf tahmini ve açıklayıcı sinyaller.', 'Bu katman modeli notebook dışına çıkarır.'],
      payload:data.evidence.score
    },
    {
      id:'aws',
      title:'AWS canlı deploy kanıtı',
      badge:'Bulut kanıtı',
      humanTitle:'Proje AWS üzerinde kısa süreli canlı çalıştırıldı',
      humanText:'Bu rapor, API’nin AWS ortamında dış URL üzerinden cevap verdiğini ve artefaktları S3 kaynağından okuyabildiğini belgelemek için tutulur.',
      bullets:['Canlı endpoint cevap verdi.', 'Artifact source tipi S3 olarak kaydedildi.', 'Maliyet için sürekli açık bırakılmadı.'],
      payload:data.evidence.aws
    },
    {
      id:'shutdown',
      title:'AWS kapatma kanıtı',
      badge:'Maliyet güvenliği',
      humanTitle:'Ücretli AWS kaynaklarının kapatıldığı kontrol edildi',
      humanText:'Bu çıktı, canlı denemeden sonra EKS/Load Balancer/EC2 gibi maliyet doğurabilecek kaynakların kapalı olduğunu gösterir.',
      bullets:['Sunum dışı zamanda AWS açık tutulmaz.', 'Boş maliyet yazmamak için kapatma raporu tutulur.', 'Bu, projenin dürüst sınırlılık kısmını güçlendirir.'],
      payload:data.evidence.shutdown
    },
    {
      id:'limits',
      title:'Dürüst sınırlar',
      badge:'Sınır',
      humanTitle:'Sistem otomatik karar vermez, karar desteği üretir',
      humanText:'Bu bölüm projenin yanlış anlaşılmasını önler: çıktı otomatik ceza veya kesin nedensellik iddiası değildir.',
      bullets:['Risk sıralaması üretir, otomatik denetim kararı vermez.', 'Nedensellik değil operasyonel öncelik hedeflenir.', 'Equity ağırlığı politika incelemesi gerektirir.'],
      payload:data.limits
    }
  ];
  $('#evidenceList').innerHTML = items.map((item,i)=>`<button class="evidence-item ${i===0?'active':''}" data-evidence="${item.id}"><b>${item.title}</b><br><span>İncele</span></button>`).join('');
  function select(id){
    $$('.evidence-item').forEach(x => x.classList.toggle('active', x.dataset.evidence === id));
    const item = items.find(x => x.id === id) || items[0];
    $('#evidenceBadge').textContent = item.badge;
    $('#evidenceHumanTitle').textContent = item.humanTitle;
    $('#evidenceHumanText').textContent = item.humanText;
    $('#evidenceHumanBullets').innerHTML = item.bullets.map(text => `<div class="evidence-bullet"><b>Kanıt:</b> ${escapeHtml(text)}</div>`).join('');
    $('#evidenceOutput').textContent = JSON.stringify(item.payload, null, 2);
    markVisited('evidence');
  }
  $$('.evidence-item').forEach(btn => btn.addEventListener('click', () => select(btn.dataset.evidence)));
  select('health');
}

initHero(); initActors(); initTour(); initMap(); initMission(); initDataCards(); initMethods(); renderMonthChart(); initExplorer(); initCompare(); initPolicy(); initTech(); initEvidence();
initializing = false;
markVisited('story');
updateProgress();
</script>
</body>
</html>
"""


def build() -> None:
    app_data = json.dumps(build_app_data(), ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__APP_DATA__", app_data)
    for path in (DOCS_OUT, PROJECT_OUT, DOWNLOADS_OUT):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")

    # Keep a copy next to the project for quick local previews.
    preview_dir = PROJECT / "reports/shareable_site"
    preview_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_OUT, preview_dir / "index.html")
    print(DOCS_OUT)
    print(PROJECT_OUT)
    print(DOWNLOADS_OUT)


if __name__ == "__main__":
    build()
