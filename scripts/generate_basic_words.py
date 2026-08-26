#!/usr/bin/env python3
"""Build LexiFlow's compact 25,000-word library from ECDICT and OEWN."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import wn


WORD_RE = re.compile(r"^[a-z][a-z'-]{0,23}$")
TARGET_COUNT = 25_000
SPOKEN_COUNT = 4_000
ENRICH_START = 2_000
ENRICH_END = 10_000
POS_NAMES = {
    "n": "noun",
    "v": "verb",
    "vt": "verb",
    "vi": "verb",
    "a": "adjective",
    "s": "adjective",
    "adj": "adjective",
    "r": "adverb",
    "adv": "adverb",
    "prep": "preposition",
    "conj": "conjunction",
    "pron": "pronoun",
    "num": "number",
    "art": "article",
    "int": "interjection",
    "interj": "interjection",
    "aux": "auxiliary",
}
WN_POS = {
    "noun": ("n",),
    "verb": ("v",),
    "adjective": ("a", "s"),
    "adverb": ("r",),
}
CLAUSE_START_RE = re.compile(
    r"^(?:i|you|he|she|it|we|they|there|this|that|these|those|someone|somebody|people)\b",
    re.IGNORECASE,
)
CLAUSE_VERB_RE = re.compile(
    r"\b(?:am|is|are|was|were|be|been|being|has|have|had|do|does|did|can|could|may|might|must|shall|should|will|would)\b",
    re.IGNORECASE,
)
SPECIAL_EXAMPLES = {
    "via": "I sent it via email.",
    "besides": "There's no one here besides us.",
    "versus": "It's quality versus quantity.",
    "re": "I'm calling re your last email.",
    "amid": "We found a quiet spot amid the crowd.",
    "till": "I'll wait till tomorrow.",
    "amongst": "He felt relaxed amongst friends.",
    "unto": "Do unto others as you would have them do unto you.",
    "amidst": "She stayed calm amidst the confusion.",
    "whereas": "I like tea, whereas he prefers coffee.",
    "nonetheless": "It was difficult; nonetheless, we finished on time.",
    "albeit": "The room was small, albeit comfortable.",
    "lest": "I wrote it down lest I forget.",
    "yours": "Is this yours?",
    "hers": "The blue jacket is hers.",
    "ours": "This table is ours.",
    "whoever": "Invite whoever you like.",
    "theirs": "The choice is theirs.",
    "whatsoever": "I have no doubt whatsoever.",
    "oneself": "It's important to be honest with oneself.",
    "thou": "Thou shalt not steal.",
    "thy": "Love thy neighbor.",
    "thee": "I give this to thee.",
    "whichever": "Choose whichever you prefer.",
    "uh": "Uh, I'm not sure.",
    "heck": "What the heck happened?",
    "um": "Um, can I ask you something?",
    "whoa": "Whoa, slow down!",
    "ooh": "Ooh, that looks good!",
    "aw": "Aw, that's so sweet!",
    "ah": "Ah, now I understand.",
    "wow": "Wow, that's amazing!",
    "huh": "Huh, that's strange.",
    "ha": "Ha, I knew it!",
    "goodbye": "Goodbye, see you tomorrow.",
    "gosh": "Gosh, that was close!",
    "alas": "Alas, it was too late.",
    "eh": "It's pretty good, eh?",
    "amen": "Amen to that.",
    "aha": "Aha, now I understand.",
    "ta": "Ta, that's very kind of you.",
    "sitcom": "We watched a sitcom after dinner.",
    "ye": "Hear ye, hear ye!",
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


def dominant_pos(value: str, translation: str, definition: str = "") -> str:
    choices: list[tuple[int, str]] = []
    for chunk in value.split("/"):
        name, _, rate = chunk.partition(":")
        score = number(rate) if rate else 1
        choices.append((score, POS_NAMES.get(name, name or "word")))
    if choices and choices[0][1] != "word":
        return max(choices)[1]
    match = re.match(r"([a-z]+)\.", translation.strip().lower())
    if match:
        return POS_NAMES.get(match.group(1), match.group(1))
    definition_match = re.match(r"([a-z]+)\.?\s+", definition.strip().lower())
    return POS_NAMES.get(definition_match.group(1), definition_match.group(1)) if definition_match else "word"


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


def normalized_gloss(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def definition_lines(value: str, part: str) -> list[str]:
    markers = {
        "noun": {"n"},
        "verb": {"v"},
        "adjective": {"a", "s"},
        "adverb": {"r"},
    }.get(part, set())
    results: list[str] = []
    normalized = value.replace("\\r", "").replace("\\n", "\n")
    for raw in normalized.splitlines():
        match = re.match(r"^([a-z]+)\.?\s+(.+)$", raw.strip(), re.IGNORECASE)
        if match and match.group(1).lower() in markers:
            results.append(match.group(2).strip())
    return results


def word_forms(word: str, exchange: str) -> set[str]:
    forms = {word}
    for chunk in exchange.split("/"):
        _, _, value = chunk.partition(":")
        forms.update(item.strip().lower() for item in value.split(",") if item.strip())
    return forms


def primary_synsets(
    lexicon: wn.Wordnet,
    word: str,
    part: str,
    definition: str,
) -> list[wn.Synset]:
    synsets = [
        synset
        for pos in WN_POS.get(part, ())
        for synset in lexicon.synsets(word, pos=pos)
    ]
    if not synsets:
        return []

    by_gloss = {normalized_gloss(synset.definition()): synset for synset in synsets}
    matched = [
        by_gloss[key]
        for line in definition_lines(definition, part)
        if (key := normalized_gloss(line)) in by_gloss
    ]
    return matched[:1] or synsets[:1]


def conversational_examples(
    word: str,
    part: str,
    raw_pos: str,
    translation: str,
    exchange: str,
    synsets: list[wn.Synset],
) -> list[str]:
    results: list[str] = []

    def add(value: str) -> None:
        normalized = re.sub(r"\s+", " ", value).strip()
        if normalized and normalized not in results:
            results.append(normalized)

    if word in SPECIAL_EXAMPLES:
        add(SPECIAL_EXAMPLES[word])
    if part == "number":
        if word.endswith(("th", "st", "nd", "rd")):
            for value in (
                f"She finished {word} in the race.",
                f"This is my {word} visit.",
                f"He lives on the {word} floor.",
            ):
                add(value)
        else:
            for value in (
                f"We need {word} chairs for the event.",
                f"There were about {word} people outside.",
                f"I waited for {word} minutes.",
            ):
                add(value)
        return results[:3]

    forms = sorted(word_forms(word, exchange), key=len, reverse=True)
    form_pattern = re.compile(
        r"(?<![a-z])(?:" + "|".join(re.escape(form) for form in forms) + r")(?![a-z])",
        re.IGNORECASE,
    )
    source_examples = [
        re.sub(r"\s+", " ", example).strip(" .")
        for synset in synsets
        for example in synset.examples()
        if form_pattern.search(example)
    ]
    source_examples = [example for example in source_examples if 2 <= len(example.split()) <= 18]
    for example in source_examples:
        if CLAUSE_START_RE.match(example) or CLAUSE_VERB_RE.search(example):
            add(example[0].upper() + example[1:] + ("" if example.endswith((".", "!", "?")) else "."))
        elif part in {"noun", "adjective"}:
            add(f"We talked about {example}.")
        else:
            add(example[0].upper() + example[1:] + ("" if example.endswith((".", "!", "?")) else "."))
        if len(results) == 3:
            return results

    variant = sum(ord(character) for character in word) % 3
    is_transitive = bool(
        re.search(r"(?:^|/)vt(?::|/|$)", raw_pos.lower())
        or re.search(r"(?:^|\n)vt\.", translation.replace("\\n", "\n").lower())
    )
    verb_fallbacks = (
        [f"Can you {word} this?", f"Why did they {word} it?", f"We need to {word} this first."]
        if is_transitive
        else [f"Why did they {word}?", f"Do you think they will {word}?", f"We may have to {word} soon."]
    )
    fallbacks = {
        "noun": [
            f"Can we talk about the {word} for a minute?",
            f"What do you know about the {word}?",
            f"They mentioned the {word} earlier.",
        ],
        "verb": verb_fallbacks,
        "adjective": [
            f"They described it as {word}.",
            f"That seems {word} to me.",
            f"It may be the {word} option.",
        ],
        "adverb": [
            f"They handled the situation {word}.",
            f"Why did it happen {word}?",
            f"She explained it {word}.",
        ],
    }
    options = fallbacks.get(
        part,
        [
            f'I heard someone use "{word}" yesterday.',
            f'What does "{word}" mean here?',
            f'Can you use "{word}" in another sentence?',
        ],
    )
    for offset in range(3):
        add(options[(variant + offset) % len(options)])
    return results[:3]


def example_gloss(word: str, translation: str) -> str:
    meaning = common_meaning(translation)
    meaning = re.sub(
        r"(^|；)(?:n|v|vt|vi|a|adj|adv|prep|conj|pron|num|art|int|aux)\.\s*",
        r"\1",
        meaning,
        flags=re.IGNORECASE,
    )
    return f"本句中的 {word} 表示“{meaning}”。"


def adjective_relations(
    word: str,
    synsets: list[wn.Synset],
    allowed_words: set[str],
) -> tuple[list[str], list[str]]:
    synonyms: list[str] = []
    antonyms: list[str] = []
    for synset in synsets:
        synonyms.extend(lemma.replace("_", " ") for lemma in synset.lemmas())
        for sense in synset.senses():
            if sense.word().lemma().lower() != word:
                continue
            antonyms.extend(
                target.word().lemma().replace("_", " ")
                for target in sense.get_related("antonym")
            )

    def clean(values: list[str]) -> list[str]:
        unique: list[str] = []
        for value in values:
            normalized = value.lower().strip()
            if (
                normalized == word
                or normalized in unique
                or normalized not in allowed_words
                or not WORD_RE.fullmatch(normalized)
            ):
                continue
            unique.append(normalized)
        return unique[:3]

    return clean(synonyms), clean(antonyms)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: generate_basic_words.py /path/to/ecdict.csv")

    source = Path(sys.argv[1])
    project = Path(__file__).resolve().parents[1]
    output = project / "public" / "data" / "words-basic.json"
    notice = project / "public" / "data" / "NOTICE.txt"
    try:
        lexicon = wn.Wordnet("oewn:2024")
    except wn.Error as exc:
        raise SystemExit(
            "Open English WordNet 2024 is required. Run: "
            "python -c \"import wn; wn.download('oewn:2024')\""
        ) from exc

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
    allowed_words = {row["word"].strip() for _, row in selected}

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
        part = dominant_pos(
            row.get("pos", ""),
            row.get("translation", ""),
            row.get("definition", ""),
        )
        entry: dict[str, object] = {
            "word": word,
            "ipa": f"/{row.get('phonetic', '').strip().strip('/')}/",
            "part": part,
            "level": level_for(rank),
            "tags": tags,
            "meaning": common_meaning(row.get("translation", "")),
            "rank": rank,
            "basic": True,
        }
        if ENRICH_START <= rank <= ENRICH_END:
            synsets = primary_synsets(lexicon, word, part, row.get("definition", ""))
            examples = conversational_examples(
                word,
                part,
                row.get("pos", ""),
                row.get("translation", ""),
                row.get("exchange", ""),
                synsets,
            )
            gloss = example_gloss(word, row.get("translation", ""))
            entry["example"] = examples[0]
            entry["spoken"] = [{"line": line, "meaning": gloss} for line in examples]
            entry["enriched"] = True
            if part == "adjective":
                synonyms, antonyms = adjective_relations(word, synsets, allowed_words)
                entry["synonyms"] = synonyms
                entry["antonyms"] = antonyms
        entries.append(entry)
        if len(entries) == TARGET_COUNT:
            break

    if len(entries) != TARGET_COUNT:
        raise SystemExit(f"Expected {TARGET_COUNT} entries, got {len(entries)}")

    output.write_text(json.dumps(entries, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    notice.write_text(
        "LexiFlow basic vocabulary data is derived from ECDICT.\n"
        "Source: https://github.com/skywind3000/ECDICT\n"
        "License: MIT License, Copyright (c) 2025 Linwei\n\n"
        "LexiFlow examples and lexical relations are derived from Open English WordNet 2024.\n"
        "Source: https://en-word.net/\n"
        "License: Creative Commons Attribution 4.0 International\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(entries)} entries to {output}")


if __name__ == "__main__":
    main()

