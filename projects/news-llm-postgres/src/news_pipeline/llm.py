from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from typing import Protocol

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


class Analyzer(Protocol):
    def analyze(self, item: RawNewsItem) -> AnalysisResult:
        ...


class RuleBasedAnalyzer:
    def analyze(self, item: RawNewsItem) -> AnalysisResult:
        text = f"{item.title} {item.summary} {item.content_text}".lower()
        scores = {
            category: sum(1 for keyword in keywords if keyword in text)
            for category, keywords in KEYWORD_RULES.items()
        }
        category = max(scores, key=scores.get) if scores else "diger"
        if scores.get(category, 0) == 0:
            category = "diger"

        keywords = extract_keywords(text)
        summary = item.summary or item.title
        confidence = min(0.95, 0.35 + scores.get(category, 0) * 0.12)

        return AnalysisResult(
            category=category,
            subcategory=category,
            sentiment="neutral",
            summary=summary[:500],
            keywords=keywords[:8],
            confidence=round(confidence, 2),
            analyzer="fallback_rules",
            model=None,
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
                "confidence",
            ],
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
                            "sentiment positive, neutral veya negative olmalı. confidence 0 ile 1 arasında sayı olmalı."
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

    keywords = data.get("keywords", [])
    if not isinstance(keywords, list):
        keywords = []

    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5

    return AnalysisResult(
        category=category,
        subcategory=str(data.get("subcategory", category))[:80],
        sentiment=str(data.get("sentiment", "neutral")).lower(),
        summary=str(data.get("summary", ""))[:800],
        keywords=[str(keyword)[:50] for keyword in keywords[:10]],
        confidence=max(0.0, min(1.0, round(confidence, 2))),
        analyzer=analyzer,
        model=model,
    )


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
    }
    counts: dict[str, int] = {}
    for word in words:
        if word not in stop_words:
            counts[word] = counts.get(word, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]
