from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any


MACRO_CATEGORIES = {"ekonomi", "siyaset"}
MACRO_RISK_FLAGS = {"market_pressure", "political_tension", "international_conflict", "legal_process"}

INDICATORS = [
    {
        "key": "tl",
        "label": "TL",
        "negative": "TL üzerinde baskı",
        "positive": "TL'yi destekler",
    },
    {
        "key": "growth",
        "label": "Ekonomik büyüme",
        "negative": "büyümeyi baskılar",
        "positive": "büyümeyi destekler",
    },
    {
        "key": "inflation",
        "label": "Enflasyon",
        "negative": "enflasyon baskısını azaltır",
        "positive": "enflasyon baskısını artırır",
    },
    {
        "key": "interest_rate_pressure",
        "label": "Faiz baskısı",
        "negative": "faiz baskısını azaltır",
        "positive": "faiz baskısını artırır",
    },
    {
        "key": "market_confidence",
        "label": "Piyasa güveni",
        "negative": "güveni zayıflatır",
        "positive": "güveni artırır",
    },
]

INDICATOR_KEYS = [indicator["key"] for indicator in INDICATORS]

MACRO_SIGNAL_TERMS = {
    "tl",
    "turk lirasi",
    "dolar",
    "euro",
    "kur",
    "enflasyon",
    "faiz",
    "merkez bankasi",
    "tcmb",
    "ekonomi",
    "buyume",
    "gsyh",
    "piyasa",
    "borsa",
    "bist",
    "altin",
    "petrol",
    "dogalgaz",
    "vergi",
    "butce",
    "asgari ucret",
    "zam",
    "ihracat",
    "ithalat",
    "yatirim",
    "kredi",
    "mevduat",
    "seçim",
    "secim",
    "meclis",
    "bakan",
    "cumhurbaskani",
    "yasa",
    "kanun",
    "karar",
    "regulasyon",
    "iran",
    "israil",
    "gazze",
    "hurmuz",
    "ukrayna",
    "rusya",
}

INDEX_PAGE_TITLES = {
    "gundem",
    "turkiye",
    "ekonomi",
    "dunya",
    "spor",
    "saglik",
    "teknoloji",
    "son dakika",
}

SURFACE_EXACT_TERMS = {
    "kadir inanir",
    "fifa dunya kupasi",
    "dunya kupasi",
    "transfer",
    "mac",
    "gol",
    "magazin",
    "sinema",
    "dizi",
    "festival",
}

SURFACE_CONTEXT_TERMS = {
    "vefat",
    "bas sagligi",
    "sanat camiasi",
    "usta oyuncu",
    "unlu oyuncu",
    "cenaze",
    "yasamini yitirdi",
    "olumuyle yasa bogdu",
}


def apply_macro_impact_analysis(payloads: list[dict[str, Any]]) -> None:
    for payload in payloads:
        quality = evaluate_content_quality(payload)
        payload["content_quality"] = quality
        payload["impact_analysis"] = analyze_macro_impact(payload, quality)


def evaluate_content_quality(payload: dict[str, Any]) -> dict[str, Any]:
    article = payload.get("article", {})
    analysis = payload.get("analysis", {})
    title = str(article.get("title", ""))
    summary = str(article.get("summary", ""))
    content_text = str(article.get("content_text", ""))
    text = normalized_text(
        " ".join(
            [
                title,
                summary,
                content_text,
                " ".join(str(item) for item in analysis.get("keywords", [])),
                " ".join(str(item) for item in analysis.get("topics", [])),
            ]
        )
    )
    title_text = normalized_text(title)
    category = str(analysis.get("category", "diger"))
    risk_flags = set(str(flag) for flag in analysis.get("risk_flags", []))

    macro_signals = matched_terms(text, MACRO_SIGNAL_TERMS)
    surface_signals = matched_terms(text, SURFACE_EXACT_TERMS)
    surface_context = matched_terms(text, SURFACE_CONTEXT_TERMS)

    if not content_text.strip() and (title_text in INDEX_PAGE_TITLES or "sayfamizda" in text):
        return quality_result(
            relevance_score=5,
            excluded=True,
            reason="Kategori/landing sayfası gibi göründüğü için makro etki hesabına alınmadı.",
            macro_signals=macro_signals,
            surface_signals=surface_signals + surface_context,
        )

    if "kadir inanir" in surface_signals or (surface_signals and surface_context):
        return quality_result(
            relevance_score=8,
            excluded=True,
            reason="Magazin/kültür ağırlıklı yüzeysel haber; TL, büyüme veya enflasyon etkisi hesaplanmadı.",
            macro_signals=macro_signals,
            surface_signals=surface_signals + surface_context,
        )

    macro_category = category in MACRO_CATEGORIES
    macro_risk = bool(risk_flags & MACRO_RISK_FLAGS)
    macro_signal = bool(macro_signals)
    if not (macro_category or macro_risk or macro_signal):
        return quality_result(
            relevance_score=15,
            excluded=True,
            reason="Ekonomi/siyaset veya makro risk sinyali taşımadığı için hesap dışı bırakıldı.",
            macro_signals=macro_signals,
            surface_signals=surface_signals + surface_context,
        )

    score = 45
    score += min(30, len(macro_signals) * 6)
    score += 10 if macro_category else 0
    score += 8 if macro_risk else 0
    if analysis.get("importance") in {"high", "critical"}:
        score += 7

    return quality_result(
        relevance_score=min(100, score),
        excluded=False,
        reason="Makro etki analizi için yeterli ekonomi/siyaset sinyali var.",
        macro_signals=macro_signals[:10],
        surface_signals=surface_signals + surface_context,
    )


def analyze_macro_impact(payload: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    if quality.get("excluded_from_macro_impact"):
        return {
            "eligible": False,
            "excluded_reason": quality.get("reason", ""),
            "indicator_scores": [],
            "net_abs_impact": 0,
            "dominant_indicator": None,
            "summary": "Bu haber yüzeysel veya makro göstergeyle zayıf ilişkili olduğu için etki hesabına alınmadı.",
            "confidence": 0.0,
            "method": "macro_rules_v1",
        }

    text = normalized_text(text_for_payload(payload))
    scores = {key: 0 for key in INDICATOR_KEYS}
    reasons: list[str] = []

    def add(term_group: tuple[str, ...], deltas: dict[str, int], note: str) -> None:
        if any(contains_term(text, term) for term in term_group):
            for key, value in deltas.items():
                scores[key] += value
            reasons.append(note)

    add(
        ("enflasyon", "zam", "fiyat artisi", "hayat pahaliligi"),
        {"tl": -2, "growth": -1, "inflation": 3, "interest_rate_pressure": 2, "market_confidence": -1},
        "Enflasyon/fiyat baskısı makro göstergelerde negatif sinyal üretiyor.",
    )
    add(
        ("faiz artisi", "siki para", "parasal sikilasma"),
        {"tl": 2, "growth": -2, "inflation": -2, "interest_rate_pressure": 3, "market_confidence": 1},
        "Sıkı para politikası TL'yi desteklerken büyümeyi baskılayabilir.",
    )
    add(
        ("faiz indirimi", "faiz dususu", "gevseme"),
        {"tl": -2, "growth": 2, "inflation": 2, "interest_rate_pressure": -2, "market_confidence": -1},
        "Faiz indirimi büyümeyi destekleyebilir ama TL/enflasyon tarafında baskı yaratabilir.",
    )
    add(
        ("faiz", "merkez bankasi", "tcmb"),
        {"tl": 1, "growth": -1, "inflation": -1, "interest_rate_pressure": 1, "market_confidence": 1},
        "Merkez Bankası/faiz başlığı piyasanın ana fiyatlama alanlarından biri.",
    )
    add(
        ("dolar", "euro", "kur", "turk lirasi", "tl"),
        {"tl": -2, "growth": -1, "inflation": 2, "interest_rate_pressure": 1, "market_confidence": -2},
        "Kur başlığı TL ve enflasyon beklentileriyle doğrudan ilişkili.",
    )
    add(
        ("borsa", "bist", "hisse", "piyasa"),
        {"tl": 0, "growth": 1, "inflation": 0, "interest_rate_pressure": 0, "market_confidence": 2},
        "Piyasa/BIST görünürlüğü güven ve risk iştahı için sinyal olabilir.",
    )
    add(
        ("ihracat", "yatirim", "uretim", "tesvik", "istihdam"),
        {"tl": 1, "growth": 3, "inflation": 0, "interest_rate_pressure": 0, "market_confidence": 2},
        "Yatırım, üretim veya ihracat haberleri büyüme tarafında destekleyici okunur.",
    )
    add(
        ("vergi", "butce", "kamu harcamasi", "asgari ucret", "emekli maasi"),
        {"tl": -1, "growth": 1, "inflation": 2, "interest_rate_pressure": 1, "market_confidence": -1},
        "Bütçe/ücret/vergi başlıkları iç talep ve fiyat baskısını etkileyebilir.",
    )
    add(
        ("secim", "seçim", "meclis", "parti", "protesto", "miting"),
        {"tl": -1, "growth": -1, "inflation": 0, "interest_rate_pressure": 0, "market_confidence": -2},
        "Siyasi belirsizlik piyasa güveni ve TL tarafında baskı oluşturabilir.",
    )
    add(
        ("yasa", "kanun", "duzenleme", "regulasyon", "karar"),
        {"tl": 0, "growth": 1, "inflation": 0, "interest_rate_pressure": 0, "market_confidence": 1},
        "Politika/düzenleme haberi piyasa beklentilerini değiştirebilir.",
    )
    add(
        ("iran", "israil", "gazze", "hurmuz", "petrol", "dogalgaz", "ukrayna", "rusya", "savas", "catisma"),
        {"tl": -2, "growth": -1, "inflation": 2, "interest_rate_pressure": 1, "market_confidence": -2},
        "Jeopolitik/enerji riski TL, enflasyon ve piyasa güveni üzerinde baskı yaratır.",
    )

    if not reasons:
        reasons.append("Makro kategori sinyali var ancak haber metninde güçlü yön belirten kelime az.")

    clamped = {key: clamp_score(value) for key, value in scores.items()}
    indicator_scores = [
        {
            "key": indicator["key"],
            "label": indicator["label"],
            "score": clamped[indicator["key"]],
            "interpretation": indicator["positive"] if clamped[indicator["key"]] > 0 else indicator["negative"]
            if clamped[indicator["key"]] < 0
            else "belirgin yön yok",
        }
        for indicator in INDICATORS
    ]
    dominant = max(indicator_scores, key=lambda row: abs(int(row["score"])))
    net_abs = sum(abs(int(row["score"])) for row in indicator_scores)
    confidence = min(0.88, 0.42 + len(reasons) * 0.07 + float(quality.get("macro_relevance_score", 0)) / 250)

    return {
        "eligible": True,
        "excluded_reason": None,
        "indicator_scores": indicator_scores,
        "net_abs_impact": net_abs,
        "dominant_indicator": dominant if abs(int(dominant["score"])) else None,
        "summary": build_impact_summary(indicator_scores, reasons),
        "rationale": reasons[:4],
        "confidence": round(confidence, 2),
        "method": "macro_rules_v1",
    }


def build_macro_impact_report(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    if payloads and "impact_analysis" not in payloads[0]:
        apply_macro_impact_analysis(payloads)

    eligible = [payload for payload in payloads if payload.get("impact_analysis", {}).get("eligible")]
    excluded = [payload for payload in payloads if not payload.get("impact_analysis", {}).get("eligible")]
    report = {
        "impact_version": "macro-impact-v1",
        "eligible_documents": len(eligible),
        "excluded_documents": len(excluded),
        "indicator_summary": summarize_indicators(eligible),
        "category_impact": summarize_category_impact(eligible),
        "top_impact_articles": build_top_impact_articles(eligible),
        "excluded_examples": build_excluded_examples(excluded),
        "trend_report": build_trend_report(eligible),
        "analysis_provider": "fallback_rules",
    }
    report["major_breaks"] = build_major_breaks(report, eligible)
    maybe_enrich_breaks_with_openai(report)
    return report


def summarize_indicators(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for indicator in INDICATORS:
        scores = [
            int(row.get("score", 0))
            for payload in payloads
            for row in payload.get("impact_analysis", {}).get("indicator_scores", [])
            if row.get("key") == indicator["key"]
        ]
        if not scores:
            average = 0.0
            abs_average = 0.0
        else:
            average = round(sum(scores) / len(scores), 2)
            abs_average = round(sum(abs(score) for score in scores) / len(scores), 2)
        rows.append(
            {
                "key": indicator["key"],
                "label": indicator["label"],
                "average_score": average,
                "absolute_average": abs_average,
                "count": len(scores),
                "interpretation": indicator["positive"] if average > 0 else indicator["negative"]
                if average < 0
                else "belirgin yön yok",
            }
        )
    return rows


def summarize_category_impact(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for payload in payloads:
        category = str(payload.get("analysis", {}).get("category", "diger"))
        grouped[category].append(int(payload.get("impact_analysis", {}).get("net_abs_impact", 0)))
    return [
        {
            "category": category,
            "count": len(values),
            "average_abs_impact": round(sum(values) / len(values), 2) if values else 0,
        }
        for category, values in sorted(grouped.items(), key=lambda item: (-sum(item[1]), item[0]))
    ]


def build_top_impact_articles(payloads: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    ranked = sorted(
        payloads,
        key=lambda payload: (
            -int(payload.get("impact_analysis", {}).get("net_abs_impact", 0)),
            str(payload.get("article", {}).get("title", "")),
        ),
    )
    rows = []
    for payload in ranked[:limit]:
        analysis = payload.get("analysis", {})
        article = payload.get("article", {})
        impact = payload.get("impact_analysis", {})
        rows.append(
            {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": payload.get("source", {}).get("key", "unknown"),
                "category": analysis.get("category", "diger"),
                "published_at": article.get("published_at") or payload.get("pipeline", {}).get("collected_at"),
                "net_abs_impact": impact.get("net_abs_impact", 0),
                "dominant_indicator": impact.get("dominant_indicator"),
                "indicator_scores": impact.get("indicator_scores", []),
                "summary": impact.get("summary", ""),
                "confidence": impact.get("confidence", 0),
            }
        )
    return rows


def build_excluded_examples(payloads: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    rows = []
    for payload in payloads[:limit]:
        rows.append(
            {
                "title": payload.get("article", {}).get("title", ""),
                "source": payload.get("source", {}).get("key", "unknown"),
                "category": payload.get("analysis", {}).get("category", "diger"),
                "reason": payload.get("impact_analysis", {}).get("excluded_reason")
                or payload.get("content_quality", {}).get("reason", ""),
            }
        )
    return rows


def build_trend_report(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    if not payloads:
        return {
            "trend_version": "macro-trends-v1",
            "bucket_granularity": "day",
            "series": [],
            "indicator_series": [],
            "top_trends": [],
            "breakpoints": [],
        }

    buckets = sorted({bucket_for_payload(payload) for payload in payloads})
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    indicator_scores: dict[tuple[str, str], list[int]] = defaultdict(list)

    for payload in payloads:
        bucket = bucket_for_payload(payload)
        analysis = payload.get("analysis", {})
        category = str(analysis.get("category", "diger"))
        counts[(bucket, "category", category)] += 1
        for topic in analysis.get("topics", [])[:6]:
            counts[(bucket, "topic", str(topic))] += 1
        for signal in payload.get("content_quality", {}).get("macro_signals", [])[:6]:
            counts[(bucket, "signal", str(signal))] += 1
        for score in payload.get("impact_analysis", {}).get("indicator_scores", []):
            indicator_scores[(bucket, str(score.get("key")))].append(int(score.get("score", 0)))

    max_by_key: dict[tuple[str, str], int] = defaultdict(int)
    for (_, kind, key), count in counts.items():
        max_by_key[(kind, key)] = max(max_by_key[(kind, key)], count)

    series = [
        {
            "bucket": bucket,
            "kind": kind,
            "key": key,
            "count": count,
            "trend_index": round(count / max(max_by_key[(kind, key)], 1) * 100),
        }
        for (bucket, kind, key), count in sorted(counts.items())
    ]

    indicator_series = []
    for (bucket, key), values in sorted(indicator_scores.items()):
        average = round(sum(values) / len(values), 2)
        indicator_series.append(
            {
                "bucket": bucket,
                "indicator": key,
                "average_score": average,
                "absolute_pressure": round(sum(abs(value) for value in values) / len(values), 2),
                "count": len(values),
            }
        )

    latest_bucket = buckets[-1]
    previous_bucket = buckets[-2] if len(buckets) > 1 else None
    latest_rows = [row for row in series if row["bucket"] == latest_bucket]
    top_trends = []
    for row in sorted(latest_rows, key=lambda item: (-int(item["count"]), item["kind"], item["key"]))[:12]:
        previous_count = 0
        if previous_bucket:
            previous_count = next(
                (
                    int(item["count"])
                    for item in series
                    if item["bucket"] == previous_bucket
                    and item["kind"] == row["kind"]
                    and item["key"] == row["key"]
                ),
                0,
            )
        top_trends.append({**row, "change": int(row["count"]) - previous_count})

    return {
        "trend_version": "macro-trends-v1",
        "bucket_granularity": "day",
        "buckets": buckets,
        "series": series,
        "indicator_series": indicator_series,
        "top_trends": top_trends,
        "breakpoints": detect_trend_breakpoints(series, buckets),
    }


def detect_trend_breakpoints(series: list[dict[str, Any]], buckets: list[str]) -> list[dict[str, Any]]:
    if not series:
        return []
    by_key: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
    for row in series:
        by_key[(str(row["kind"]), str(row["key"]))][str(row["bucket"])] = int(row["count"])

    breakpoints = []
    latest_bucket = buckets[-1]
    previous_bucket = buckets[-2] if len(buckets) > 1 else None
    for (kind, key), bucket_counts in by_key.items():
        latest = bucket_counts.get(latest_bucket, 0)
        previous = bucket_counts.get(previous_bucket, 0) if previous_bucket else 0
        change = latest - previous
        if change >= 2 or (not previous_bucket and latest >= 2):
            breakpoints.append(
                {
                    "bucket": latest_bucket,
                    "kind": kind,
                    "key": key,
                    "count": latest,
                    "change": change,
                    "analysis": trend_break_analysis(kind, key, latest, change, previous_bucket),
                    "analysis_method": "fallback_rules",
                }
            )
    return sorted(breakpoints, key=lambda row: (-int(row["change"]), row["kind"], row["key"]))[:8]


def build_major_breaks(report: dict[str, Any], payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trend_breaks = list(report.get("trend_report", {}).get("breakpoints", []))
    top_articles = report.get("top_impact_articles", [])
    for article in top_articles[:3]:
        dominant = article.get("dominant_indicator") or {}
        if not dominant:
            continue
        trend_breaks.append(
            {
                "bucket": article.get("published_at", ""),
                "kind": "article_impact",
                "key": dominant.get("label", "Makro etki"),
                "count": article.get("net_abs_impact", 0),
                "change": article.get("net_abs_impact", 0),
                "article_title": article.get("title", ""),
                "analysis": (
                    f"{article.get('title', 'Haber')} başlığı {dominant.get('label', 'makro gösterge')} tarafında "
                    f"{dominant.get('score', 0)} puanlık sinyal üretiyor. "
                    f"Bu haber tek başına karar değildir; aynı başlığın başka kaynaklarda tekrarı ve zaman içindeki yönü izlenmeli."
                ),
                "analysis_method": "fallback_rules",
            }
        )
    return sorted(trend_breaks, key=lambda row: -abs(int(row.get("change", 0))))[:10]


def maybe_enrich_breaks_with_openai(report: dict[str, Any]) -> None:
    if not os.getenv("OPENAI_API_KEY") or not report.get("major_breaks"):
        return
    try:
        from openai import OpenAI

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        client = OpenAI()
        prompt = {
            "task": "Türkçe haber trend kırılımları için 2-3 cümlelik kısa analiz yaz.",
            "rules": [
                "Abartılı kesinlik kullanma.",
                "Makro göstergeler için haber sinyali olarak yorumla.",
                "Sadece JSON döndür.",
            ],
            "breaks": report["major_breaks"][:6],
            "indicator_summary": report.get("indicator_summary", []),
        }
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Sadece geçerli JSON döndür. Şema: {\"analyses\":[{\"index\":0,\"analysis\":\"...\"}]}"},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        analyses = data.get("analyses", [])
        if isinstance(analyses, list):
            for row in analyses:
                index = int(row.get("index", -1))
                if 0 <= index < len(report["major_breaks"]) and row.get("analysis"):
                    report["major_breaks"][index]["analysis"] = str(row["analysis"])[:700]
                    report["major_breaks"][index]["analysis_method"] = f"openai:{model}"
            report["analysis_provider"] = f"openai:{model}"
    except Exception as exc:
        report["analysis_provider_error"] = f"{type(exc).__name__}: {exc}"


def trend_break_analysis(kind: str, key: str, count: int, change: int, previous_bucket: str | None) -> str:
    if previous_bucket:
        return (
            f"{key} başlığı son zaman kovasında {change} haber artışıyla öne çıktı. "
            f"Bu artış tek başına kesin sonuç değildir; aynı sinyal birkaç kaynakta sürerse trend kırılımı olarak izlenebilir."
        )
    return (
        f"{key} başlığı bu çalıştırmada {count} haberle yoğunlaştı. "
        f"Geçmiş koşular biriktikçe bu alan Google Trends benzeri şekilde artış/düşüş yönünü daha net gösterecek."
    )


def build_impact_summary(indicator_scores: list[dict[str, Any]], reasons: list[str]) -> str:
    strongest = sorted(indicator_scores, key=lambda row: -abs(int(row["score"])))[:2]
    parts = [f"{row['label']} {row['score']:+d}" for row in strongest if int(row["score"]) != 0]
    if not parts:
        return "Haber makro gündeme yakın ama göstergelerde belirgin yön üretmedi."
    return f"Öne çıkan etki: {', '.join(parts)}. {reasons[0]}"


def quality_result(
    relevance_score: int,
    excluded: bool,
    reason: str,
    macro_signals: list[str],
    surface_signals: list[str],
) -> dict[str, Any]:
    return {
        "macro_relevance_score": relevance_score,
        "excluded_from_macro_impact": excluded,
        "reason": reason,
        "macro_signals": macro_signals,
        "surface_signals": surface_signals,
    }


def text_for_payload(payload: dict[str, Any]) -> str:
    article = payload.get("article", {})
    analysis = payload.get("analysis", {})
    return " ".join(
        [
            str(article.get("title", "")),
            str(article.get("summary", "")),
            str(article.get("content_text", "")),
            " ".join(str(item) for item in analysis.get("keywords", [])),
            " ".join(str(item) for item in analysis.get("topics", [])),
            " ".join(str(item) for item in analysis.get("risk_flags", [])),
        ]
    )


def bucket_for_payload(payload: dict[str, Any]) -> str:
    article = payload.get("article", {})
    pipeline = payload.get("pipeline", {})
    value = article.get("published_at") or pipeline.get("collected_at") or ""
    parsed = parse_datetime(value)
    if parsed is None:
        return "unknown"
    return parsed.date().isoformat()


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(text.split(".")[0])
        except ValueError:
            return None


def normalized_text(value: str) -> str:
    text = value.casefold().replace("ı", "i")
    normalized = unicodedata.normalize("NFKD", text)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", without_marks)).strip()


def matched_terms(text: str, terms: set[str]) -> list[str]:
    return sorted(term for term in terms if contains_term(text, term))


def contains_term(text: str, term: str) -> bool:
    normalized_term = normalized_text(term)
    if not normalized_term:
        return False
    return f" {normalized_term} " in f" {text} "


def clamp_score(value: int) -> int:
    return max(-5, min(5, int(value)))
