#!/usr/bin/env python3
"""Select natural English–Chinese examples from Tatoeba for LexiFlow.

This is a one-time corpus preparation step. The generated compact JSON is
committed so ordinary GitHub Pages builds do not need to download Tatoeba's
large export files again.
"""

from __future__ import annotations

import bz2
import gzip
import heapq
import json
import re
import sys
import tarfile
from collections import defaultdict
from pathlib import Path


ENRICH_START = 1
ENRICH_END = 15_000
MAX_CANDIDATES = 12
TOKEN_RE = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)*")
URL_RE = re.compile(r"(?:https?://|www\.|\S+@\S+)", re.IGNORECASE)
BAD_TEXT_RE = re.compile(
    r"\b(?:tom|mary|esperanto|tatoeba|sami|mennad|layla|taninna|"
    r"fadil|boston|christmas|god|jesus)\b",
    re.IGNORECASE,
)
META_RE = re.compile(
    r"\b(?:how do you (?:say|spell)|what does .+ mean|use .+ in a sentence|"
    r"translate this|this sentence|this word)\b",
    re.IGNORECASE,
)
CORPUS_NOISE_RE = re.compile(
    r"\b(?:transcri(?:pt|ption|pci[oó]n)|subtitles?|captions?|sponsored|"
    r"copyright|all rights reserved|applause|laughter|inaudible)\b",
    re.IGNORECASE,
)
SPOKEN_MARKERS = {
    "i", "i'm", "i've", "i'll", "i'd", "me", "my", "we", "we're", "we've",
    "we'll", "our", "you", "you're", "you've", "you'll", "your", "he", "she",
    "they", "it", "this", "that", "can", "can't", "could", "couldn't", "will",
    "won't", "would", "wouldn't", "should", "shouldn't", "do", "don't", "did",
    "didn't", "let's", "please", "really", "just", "maybe", "probably",
}
TRADITIONAL_HINTS = set("們這個為與會說時來還裡見過學習體應該問題讓給從麼點對實現開關話長處總經認識")
SIMPLIFIED_HINTS = set("们这个为与会说时来还里见过学习体应该问题让给从么点对实现开关话长处总经认识")

try:
    from opencc import OpenCC

    CHINESE_CONVERTER = OpenCC("t2s")
except ImportError:
    CHINESE_CONVERTER = None


def simplified_chinese(text: str) -> str:
    return CHINESE_CONVERTER.convert(text) if CHINESE_CONVERTER else text


def load_target_words(project: Path) -> dict[str, str]:
    targets: dict[str, str] = {}
    chunk_dir = project / "public" / "data" / "words-basic"
    for chunk_path in sorted(chunk_dir.glob("[0-9][0-9].json")):
        for entry in json.loads(chunk_path.read_text(encoding="utf-8")):
            rank = int(entry.get("rank", 0))
            if ENRICH_START <= rank <= ENRICH_END:
                targets[str(entry["word"]).lower()] = str(entry.get("part", "word"))
    if len(targets) < 14_000:
        raise SystemExit(f"Expected about 15,000 target words, found {len(targets)}")
    return targets


def load_chinese(path: Path) -> dict[int, str]:
    sentences: dict[int, str] = {}
    with bz2.open(path, "rt", encoding="utf-8") as source:
        for raw in source:
            sentence_id, language, text = raw.rstrip("\n").split("\t", 2)
            if language == "cmn" and 2 <= len(text.strip()) <= 80:
                sentences[int(sentence_id)] = simplified_chinese(text.strip())
    return sentences


def link_member(archive: tarfile.TarFile):
    for member in archive:
        if member.isfile() and (member.name.endswith(".csv") or member.name.endswith(".tsv")):
            extracted = archive.extractfile(member)
            if extracted is not None:
                return extracted
    raise SystemExit("No link table found in links.tar.bz2")


def load_english_to_chinese(path: Path, chinese: dict[int, str]) -> dict[int, list[str]]:
    chinese_ids = set(chinese)
    direct: dict[int, list[str]] = defaultdict(list)
    with tarfile.open(path, "r:bz2") as archive:
        stream = link_member(archive)
        for raw in stream:
            fields = raw.decode("utf-8").rstrip("\n").replace("\t", " ").split()
            if len(fields) < 2 or not fields[0].isdigit() or not fields[1].isdigit():
                continue
            left, right = int(fields[0]), int(fields[1])
            if left in chinese_ids and right not in chinese_ids:
                english_id, translation = right, chinese[left]
            elif right in chinese_ids and left not in chinese_ids:
                english_id, translation = left, chinese[right]
            else:
                continue
            values = direct[english_id]
            if translation not in values and len(values) < 4:
                values.append(translation)

    # Tatoeba exposes indirect translations through one pivot sentence. They are
    # used only when an English sentence has no direct Mandarin link.
    indirect: dict[int, list[str]] = defaultdict(list)
    with tarfile.open(path, "r:bz2") as archive:
        stream = link_member(archive)
        for raw in stream:
            fields = raw.decode("utf-8").rstrip("\n").replace("\t", " ").split()
            if len(fields) < 2 or not fields[0].isdigit() or not fields[1].isdigit():
                continue
            left, right = int(fields[0]), int(fields[1])
            for pivot, candidate in ((left, right), (right, left)):
                if candidate in chinese_ids or candidate in direct or pivot not in direct:
                    continue
                values = indirect[candidate]
                for translation in direct[pivot]:
                    if translation not in values and len(values) < 3:
                        values.append(translation)
    return {**indirect, **direct}


def inflected_forms(word: str, part: str) -> set[str]:
    forms = {word}
    if not word.isalpha() or len(word) < 3:
        return forms
    vowel = lambda character: character in "aeiou"
    if part in {"noun", "verb"}:
        if word.endswith("y") and not vowel(word[-2]):
            forms.add(f"{word[:-1]}ies")
        elif word.endswith(("s", "x", "z", "ch", "sh")):
            forms.add(f"{word}es")
        else:
            forms.add(f"{word}s")
    if part == "verb":
        if word.endswith("e"):
            forms.update({f"{word}d", f"{word[:-1]}ing"})
        elif word.endswith("y") and not vowel(word[-2]):
            forms.update({f"{word[:-1]}ied", f"{word}ing"})
        else:
            forms.update({f"{word}ed", f"{word}ing"})
            if (
                len(word) <= 6
                and len(word) >= 3
                and not vowel(word[-1])
                and vowel(word[-2])
                and not vowel(word[-3])
                and word[-1] not in "wxy"
            ):
                forms.update({f"{word}{word[-1]}ed", f"{word}{word[-1]}ing"})
    if part == "adjective" and len(word) <= 8:
        if word.endswith("y"):
            forms.update({f"{word[:-1]}ier", f"{word[:-1]}iest"})
        elif word.endswith("e"):
            forms.update({f"{word}r", f"{word}st"})
        else:
            forms.update({f"{word}er", f"{word}est"})
    return forms


def target_form_index(targets: dict[str, str]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for word, part in targets.items():
        for form in inflected_forms(word, part):
            index[form].add(word)
    return index


def normalized_tokens(text: str) -> list[str]:
    result: list[str] = []
    for token in TOKEN_RE.findall(text.lower()):
        if token.endswith("'s") and len(token) > 3:
            token = token[:-2]
        result.append(token)
    return result


def english_score(text: str, tokens: list[str]) -> int | None:
    if not 4 <= len(tokens) <= 18 or len(text) > 125:
        return None
    if (
        URL_RE.search(text)
        or BAD_TEXT_RE.search(text)
        or META_RE.search(text)
        or CORPUS_NOISE_RE.search(text)
        or "..." in text
    ):
        return None
    if any(character in text for character in "{}[]<>|_"):
        return None
    if sum(character.isdigit() for character in text) > 3:
        return None
    if text.count('"') + text.count("“") + text.count("”") > 4:
        return None

    token_set = set(tokens)
    score = 100 - abs(len(tokens) - 9) * 2
    score += min(12, len(token_set & SPOKEN_MARKERS) * 3)
    score += 5 if "?" in text else 0
    score += 4 if re.search(r"\b[A-Za-z]+['’](?:t|re|ve|ll|d|m|s)\b", text) else 0
    score += 2 if text.rstrip().endswith((".", "?", "!")) else 0
    proper_names = re.findall(r"(?<![.!?]\s)\b[A-Z][a-z]{2,}\b", text[1:])
    score -= min(12, len(proper_names) * 4)
    score -= max(0, text.count(",") - 2) * 2
    score -= max(0, text.count(";") * 3)
    return score


def chinese_score(text: str) -> int:
    score = 50 - abs(len(text) - 16)
    score += sum(character in SIMPLIFIED_HINTS for character in text) * 2
    score -= sum(character in TRADITIONAL_HINTS for character in text) * 3
    score += 3 if text.rstrip().endswith(("。", "？", "！", "?", "!")) else 0
    return score


def choose_translation(values: list[str]) -> str | None:
    suitable = [
        value for value in values
        if 3 <= len(value) <= 70 and not URL_RE.search(value) and "�" not in value
    ]
    return max(suitable, key=chinese_score) if suitable else None


def select_examples(
    english_path: Path,
    targets: dict[str, str],
    translations: dict[int, list[str]],
) -> dict[str, list[dict[str, object]]]:
    heaps: dict[str, list[tuple[int, int, str, str]]] = defaultdict(list)
    form_index = target_form_index(targets)
    serial = 0
    with bz2.open(english_path, "rt", encoding="utf-8") as source:
        for raw in source:
            sentence_id, language, text = raw.rstrip("\n").split("\t", 2)
            numeric_id = int(sentence_id)
            if language != "eng" or numeric_id not in translations:
                continue
            tokens = normalized_tokens(text)
            matched = {
                target
                for token in tokens
                for target in form_index.get(token, ())
            }
            if not matched:
                continue
            score = english_score(text, tokens)
            translation = choose_translation(translations[numeric_id])
            if score is None or translation is None:
                continue
            for word in matched:
                serial += 1
                item = (score, serial, text.strip(), translation)
                heap = heaps[word]
                if len(heap) < MAX_CANDIDATES:
                    heapq.heappush(heap, item)
                elif item > heap[0]:
                    heapq.heapreplace(heap, item)

    selected: dict[str, list[dict[str, object]]] = {}
    for word, heap in heaps.items():
        choices = sorted(heap, reverse=True)
        accepted: list[dict[str, object]] = []
        accepted_token_sets: list[set[str]] = []
        for score, _, line, meaning in choices:
            token_set = set(normalized_tokens(line))
            if any(
                len(token_set & previous) / max(1, len(token_set | previous)) > 0.62
                for previous in accepted_token_sets
            ):
                continue
            accepted.append({"line": line, "meaning": meaning, "quality": score})
            accepted_token_sets.append(token_set)
            if len(accepted) == 3:
                break
        if accepted:
            selected[word] = accepted
    return selected


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: build_tatoeba_examples.py /path/to/tatoeba-exports")
    project = Path(__file__).resolve().parents[1]
    source_dir = Path(sys.argv[1]).resolve()
    targets = load_target_words(project)
    chinese = load_chinese(source_dir / "cmn_sentences.tsv.bz2")
    translations = load_english_to_chinese(source_dir / "links.tar.bz2", chinese)
    examples = select_examples(
        source_dir / "eng_sentences.tsv.bz2",
        targets,
        translations,
    )
    counts = {str(number): sum(len(value) >= number for value in examples.values()) for number in (1, 2, 3)}
    examples = {
        word: [
            {"line": str(item["line"]), "meaning": str(item["meaning"])}
            for item in items
        ]
        for word, items in examples.items()
    }
    output = project / "data" / "spoken_examples.json.gz"
    output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output, "wt", encoding="utf-8", compresslevel=9) as compressed:
        json.dump(
            {
                "source": "https://tatoeba.org/",
                "license": "CC BY 2.0 FR",
                "rankRange": [ENRICH_START, ENRICH_END],
                "coverage": counts,
                "examples": examples,
            },
            compressed,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    print(f"Wrote {len(examples):,} words to {output}; coverage={counts}")


if __name__ == "__main__":
    main()
