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
OUTPUT_CHUNK_SIZE = 1_000
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
SPECIAL_EXAMPLES = {
    "via": ("I sent it via email.", "我是通过电子邮件把它发出去的。"),
    "besides": ("There's no one here besides us.", "这里除了我们之外没有别人。"),
    "versus": ("It's quality versus quantity.", "这是质量与数量之间的较量。"),
    "re": ("I'm calling re your last email.", "我打电话来是想谈谈你上一封邮件的事。"),
    "amid": ("We found a quiet spot amid the crowd.", "我们在人群中找到了一个安静的地方。"),
    "till": ("I'll wait till tomorrow.", "我会一直等到明天。"),
    "amongst": ("He felt relaxed amongst friends.", "和朋友们在一起时，他感到很放松。"),
    "unto": ("Do unto others as you would have them do unto you.", "你希望别人怎样待你，就要怎样待别人。"),
    "amidst": ("She stayed calm amidst the confusion.", "在混乱之中，她依然保持冷静。"),
    "whereas": ("I like tea, whereas he prefers coffee.", "我喜欢茶，而他更喜欢咖啡。"),
    "nonetheless": ("It was difficult; nonetheless, we finished on time.", "这件事很难，但我们还是按时完成了。"),
    "albeit": ("The room was small, albeit comfortable.", "这个房间虽然小，但很舒适。"),
    "lest": ("I wrote it down lest I forget.", "我把它写了下来，以免忘记。"),
    "yours": ("Is this yours?", "这是你的吗？"),
    "hers": ("The blue jacket is hers.", "那件蓝色夹克是她的。"),
    "ours": ("This table is ours.", "这张桌子是我们的。"),
    "whoever": ("Invite whoever you like.", "你想邀请谁就邀请谁。"),
    "theirs": ("The choice is theirs.", "选择权在他们手里。"),
    "whatsoever": ("I have no doubt whatsoever.", "我完全没有任何疑问。"),
    "oneself": ("It's important to be honest with oneself.", "对自己诚实很重要。"),
    "thou": ("Thou shalt not steal.", "你不可偷盗。"),
    "thy": ("Love thy neighbor.", "要爱你的邻人。"),
    "thee": ("I give this to thee.", "我把这个给你。"),
    "whichever": ("Choose whichever you prefer.", "你喜欢哪一个就选哪一个。"),
    "uh": ("Uh, I'm not sure.", "呃，我不太确定。"),
    "heck": ("What the heck happened?", "到底发生了什么？"),
    "um": ("Um, can I ask you something?", "嗯，我能问你一件事吗？"),
    "whoa": ("Whoa, slow down!", "哇，慢一点！"),
    "ooh": ("Ooh, that looks good!", "哦，那个看起来真不错！"),
    "aw": ("Aw, that's so sweet!", "啊，这也太暖心了！"),
    "ah": ("Ah, now I understand.", "啊，我现在明白了。"),
    "wow": ("Wow, that's amazing!", "哇，那太棒了！"),
    "huh": ("Huh, that's strange.", "咦，这很奇怪。"),
    "ha": ("Ha, I knew it!", "哈，我就知道！"),
    "goodbye": ("Goodbye, see you tomorrow.", "再见，明天见。"),
    "gosh": ("Gosh, that was close!", "天哪，刚才真险！"),
    "alas": ("Alas, it was too late.", "唉，已经太晚了。"),
    "eh": ("It's pretty good, eh?", "这个很不错，是吧？"),
    "amen": ("Amen to that.", "我完全赞同。"),
    "aha": ("Aha, now I understand.", "啊哈，我现在明白了。"),
    "ta": ("Ta, that's very kind of you.", "谢啦，你真是太好了。"),
    "sitcom": ("We watched a sitcom after dinner.", "晚饭后我们看了一部情景喜剧。"),
    "ye": ("Hear ye, hear ye!", "诸位，请听！"),
}
CHINESE_MEANING_OVERRIDES = {
    # ECDICT's first Chinese sense for this entry is the unrelated literal "听".
    "audition": "试镜",
}
DISPLAY_MEANING_OVERRIDES = {
    "audition": "试镜；试演；试音",
}
SPECIAL_EXAMPLE_SETS = {
    "audition": [
        ("I have an audition tomorrow.", "我明天有一场试镜。"),
        ("How did your audition go?", "你的试镜进行得怎么样？"),
        ("She nailed the audition.", "她在试镜中表现得非常出色。"),
    ],
    "supplemental": [
        ("The report includes supplemental information.", "这份报告包含补充信息。"),
        ("Is there any supplemental material?", "有补充材料吗？"),
        ("We need supplemental funding to finish the project.", "我们需要额外资金才能完成这个项目。"),
    ],
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


def primary_chinese_meaning(word: str, translation: str, part: str) -> str:
    """Pick one short Chinese sense matching the entry's dominant part of speech."""
    if word in CHINESE_MEANING_OVERRIDES:
        return CHINESE_MEANING_OVERRIDES[word]
    preferred_markers = {
        "noun": {"n"},
        "verb": {"v", "vt", "vi"},
        "adjective": {"a", "adj"},
        "adverb": {"ad", "adv"},
        "number": {"num"},
    }.get(part, set())
    normalized = translation.replace("\\r", "").replace("\r", "").replace("\\n", "\n")
    choices: list[tuple[bool, str]] = []
    for raw in normalized.splitlines():
        line = re.sub(r"^\[[^]]+\]\s*", "", raw.strip())
        match = re.match(
            r"^(n|v|vt|vi|a|adj|ad|adv|prep|conj|pron|num|art|int|aux)\.\s*(.+)$",
            line,
            re.IGNORECASE,
        )
        marker = match.group(1).lower() if match else ""
        content = match.group(2) if match else line
        first_sense = re.split(r"[,，;；]", content, maxsplit=1)[0].strip()
        first_sense = re.sub(r"^[^\u3400-\u9fff]+", "", first_sense)
        if first_sense:
            choices.append((marker in preferred_markers, first_sense))
    for preferred, meaning in choices:
        if preferred:
            return meaning
    if choices:
        return choices[0][1]
    return common_meaning(translation) or "这个词"


def conversational_examples(
    word: str,
    part: str,
    raw_pos: str,
    translation: str,
) -> list[tuple[str, str]]:
    """Return three controlled English examples paired with full Chinese translations."""
    results: list[tuple[str, str]] = []

    def add(line: str, meaning: str) -> None:
        normalized_line = re.sub(r"\s+", " ", line).strip()
        normalized_meaning = re.sub(r"\s+", " ", meaning).strip()
        if normalized_line and all(normalized_line != existing[0] for existing in results):
            results.append((normalized_line, normalized_meaning))

    for line, chinese in SPECIAL_EXAMPLE_SETS.get(word, []):
        add(line, chinese)
    if word in SPECIAL_EXAMPLES:
        add(*SPECIAL_EXAMPLES[word])
    meaning = primary_chinese_meaning(word, translation, part)
    if part == "number":
        if word.endswith(("th", "st", "nd", "rd")):
            options = [
                (f"She finished {word} in the race.", f"她在比赛中获得了{meaning}名。"),
                (f"This is my {word} visit.", f"这是我{meaning}次来。"),
                (f"He lives on the {word} floor.", f"他住在{meaning}层。"),
            ]
        else:
            options = [
                (f"We need {word} chairs for the event.", f"这场活动需要{meaning}把椅子。"),
                (f"There were about {word} people outside.", f"外面大约有{meaning}个人。"),
                (f"I waited for {word} minutes.", f"我等了{meaning}分钟。"),
            ]
        for line, chinese in options:
            add(line, chinese)
        return results[:3]

    variant = sum(ord(character) for character in word) % 3
    is_transitive = bool(
        re.search(r"(?:^|/)vt(?::|/|$)", raw_pos.lower())
        or re.search(r"(?:^|\n)vt\.", translation.replace("\\n", "\n").lower())
    )
    verb_fallbacks = (
        [
            (f"Can you {word} this?", f"你能{meaning}这个吗？"),
            (f"Why did they {word} it?", f"他们为什么要{meaning}它？"),
            (f"We need to {word} this first.", f"我们需要先{meaning}这个。"),
        ]
        if is_transitive
        else [
            (f"Why did they {word}?", f"他们为什么{meaning}？"),
            (f"Do you think they will {word}?", f"你觉得他们会{meaning}吗？"),
            (f"We may have to {word} soon.", f"我们可能很快就得{meaning}。"),
        ]
    )
    fallbacks = {
        "noun": [
            (f"Can we talk about the {word} for a minute?", f"我们能聊一下“{meaning}”吗？"),
            (f"What do you know about the {word}?", f"关于“{meaning}”，你了解多少？"),
            (f"They mentioned the {word} earlier.", f"他们刚才提到了“{meaning}”。"),
        ],
        "verb": verb_fallbacks,
        "adjective": [
            (f"They described it as {word}.", f"他们把它描述为“{meaning}”。"),
            (f"That seems {word} to me.", f"在我看来，那似乎是“{meaning}”。"),
            (f"It may be the {word} option.", f"它可能是那个“{meaning}”选项。"),
        ],
        "adverb": [
            (f"They handled the situation {word}.", f"他们以“{meaning}”的方式处理了这种情况。"),
            (f"Why did it happen {word}?", f"为什么事情会以“{meaning}”的方式发生？"),
            (f"She explained it {word}.", f"她以“{meaning}”的方式解释了这件事。"),
        ],
    }
    options = fallbacks.get(
        part,
        [
            (f'I heard someone use "{word}" yesterday.', f'我昨天听到有人使用“{word}”这个词。'),
            (f'What does "{word}" mean here?', f'“{word}”在这里是什么意思？'),
            (f'Can you use "{word}" in another sentence?', f'你能在另一个句子里使用“{word}”吗？'),
        ],
    )
    for offset in range(3):
        add(*options[(variant + offset) % len(options)])
    return results[:3]


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
    chunk_directory = project / "public" / "data" / "words-basic"
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
            "meaning": DISPLAY_MEANING_OVERRIDES.get(
                word,
                common_meaning(row.get("translation", "")),
            ),
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
            )
            entry["example"] = examples[0][0]
            entry["spoken"] = [
                {"line": line, "meaning": chinese}
                for line, chinese in examples
            ]
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

    compact_json = lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    output.write_text(compact_json(entries), encoding="utf-8")
    chunk_directory.mkdir(parents=True, exist_ok=True)
    chunk_count = (len(entries) + OUTPUT_CHUNK_SIZE - 1) // OUTPUT_CHUNK_SIZE
    for index in range(chunk_count):
        start = index * OUTPUT_CHUNK_SIZE
        chunk = entries[start : start + OUTPUT_CHUNK_SIZE]
        (chunk_directory / f"{index:02d}.json").write_text(
            compact_json(chunk),
            encoding="utf-8",
        )
    (chunk_directory / "manifest.json").write_text(
        compact_json(
            {
                "total": len(entries),
                "chunkSize": OUTPUT_CHUNK_SIZE,
                "chunks": chunk_count,
            }
        ),
        encoding="utf-8",
    )
    notice.write_text(
        "LexiFlow basic vocabulary data is derived from ECDICT.\n"
        "Source: https://github.com/skywind3000/ECDICT\n"
        "License: MIT License, Copyright (c) 2025 Linwei\n\n"
        "LexiFlow lexical relations are derived from Open English WordNet 2024.\n"
        "Source: https://en-word.net/\n"
        "License: Creative Commons Attribution 4.0 International\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(entries)} entries to {output} and {chunk_count} mobile chunks")


if __name__ == "__main__":
    main()

