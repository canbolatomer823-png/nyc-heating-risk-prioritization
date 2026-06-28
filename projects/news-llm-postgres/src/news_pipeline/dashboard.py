from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_dashboard(
    payloads_path: str | Path,
    patterns_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    payloads = read_jsonl(payloads_path)
    patterns = read_json(patterns_path)
    html = render_dashboard_html(payloads, patterns)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")
    return {
        "status": "ok",
        "output_path": str(destination),
        "payloads": len(payloads),
        "clusters": len(patterns.get("clusters", [])),
    }


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Payload file not found: {source}")
    rows = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def read_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Pattern file not found: {source}")
    return json.loads(source.read_text(encoding="utf-8"))


def render_dashboard_html(payloads: list[dict[str, Any]], patterns: dict[str, Any]) -> str:
    data = {
        "payloads": payloads,
        "patterns": patterns,
    }
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return DASHBOARD_TEMPLATE.replace("__DASHBOARD_DATA__", data_json)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a standalone dashboard from news payloads and pattern output.")
    parser.add_argument("--payloads", default="outputs/latest_payloads.jsonl", help="Input JSONL payload path.")
    parser.add_argument("--patterns", default="outputs/latest_patterns.json", help="Input pattern JSON path.")
    parser.add_argument("--output", default="outputs/dashboard.html", help="Output dashboard HTML path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_dashboard(args.payloads, args.patterns, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


DASHBOARD_TEMPLATE = r"""<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>News Pattern Dashboard</title>
  <style>
    :root {
      --bg: #f5f7fb;
      --surface: #ffffff;
      --line: #d9e2ec;
      --text: #17202a;
      --muted: #667085;
      --teal: #0f766e;
      --blue: #2563eb;
      --amber: #b7791f;
      --red: #b42318;
      --green: #15803d;
      --shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px;
      letter-spacing: 0;
    }

    a {
      color: var(--blue);
      text-decoration: none;
    }

    .shell {
      min-height: 100vh;
    }

    .topbar {
      position: sticky;
      top: 0;
      z-index: 10;
      background: rgba(245, 247, 251, 0.96);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(10px);
    }

    .topbar-inner {
      max-width: 1240px;
      margin: 0 auto;
      padding: 16px 24px 14px;
      display: grid;
      gap: 14px;
    }

    .title-row {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
    }

    h1 {
      margin: 0;
      font-size: 24px;
      line-height: 1.15;
      font-weight: 750;
    }

    .subtitle {
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
    }

    .run-meta {
      color: var(--muted);
      font-size: 13px;
      text-align: right;
      min-width: 220px;
    }

    .tabs {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding-bottom: 2px;
    }

    .tab {
      border: 1px solid var(--line);
      background: var(--surface);
      color: var(--text);
      border-radius: 8px;
      padding: 8px 12px;
      cursor: pointer;
      font: inherit;
      white-space: nowrap;
    }

    .tab.active {
      border-color: var(--teal);
      background: #e7f5f1;
      color: #0b5f59;
    }

    main {
      max-width: 1240px;
      margin: 0 auto;
      padding: 22px 24px 40px;
    }

    .view {
      display: none;
    }

    .view.active {
      display: block;
    }

    .grid {
      display: grid;
      gap: 16px;
    }

    .grid.two {
      grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
    }

    .grid.three {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .insight-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .insight-card {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 14px;
      min-height: 150px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .insight-card.high {
      border-top: 4px solid var(--red);
    }

    .insight-card.medium {
      border-top: 4px solid var(--amber);
    }

    .insight-card.low {
      border-top: 4px solid var(--teal);
    }

    .insight-title {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
    }

    .insight-metric {
      font-size: 28px;
      font-weight: 780;
      line-height: 1;
    }

    .insight-label {
      color: var(--text);
      font-weight: 650;
    }

    .insight-detail {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
    }

    .kpis {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .panel,
    .kpi,
    .cluster-card,
    .article-row {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }

    .kpi {
      padding: 14px;
      min-height: 92px;
    }

    .kpi-label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
    }

    .kpi-value {
      margin-top: 8px;
      font-size: 30px;
      font-weight: 760;
      line-height: 1;
    }

    .kpi-note {
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
    }

    .decision-panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 18px;
      margin-bottom: 16px;
    }

    .decision-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
    }

    .decision-title {
      margin: 0;
      font-size: 22px;
      line-height: 1.2;
      font-weight: 780;
    }

    .decision-detail {
      margin-top: 8px;
      color: var(--muted);
      line-height: 1.45;
    }

    .decision-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 34px;
      border-radius: 999px;
      padding: 6px 12px;
      background: #e7f5f1;
      color: #0b5f59;
      font-weight: 760;
      white-space: nowrap;
    }

    .decision-badge.high {
      background: #ffe8e5;
      color: var(--red);
    }

    .decision-badge.medium {
      background: #fff4df;
      color: #8a4b00;
    }

    .decision-badge.low {
      background: #e7f7ed;
      color: var(--green);
    }

    .decision-path {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 16px;
    }

    .path-step {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfdff;
    }

    .path-index {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }

    .path-text {
      margin-top: 4px;
      line-height: 1.35;
      font-weight: 650;
    }

    .outlier-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .outlier-card {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 14px;
      min-height: 128px;
    }

    .outlier-card h3 {
      margin: 0 0 8px;
      font-size: 14px;
    }

    .outlier-value {
      font-size: 24px;
      font-weight: 780;
      line-height: 1.1;
    }

    .outlier-note {
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
    }

    .analysis-note {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      margin: -6px 0 12px;
    }

    .panel {
      padding: 16px;
      min-width: 0;
    }

    .panel h2 {
      margin: 0 0 14px;
      font-size: 16px;
      line-height: 1.3;
    }

    .bar-row {
      display: grid;
      grid-template-columns: 120px minmax(0, 1fr) 40px;
      gap: 10px;
      align-items: center;
      margin: 10px 0;
    }

    .bar-label {
      color: var(--text);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .bar-track {
      height: 10px;
      background: #edf2f7;
      border-radius: 999px;
      overflow: hidden;
    }

    .bar-fill {
      height: 100%;
      background: var(--teal);
      border-radius: inherit;
    }

    .count {
      color: var(--muted);
      text-align: right;
      font-variant-numeric: tabular-nums;
    }

    .impact-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);
      gap: 16px;
      margin-bottom: 16px;
    }

    .indicator-row {
      display: grid;
      grid-template-columns: 150px minmax(0, 1fr) 56px;
      gap: 10px;
      align-items: center;
      margin: 12px 0;
    }

    .indicator-label {
      font-weight: 650;
    }

    .impact-scale {
      position: relative;
      height: 12px;
      border-radius: 999px;
      background: linear-gradient(90deg, #b42318 0%, #f2d3ce 46%, #eef2f6 50%, #cdeedc 54%, #15803d 100%);
      overflow: hidden;
    }

    .impact-scale::after {
      content: "";
      position: absolute;
      left: 50%;
      top: 0;
      width: 2px;
      height: 100%;
      background: rgba(23, 32, 42, 0.45);
    }

    .impact-dot {
      position: absolute;
      top: 50%;
      width: 14px;
      height: 14px;
      border-radius: 999px;
      background: var(--text);
      border: 2px solid #fff;
      transform: translate(-50%, -50%);
      box-shadow: 0 4px 10px rgba(15, 23, 42, 0.22);
    }

    .impact-score {
      font-variant-numeric: tabular-nums;
      font-weight: 750;
      text-align: right;
    }

    .impact-score.positive {
      color: var(--green);
    }

    .impact-score.negative {
      color: var(--red);
    }

    .impact-article {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 10px;
      background: #fbfdff;
    }

    .impact-scores {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
    }

    .score-pill {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 12px;
      font-weight: 700;
      background: #eef2f6;
      color: var(--text);
    }

    .score-pill.positive {
      background: #e7f7ed;
      color: var(--green);
    }

    .score-pill.negative {
      background: #ffe8e5;
      color: var(--red);
    }

    .trend-bars {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 10px;
      align-items: end;
      min-height: 220px;
    }

    .trend-col {
      display: grid;
      gap: 8px;
      align-items: end;
      min-height: 200px;
    }

    .trend-bar {
      align-self: end;
      min-height: 10px;
      border-radius: 8px 8px 4px 4px;
      background: var(--blue);
      color: #fff;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding-top: 6px;
      font-size: 12px;
      font-weight: 700;
    }

    .trend-label {
      color: var(--muted);
      font-size: 12px;
      text-align: center;
      min-height: 32px;
    }

    .break-list {
      display: grid;
      gap: 10px;
    }

    .break-item {
      border-left: 3px solid var(--blue);
      border-radius: 6px;
      background: #f7fbff;
      padding: 10px 12px;
    }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 4px 8px;
      border-radius: 999px;
      background: #eef6ff;
      color: #174ea6;
      font-size: 12px;
      max-width: 100%;
    }

    .chip.warn {
      background: #fff4df;
      color: #8a4b00;
    }

    .chip.red {
      background: #ffe8e5;
      color: var(--red);
    }

    .cluster-list {
      display: grid;
      gap: 12px;
      min-width: 0;
    }

    .cluster-card {
      padding: 14px;
      min-width: 0;
      overflow: hidden;
    }

    .cluster-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      margin-bottom: 10px;
      min-width: 0;
    }

    .cluster-title {
      font-weight: 700;
      line-height: 1.35;
      min-width: 0;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .cluster-size {
      flex: 0 0 auto;
      border-radius: 8px;
      background: #e7f5f1;
      color: #0b5f59;
      padding: 5px 8px;
      font-size: 12px;
      font-weight: 700;
    }

    .score-line {
      display: grid;
      grid-template-columns: 92px minmax(0, 1fr) 48px;
      gap: 8px;
      align-items: center;
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
    }

    .link-list {
      margin: 10px 0 0;
      padding-left: 18px;
      color: var(--muted);
    }

    .link-list li {
      margin: 4px 0;
      overflow-wrap: anywhere;
    }

    .link-list a {
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .article-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 118px 110px;
      gap: 12px;
      align-items: center;
      padding: 12px 14px;
      margin-bottom: 8px;
      box-shadow: none;
    }

    .article-title {
      font-weight: 650;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .article-meta {
      color: var(--muted);
      font-size: 12px;
    }

    .filters {
      display: grid;
      grid-template-columns: minmax(160px, 1fr) repeat(2, minmax(110px, 0.6fr));
      gap: 10px;
      margin-bottom: 12px;
    }

    .filters input,
    .filters select {
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px 10px;
      font: inherit;
      background: var(--surface);
      min-width: 0;
    }

    .article-table {
      display: grid;
      gap: 8px;
    }

    .article-table .article-row {
      grid-template-columns: minmax(0, 1fr) 120px 140px 110px;
    }

    .source-health {
      display: grid;
      gap: 8px;
    }

    .health-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 86px 58px;
      gap: 10px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfdff;
    }

    .status-dot {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 24px;
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 12px;
      font-weight: 700;
      background: #eef6ff;
      color: #174ea6;
    }

    .status-dot.ok {
      background: #e7f7ed;
      color: var(--green);
    }

    .status-dot.partial,
    .status-dot.empty {
      background: #fff4df;
      color: #8a4b00;
    }

    .status-dot.blocked {
      background: #ffe8e5;
      color: var(--red);
    }

    .empty {
      padding: 24px;
      border: 1px dashed var(--line);
      border-radius: 8px;
      color: var(--muted);
      background: #fafcff;
    }

    .search {
      width: 100%;
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px 10px;
      margin-bottom: 12px;
      font: inherit;
      background: var(--surface);
    }

    .error-list {
      display: grid;
      gap: 8px;
    }

    .error-item {
      border-left: 3px solid var(--red);
      background: #fff7f6;
      padding: 10px 12px;
      border-radius: 6px;
      color: #7a271a;
      overflow-wrap: anywhere;
    }

    @media (max-width: 900px) {
      .title-row,
      .decision-head,
      .decision-path,
      .grid.two,
      .grid.three,
      .insight-grid,
      .outlier-grid,
      .impact-grid,
      .kpis,
      .indicator-row,
      .article-row,
      .filters,
      .article-table .article-row,
      .health-row {
        grid-template-columns: 1fr;
      }

      .title-row {
        align-items: flex-start;
      }

      .run-meta {
        text-align: left;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div class="topbar-inner">
        <div class="title-row">
          <div>
            <h1>News Pattern Dashboard</h1>
            <div class="subtitle">Karar özeti, outlier gündemler ve drilldown analizi</div>
          </div>
          <div class="run-meta" id="runMeta"></div>
        </div>
        <nav class="tabs" aria-label="Dashboard views">
          <button class="tab active" data-view="overview">Karar</button>
          <button class="tab" data-view="intelligence">Outlier</button>
          <button class="tab" data-view="impact">Etki</button>
          <button class="tab" data-view="clusters">Drilldown</button>
          <button class="tab" data-view="sources">Kaynaklar</button>
        </nav>
      </div>
    </header>

    <main>
      <section class="view active" id="overview">
        <div id="decisionPanel"></div>
        <div class="kpis" id="kpis"></div>
        <div class="outlier-grid" id="overviewOutliers"></div>
        <div class="grid two">
          <div class="panel">
            <h2>Drilldown Sırası</h2>
            <div id="decisionPath"></div>
          </div>
          <div class="panel">
            <h2>Karar Notları</h2>
            <div id="observations"></div>
          </div>
        </div>
      </section>

      <section class="view" id="intelligence">
        <div class="outlier-grid" id="outlierCards"></div>
        <div class="grid two">
          <div class="panel">
            <h2>Outlier Clusterlar</h2>
            <p class="analysis-note">Tekil haberler burada ana karar noktası değil; aynı olayın birden fazla kaynakta ve güçlü sinyalle görünmesi öne çıkarılır.</p>
            <div class="cluster-list" id="priorityClusters"></div>
          </div>
          <div class="panel">
            <h2>Trend Kırılımları</h2>
            <div id="outlierTrends"></div>
            <div style="height:14px"></div>
            <h2>Gösterge Outlierları</h2>
            <div id="outlierIndicators"></div>
          </div>
        </div>
        <div class="panel" style="margin-top:16px">
          <h2>Kanıt Haberleri</h2>
          <p class="analysis-note">Bu bölüm, outlier kararını açıklamak için tutulur; tekil haber tek başına karar verdirmez.</p>
          <div id="articleEvidence"></div>
        </div>
      </section>

      <section class="view" id="impact">
        <div class="kpis" id="impactKpis"></div>
        <div class="impact-grid">
          <div class="panel">
            <h2>Makro Gösterge Etkisi</h2>
            <div id="indicatorImpact"></div>
          </div>
          <div class="panel">
            <h2>Google Trends Benzeri Trend</h2>
            <div id="macroTrend"></div>
          </div>
        </div>
        <div class="grid two">
          <div class="panel">
            <h2>En Etkili Ekonomi / Siyaset Haberleri</h2>
            <div id="topImpactArticles"></div>
          </div>
          <div class="panel">
            <h2>Kırılım Analizi ve Hesap Dışı Haberler</h2>
            <div id="majorBreaks"></div>
            <div style="height:14px"></div>
            <div id="excludedImpactArticles"></div>
          </div>
        </div>
      </section>

      <section class="view" id="clusters">
        <input class="search" id="clusterSearch" placeholder="Cluster, kaynak veya ortak terim ara">
        <div class="grid two">
          <div class="panel">
            <h2>Cluster Drilldown</h2>
            <div class="cluster-list" id="clusterList"></div>
          </div>
          <div class="panel">
            <h2>Olay ve Risk Dağılımı</h2>
            <div id="eventBars"></div>
            <div style="height:14px"></div>
            <div id="riskBars"></div>
          </div>
        </div>
        <div class="grid two" style="margin-top:16px">
          <div class="panel">
            <h2>Kategori ve Lokasyon</h2>
            <div id="categoryBars"></div>
            <div style="height:14px"></div>
            <div id="geoBars"></div>
          </div>
          <div class="panel">
            <h2>Haber Kanıtı</h2>
            <div class="filters">
              <input id="articleSearch" placeholder="Başlık, kaynak, kategori veya topic ara">
              <select id="categoryFilter"></select>
              <select id="sourceFilter"></select>
            </div>
            <div class="article-table" id="articleTable"></div>
          </div>
        </div>
      </section>

      <section class="view" id="sources">
        <div class="grid three">
          <div class="panel">
            <h2>Kaynak Dağılımı</h2>
            <div id="sourceBars"></div>
          </div>
          <div class="panel">
            <h2>Kaynak Sağlığı</h2>
            <div id="sourceHealthSources"></div>
          </div>
          <div class="panel">
            <h2>Kaynak Hataları</h2>
            <div id="sourceErrors"></div>
          </div>
        </div>
      </section>
    </main>
  </div>

  <script>
    const DASHBOARD_DATA = __DASHBOARD_DATA__;
    const payloads = DASHBOARD_DATA.payloads || [];
    const patterns = DASHBOARD_DATA.patterns || {};
    const pipeline = patterns.pipeline || {};
    const clusterRankingById = Object.fromEntries((patterns.cluster_rankings || []).map(row => [row.cluster_id, row]));
    const macroImpact = patterns.macro_impact || {};
    const outlierReport = patterns.outlier_report || {};
    const decisionSummary = patterns.decision_summary || {};

    function byId(id) {
      return document.getElementById(id);
    }

    function esc(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function records(name) {
      return Array.isArray(patterns[name]) ? patterns[name] : [];
    }

    function unique(values) {
      return [...new Set(values.filter(Boolean))];
    }

    function countRecordsFromPayloads(pathFn) {
      const counts = {};
      payloads.forEach(payload => {
        const values = pathFn(payload);
        (Array.isArray(values) ? values : [values]).filter(Boolean).forEach(value => {
          counts[value] = (counts[value] || 0) + 1;
        });
      });
      return Object.entries(counts)
        .map(([value, count]) => ({ value, count }))
        .sort((left, right) => right.count - left.count || left.value.localeCompare(right.value));
    }

    function optionList(rows, label) {
      return `<option value="">${esc(label)}</option>` + rows.map(row => `<option value="${esc(row.value || row.key)}">${esc(row.value || row.key)}</option>`).join("");
    }

    function metricCard(label, value, note) {
      return `<div class="kpi"><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${esc(value)}</div><div class="kpi-note">${esc(note || "")}</div></div>`;
    }

    function insightCard(card) {
      return `<article class="insight-card ${esc(card.severity || "low")}">
        <div class="insight-title">${esc(card.title)}</div>
        <div class="insight-metric">${esc(card.metric)}</div>
        <div class="insight-label">${esc(card.label || "")}</div>
        <div class="insight-detail">${esc(card.detail || "")}</div>
      </article>`;
    }

    function decisionPanel() {
      const metrics = decisionSummary.metrics || {};
      return `<section class="decision-panel">
        <div class="decision-head">
          <div>
            <h2 class="decision-title">${esc(decisionSummary.headline || "Karar özeti yok")}</h2>
            <div class="decision-detail">${esc(decisionSummary.why || "Outlier üretmek için daha fazla veri gerekiyor.")}</div>
          </div>
          <span class="decision-badge ${esc(decisionSummary.priority || "medium")}">${esc(decisionSummary.decision_label || "İzle")}</span>
        </div>
        <div class="decision-detail"><strong>Odak:</strong> ${esc(decisionSummary.focus || "Belirgin odak yok")}</div>
        <div class="article-meta" style="margin-top:12px">${esc(metrics.active_sources || 0)} aktif kaynak · ${esc(metrics.blocked_sources || 0)} problemli kaynak · ${esc(metrics.outlier_count || 0)} outlier sinyali</div>
      </section>`;
    }

    function outlierSummaryCard(title, value, note) {
      return `<article class="outlier-card">
        <h3>${esc(title)}</h3>
        <div class="outlier-value">${esc(value)}</div>
        <div class="outlier-note">${esc(note || "")}</div>
      </article>`;
    }

    function renderOutlierCards(targetId) {
      const indicator = (outlierReport.indicator_outliers || [])[0];
      const cluster = (outlierReport.cluster_outliers || [])[0];
      const trend = (outlierReport.trend_outliers || [])[0];
      byId(targetId).innerHTML = [
        outlierSummaryCard(
          "Gösterge",
          indicator ? `${indicator.label} ${Number(indicator.average_score || 0) > 0 ? "+" : ""}${indicator.average_score}` : "-",
          indicator ? indicator.why : "Belirgin gösterge outlierı yok"
        ),
        outlierSummaryCard(
          "Cluster",
          cluster ? `${cluster.cluster_size} haber` : "-",
          cluster ? cluster.why : "Çok kaynaklı yüksek etki clusterı yok"
        ),
        outlierSummaryCard(
          "Trend",
          trend ? `${trend.key} ${Number(trend.change || 0) >= 0 ? "+" : ""}${trend.change}` : "-",
          trend ? trend.why : "Belirgin trend kırılımı yok"
        ),
      ].join("");
    }

    function scoreClass(score) {
      const numeric = Number(score || 0);
      if (numeric > 0) {
        return "positive";
      }
      if (numeric < 0) {
        return "negative";
      }
      return "";
    }

    function signedScore(score) {
      const numeric = Number(score || 0);
      return `${numeric > 0 ? "+" : ""}${numeric}`;
    }

    function scorePill(score) {
      return `<span class="score-pill ${scoreClass(score.score)}">${esc(score.label)} ${esc(signedScore(score.score))}</span>`;
    }

    function indicatorScale(row) {
      const score = Number(row.average_score || 0);
      const left = Math.max(0, Math.min(100, (score + 5) * 10));
      return `<div class="indicator-row">
        <div>
          <div class="indicator-label">${esc(row.label)}</div>
          <div class="article-meta">${esc(row.interpretation || "")}</div>
        </div>
        <div class="impact-scale" title="-5 / +5">
          <span class="impact-dot" style="left:${left}%"></span>
        </div>
        <div class="impact-score ${scoreClass(score)}">${esc(score > 0 ? "+" + score.toFixed(2) : score.toFixed(2))}</div>
      </div>`;
    }

    function impactArticleCard(article) {
      const scores = article.indicator_scores || [];
      const scoreHtml = scores.map(scorePill).join("");
      const dominant = article.dominant_indicator
        ? `${article.dominant_indicator.label} ${signedScore(article.dominant_indicator.score)}`
        : "belirgin yön yok";
      return `<article class="impact-article">
        <div class="article-title" title="${esc(article.title)}">${esc(article.title)}</div>
        <div class="article-meta">${esc(article.source)} · ${esc(article.category)} · net ${esc(article.net_abs_impact)} · ${esc(dominant)}</div>
        <div class="impact-scores">${scoreHtml}</div>
        <div class="insight-detail" style="margin-top:8px">${esc(article.summary || "")}</div>
      </article>`;
    }

    function renderTrendBars() {
      const trend = macroImpact.trend_report || {};
      const topTrends = trend.top_trends || [];
      if (!topTrends.length) {
        return `<div class="empty">Trend için yeterli makro haber yok</div>`;
      }
      const max = Math.max(...topTrends.map(row => Number(row.trend_index || row.count || 0)), 1);
      return `<div class="trend-bars">${topTrends.slice(0, 8).map(row => {
        const height = Math.max(12, Number(row.trend_index || row.count || 0) / max * 180);
        return `<div class="trend-col">
          <div class="trend-bar" style="height:${height}px">${esc(row.trend_index || row.count)}</div>
          <div class="trend-label">${esc(row.key)}<br>${esc(row.kind)} · ${esc(row.change >= 0 ? "+" + row.change : row.change)}</div>
        </div>`;
      }).join("")}</div>`;
    }

    function renderMajorBreaks(rows) {
      const breaks = rows || macroImpact.major_breaks || [];
      if (!breaks.length) {
        return `<div class="empty">Şu an belirgin kırılım yok</div>`;
      }
      return `<div class="break-list">${breaks.slice(0, 5).map(item => `<div class="break-item">
        <div class="article-title">${esc(item.key || item.article_title || "Kırılım")}</div>
        <div class="article-meta">${esc(item.kind)} · değişim ${esc(item.change || 0)} · ${esc(item.analysis_method || "")}</div>
        <div class="insight-detail" style="margin-top:6px">${esc(item.analysis || "")}</div>
      </div>`).join("")}</div>`;
    }

    function renderBars(targetId, rows, color) {
      const target = byId(targetId);
      if (!rows.length) {
        target.innerHTML = `<div class="empty">Veri yok</div>`;
        return;
      }
      const max = Math.max(...rows.map(row => Number(row.count || 0)), 1);
      target.innerHTML = rows.map(row => {
        const width = Math.max(4, Number(row.count || 0) / max * 100);
        return `<div class="bar-row">
          <div class="bar-label" title="${esc(row.value)}">${esc(row.value)}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${width}%;background:${color || "var(--teal)"}"></div></div>
          <div class="count">${esc(row.count)}</div>
        </div>`;
      }).join("");
    }

    function renderChips(targetId, rows, className) {
      const target = byId(targetId);
      if (!rows.length) {
        target.innerHTML = `<div class="empty">Veri yok</div>`;
        return;
      }
      target.innerHTML = rows.map(row => `<span class="chip ${className || ""}">${esc(row.value)} · ${esc(row.count)}</span>`).join("");
    }

    function renderOverview() {
      const clusters = patterns.clusters || [];
      const metrics = decisionSummary.metrics || {};
      const highClusters = (outlierReport.cluster_outliers || []).length;
      byId("decisionPanel").innerHTML = decisionPanel();
      byId("kpis").innerHTML = [
        metricCard("Makro Haber", metrics.macro_documents || macroImpact.eligible_documents || 0, "Etki hesabına giren"),
        metricCard("Outlier", metrics.outlier_count || 0, "Öne çıkan sinyal"),
        metricCard("Cluster", highClusters, "Öncelikli grup"),
        metricCard("Hesap Dışı", metrics.excluded_documents || macroImpact.excluded_documents || 0, "Yüzeysel/düşük ilişkili"),
      ].join("");

      renderOutlierCards("overviewOutliers");

      const steps = decisionSummary.recommended_next_steps || [];
      byId("decisionPath").innerHTML = steps.length
        ? steps.slice(0, 3).map((step, index) => `<div class="path-step">
            <div class="path-index">Adım ${index + 1}</div>
            <div class="path-text">${esc(step)}</div>
          </div>`).join("")
        : `<div class="empty">Drilldown adımı yok</div>`;

      byId("observations").innerHTML = (patterns.observations || []).length
        ? `<div class="chips">${patterns.observations.map(item => `<span class="chip warn">${esc(item)}</span>`).join("")}</div>`
        : `<div class="empty">Pattern notu yok</div>`;
    }

    function clusterCard(cluster) {
      const ranking = clusterRankingById[cluster.cluster_id] || {};
      const terms = (cluster.common_terms || []).map(term => `<span class="chip">${esc(term)}</span>`).join("");
      const sources = (cluster.sources || []).map(source => `<span class="chip warn">${esc(source)}</span>`).join("");
      const links = (cluster.urls || []).slice(0, 5).map(url => `<li><a href="${esc(url)}" target="_blank" rel="noreferrer">${esc(url)}</a></li>`).join("");
      const score = Number(ranking.impact_score || 0);
      const scoreWidth = Math.max(5, Math.min(100, score));
      return `<article class="cluster-card" data-search="${esc(JSON.stringify(cluster).toLowerCase())}">
        <div class="cluster-head">
          <div class="cluster-title">${esc(cluster.representative_title || cluster.cluster_id)}</div>
          <div class="cluster-size">${esc(cluster.cluster_size || 1)} haber · ${esc(ranking.impact_level || "low")}</div>
        </div>
        <div class="chips">${sources}</div>
        <div class="chips" style="margin-top:8px">${terms}</div>
        <div class="score-line">
          <span>Etki skoru</span>
          <div class="bar-track"><div class="bar-fill" style="width:${scoreWidth}%;background:var(--amber)"></div></div>
          <span class="count">${esc(score)}</span>
        </div>
        <div class="chips" style="margin-top:8px">
          ${ranking.dominant_category ? `<span class="chip">${esc(ranking.dominant_category)}</span>` : ""}
          ${ranking.dominant_event_type ? `<span class="chip">${esc(ranking.dominant_event_type)}</span>` : ""}
          ${(ranking.risk_flags || []).map(flag => `<span class="chip red">${esc(flag)}</span>`).join("")}
        </div>
        ${links ? `<ul class="link-list">${links}</ul>` : ""}
      </article>`;
    }

    function renderClusters(filterText = "") {
      const clusters = patterns.clusters || [];
      const normalized = filterText.trim().toLowerCase();
      const filtered = normalized
        ? clusters.filter(cluster => JSON.stringify(cluster).toLowerCase().includes(normalized))
        : clusters;
      byId("clusterList").innerHTML = filtered.length
        ? filtered.map(clusterCard).join("")
        : `<div class="empty">Eşleşen cluster yok</div>`;
    }

    function renderIntelligence() {
      renderOutlierCards("outlierCards");

      const clusterMap = Object.fromEntries((patterns.clusters || []).map(cluster => [cluster.cluster_id, cluster]));
      const priority = (outlierReport.cluster_outliers || [])
        .map(row => ({ ...(clusterMap[row.cluster_id] || {}), ...row }))
        .filter(Boolean);
      byId("priorityClusters").innerHTML = priority.length
        ? priority.map(clusterCard).join("")
        : `<div class="empty">Öncelikli cluster yok</div>`;

      byId("outlierTrends").innerHTML = renderMajorBreaks(outlierReport.trend_outliers || []);
      const indicators = outlierReport.indicator_outliers || [];
      byId("outlierIndicators").innerHTML = indicators.length
        ? indicators.map(indicatorScale).join("")
        : `<div class="empty">Gösterge outlierı yok</div>`;
      const evidence = outlierReport.article_evidence || [];
      byId("articleEvidence").innerHTML = evidence.length
        ? evidence.map(impactArticleCard).join("")
        : `<div class="empty">Kanıt haber yok</div>`;
    }

    function renderImpact() {
      const indicatorSummary = macroImpact.indicator_summary || [];
      const trend = macroImpact.trend_report || {};
      const topArticles = macroImpact.top_impact_articles || [];
      const excluded = macroImpact.excluded_examples || [];
      const strongest = indicatorSummary
        .slice()
        .sort((left, right) => Number(right.absolute_average || 0) - Number(left.absolute_average || 0))[0];

      byId("impactKpis").innerHTML = [
        metricCard("Makro Haber", macroImpact.eligible_documents || 0, "Ekonomi/siyaset etkisi hesaplandı"),
        metricCard("Hesap Dışı", macroImpact.excluded_documents || 0, "Yüzeysel veya zayıf ilişkili"),
        metricCard("En Güçlü Gösterge", strongest ? strongest.label : "-", strongest ? signedScore(strongest.average_score) : "Veri yok"),
        metricCard("Trend Kırılımı", (macroImpact.major_breaks || []).length, "2-3 cümle analiz saklandı"),
      ].join("");

      byId("indicatorImpact").innerHTML = indicatorSummary.length
        ? indicatorSummary.map(indicatorScale).join("")
        : `<div class="empty">Makro gösterge skoru yok</div>`;

      byId("macroTrend").innerHTML = renderTrendBars();
      byId("topImpactArticles").innerHTML = topArticles.length
        ? topArticles.slice(0, 8).map(impactArticleCard).join("")
        : `<div class="empty">Etki hesaplanan haber yok</div>`;
      byId("majorBreaks").innerHTML = renderMajorBreaks();
      byId("excludedImpactArticles").innerHTML = excluded.length
        ? `<h2>Hesap Dışı Bırakılanlar</h2>${excluded.slice(0, 6).map(item => `<div class="impact-article">
            <div class="article-title">${esc(item.title)}</div>
            <div class="article-meta">${esc(item.source)} · ${esc(item.category)}</div>
            <div class="insight-detail" style="margin-top:6px">${esc(item.reason)}</div>
          </div>`).join("")}`
        : "";

      if (!trend.series?.length && !indicatorSummary.length) {
        byId("macroTrend").innerHTML = `<div class="empty">Trend için önce ekonomi/siyaset haberi gerekiyor</div>`;
      }
    }

    function renderSourceHealth(targetId = "sourceHealth") {
      const rows = patterns.source_health || [];
      const html = rows.map(row => `<div class="health-row">
        <div>
          <div class="article-title">${esc(row.name || row.key)}</div>
          <div class="article-meta">${esc(row.source_type || "html")}${row.errors?.length ? " · " + esc(row.errors[0]) : ""}</div>
        </div>
        <span class="status-dot ${esc(row.status)}">${esc(row.status)}</span>
        <div class="count">${esc(row.documents)} haber</div>
      </div>`).join("");
      byId(targetId).innerHTML = html ? `<div class="source-health">${html}</div>` : `<div class="empty">Kaynak bilgisi yok</div>`;
    }

    function renderArticleFilters() {
      const categories = records("category_counts").length
        ? records("category_counts")
        : countRecordsFromPayloads(payload => payload.analysis?.category);
      const sources = records("source_counts").length
        ? records("source_counts")
        : countRecordsFromPayloads(payload => payload.source?.key);
      byId("categoryFilter").innerHTML = optionList(categories, "Tüm kategoriler");
      byId("sourceFilter").innerHTML = optionList(sources, "Tüm kaynaklar");
    }

    function renderArticles() {
      const query = byId("articleSearch").value.trim().toLowerCase();
      const category = byId("categoryFilter").value;
      const source = byId("sourceFilter").value;
      const filtered = payloads.filter(payload => {
        const haystack = JSON.stringify({
          title: payload.article?.title,
          source: payload.source?.key,
          category: payload.analysis?.category,
          topics: payload.analysis?.topics,
          entities: payload.analysis?.entities
        }).toLowerCase();
        return (!query || haystack.includes(query))
          && (!category || payload.analysis?.category === category)
          && (!source || payload.source?.key === source);
      });
      byId("articleTable").innerHTML = filtered.slice(0, 80).map(payload => {
        const article = payload.article || {};
        const analysis = payload.analysis || {};
        const sourceInfo = payload.source || {};
        return `<div class="article-row">
          <div>
            <div class="article-title" title="${esc(article.title)}">${esc(article.title)}</div>
            <div class="article-meta">${esc(article.url || "")}</div>
          </div>
          <span class="chip">${esc(analysis.category || "diger")}</span>
          <span class="chip warn">${esc(sourceInfo.key || "unknown")}</span>
          <span class="chip ${payload.cluster?.cluster_size > 1 ? "warn" : ""}">${esc(payload.cluster?.cluster_size || 1)} cluster</span>
        </div>`;
      }).join("") || `<div class="empty">Filtreye uyan haber yok</div>`;
    }

    function renderSources() {
      renderBars("sourceBars", records("source_counts"), "var(--amber)");
      const errors = pipeline.errors || [];
      byId("sourceErrors").innerHTML = errors.length
        ? `<div class="error-list">${errors.map(error => `<div class="error-item"><strong>${esc(error.source)}</strong><br>${esc(error.error)}</div>`).join("")}</div>`
        : `<div class="empty">Kaynak hatası yok</div>`;
      renderSourceHealth("sourceHealthSources");
    }

    function renderAll() {
      const generatedAt = pipeline.generated_at || payloads[0]?.pipeline?.collected_at || "";
      byId("runMeta").innerHTML = generatedAt
        ? `Son çalışma<br><strong>${esc(generatedAt)}</strong>`
        : `Yerel dashboard`;
      renderOverview();
      renderClusters();
      renderIntelligence();
      renderImpact();
      renderBars("categoryBars", records("category_counts"), "var(--teal)");
      renderBars("eventBars", records("event_type_counts"), "var(--blue)");
      renderBars("riskBars", records("risk_flag_counts"), "var(--red)");
      renderBars("geoBars", records("geography_counts"), "var(--blue)");
      renderArticleFilters();
      renderArticles();
      renderSources();
    }

    document.querySelectorAll(".tab").forEach(tab => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach(item => item.classList.remove("active"));
        document.querySelectorAll(".view").forEach(item => item.classList.remove("active"));
        tab.classList.add("active");
        byId(tab.dataset.view).classList.add("active");
      });
    });

    byId("clusterSearch").addEventListener("input", event => {
      renderClusters(event.target.value);
    });

    ["articleSearch", "categoryFilter", "sourceFilter"].forEach(id => {
      byId(id).addEventListener("input", renderArticles);
      byId(id).addEventListener("change", renderArticles);
    });

    renderAll();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
