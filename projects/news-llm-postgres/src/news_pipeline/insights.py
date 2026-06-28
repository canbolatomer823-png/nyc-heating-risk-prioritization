from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .impact import build_macro_impact_report
from .models import NewsSource


def enrich_pattern_report(
    patterns: dict[str, Any],
    payloads: list[dict[str, Any]],
    sources: list[NewsSource],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    enriched = dict(patterns)
    enriched["source_health"] = build_source_health(payloads, sources, errors)
    enriched["macro_impact"] = build_macro_impact_report(payloads)
    enriched["cluster_rankings"] = rank_clusters(payloads, enriched.get("clusters", []))
    enriched["entity_network"] = build_entity_network(payloads)
    enriched["coverage_matrix"] = build_coverage_matrix(payloads)
    enriched["outlier_report"] = build_outlier_report(enriched, payloads)
    enriched["decision_summary"] = build_decision_summary(enriched, payloads)
    enriched["insight_cards"] = build_insight_cards(enriched, payloads)
    return enriched


def build_source_health(
    payloads: list[dict[str, Any]],
    sources: list[NewsSource],
    errors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    documents_by_source = Counter(str(payload.get("source", {}).get("key", "unknown")) for payload in payloads)
    errors_by_source: dict[str, list[str]] = defaultdict(list)
    for error in errors:
        errors_by_source[str(error.get("source", "unknown"))].append(str(error.get("error", "")))

    rows = []
    for source in sources:
        documents = documents_by_source.get(source.key, 0)
        source_errors = errors_by_source.get(source.key, [])
        if documents and not source_errors:
            status = "ok"
        elif documents and source_errors:
            status = "partial"
        else:
            status = "blocked" if source_errors else "empty"
        rows.append(
            {
                "key": source.key,
                "name": source.name,
                "source_type": source.source_type,
                "documents": documents,
                "status": status,
                "errors": source_errors[:3],
            }
        )

    return sorted(rows, key=lambda row: (status_rank(row["status"]), -int(row["documents"]), row["key"]))


def rank_clusters(payloads: list[dict[str, Any]], clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads_by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for payload in payloads:
        cluster_id = str(payload.get("cluster", {}).get("cluster_id", ""))
        if cluster_id:
            payloads_by_cluster[cluster_id].append(payload)

    ranked = []
    for cluster in clusters:
        cluster_id = str(cluster.get("cluster_id", ""))
        members = payloads_by_cluster.get(cluster_id, [])
        categories = Counter(str(member.get("analysis", {}).get("category", "diger")) for member in members)
        event_types = Counter(str(member.get("analysis", {}).get("event_type", "general")) for member in members)
        risk_flags = sorted(
            {
                flag
                for member in members
                for flag in member.get("analysis", {}).get("risk_flags", [])
            }
        )
        locations = sorted(
            {
                place
                for member in members
                for place in member.get("analysis", {}).get("geography", [])
            }
        )
        sources = sorted({str(member.get("source", {}).get("key", "unknown")) for member in members})
        high_importance_count = sum(
            1
            for member in members
            if member.get("analysis", {}).get("importance") in {"high", "critical"}
        )
        macro_members = [
            member
            for member in members
            if member.get("impact_analysis", {}).get("eligible")
        ]
        surface_members = len(members) - len(macro_members)
        macro_impact = sum(
            int(member.get("impact_analysis", {}).get("net_abs_impact", 0))
            for member in macro_members
        )
        impact_score = (
            len(members) * 10
            + len(sources) * 5
            + len(risk_flags) * 4
            + len(locations) * 2
            + high_importance_count * 4
            + macro_impact
            - surface_members * 8
        )
        impact_score = max(0, impact_score)
        ranked.append(
            {
                "cluster_id": cluster_id,
                "representative_title": cluster.get("representative_title", ""),
                "cluster_size": len(members) or int(cluster.get("cluster_size", 0)),
                "impact_score": impact_score,
                "impact_level": impact_level(impact_score),
                "macro_documents": len(macro_members),
                "surface_documents": surface_members,
                "dominant_category": most_common_value(categories, "diger"),
                "dominant_event_type": most_common_value(event_types, "general"),
                "sources": sources,
                "risk_flags": risk_flags,
                "locations": locations,
            }
        )

    return sorted(ranked, key=lambda row: (-int(row["impact_score"]), row["representative_title"]))


def build_entity_network(payloads: list[dict[str, Any]], limit: int = 24) -> dict[str, list[dict[str, Any]]]:
    node_counts: Counter[str] = Counter()
    edge_counts: Counter[tuple[str, str]] = Counter()

    for payload in payloads:
        analysis = payload.get("analysis", {})
        entities = analysis.get("entities", {})
        tokens = []
        if isinstance(entities, dict):
            for key in ("persons", "organizations", "locations"):
                tokens.extend(str(value) for value in entities.get(key, []))
        tokens.extend(str(topic) for topic in analysis.get("topics", [])[:4])
        tokens = [token for token in dict.fromkeys(tokens) if len(token) > 2][:10]

        node_counts.update(tokens)
        for left_index, left in enumerate(tokens):
            for right in tokens[left_index + 1 :]:
                edge_counts.update([tuple(sorted((left, right)))])

    nodes = [
        {"id": value, "count": count, "kind": infer_node_kind(value)}
        for value, count in node_counts.most_common(limit)
    ]
    allowed = {node["id"] for node in nodes}
    edges = [
        {"source": left, "target": right, "count": count}
        for (left, right), count in edge_counts.most_common(limit * 2)
        if left in allowed and right in allowed
    ][:limit]
    return {"nodes": nodes, "edges": edges}


def build_coverage_matrix(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix: dict[tuple[str, str], int] = defaultdict(int)
    for payload in payloads:
        source = str(payload.get("source", {}).get("key", "unknown"))
        category = str(payload.get("analysis", {}).get("category", "diger"))
        matrix[(source, category)] += 1
    rows = [
        {"source": source, "category": category, "count": count}
        for (source, category), count in matrix.items()
    ]
    return sorted(rows, key=lambda row: (row["source"], row["category"]))


def build_outlier_report(patterns: dict[str, Any], payloads: list[dict[str, Any]]) -> dict[str, Any]:
    cluster_rows = [
        {
            **cluster,
            "why": cluster_outlier_reason(cluster),
        }
        for cluster in patterns.get("cluster_rankings", [])
        if int(cluster.get("cluster_size", 0)) > 1
        and (
            cluster.get("impact_level") in {"high", "medium"}
            or int(cluster.get("macro_documents", 0)) > 0
        )
    ][:5]

    macro_impact = patterns.get("macro_impact", {})
    indicator_rows = [
        {
            **indicator,
            "direction": "positive" if float(indicator.get("average_score", 0)) > 0 else "negative",
            "why": indicator_outlier_reason(indicator),
        }
        for indicator in sorted(
            macro_impact.get("indicator_summary", []),
            key=lambda row: -float(row.get("absolute_average", 0)),
        )
        if float(indicator.get("absolute_average", 0)) >= 0.75
    ][:5]

    trend_rows = [
        {
            **row,
            "why": trend_outlier_reason(row),
        }
        for row in macro_impact.get("major_breaks", [])
        if row.get("kind") != "article_impact"
        and abs(int(row.get("change", 0))) >= 2
    ][:5]

    evidence_rows = [
        row
        for row in macro_impact.get("top_impact_articles", [])
        if int(row.get("net_abs_impact", 0)) >= 6
    ][:6]

    return {
        "outlier_version": "outliers-v1",
        "cluster_outliers": cluster_rows,
        "indicator_outliers": indicator_rows,
        "trend_outliers": trend_rows,
        "article_evidence": evidence_rows,
        "excluded_examples": macro_impact.get("excluded_examples", [])[:6],
        "single_article_note": "Tekil haberler karar noktası değil; sadece outlier ve cluster için kanıt olarak kullanılır.",
    }


def build_decision_summary(patterns: dict[str, Any], payloads: list[dict[str, Any]]) -> dict[str, Any]:
    macro_impact = patterns.get("macro_impact", {})
    outliers = patterns.get("outlier_report", {})
    source_health = patterns.get("source_health", [])
    active_sources = sum(1 for source in source_health if int(source.get("documents", 0)) > 0)
    blocked_sources = sum(1 for source in source_health if source.get("status") in {"blocked", "partial"})
    top_indicator = first_or_none(outliers.get("indicator_outliers", []))
    top_cluster = first_or_none(outliers.get("cluster_outliers", []))
    top_trend = first_or_none(outliers.get("trend_outliers", []))

    if top_indicator:
        direction = "baskı" if float(top_indicator.get("average_score", 0)) < 0 else "destek"
        headline = f"{top_indicator.get('label')} tarafında {direction} sinyali öne çıkıyor"
    elif top_cluster:
        headline = f"{top_cluster.get('dominant_category', 'gündem')} clusterı izlenmeli"
    elif top_trend:
        headline = f"{top_trend.get('key')} trendi yükseliyor"
    else:
        headline = "Bu çalıştırmada belirgin makro outlier düşük"

    outlier_count = (
        len(outliers.get("cluster_outliers", []))
        + len(outliers.get("indicator_outliers", []))
        + len(outliers.get("trend_outliers", []))
    )
    if outlier_count >= 6:
        decision_label = "Yakından izle"
        priority = "high"
    elif outlier_count >= 2:
        decision_label = "İzle ve drilldown yap"
        priority = "medium"
    else:
        decision_label = "Düşük öncelik"
        priority = "low"

    focus_parts = []
    if top_cluster:
        focus_parts.append(f"{top_cluster.get('representative_title', '')[:90]}")
    if top_trend:
        focus_parts.append(f"{top_trend.get('key')} trend kırılımı")
    if top_indicator:
        focus_parts.append(f"{top_indicator.get('label')} {float(top_indicator.get('average_score', 0)):+.2f}")

    return {
        "summary_version": "decision-summary-v1",
        "headline": headline,
        "decision_label": decision_label,
        "priority": priority,
        "focus": " · ".join(part for part in focus_parts if part) or "Belirgin odak yok",
        "why": build_decision_why(top_indicator, top_cluster, top_trend),
        "recommended_next_steps": [
            "Önce outlier cluster ve trend kırılımlarına bak.",
            "Tekil haberleri sadece kanıt olarak kontrol et.",
            "Server deploy sonrası scheduled run ile trend geçmişi biriktir.",
        ],
        "metrics": {
            "total_documents": len(payloads),
            "macro_documents": macro_impact.get("eligible_documents", 0),
            "excluded_documents": macro_impact.get("excluded_documents", 0),
            "outlier_count": outlier_count,
            "active_sources": active_sources,
            "blocked_sources": blocked_sources,
        },
    }


def build_insight_cards(patterns: dict[str, Any], payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = []
    total_documents = len(payloads)
    decision_summary = patterns.get("decision_summary", {})
    clusters = patterns.get("cluster_rankings", [])
    source_health = patterns.get("source_health", [])
    categories = patterns.get("category_counts", [])
    risks = patterns.get("risk_flag_counts", [])
    geo = patterns.get("geography_counts", [])
    macro_impact = patterns.get("macro_impact", {})

    if decision_summary:
        cards.append(
            {
                "title": "Karar etiketi",
                "metric": decision_summary.get("decision_label", "İzle"),
                "label": decision_summary.get("priority", "medium"),
                "severity": decision_summary.get("priority", "medium"),
                "detail": decision_summary.get("headline", ""),
            }
        )

    if clusters:
        top_cluster = clusters[0]
        cards.append(
            {
                "title": "En güçlü gündem kümesi",
                "metric": str(top_cluster["cluster_size"]),
                "label": "haber",
                "severity": top_cluster["impact_level"],
                "detail": (
                    f"{top_cluster['representative_title']} başlığı etrafında "
                    f"{len(top_cluster['sources'])} kaynak ve {len(top_cluster['risk_flags'])} risk sinyali var."
                ),
            }
        )

    if macro_impact:
        cards.append(
            {
                "title": "Makro etki analizi",
                "metric": str(macro_impact.get("eligible_documents", 0)),
                "label": "haber",
                "severity": "medium" if macro_impact.get("eligible_documents", 0) else "low",
                "detail": (
                    f"{macro_impact.get('excluded_documents', 0)} yüzeysel/düşük ilişkili haber "
                    "TL, büyüme ve enflasyon hesabına alınmadı."
                ),
            }
        )

        top_indicator = next(
            (
                row
                for row in sorted(
                    macro_impact.get("indicator_summary", []),
                    key=lambda item: -float(item.get("absolute_average", 0)),
                )
                if float(row.get("absolute_average", 0)) > 0
            ),
            None,
        )
        if top_indicator:
            cards.append(
                {
                    "title": "En güçlü gösterge",
                    "metric": f"{top_indicator['average_score']:+.2f}",
                    "label": top_indicator["label"],
                    "severity": "medium",
                    "detail": top_indicator["interpretation"],
                }
            )

    if categories and total_documents:
        top_category = categories[0]
        share = round(int(top_category["count"]) / total_documents * 100)
        cards.append(
            {
                "title": "Baskın kategori",
                "metric": f"%{share}",
                "label": top_category["value"],
                "severity": "medium" if share >= 35 else "low",
                "detail": f"Bu çalıştırmada {top_category['value']} kategorisi öne çıkıyor.",
            }
        )

    blocked_sources = [source for source in source_health if source["status"] in {"blocked", "partial"}]
    if blocked_sources:
        names = ", ".join(source["key"] for source in blocked_sources[:3])
        cards.append(
            {
                "title": "Kaynak sağlığı",
                "metric": str(len(blocked_sources)),
                "label": "problem",
                "severity": "high",
                "detail": f"Kontrol edilmesi gereken kaynaklar: {names}.",
            }
        )

    if risks:
        top_risk = risks[0]
        cards.append(
            {
                "title": "Risk sinyali",
                "metric": str(top_risk["count"]),
                "label": top_risk["value"],
                "severity": "medium",
                "detail": f"{top_risk['value']} sinyali haberlerde tekrar ediyor.",
            }
        )

    if geo:
        top_place = geo[0]
        cards.append(
            {
                "title": "Lokasyon odağı",
                "metric": str(top_place["count"]),
                "label": top_place["value"],
                "severity": "low",
                "detail": f"Lokasyon bazında {top_place['value']} daha görünür.",
            }
        )

    if not cards:
        cards.append(
            {
                "title": "Veri hacmi düşük",
                "metric": str(total_documents),
                "label": "haber",
                "severity": "low",
                "detail": "Daha anlamlı pattern için daha fazla kaynak veya daha yüksek limit denenmeli.",
            }
        )

    return cards


def status_rank(status: str) -> int:
    return {"blocked": 0, "partial": 1, "empty": 2, "ok": 3}.get(status, 4)


def impact_level(score: int) -> str:
    if score >= 45:
        return "high"
    if score >= 28:
        return "medium"
    return "low"


def most_common_value(counter: Counter[str], fallback: str) -> str:
    if not counter:
        return fallback
    return counter.most_common(1)[0][0]


def infer_node_kind(value: str) -> str:
    if value[:1].isupper() and " " in value:
        return "entity"
    if value[:1].isupper():
        return "location"
    return "topic"


def first_or_none(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return rows[0] if rows else None


def cluster_outlier_reason(cluster: dict[str, Any]) -> str:
    parts = [
        f"{cluster.get('cluster_size', 0)} haber",
        f"{len(cluster.get('sources', []))} kaynak",
    ]
    if cluster.get("risk_flags"):
        parts.append(f"{len(cluster.get('risk_flags', []))} risk sinyali")
    if int(cluster.get("macro_documents", 0)):
        parts.append(f"{cluster.get('macro_documents')} makro haber")
    return ", ".join(parts)


def indicator_outlier_reason(indicator: dict[str, Any]) -> str:
    score = float(indicator.get("average_score", 0))
    return f"Ortalama etki {score:+.2f}; {indicator.get('interpretation', 'belirgin yön yok')}."


def trend_outlier_reason(row: dict[str, Any]) -> str:
    return f"{row.get('key')} başlığı {row.get('change', 0):+} değişim ve {row.get('count', 0)} haberle ayrışıyor."


def build_decision_why(
    indicator: dict[str, Any] | None,
    cluster: dict[str, Any] | None,
    trend: dict[str, Any] | None,
) -> str:
    parts = []
    if indicator:
        parts.append(indicator_outlier_reason(indicator))
    if cluster:
        parts.append(f"En güçlü cluster: {cluster_outlier_reason(cluster)}.")
    if trend:
        parts.append(trend_outlier_reason(trend))
    if not parts:
        return "Kayda değer outlier az; daha anlamlı trend için scheduled run gerekir."
    return " ".join(parts)
