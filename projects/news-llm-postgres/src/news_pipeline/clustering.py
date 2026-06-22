from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from typing import Any

STOP_WORDS = {
    "ama",
    "ancak",
    "bir",
    "çok",
    "daha",
    "dedi",
    "diye",
    "gibi",
    "haber",
    "için",
    "ile",
    "olan",
    "olarak",
    "son",
    "sonra",
    "tüm",
    "var",
    "yeni",
}


def apply_clusters(payloads: list[dict[str, Any]], similarity_threshold: float = 0.28) -> None:
    if not payloads:
        return

    vectors = [vectorize_payload(payload) for payload in payloads]
    parent = list(range(len(payloads)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left in range(len(payloads)):
        for right in range(left + 1, len(payloads)):
            if cosine_similarity(vectors[left], vectors[right]) >= similarity_threshold:
                union(left, right)

    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(payloads)):
        groups[find(index)].append(index)

    for indices in groups.values():
        representative_index = choose_representative(indices, vectors)
        representative = payloads[representative_index]
        cluster_id = build_cluster_id(representative)
        common_terms = common_terms_for_group(indices, vectors)
        urls = [payloads[index]["article"]["url"] for index in indices]

        for index in indices:
            payload = payloads[index]
            payload["cluster"] = {
                "cluster_id": cluster_id,
                "cluster_size": len(indices),
                "method": "token_cosine_v1",
                "similarity_threshold": similarity_threshold,
                "representative_title": representative["article"]["title"],
                "common_terms": common_terms,
                "related_urls": [url for url in urls if url != payload["article"]["url"]][:8],
            }


def build_pattern_report(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    category_counts: Counter[str] = Counter()
    event_type_counts: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    geography_counts: Counter[str] = Counter()
    risk_flag_counts: Counter[str] = Counter()
    entity_counts = {
        "persons": Counter(),
        "organizations": Counter(),
        "locations": Counter(),
    }
    clusters_by_id: dict[str, dict[str, Any]] = {}

    for payload in payloads:
        analysis = payload.get("analysis", {})
        source = payload.get("source", {})
        cluster = payload.get("cluster", {})

        category_counts.update([str(analysis.get("category", "diger"))])
        event_type_counts.update([str(analysis.get("event_type", "general"))])
        source_counts.update([str(source.get("key", "unknown"))])
        topic_counts.update(str(topic) for topic in analysis.get("topics", []))
        geography_counts.update(str(place) for place in analysis.get("geography", []))
        risk_flag_counts.update(str(flag) for flag in analysis.get("risk_flags", []))

        entities = analysis.get("entities", {})
        if isinstance(entities, dict):
            for key in entity_counts:
                entity_counts[key].update(str(value) for value in entities.get(key, []))

        cluster_id = str(cluster.get("cluster_id", ""))
        if cluster_id and int(cluster.get("cluster_size", 1)) > 1:
            clusters_by_id.setdefault(
                cluster_id,
                {
                    "cluster_id": cluster_id,
                    "cluster_size": cluster.get("cluster_size", 1),
                    "representative_title": cluster.get("representative_title", ""),
                    "common_terms": cluster.get("common_terms", []),
                    "sources": set(),
                    "categories": set(),
                    "urls": [],
                },
            )
            clusters_by_id[cluster_id]["sources"].add(source.get("key", "unknown"))
            clusters_by_id[cluster_id]["categories"].add(analysis.get("category", "diger"))
            clusters_by_id[cluster_id]["urls"].append(payload.get("article", {}).get("url", ""))

    clusters = []
    for cluster in clusters_by_id.values():
        clusters.append(
            {
                **cluster,
                "sources": sorted(cluster["sources"]),
                "categories": sorted(cluster["categories"]),
                "urls": [url for url in cluster["urls"] if url],
            }
        )

    clusters.sort(key=lambda item: (-int(item["cluster_size"]), item["representative_title"]))

    return {
        "pattern_version": "patterns-v1",
        "total_documents": len(payloads),
        "category_counts": counter_to_records(category_counts),
        "event_type_counts": counter_to_records(event_type_counts),
        "source_counts": counter_to_records(source_counts),
        "top_topics": counter_to_records(topic_counts, limit=20),
        "top_entities": {
            key: counter_to_records(counter, limit=15)
            for key, counter in entity_counts.items()
        },
        "geography_counts": counter_to_records(geography_counts, limit=20),
        "risk_flag_counts": counter_to_records(risk_flag_counts, limit=20),
        "clusters": clusters,
        "observations": build_observations(
            total_documents=len(payloads),
            category_counts=category_counts,
            geography_counts=geography_counts,
            risk_flag_counts=risk_flag_counts,
            clusters=clusters,
        ),
    }


def vectorize_payload(payload: dict[str, Any]) -> Counter[str]:
    article = payload.get("article", {})
    analysis = payload.get("analysis", {})
    text_parts = [
        article.get("title", ""),
        article.get("summary", ""),
        article.get("content_text", ""),
        " ".join(analysis.get("keywords", [])),
        " ".join(analysis.get("topics", [])),
    ]
    tokens = tokenize(" ".join(str(part) for part in text_parts))
    return Counter(tokens)


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-ZğüşöçıİĞÜŞÖÇ0-9]{3,}", text.lower())
    return [stem_token(token) for token in tokens if token not in STOP_WORDS]


def stem_token(token: str) -> str:
    if token in {"kararı", "kararını", "kararının"}:
        return "karar"
    for suffix in (
        "larının",
        "lerinin",
        "lardan",
        "lerden",
        "ları",
        "leri",
        "ının",
        "inin",
        "unu",
        "ünü",
        "ını",
        "ini",
        "dan",
        "den",
        "tan",
        "ten",
        "nda",
        "nde",
        "nın",
        "nin",
        "nun",
        "nün",
        "lar",
        "ler",
        "dır",
        "dir",
        "dur",
        "dür",
    ):
        if token.endswith(suffix) and len(token) > len(suffix) + 3:
            return token[: -len(suffix)]
    return token


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(count * count for count in left.values()))
    right_norm = math.sqrt(sum(count * count for count in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def choose_representative(indices: list[int], vectors: list[Counter[str]]) -> int:
    return max(indices, key=lambda index: (sum(vectors[index].values()), -index))


def common_terms_for_group(indices: list[int], vectors: list[Counter[str]]) -> list[str]:
    totals: Counter[str] = Counter()
    for index in indices:
        totals.update(vectors[index])
    return [term for term, _ in totals.most_common(8)]


def build_cluster_id(payload: dict[str, Any]) -> str:
    key = payload.get("pipeline", {}).get("content_hash") or payload.get("article", {}).get("url", "")
    digest = hashlib.sha1(str(key).encode("utf-8")).hexdigest()[:10]
    return f"cluster_{digest}"


def counter_to_records(counter: Counter[str], limit: int = 12) -> list[dict[str, Any]]:
    return [
        {"value": value, "count": count}
        for value, count in counter.most_common(limit)
        if value
    ]


def build_observations(
    total_documents: int,
    category_counts: Counter[str],
    geography_counts: Counter[str],
    risk_flag_counts: Counter[str],
    clusters: list[dict[str, Any]],
) -> list[str]:
    observations = []
    if clusters:
        observations.append("Benzer haber kümeleri bulundu; aynı olay farklı kaynaklarda tekrar ediyor olabilir.")

    if total_documents:
        category, count = category_counts.most_common(1)[0]
        if count / total_documents >= 0.35:
            observations.append(f"Bu çalıştırmada en yoğun kategori {category}.")

    if geography_counts:
        place, _ = geography_counts.most_common(1)[0]
        observations.append(f"Lokasyon bazında en sık geçen yer {place}.")

    if risk_flag_counts:
        flag, _ = risk_flag_counts.most_common(1)[0]
        observations.append(f"Öne çıkan risk/pattern sinyali {flag}.")

    if not observations:
        observations.append("Belirgin tekrar eden pattern düşük; daha fazla veriyle tekrar bakılmalı.")

    return observations
