from __future__ import annotations

import json
from pathlib import Path

from .models import NewsSource


def load_sources(path: str | Path) -> list[NewsSource]:
    source_path = Path(path)
    data = json.loads(source_path.read_text(encoding="utf-8"))
    sources = [NewsSource(**item) for item in data]
    return [source for source in sources if source.enabled]
