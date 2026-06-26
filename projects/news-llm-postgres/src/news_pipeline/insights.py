from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .models import NewsSource


def enrich_pattern_report(
    patterns: dict[str, Any],
    payloads: list[dict[str, Any]],
    sources: list[NewsSource],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    enriched = dict(patterns)
    enriched["source_health"] = build_source_health(payloads, sources, errors)
    enriched["cluster_rankings"] = rank_clusters(payloads, enriched.get("clusters", []))
    enriched["entity_network"] = build_entity_network(payloads)
    enriched["coverage_matrix"] = build_coverage_matrix(payloads)
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
        impact_score = (
            len(members) * 10
            + len(sources) * 5
            + len(risk_flags) * 4
            + len(locations) * 2
            + high_importance_count * 4
        )
        ranked.append(
            {
                "cluster_id": cluster_id,
                "representative_title": cluster.get("representative_title", ""),
                "cluster_size": len(members) or int(cluster.get("cluster_size", 0)),
                "impact_score": impact_score,
                "impact_level": impact_level(impact_score),
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


def build_insight_cards(patterns: dict[str, Any], payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = []
    total_documents = len(payloads)
    clusters = patterns.get("cluster_rankings", [])
    source_health = patterns.get("source_health", [])
    categories = patterns.get("category_counts", [])
    risks = patterns.get("risk_flag_counts", [])
    geo = patterns.get("geography_counts", [])

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
