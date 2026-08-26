export type WordEntry = {
  word: string;
  ipa: string;
  part: string;
  level: string;
  tags: ('口语高频' | 'IELTS')[];
  meaning: string;
  note: string;
  spoken: { line: string; meaning: string }[];
  example: string;
  translation: string;
  similar: string[];
  synonyms: string[];
  antonyms: string[];
  phrases: { phrase: string; meaning: string }[];
  basic?: boolean;
  enriched?: boolean;
  rank?: number;
};

export const words: WordEntry[] = [
  {
    word: 'practical', ipa: '/ˈpræk.tɪ.kəl/', part: 'adjective', level: 'B2', tags: ['口语高频', 'IELTS'],
    meaning: '实际的；实用的；切实可行的', note: '口语里常用于把讨论拉回现实，或评价一个方案是否真的行得通。',
    spoken: [{ line: 'Is that really practical?', meaning: '那真的可行吗？' }, { line: 'On a practical level, we need more time.', meaning: '从实际层面来说，我们需要更多时间。' }],
    example: "Let’s be practical and book the earlier train.", translation: '咱们实际一点，订早一点的火车吧。',
    similar: ['practice', 'practically', 'practicable'], synonyms: ['realistic', 'useful', 'sensible'], antonyms: ['impractical', 'unrealistic'],
    phrases: [{ phrase: 'practical advice', meaning: '实用建议' }, { phrase: 'for practical purposes', meaning: '从实际用途来看' }],
  },
  {
    word: 'reliable', ipa: '/rɪˈlaɪ.ə.bəl/', part: 'adjective', level: 'B1', tags: ['口语高频', 'IELTS'],
    meaning: '可靠的；可信赖的；稳定的', note: '可以形容人、消息、交通工具或数据，是推荐某人某物时的高频词。',
    spoken: [{ line: 'Can we rely on this data?', meaning: '这些数据可靠吗？' }, { line: 'He’s always been reliable.', meaning: '他一直都很靠谱。' }],
    example: 'Maya is the most reliable person on our team.', translation: 'Maya 是我们团队里最靠谱的人。',
    similar: ['reliably', 'reliability', 'reliant'], synonyms: ['dependable', 'trustworthy', 'consistent'], antonyms: ['unreliable', 'inconsistent'],
    phrases: [{ phrase: 'a reliable source', meaning: '可靠的消息来源' }, { phrase: 'fairly reliable', meaning: '相当可靠' }],
  },
  {
    word: 'figure', ipa: '/ˈfɪɡ.jɚ/', part: 'verb · noun', level: 'B1', tags: ['口语高频'],
    meaning: '认为；估计；弄明白；数字', note: '美式口语中 figure 常等于 think；figure out 是必须掌握的高频短语。',
    spoken: [{ line: 'I figure we’ll be there by eight.', meaning: '我估计我们八点前能到。' }, { line: 'We’ll figure something out.', meaning: '我们会想出办法的。' }],
    example: 'I figured you might need a hand.', translation: '我想着你可能需要帮忙。',
    similar: ['figurative', 'figuratively', 'figuration'], synonyms: ['think', 'calculate', 'understand'], antonyms: ['misjudge', 'overlook'],
    phrases: [{ phrase: 'figure out', meaning: '弄清楚；想出办法' }, { phrase: 'go figure', meaning: '真想不到；谁知道呢' }],
  },
  {
    word: 'awkward', ipa: '/ˈɑː.kwɚd/', part: 'adjective', level: 'B2', tags: ['口语高频'],
    meaning: '尴尬的；别扭的；难处理的', note: '既可形容社交气氛，也可形容姿势、时间或处境“不太方便”。',
    spoken: [{ line: 'Well, this is awkward.', meaning: '呃，这就有点尴尬了。' }, { line: 'Is now an awkward time?', meaning: '现在是不是不太方便？' }],
    example: 'There was an awkward silence after his joke.', translation: '他的笑话说完后，现场一阵尴尬的沉默。',
    similar: ['awkwardly', 'awkwardness', 'outward'], synonyms: ['uncomfortable', 'clumsy', 'tricky'], antonyms: ['comfortable', 'graceful'],
    phrases: [{ phrase: 'awkward silence', meaning: '尴尬的沉默' }, { phrase: 'an awkward question', meaning: '难以回答的问题' }],
  },
  {
    word: 'handle', ipa: '/ˈhæn.dəl/', part: 'verb · noun', level: 'B1', tags: ['口语高频', 'IELTS'],
    meaning: '处理；应付；操控；把手', note: '谈工作能力、压力或棘手情况时，比 deal with 更简洁直接。',
    spoken: [{ line: 'I can handle it from here.', meaning: '接下来我能搞定。' }, { line: 'How are you handling the pressure?', meaning: '你是怎么应对压力的？' }],
    example: 'Don’t worry—I can handle it.', translation: '别担心，我能处理。',
    similar: ['handler', 'handling', 'handful'], synonyms: ['manage', 'deal with', 'cope with'], antonyms: ['mismanage', 'neglect'],
    phrases: [{ phrase: 'handle the pressure', meaning: '应对压力' }, { phrase: 'too hot to handle', meaning: '棘手得难以处理' }],
  },
  {
    word: 'approach', ipa: '/əˈproʊtʃ/', part: 'noun · verb', level: 'B2', tags: ['口语高频', 'IELTS'],
    meaning: '方法；态度；接近；着手处理', note: '雅思写作常指解决问题的方法，口语里也能说“换个方式来”。',
    spoken: [{ line: 'Let’s approach it another way.', meaning: '我们换个方式处理吧。' }, { line: 'I like your approach.', meaning: '我喜欢你的处理方式。' }],
    example: 'We need a different approach to this problem.', translation: '我们需要用不同的方法处理这个问题。',
    similar: ['reproach', 'approachable', 'approaching'], synonyms: ['method', 'strategy', 'come near'], antonyms: ['avoid', 'withdraw'],
    phrases: [{ phrase: 'a practical approach', meaning: '务实的方法' }, { phrase: 'approach someone', meaning: '上前与某人交谈' }],
  },
  {
    word: 'significant', ipa: '/sɪɡˈnɪf.ə.kənt/', part: 'adjective', level: 'B2', tags: ['IELTS'],
    meaning: '重要的；显著的；有意义的', note: '描述数据变化、影响或进步的雅思核心词，比 big / important 更精确。',
    spoken: [{ line: 'That’s a significant difference.', meaning: '那是个很明显的差别。' }, { line: 'It had a significant impact on me.', meaning: '它对我产生了很大的影响。' }],
    example: 'We’ve made significant progress this month.', translation: '这个月我们取得了显著进展。',
    similar: ['significance', 'significantly', 'insignificant'], synonyms: ['considerable', 'important', 'meaningful'], antonyms: ['minor', 'insignificant'],
    phrases: [{ phrase: 'a significant increase', meaning: '显著增长' }, { phrase: 'statistically significant', meaning: '具有统计显著性的' }],
  },
  {
    word: 'perspective', ipa: '/pɚˈspek.tɪv/', part: 'noun', level: 'B2', tags: ['口语高频', 'IELTS'],
    meaning: '视角；观点；看问题的方式', note: '讨论不同立场时非常自然；put it in perspective 表示客观看待。',
    spoken: [{ line: 'That’s one way to look at it.', meaning: '那也是一种看法。' }, { line: 'Let me give you my perspective.', meaning: '我来说说我的看法。' }],
    example: 'Try to see it from her perspective.', translation: '试着从她的角度看这件事。',
    similar: ['prospective', 'respective', 'prospect'], synonyms: ['viewpoint', 'outlook', 'angle'], antonyms: ['blindness', 'misconception'],
    phrases: [{ phrase: 'from my perspective', meaning: '在我看来' }, { phrase: 'put it in perspective', meaning: '客观全面地看待它' }],
  },
  {
    word: 'clarify', ipa: '/ˈkler.ə.faɪ/', part: 'verb', level: 'B2', tags: ['口语高频', 'IELTS'],
    meaning: '澄清；说明；使更清楚', note: '开会、课堂和雅思口语中礼貌确认信息的好词。',
    spoken: [{ line: 'Just to clarify, are we meeting at six?', meaning: '确认一下，我们是六点见吗？' }, { line: 'Could you clarify that last point?', meaning: '你能说明一下最后那一点吗？' }],
    example: 'Could you clarify what you mean by “flexible”?', translation: '你能说明一下你说的“灵活”是什么意思吗？',
    similar: ['clarity', 'clarification', 'classify'], synonyms: ['explain', 'make clear', 'specify'], antonyms: ['confuse', 'obscure'],
    phrases: [{ phrase: 'clarify a point', meaning: '澄清一个观点' }, { phrase: 'just to clarify', meaning: '确认一下；说明一下' }],
  },
  {
    word: 'flexible', ipa: '/ˈflek.sə.bəl/', part: 'adjective', level: 'B2', tags: ['口语高频', 'IELTS'],
    meaning: '灵活的；可变通的；柔韧的', note: '描述时间、计划、规则或性格都很自然，常用于协商安排。',
    spoken: [{ line: 'My schedule is pretty flexible.', meaning: '我的时间安排很灵活。' }, { line: 'We can be flexible about the date.', meaning: '日期方面我们可以变通。' }],
    example: 'I’m flexible, so any time after six works for me.', translation: '我时间比较灵活，六点以后都可以。',
    similar: ['flexibility', 'flexibly', 'reflexive'], synonyms: ['adaptable', 'adjustable', 'open-minded'], antonyms: ['rigid', 'inflexible'],
    phrases: [{ phrase: 'flexible hours', meaning: '弹性工作时间' }, { phrase: 'be flexible about', meaning: '在某事上可以变通' }],
  },
  {
    word: 'sustainable', ipa: '/səˈsteɪ.nə.bəl/', part: 'adjective', level: 'B2', tags: ['IELTS'],
    meaning: '可持续的；能长期维持的', note: '不只用于环保，也能形容商业模式、习惯或生活节奏能否长久。',
    spoken: [{ line: 'This pace just isn’t sustainable.', meaning: '这个节奏实在无法长期维持。' }, { line: 'We need a more sustainable plan.', meaning: '我们需要一个更能长久执行的计划。' }],
    example: 'Working twelve hours a day isn’t sustainable.', translation: '每天工作十二小时是无法长期维持的。',
    similar: ['sustain', 'sustainability', 'sustained'], synonyms: ['viable', 'maintainable', 'eco-friendly'], antonyms: ['unsustainable', 'short-lived'],
    phrases: [{ phrase: 'sustainable growth', meaning: '可持续增长' }, { phrase: 'a sustainable lifestyle', meaning: '可持续的生活方式' }],
  },
  {
    word: 'relevant', ipa: '/ˈrel.ə.vənt/', part: 'adjective', level: 'B2', tags: ['口语高频', 'IELTS'],
    meaning: '相关的；切题的；有现实意义的', note: '写作筛选论据、口语判断信息是否切题时都很实用。',
    spoken: [{ line: 'How is that relevant?', meaning: '那有什么关系？' }, { line: 'I have some relevant experience.', meaning: '我有一些相关经验。' }],
    example: 'That’s interesting, but is it relevant to the question?', translation: '那很有意思，但和这个问题有关吗？',
    similar: ['relevance', 'irrelevant', 'relatively'], synonyms: ['related', 'applicable', 'pertinent'], antonyms: ['irrelevant', 'unrelated'],
    phrases: [{ phrase: 'highly relevant', meaning: '高度相关' }, { phrase: 'relevant experience', meaning: '相关经验' }],
  },
];

export const libraryStats = [
  { label: '高频核心', count: '3,000' },
  { label: '日常进阶', count: '5,000' },
  { label: '母语扩展', count: '17,000' },
];

