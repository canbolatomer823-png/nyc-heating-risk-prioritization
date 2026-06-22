from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from typing import Any, Protocol

from .models import AnalysisResult, RawNewsItem

CATEGORIES = [
    "siyaset",
    "ekonomi",
    "dunya",
    "teknoloji",
    "spor",
    "saglik",
    "kultur",
    "hukuk",
    "egitim",
    "diger",
]

KEYWORD_RULES = {
    "siyaset": [
        "cumhurbaşkanı",
        "meclis",
        "bakan",
        "parti",
        "seçim",
        "belediye",
        "chp",
        "ak parti",
        "mhp",
        "dem parti",
    ],
    "ekonomi": [
        "ekonomi",
        "enflasyon",
        "faiz",
        "merkez bankası",
        "dolar",
        "euro",
        "borsa",
        "piyasa",
        "altın",
        "kredi",
        "zam",
    ],
    "dunya": [
        "abd",
        "avrupa",
        "rusya",
        "ukrayna",
        "israil",
        "gazze",
        "nato",
        "bm",
        "almanya",
        "fransa",
    ],
    "teknoloji": [
        "teknoloji",
        "yapay zeka",
        "ai",
        "robot",
        "siber",
        "uydu",
        "telefon",
        "çip",
        "yazılım",
    ],
    "spor": [
        "spor",
        "futbol",
        "basketbol",
        "maç",
        "gol",
        "transfer",
        "galatasaray",
        "fenerbahçe",
        "beşiktaş",
    ],
    "saglik": [
        "sağlık",
        "hastane",
        "doktor",
        "aşı",
        "ilaç",
        "salgın",
        "hasta",
    ],
    "kultur": [
        "film",
        "müzik",
        "kitap",
        "festival",
        "sanat",
        "sergi",
        "sinema",
    ],
    "hukuk": [
        "mahkeme",
        "savcı",
        "dava",
        "anayasa",
        "hukuk",
        "tutuklama",
        "karar",
    ],
    "egitim": [
        "eğitim",
        "okul",
        "üniversite",
        "öğrenci",
        "öğretmen",
        "sınav",
        "yök",
    ],
}

EVENT_RULES = {
    "incident": ["deprem", "yangın", "sel", "kaza", "patlama", "saldırı", "çatışma"],
    "policy_decision": ["karar", "düzenleme", "kanun", "yasa", "genelge", "faiz kararı"],
    "statement": ["açıkladı", "açıklama", "konuştu", "duyurdu", "mesaj"],
    "market_update": ["borsa", "piyasa", "dolar", "euro", "altın", "petrol", "enflasyon"],
    "legal_case": ["mahkeme", "dava", "savcı", "tutuklama", "iddianame", "karar"],
    "sports_result": ["maç", "gol", "skor", "transfer", "şampiyon"],
    "technology_update": ["yapay zeka", "siber", "uydu", "yazılım", "çip", "robot"],
    "social_discussion": ["reddit", "yorum", "tartışma", "sosyal medya"],
}

RISK_RULES = {
    "public_safety": ["deprem", "yangın", "sel", "kaza", "patlama", "saldırı", "zehirlenme"],
    "legal_process": ["tutuklama", "gözaltı", "mahkeme", "savcı", "dava", "iddianame"],
    "market_pressure": ["enflasyon", "faiz", "zam", "dolar", "euro", "borsa", "piyasa"],
    "political_tension": ["seçim", "parti", "meclis", "protesto", "miting"],
    "international_conflict": ["savaş", "çatışma", "israil", "gazze", "ukrayna", "rusya"],
}

HIGH_IMPORTANCE_TERMS = {
    "son dakika",
    "deprem",
    "yangın",
    "saldırı",
    "patlama",
    "gözaltı",
    "tutuklama",
    "faiz kararı",
    "enflasyon",
}

TURKISH_LOCATIONS = {
    "adana",
    "ankara",
    "antalya",
    "bursa",
    "diyarbakır",
    "edirne",
    "erzurum",
    "gaziantep",
    "istanbul",
    "izmir",
    "kayseri",
    "kocaeli",
    "konya",
    "malatya",
    "mersin",
    "muğla",
    "samsun",
    "trabzon",
    "türkiye",
    "van",
}

LOCATION_DISPLAY = {
    "istanbul": "İstanbul",
    "izmir": "İzmir",
    "türkiye": "Türkiye",
}

COMMON_ENTITY_PREFIXES = {
    "son",
    "bugün",
    "yeni",
    "ilk",
    "son dakika",
}


class Analyzer(Protocol):
    def analyze(self, item: RawNewsItem) -> AnalysisResult:
        ...


class RuleBasedAnalyzer:
    def analyze(self, item: RawNewsItem) -> AnalysisResult:
        raw_text = f"{item.title} {item.summary} {item.content_text}"
        text = raw_text.lower()
        scores = {
            category: sum(1 for keyword in keywords if keyword in text)
            for category, keywords in KEYWORD_RULES.items()
        }
        category = max(scores, key=scores.get) if scores else "diger"
        if scores.get(category, 0) == 0:
            category = "diger"

        keywords = extract_keywords(text)
        entities = extract_entities(raw_text)
        geography = extract_geography(text)
        event_type = infer_event_type(text, category)
        risk_flags = extract_risk_flags(text)
        importance = infer_importance(text, risk_flags)
        topics = build_topics(category, event_type, keywords, geography, risk_flags)
        summary = item.summary or item.title
        confidence = min(0.95, 0.35 + scores.get(category, 0) * 0.12)

        return AnalysisResult(
            category=category,
            subcategory=event_type if event_type != "general" else category,
            sentiment="neutral",
            summary=summary[:500],
            keywords=keywords[:8],
            confidence=round(confidence, 2),
            analyzer="fallback_rules",
            model=None,
            topics=topics,
            entities=entities,
            event_type=event_type,
            geography=geography,
            importance=importance,
            risk_flags=risk_flags,
        )


class OpenAIAnalyzer:
    def __init__(self, model: str | None = None) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai is required. Run `pip install -r requirements.txt`.") from exc

        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = OpenAI()
        self.fallback = RuleBasedAnalyzer()

    def analyze(self, item: RawNewsItem) -> AnalysisResult:
        prompt = {
            "title": item.title,
            "summary": item.summary,
            "content_text": item.content_text[:4000],
            "allowed_categories": CATEGORIES,
            "required_json_keys": [
                "category",
                "subcategory",
                "sentiment",
                "summary",
                "keywords",
                "topics",
                "entities",
                "event_type",
                "geography",
                "importance",
                "risk_flags",
                "language",
                "confidence",
            ],
            "entities_shape": {
                "persons": ["kişi isimleri"],
                "organizations": ["kurum, şirket, parti, bakanlık"],
                "locations": ["şehir, ülke, bölge"],
            },
            "importance_values": ["low", "normal", "high", "critical"],
        }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Sen Türkçe haberleri sınıflandıran bir analiz servisinin parçasısın. "
                            "Sadece geçerli JSON döndür. Kategori allowed_categories içinden seçilmeli. "
                            "sentiment positive, neutral veya negative olmalı. confidence 0 ile 1 arasında sayı olmalı. "
                            "Haberi sadece temel kategoriye ayırma; olay tipi, konu başlıkları, kişi/kurum/yer "
                            "varlıkları, önem seviyesi ve risk/pattern sinyalleri de çıkar."
                        ),
                    },
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            return coerce_analysis(data, analyzer="openai", model=self.model)
        except Exception as exc:
            fallback = self.fallback.analyze(item)
            fallback_data = asdict(fallback)
            fallback_data["error"] = f"openai_failed: {type(exc).__name__}: {exc}"
            return AnalysisResult(**fallback_data)


def get_analyzer(name: str) -> Analyzer:
    if name == "fallback":
        return RuleBasedAnalyzer()
    if name == "openai":
        return OpenAIAnalyzer()
    if name == "auto":
        if os.getenv("OPENAI_API_KEY"):
            return OpenAIAnalyzer()
        return RuleBasedAnalyzer()
    raise ValueError(f"Unknown analyzer: {name}")


def coerce_analysis(data: dict, analyzer: str, model: str | None) -> AnalysisResult:
    category = str(data.get("category", "diger")).lower()
    if category not in CATEGORIES:
        category = "diger"

    sentiment = str(data.get("sentiment", "neutral")).lower()
    if sentiment not in {"positive", "neutral", "negative"}:
        sentiment = "neutral"

    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5

    return AnalysisResult(
        category=category,
        subcategory=str(data.get("subcategory", category))[:80],
        sentiment=sentiment,
        summary=str(data.get("summary", ""))[:800],
        keywords=coerce_str_list(data.get("keywords"), limit=10, item_limit=50),
        confidence=max(0.0, min(1.0, round(confidence, 2))),
        analyzer=analyzer,
        model=model,
        topics=coerce_str_list(data.get("topics"), limit=12, item_limit=80),
        entities=coerce_entities(data.get("entities")),
        event_type=str(data.get("event_type", "general"))[:80],
        geography=coerce_str_list(data.get("geography"), limit=10, item_limit=80),
        importance=coerce_importance(data.get("importance")),
        risk_flags=coerce_str_list(data.get("risk_flags"), limit=12, item_limit=80),
        language=str(data.get("language", "tr"))[:12],
    )


def coerce_str_list(value: Any, limit: int, item_limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:item_limit] for item in value[:limit] if str(item).strip()]


def coerce_entities(value: Any) -> dict[str, list[str]]:
    empty = {"persons": [], "organizations": [], "locations": []}
    if not isinstance(value, dict):
        return empty
    return {
        "persons": coerce_str_list(value.get("persons"), limit=12, item_limit=80),
        "organizations": coerce_str_list(value.get("organizations"), limit=12, item_limit=100),
        "locations": coerce_str_list(value.get("locations"), limit=12, item_limit=80),
    }


def coerce_importance(value: Any) -> str:
    importance = str(value or "normal").lower()
    if importance not in {"low", "normal", "high", "critical"}:
        return "normal"
    return importance


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-ZğüşöçıİĞÜŞÖÇ]{4,}", text.lower())
    stop_words = {
        "olan",
        "için",
        "daha",
        "sonra",
        "göre",
        "kadar",
        "haber",
        "olarak",
        "ancak",
        "ile",
        "bir",
        "çok",
        "son",
        "dakika",
        "dedi",
        "gibi",
        "var",
    }
    counts: dict[str, int] = {}
    for word in words:
        if word not in stop_words:
            counts[word] = counts.get(word, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def extract_entities(text: str) -> dict[str, list[str]]:
    candidates = re.findall(
        r"\b[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü.-]+(?:\s+[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü.-]+){0,4}",
        text,
    )
    entities = {"persons": [], "organizations": [], "locations": []}
    for candidate in candidates:
        cleaned = " ".join(candidate.split()).strip(" .,-")
        if len(cleaned) < 3:
            continue
        lowered = cleaned.lower()
        if any(lowered.startswith(prefix) for prefix in COMMON_ENTITY_PREFIXES):
            continue

        bucket = classify_entity(cleaned)
        if cleaned not in entities[bucket]:
            entities[bucket].append(cleaned)

    return {key: values[:10] for key, values in entities.items()}


def classify_entity(entity: str) -> str:
    lowered = entity.lower()
    if lowered in TURKISH_LOCATIONS:
        return "locations"
    if any(location in lowered.split() for location in TURKISH_LOCATIONS):
        return "locations"

    organization_markers = [
        "bakanlığı",
        "bankası",
        "partisi",
        "belediyesi",
        "üniversitesi",
        "başkanlığı",
        "kurulu",
        "meclisi",
        "mahkemesi",
        "holding",
        "a.ş",
    ]
    if any(marker in lowered for marker in organization_markers):
        return "organizations"
    if entity.isupper() and 2 <= len(entity) <= 8:
        return "organizations"
    if len(entity.split()) == 1:
        return "organizations"
    return "persons"


def extract_geography(text: str) -> list[str]:
    locations = []
    for location in sorted(TURKISH_LOCATIONS):
        if re.search(rf"\b{re.escape(location)}\b", text):
            locations.append(LOCATION_DISPLAY.get(location, location.title()))
    return locations[:10]


def infer_event_type(text: str, category: str) -> str:
    event_scores = {
        event_type: sum(1 for keyword in keywords if keyword in text)
        for event_type, keywords in EVENT_RULES.items()
    }
    event_type = max(event_scores, key=event_scores.get)
    if event_scores[event_type] > 0:
        return event_type
    if category == "diger":
        return "general"
    return f"{category}_news"


def extract_risk_flags(text: str) -> list[str]:
    flags = []
    for flag, keywords in RISK_RULES.items():
        if any(keyword in text for keyword in keywords):
            flags.append(flag)
    return flags


def infer_importance(text: str, risk_flags: list[str]) -> str:
    if "son dakika" in text or len(risk_flags) >= 3:
        return "critical"
    if risk_flags or any(term in text for term in HIGH_IMPORTANCE_TERMS):
        return "high"
    return "normal"


def build_topics(
    category: str,
    event_type: str,
    keywords: list[str],
    geography: list[str],
    risk_flags: list[str],
) -> list[str]:
    topics = [category, event_type]
    topics.extend(keywords[:5])
    topics.extend(location.lower() for location in geography[:3])
    topics.extend(risk_flags[:3])

    deduped = []
    for topic in topics:
        if topic and topic not in deduped:
            deduped.append(topic)
    return deduped[:12]
