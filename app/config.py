"""Loads config/app.yaml, config/thresholds.yaml and translations/*.json.
Disabled regions, harbours and languages are filtered out here, so the rest of
the code only ever sees what is switched on."""
import json
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


@lru_cache
def load_thresholds() -> dict:
    return yaml.safe_load((ROOT / "config" / "thresholds.yaml").read_text(encoding="utf-8"))


@lru_cache
def load_app() -> dict:
    cfg = yaml.safe_load((ROOT / "config" / "app.yaml").read_text(encoding="utf-8"))
    langs = {k: v for k, v in cfg["languages"].items() if v.get("enabled")}
    regions = {}
    for rid, r in cfg["regions"].items():
        if not r.get("enabled"):
            continue
        r = dict(r)
        r["id"] = rid
        r["languages"] = [lang for lang in r["languages"] if lang in langs]
        # all_harbours (switched on or off) fixes which points are fetched together, so switching a
        # harbour off never changes the saved replay file and replay keeps working offline.
        r["all_harbours"] = list(r["harbours"])
        r["harbours"] = [h for h in r["harbours"] if h.get("enabled")]
        r["replay"] = [x for x in r.get("replay", []) if x in cfg.get("replays", {})]
        regions[rid] = r
    cfg["languages"] = langs
    cfg["regions"] = regions
    return cfg


@lru_cache
def load_translations(lang: str) -> dict:
    return json.loads((ROOT / "translations" / f"{lang}.json").read_text(encoding="utf-8"))


def region(region_id: str) -> dict:
    regions = load_app()["regions"]
    if region_id not in regions:
        raise ValueError(f"unknown or disabled region: {region_id}")
    return regions[region_id]


def harbour(region_id: str, harbour_id: str) -> dict:
    for h in region(region_id)["harbours"]:
        if h["id"] == harbour_id:
            return h
    raise ValueError(f"unknown or disabled harbour: {harbour_id}")
