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
      grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);
    }

    .grid.three {
      grid-template-columns: repeat(3, minmax(0, 1fr));
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
    }

    .cluster-card {
      padding: 14px;
    }

    .cluster-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      margin-bottom: 10px;
    }

    .cluster-title {
      font-weight: 700;
      line-height: 1.35;
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

    .link-list {
      margin: 10px 0 0;
      padding-left: 18px;
      color: var(--muted);
    }

    .link-list li {
      margin: 4px 0;
      overflow-wrap: anywhere;
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

    .map-canvas {
      position: relative;
      min-height: 360px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #eaf1f7;
      overflow: hidden;
    }

    .map-canvas svg {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
    }

    .marker {
      position: absolute;
      transform: translate(-50%, -50%);
      display: grid;
      place-items: center;
      border-radius: 999px;
      background: rgba(15, 118, 110, 0.86);
      color: #fff;
      border: 2px solid #fff;
      box-shadow: 0 8px 20px rgba(15, 23, 42, 0.25);
      font-size: 12px;
      font-weight: 700;
    }

    .marker-label {
      position: absolute;
      transform: translate(-50%, 16px);
      padding: 3px 6px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.92);
      color: var(--text);
      font-size: 12px;
      white-space: nowrap;
      border: 1px solid var(--line);
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
      .grid.two,
      .grid.three,
      .kpis,
      .article-row {
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
            <div class="subtitle">Kümeleme, kategori, lokasyon ve kaynak sinyalleri</div>
          </div>
          <div class="run-meta" id="runMeta"></div>
        </div>
        <nav class="tabs" aria-label="Dashboard views">
          <button class="tab active" data-view="overview">Genel</button>
          <button class="tab" data-view="clusters">Kümeler</button>
          <button class="tab" data-view="categories">Kategoriler</button>
          <button class="tab" data-view="map">Harita</button>
          <button class="tab" data-view="sources">Kaynaklar</button>
        </nav>
      </div>
    </header>

    <main>
      <section class="view active" id="overview">
        <div class="kpis" id="kpis"></div>
        <div class="grid two">
          <div class="panel">
            <h2>Öne Çıkan Pattern Notları</h2>
            <div id="observations"></div>
          </div>
          <div class="panel">
            <h2>Son Haberler</h2>
            <div id="latestArticles"></div>
          </div>
        </div>
      </section>

      <section class="view" id="clusters">
        <input class="search" id="clusterSearch" placeholder="Cluster, kaynak veya ortak terim ara">
        <div class="cluster-list" id="clusterList"></div>
      </section>

      <section class="view" id="categories">
        <div class="grid two">
          <div class="panel">
            <h2>Kategori Dağılımı</h2>
            <div id="categoryBars"></div>
          </div>
          <div class="panel">
            <h2>Olay Tipleri</h2>
            <div id="eventBars"></div>
          </div>
        </div>
        <div class="grid two" style="margin-top:16px">
          <div class="panel">
            <h2>Topic Yoğunluğu</h2>
            <div id="topicChips" class="chips"></div>
          </div>
          <div class="panel">
            <h2>Risk Sinyalleri</h2>
            <div id="riskBars"></div>
          </div>
        </div>
      </section>

      <section class="view" id="map">
        <div class="grid two">
          <div class="panel">
            <h2>Lokasyon Haritası</h2>
            <div class="map-canvas" id="mapCanvas">
              <svg viewBox="0 0 900 360" preserveAspectRatio="none" aria-hidden="true">
                <path d="M74 180 L118 140 L204 132 L270 104 L348 120 L438 98 L542 124 L650 116 L780 152 L830 202 L752 236 L620 250 L510 234 L414 260 L306 236 L210 242 L132 218 Z" fill="#d8e7f0" stroke="#9db4c4" stroke-width="3"></path>
                <path d="M152 242 L210 274 L318 286 L428 278 L536 294 L690 268 L776 236" fill="none" stroke="#b8c9d6" stroke-width="2"></path>
              </svg>
            </div>
          </div>
          <div class="panel">
            <h2>Lokasyon Sayımları</h2>
            <div id="geoBars"></div>
          </div>
        </div>
      </section>

      <section class="view" id="sources">
        <div class="grid two">
          <div class="panel">
            <h2>Kaynak Dağılımı</h2>
            <div id="sourceBars"></div>
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
    const cityCoords = {
      "Türkiye": [50, 48],
      "İstanbul": [26, 43],
      "Ankara": [49, 47],
      "İzmir": [22, 60],
      "Bursa": [30, 48],
      "Antalya": [36, 74],
      "Adana": [59, 70],
      "Gaziantep": [68, 67],
      "Diyarbakır": [77, 57],
      "Samsun": [59, 31],
      "Trabzon": [75, 27],
      "Van": [87, 51],
      "Konya": [47, 64],
      "Kayseri": [60, 55],
      "Mersin": [56, 73],
      "Edirne": [15, 37],
      "Kocaeli": [30, 43],
      "Muğla": [25, 70],
      "Erzurum": [79, 42],
      "Malatya": [68, 56]
    };

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

    function metricCard(label, value, note) {
      return `<div class="kpi"><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${esc(value)}</div><div class="kpi-note">${esc(note || "")}</div></div>`;
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
      const categoryCount = records("category_counts").length || unique(payloads.map(p => p.analysis?.category)).length;
      const sourceCount = records("source_counts").length || unique(payloads.map(p => p.source?.key)).length;
      const errors = pipeline.errors || [];
      byId("kpis").innerHTML = [
        metricCard("Haber", payloads.length, "JSONB payload"),
        metricCard("Cluster", clusters.length, "Benzer haber grubu"),
        metricCard("Kategori", categoryCount, "Aktif sınıf"),
        metricCard("Kaynak", sourceCount, errors.length ? `${errors.length} hata` : "Temiz")
      ].join("");

      byId("observations").innerHTML = (patterns.observations || []).length
        ? `<div class="chips">${patterns.observations.map(item => `<span class="chip warn">${esc(item)}</span>`).join("")}</div>`
        : `<div class="empty">Pattern notu yok</div>`;

      byId("latestArticles").innerHTML = payloads.slice(0, 8).map(payload => {
        const article = payload.article || {};
        const analysis = payload.analysis || {};
        const source = payload.source || {};
        return `<div class="article-row">
          <div>
            <div class="article-title" title="${esc(article.title)}">${esc(article.title)}</div>
            <div class="article-meta">${esc(source.name || source.key)} · ${esc(analysis.event_type || "general")}</div>
          </div>
          <span class="chip">${esc(analysis.category || "diger")}</span>
          <span class="chip ${payload.cluster?.cluster_size > 1 ? "warn" : ""}">cluster ${esc(payload.cluster?.cluster_size || 1)}</span>
        </div>`;
      }).join("") || `<div class="empty">Haber yok</div>`;
    }

    function clusterCard(cluster) {
      const terms = (cluster.common_terms || []).map(term => `<span class="chip">${esc(term)}</span>`).join("");
      const sources = (cluster.sources || []).map(source => `<span class="chip warn">${esc(source)}</span>`).join("");
      const links = (cluster.urls || []).slice(0, 5).map(url => `<li><a href="${esc(url)}" target="_blank" rel="noreferrer">${esc(url)}</a></li>`).join("");
      return `<article class="cluster-card" data-search="${esc(JSON.stringify(cluster).toLowerCase())}">
        <div class="cluster-head">
          <div class="cluster-title">${esc(cluster.representative_title || cluster.cluster_id)}</div>
          <div class="cluster-size">${esc(cluster.cluster_size || 1)} haber</div>
        </div>
        <div class="chips">${sources}</div>
        <div class="chips" style="margin-top:8px">${terms}</div>
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

    function renderMap() {
      renderBars("geoBars", records("geography_counts"), "var(--blue)");
      const canvas = byId("mapCanvas");
      canvas.querySelectorAll(".marker,.marker-label").forEach(node => node.remove());
      const rows = records("geography_counts");
      if (!rows.length) {
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.style.position = "absolute";
        empty.style.left = "16px";
        empty.style.right = "16px";
        empty.style.bottom = "16px";
        empty.textContent = "Lokasyon verisi yok";
        canvas.appendChild(empty);
        return;
      }
      const max = Math.max(...rows.map(row => Number(row.count || 0)), 1);
      rows.forEach((row, index) => {
        const coords = cityCoords[row.value] || [18 + (index * 13) % 70, 35 + (index * 11) % 42];
        const size = 18 + Number(row.count || 1) / max * 22;
        const marker = document.createElement("div");
        marker.className = "marker";
        marker.style.left = coords[0] + "%";
        marker.style.top = coords[1] + "%";
        marker.style.width = size + "px";
        marker.style.height = size + "px";
        marker.textContent = row.count;
        const label = document.createElement("div");
        label.className = "marker-label";
        label.style.left = coords[0] + "%";
        label.style.top = coords[1] + "%";
        label.textContent = row.value;
        canvas.appendChild(marker);
        canvas.appendChild(label);
      });
    }

    function renderSources() {
      renderBars("sourceBars", records("source_counts"), "var(--amber)");
      const errors = pipeline.errors || [];
      byId("sourceErrors").innerHTML = errors.length
        ? `<div class="error-list">${errors.map(error => `<div class="error-item"><strong>${esc(error.source)}</strong><br>${esc(error.error)}</div>`).join("")}</div>`
        : `<div class="empty">Kaynak hatası yok</div>`;
    }

    function renderAll() {
      const generatedAt = pipeline.generated_at || payloads[0]?.pipeline?.collected_at || "";
      byId("runMeta").innerHTML = generatedAt
        ? `Son çalışma<br><strong>${esc(generatedAt)}</strong>`
        : `Yerel dashboard`;
      renderOverview();
      renderClusters();
      renderBars("categoryBars", records("category_counts"), "var(--teal)");
      renderBars("eventBars", records("event_type_counts"), "var(--blue)");
      renderBars("riskBars", records("risk_flag_counts"), "var(--red)");
      renderChips("topicChips", records("top_topics"));
      renderMap();
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

    renderAll();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
