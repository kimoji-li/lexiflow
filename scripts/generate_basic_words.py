#!/usr/bin/env python3
"""Build LexiFlow's compact 20,000-word base library from ECDICT."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path


WORD_RE = re.compile(r"^[a-z][a-z'-]{0,23}$")
TARGET_COUNT = 20_000
SPOKEN_COUNT = 4_000
POS_NAMES = {
    "n": "noun",
    "v": "verb",
    "adj": "adjective",
    "adv": "adverb",
    "prep": "preposition",
    "conj": "conjunction",
    "pron": "pronoun",
    "num": "number",
    "art": "article",
    "int": "interjection",
    "aux": "auxiliary",
}


def number(value: str) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def common_meaning(value: str) -> str:
    lines: list[str] = []
    normalized = value.replace("\\r", "").replace("\r", "").replace("\\n", "\n")
    for raw in normalized.splitlines():
        line = re.sub(r"\s+", " ", raw).strip(" ;")
        if "[" in line:
            line = line.split("[", 1)[0].strip(" ;")
        if not line or line.startswith("[") or re.fullmatch(r"[a-z]+\.", line.lower()):
            continue
        lines.append(line)
        if len(lines) == 3:
            break
    text = "；".join(lines)
    return text[:220].rstrip("；")


def dominant_pos(value: str, translation: str) -> str:
    choices: list[tuple[int, str]] = []
    for chunk in value.split("/"):
        name, _, rate = chunk.partition(":")
        score = number(rate) if rate else 1
        choices.append((score, POS_NAMES.get(name, name or "word")))
    if choices and choices[0][1] != "word":
        return max(choices)[1]
    match = re.match(r"([a-z]+)\.", translation.strip().lower())
    return POS_NAMES.get(match.group(1), match.group(1)) if match else "word"


def level_for(rank: int) -> str:
    if rank <= 1500:
        return "A1"
    if rank <= 3000:
        return "A2"
    if rank <= 5000:
        return "B1"
    if rank <= 7000:
        return "B2"
    if rank <= 16000:
        return "C1"
    return "C2"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: generate_basic_words.py /path/to/ecdict.csv")

    source = Path(sys.argv[1])
    project = Path(__file__).resolve().parents[1]
    output = project / "public" / "data" / "words-basic.json"
    notice = project / "public" / "data" / "NOTICE.txt"

    candidates: list[tuple[int, dict[str, str]]] = []
    with source.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            word = row["word"].strip()
            if word != word.lower() or not WORD_RE.fullmatch(word):
                continue
            if "0:" in row.get("exchange", ""):
                continue
            phonetic = row.get("phonetic", "").strip()
            meaning = common_meaning(row.get("translation", ""))
            if not phonetic or not meaning:
                continue
            modern_rank = number(row.get("frq", ""))
            historical_rank = number(row.get("bnc", ""))
            if modern_rank:
                score = modern_rank
            elif historical_rank:
                score = historical_rank + 20000
            else:
                continue
            candidates.append((score, row))

    candidates.sort(key=lambda item: (item[0], item[1]["word"]))
    selected = candidates[: TARGET_COUNT + 1000]

    entries: list[dict[str, object]] = []
    seen: set[str] = set()
    for _, row in selected:
        word = row["word"].strip()
        if word in seen:
            continue
        seen.add(word)
        rank = len(entries) + 1
        source_tags = row.get("tag", "").lower().split()
        tags: list[str] = []
        if rank <= SPOKEN_COUNT:
            tags.append("口语高频")
        if "ielts" in source_tags:
            tags.append("IELTS")
        entries.append(
            {
                "word": word,
                "ipa": f"/{row.get('phonetic', '').strip().strip('/')}/",
                "part": dominant_pos(row.get("pos", ""), row.get("translation", "")),
                "level": level_for(rank),
                "tags": tags,
                "meaning": common_meaning(row.get("translation", "")),
                "rank": rank,
                "basic": True,
            }
        )
        if len(entries) == TARGET_COUNT:
            break

    if len(entries) != TARGET_COUNT:
        raise SystemExit(f"Expected {TARGET_COUNT} entries, got {len(entries)}")

    output.write_text(json.dumps(entries, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    notice.write_text(
        "LexiFlow basic vocabulary data is derived from ECDICT.\n"
        "Source: https://github.com/skywind3000/ECDICT\n"
        "License: MIT License, Copyright (c) 2025 Linwei\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(entries)} entries to {output}")


if __name__ == "__main__":
    main()
