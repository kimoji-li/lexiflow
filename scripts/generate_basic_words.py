#!/usr/bin/env python3
"""Build LexiFlow's compact library with spoken-usage data from vetted open data.

New per-word fields (ranks 1-15,000), all deterministically derived:
  frequency    {band, scenes, text}  spoken-frequency band + usage scenes
  senses       [{pos, gloss}]        short Chinese senses split from ECDICT
  tips         [{type, text}]        homophone warnings (e.g. knead / need)
  derivatives  [str]                 WordNet derivations (wordness, electricity)
  synonyms     [str]                 all parts of speech (was adjectives only)
  antonyms     [str]                 all parts of speech
Sources: ECDICT (MIT), Open English WordNet 2024 (CC BY 4.0), Tatoeba (CC BY 2.0 FR).
"""

from __future__ import annotations

import csv
import gzip
import json
import re
import sys
from pathlib import Path

import wn


WORD_RE = re.compile(r"^[a-z][a-z'-]{0,23}$")
TARGET_COUNT = 25_000
OUTPUT_CHUNK_SIZE = 1_000
SPOKEN_COUNT = 4_000
SPOKEN_ENRICH_START = 1
SPOKEN_ENRICH_END = 15_000
WORDNET_ENRICH_END = 15_000
POS_NAMES = {
    "n": "noun",
    "v": "verb",
    "vt": "verb",
    "vi": "verb",
    "r": "adverb",
    "adv": "adverb",
    "a": "adjective",
    "s": "adjective",
    "adj": "adjective",
    "prep": "preposition",
    "conj": "conjunction",
    "pron": "pronoun",
    "num": "number",
    "art": "article",
    "int": "interjection",
    "interj": "interjection",
    "aux": "auxiliary",
}
POS_ABBREV = {
    "noun": "n.",
    "verb": "v.",
    "adjective": "adj.",
    "adverb": "adv.",
    "preposition": "prep.",
    "conjunction": "conj.",
    "pronoun": "pron.",
    "number": "num.",
    "article": "art.",
    "interjection": "int.",
    "auxiliary": "aux.",
    "word": "",
}
WN_POS = {
    "noun": ("n",),
    "verb": ("v",),
    "adjective": ("a", "s"),
    "adverb": ("r",),
}
# WordNet lexicographer file -> Chinese usage scenes.
LEXFILE_SCENES = {
    "noun.tops": ("通用",),
    "noun.act": ("行为", "动作"),
    "noun.animal": ("动物",),
    "noun.artifact": ("物品", "器具"),
    "noun.attribute": ("特征", "属性"),
    "noun.body": ("身体", "生理"),
    "noun.cognition": ("认知", "思考"),
    "noun.communication": ("交流", "表达"),
    "noun.event": ("事件", "情况"),
    "noun.feeling": ("情感", "感受"),
    "noun.food": ("饮食",),
    "noun.group": ("群体",),
    "noun.location": ("地点", "位置"),
    "noun.motive": ("动机", "目的"),
    "noun.object": ("物体",),
    "noun.person": ("人物",),
    "noun.phenomenon": ("现象", "自然"),
    "noun.plant": ("植物",),
    "noun.possession": ("财物",),
    "noun.process": ("过程",),
    "noun.quantity": ("数量",),
    "noun.relation": ("关系",),
    "noun.shape": ("形状", "外观"),
    "noun.state": ("状态",),
    "noun.substance": ("物质", "材料"),
    "noun.time": ("时间",),
    "verb.body": ("身体动作", "护理"),
    "verb.change": ("变化",),
    "verb.cognition": ("思考", "认知"),
    "verb.communication": ("交流", "表达"),
    "verb.competition": ("竞争", "对抗"),
    "verb.consumption": ("饮食", "消耗"),
    "verb.contact": ("接触", "揉按"),
    "verb.creation": ("创造", "制作"),
    "verb.emotion": ("情感", "情绪"),
    "verb.motion": ("移动", "行动"),
    "verb.perception": ("感知", "观察"),
    "verb.possession": ("拥有", "支配"),
    "verb.social": ("社交", "人际"),
    "verb.stative": ("状态",),
    "verb.weather": ("天气",),
    "adj.all": ("描述",),
    "adj.pert": ("描述", "关联"),
    "adv.all": ("方式", "程度"),
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
IELTS_USAGE_GROUPS = (
    (
        {
            "approximately", "considerable", "decrease", "decline", "dramatic",
            "fluctuate", "gradual", "increase", "marginal", "moderate", "proportion",
            "rapid", "ratio", "remain", "roughly", "significant", "slight", "stable",
            "steady", "substantial", "trend",
        },
        {
            "label": "雅思写作 Task 1",
            "scene": "适合描述图表中的数量、比例或变化趋势；使用时要同时写清比较对象和时间范围。",
        },
    ),
    (
        {
            "analysis", "assess", "attribute", "correlation", "demonstrate", "evidence",
            "evaluate", "hypothesis", "illustrate", "imply", "indicate", "interpret",
            "phenomenon", "reveal", "statistics", "suggest",
        },
        {
            "label": "雅思写作论证",
            "scene": "适合引出证据、研究发现或分析结果；不要把可能性写成绝对事实。",
        },
    ),
    (
        {
            "alleviate", "barrier", "effective", "efficient", "encourage", "enforce",
            "facilitate", "feasible", "framework", "hinder", "implement", "incentive",
            "mitigate", "obstacle", "policy", "promote", "prohibit", "regulate",
            "restrict", "strategy", "sustainable", "tackle", "viable",
        },
        {
            "label": "雅思写作 Task 2",
            "scene": "适合讨论解决方案、政策可行性或执行效果；最好配合一个具体措施或结果。",
        },
    ),
    (
        {
            "consequence", "contribute", "derive", "exacerbate", "factor", "impact",
            "influence", "outcome", "stem", "trigger",
        },
        {
            "label": "雅思写作因果链",
            "scene": "适合解释原因、影响与后果；注意搭配正确介词，并把因果关系写完整。",
        },
    ),
    (
        {
            "apparent", "beneficial", "compelling", "complex", "controversial",
            "crucial", "detrimental", "inevitable", "perspective", "prevalent",
            "reasonable", "relevant", "remarkable", "sensitive", "subtle", "valid",
            "vital", "widespread",
        },
        {
            "label": "雅思口语 Part 3 / 写作",
            "scene": "适合表达较成熟的评价或观点；口语中可用于展开理由，写作中可用于更准确地限定判断。",
        },
    ),
    (
        {
            "biodiversity", "carbon", "conservation", "ecosystem", "emission", "habitat",
            "pollution", "renewable",
        },
        {
            "label": "雅思环境主题",
            "scene": "常见于环境类口语 Part 3 和写作 Task 2；建议结合污染来源、保护措施或长期影响来使用。",
        },
    ),
    (
        {
            "discrimination", "diversity", "elderly", "employment", "globalization",
            "inequality", "migration", "poverty", "unemployment", "urbanization",
            "welfare",
        },
        {
            "label": "雅思社会主题",
            "scene": "常用于社会公平、就业、人口流动或公共服务话题；需要说明受影响的人群和具体背景。",
        },
    ),
    (
        {
            "academic", "cognitive", "curriculum", "literacy", "motivation",
            "scholarship", "vocational",
        },
        {
            "label": "雅思教育主题",
            "scene": "常用于教育类口语与写作；可结合课程设计、学习效果或教育机会来展开。",
        },
    ),
)


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


def frequency_band(rank: int) -> str:
    if rank <= 1500:
        return "极高频"
    if rank <= 3000:
        return "高频"
    if rank <= 5000:
        return "中高频"
    if rank <= 7000:
        return "中频"
    if rank <= 10000:
        return "中低频"
    if rank <= 15000:
        return "低频"
    return "罕用"


def normalized_gloss(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def normalize_ipa(ipa: str) -> str:
    """Strip stress marks, length marks and separators to group homophones."""
    text = ipa.strip().strip("/")
    for char in ("ˈ", "ˌ", ".", " ", "ː", "ˈ"):
        text = text.replace(char, "")
    return text


def definition_lines(value: str, part: str) -> list[str]:
    markers = {
        "noun": {"n"},
        "verb": {"v"},
        "adjective": {"a", "s"},
        "adverb": {"r"},
    }.get(part, set())
    results: list[str] = []
    normalized = value.replace("\\r", "").replace("\r", "").replace("\\n", "\n")
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
    limit: int = 2,
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
    chosen: list[wn.Synset] = []
    for synset in matched + synsets:
        if synset not in chosen:
            chosen.append(synset)
        if len(chosen) == limit:
            break
    return chosen


def all_synsets(lexicon: wn.Wordnet, word: str, part: str) -> list[wn.Synset]:
    return [
        synset
        for pos in WN_POS.get(part, ())
        for synset in lexicon.synsets(word, pos=pos)
    ]


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


def split_senses(translation: str, fallback_part: str, max_senses: int = 6) -> list[dict[str, str]]:
    """Split ECDICT Chinese gloss into short senses tagged with part of speech."""
    normalized = translation.replace("\\r", "").replace("\r", "").replace("\\n", "\n")
    senses: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in normalized.splitlines():
        line = raw.strip()
        if line.startswith("[网络") or line.startswith("["):
            continue
        match = re.match(
            r"^(n|v|vt|vi|a|adj|ad|adv|prep|conj|pron|num|art|int|aux)\.\s*(.+)$",
            line,
            re.IGNORECASE,
        )
        if match:
            pos_name = POS_NAMES.get(match.group(1).lower(), "word")
            body = match.group(2)
        else:
            pos_name = fallback_part
            body = line
        for chunk in re.split(r"[;；]", body):
            pieces = [
                re.sub(r"^[^\u3400-\u9fff]+", "", re.sub(r"\s+", " ", p).strip(" ,，.。"))
                for p in re.split(r"[,，]", chunk)
            ]
            pieces = [p for p in pieces if p]
            gloss = "、".join(pieces[:3])
            if not gloss or len(gloss) > 18 or gloss in seen:
                continue
            seen.add(gloss)
            abbrev = POS_ABBREV.get(pos_name, "")
            senses.append({"pos": abbrev, "gloss": gloss})
            if len(senses) == max_senses:
                return senses
    return senses


def scenes_for_synsets(synsets: list[wn.Synset], limit: int = 2) -> list[str]:
    scenes: list[str] = []
    for synset in synsets:
        lexfile = ""
        try:
            lexfile = synset.lexfile()
        except Exception:
            lexfile = ""
        for scene in LEXFILE_SCENES.get(lexfile.lower(), ()):
            if scene not in scenes:
                scenes.append(scene)
        if len(scenes) >= limit:
            break
    return scenes[:limit]


def frequency_text(band: str, scenes: list[str]) -> str:
    if scenes:
        return f"{band}，{'、'.join(scenes)}场景多见"
    if band == "极高频":
        return "极高频，日常对话核心词"
    return band


def conversational_examples(
    word: str,
    corpus_examples: dict[str, list[dict[str, object]]],
) -> list[tuple[str, str]]:
    """Return up to three natural, bilingual examples without template filler."""
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
    for item in corpus_examples.get(word, []):
        add(str(item.get("line", "")), str(item.get("meaning", "")))
    return results[:3]


def ielts_usage_for(word: str, tags: list[str]) -> dict[str, str] | None:
    """Return a conservative IELTS note only for clearly useful vocabulary."""
    if "IELTS" not in tags:
        return None
    for words, usage in IELTS_USAGE_GROUPS:
        if word in words:
            return usage
    return None


def word_relations(
    word: str,
    synsets: list[wn.Synset],
    allowed_words: set[str],
) -> tuple[list[str], list[str], list[str]]:
    synonyms: list[str] = []
    antonyms: list[str] = []
    derivatives: list[str] = []
    for synset in synsets:
        for lemma in synset.lemmas():
            synonyms.append(lemma.replace("_", " "))
        for sense in synset.senses():
            if sense.word().lemma().lower() != word:
                continue
            for target in sense.get_related("antonym"):
                antonyms.append(target.word().lemma().replace("_", " "))
            for target in sense.get_related("derivation"):
                derivatives.append(target.word().lemma().replace("_", " "))

    def clean(values: list[str], cap: int) -> list[str]:
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
        return unique[:cap]

    return clean(synonyms, 4), clean(antonyms, 3), clean(derivatives, 4)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: generate_basic_words.py /path/to/ecdict.csv")

    source = Path(sys.argv[1])
    project = Path(__file__).resolve().parents[1]
    output = project / "public" / "data" / "words-basic.json"
    chunk_directory = project / "public" / "data" / "words-basic"
    notice = project / "public" / "data" / "NOTICE.txt"
    corpus_path = project / "data" / "spoken_examples.json.gz"
    if not corpus_path.exists():
        raise SystemExit(
            "Missing data/spoken_examples.json.gz. Run scripts/build_tatoeba_examples.py first."
        )
    with gzip.open(corpus_path, "rt", encoding="utf-8") as compressed:
        corpus_payload = json.load(compressed)
    corpus_examples: dict[str, list[dict[str, object]]] = corpus_payload["examples"]
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

    # First pass: ordered entries and an IPA index for homophone detection.
    ordered_rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for _, row in selected:
        word = row["word"].strip()
        if word in seen:
            continue
        seen.add(word)
        ordered_rows.append(row)
        if len(ordered_rows) == TARGET_COUNT:
            break

    ipa_index: dict[str, list[str]] = {}
    for row in ordered_rows:
        phonetic = row.get("phonetic", "").strip()
        if phonetic:
            key = normalize_ipa(phonetic)
            ipa_index.setdefault(key, []).append(row["word"].strip())

    entries: list[dict[str, object]] = []
    for row in ordered_rows:
        word = row["word"].strip()
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

        # WordNet-derived spoken-usage data for ranks 1-15,000.
        if rank <= WORDNET_ENRICH_END:
            synsets = all_synsets(lexicon, word, part)
            primary = primary_synsets(lexicon, word, part, row.get("definition", ""))
            scenes = scenes_for_synsets(synsets)
            band = frequency_band(rank)
            entry["frequency"] = {
                "band": band,
                "scenes": scenes,
                "text": frequency_text(band, scenes),
            }
            entry["senses"] = split_senses(row.get("translation", ""), part)
            synonyms, antonyms, derivatives = word_relations(word, synsets, allowed_words)
            entry["synonyms"] = synonyms
            entry["antonyms"] = antonyms
            entry["derivatives"] = derivatives
            entry["enriched"] = True

            # Homophone tip from the global IPA index.
            phonetic = row.get("phonetic", "").strip()
            if phonetic:
                peers = [peer for peer in ipa_index.get(normalize_ipa(phonetic), []) if peer != word]
                if peers:
                    peer = peers[0]
                    peer_row = next((r for r in ordered_rows if r["word"].strip() == peer), None)
                    peer_meaning = (
                        primary_chinese_meaning(peer, peer_row.get("translation", ""), "word")
                        if peer_row else ""
                    )
                    own_meaning = primary_chinese_meaning(word, row.get("translation", ""), part)
                    text = (
                        f"发音和 {peer} 完全同音，只能靠上下文区分：{word} 指{own_meaning}，"
                        f"{peer} 指{peer_meaning}。"
                    )
                    entry["tips"] = [{"type": "homophone", "text": text}]

            examples = conversational_examples(word, corpus_examples)
            if examples:
                entry["example"] = examples[0][0]
                entry["spoken"] = [
                    {"line": line, "meaning": chinese}
                    for line, chinese in examples
                ]
            if ielts_usage := ielts_usage_for(word, tags):
                entry["ieltsUsage"] = ielts_usage
        entries.append(entry)

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
        "License: Creative Commons Attribution 4.0 International\n\n"
        "LexiFlow bilingual example sentences are selected from Tatoeba.\n"
        "Source: https://tatoeba.org/\n"
        "License: Creative Commons Attribution 2.0 France\n",
        encoding="utf-8",
    )
    enriched = sum(1 for entry in entries if entry.get("enriched"))
    with_examples = sum(1 for entry in entries if entry.get("spoken"))
    with_homophones = sum(1 for entry in entries if entry.get("tips"))
    print(
        f"Wrote {len(entries)} entries ({enriched} enriched, {with_examples} with examples, "
        f"{with_homophones} with homophone tips) and {chunk_count} chunks"
    )


if __name__ == "__main__":
    main()
