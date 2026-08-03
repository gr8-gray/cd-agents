"""Narration as a true node function — a direct call to cire's local Ollama.

The digest already renders every number; this only writes prose around the flags,
so the model can never introduce or alter a figure. keep_alive=0 unloads the model
after each call (frees VRAM alongside finance-watcher). Any failure returns a safe
deterministic fallback — a model hiccup must never break the daily digest.
"""
import re

import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "granite3.3:8b"  # small, fast, instruct (no reasoning traces); tune on the node
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _fallback(metrics, flags) -> str:
    if not flags:
        return "All monitored metrics are within the normal range versus the 7-day baseline."
    return "Flagged today: " + "; ".join(f.message for f in flags)


def narrate(metrics, flags, model: str = MODEL, timeout: int = 60) -> str:
    facts = ", ".join(f"{k}={v}" for k, v in metrics.items())
    flagtext = "; ".join(f.message for f in flags) if flags else "no anomalies"
    prompt = (
        "You are a terse analytics assistant for the Immortal Vibes store. In 2-4 "
        "sentences, tell the owner what today's numbers mean. Do not invent figures "
        "beyond those given; focus on what the flags imply and what to check.\n"
        f"Metrics: {facts}\nFlags: {flagtext}\n"
    )
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": 0,
                "options": {"temperature": 0.3},
            },
            timeout=timeout,
        )
        r.raise_for_status()
        txt = _THINK.sub("", r.json().get("response") or "").strip()
        return txt or _fallback(metrics, flags)
    except Exception:
        return _fallback(metrics, flags)
