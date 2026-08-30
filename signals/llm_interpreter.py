from __future__ import annotations

import json
import os
from typing import Any


def interpret_setup(payload: dict[str, Any]) -> str:
    """Summarize confluence from numeric fields only. No price prediction."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            return _claude_summary(payload, api_key)
        except Exception:  # noqa: BLE001
            pass
    return _local_summary(payload)


def _local_summary(payload: dict[str, Any]) -> str:
    direction = "yükseliş" if payload.get("direction") == "up" else "düşüş"
    ratio = payload.get("nearest_ratio")
    score = payload.get("score")
    regime = payload.get("regime_label", "neutral")
    sr = payload.get("parts", {}).get("sr_overlap", 0)
    tl = payload.get("parts", {}).get("trendline", 0)
    bits = [
        f"Setup {direction} yönlü bir Fibonacci bacağının {ratio} geri çekilmesine yakın.",
        f"Confluence skoru {score:.1f}/100.",
    ]
    if sr >= 60:
        bits.append("Fiyat aynı zamanda geçmiş pivot kümelenmesinden gelen bir S/R bandıyla çakışıyor.")
    if tl >= 60:
        bits.append("Trend çizgisi dokunuşu skorlamayı destekliyor.")
    bits.append(f"Makro rejim etiketi: {regime}.")
    bits.append("Bu metin verilen sayısal alanların özetidir; yön tahmini değildir.")
    return " ".join(bits)


def _claude_summary(payload: dict[str, Any], api_key: str) -> str:
    import urllib.request

    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 220,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Aşağıdaki teknik veriye göre bu setup'ın confluence gerekçesini "
                    "2-3 cümlede özetle. Yeni bilgi uydurma, fiyat tahmini üretme, "
                    "sadece verilen veriyi yorumla.\n\n"
                    + json.dumps(payload, default=str)
                ),
            }
        ],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return data["content"][0]["text"]
