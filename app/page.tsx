'use client';

import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { libraryStats, words as curatedWords, type WordEntry } from './words';

type Mode = 'card' | 'list';
type Filter = '全部' | '口语高频' | 'IELTS' | '已收藏';
type BasicWordPayload = Pick<WordEntry, 'word' | 'ipa' | 'part' | 'level' | 'tags' | 'meaning' | 'basic' | 'rank'>;

const LIBRARY_SIZE = 20000;
const LIST_PAGE_SIZE = 120;

export default function Home() {
  const [mode, setMode] = useState<Mode>('card');
  const [filter, setFilter] = useState<Filter>('全部');
  const [query, setQuery] = useState('');
  const [allWords, setAllWords] = useState<WordEntry[]>(curatedWords);
  const [selected, setSelected] = useState(curatedWords[0].word);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [known, setKnown] = useState<string[]>([]);
  const [saved, setSaved] = useState<string[]>([]);
  const [loadingLibrary, setLoadingLibrary] = useState(true);
  const [listPage, setListPage] = useState(0);
  const [listJump, setListJump] = useState('');
  const [jumpedSequence, setJumpedSequence] = useState<number | null>(null);
  const touchStart = useRef<number | null>(null);

  useEffect(() => {
    const storedTheme = localStorage.getItem('lexiflow-theme') as 'light' | 'dark' | null;
    const preferredDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const nextTheme = storedTheme ?? (preferredDark ? 'dark' : 'light');
    setTheme(nextTheme);
    document.documentElement.dataset.theme = nextTheme;
    setKnown(JSON.parse(localStorage.getItem('lexiflow-known') ?? '[]'));
    setSaved(JSON.parse(localStorage.getItem('lexiflow-saved') ?? '[]'));
    const fromUrl = new URLSearchParams(window.location.search).get('word');
    const dataUrl = new URL('data/words-basic.json', window.location.href);
    fetch(dataUrl)
      .then((response) => {
        if (!response.ok) throw new Error(`Unable to load vocabulary: ${response.status}`);
        return response.json() as Promise<BasicWordPayload[]>;
      })
      .then((basicWords) => {
        const curatedSet = new Set(curatedWords.map((item) => item.word));
        const normalized = basicWords.map((item): WordEntry => ({
          ...item,
          note: '',
          spoken: [],
          example: '',
          translation: '',
          similar: [],
          synonyms: [],
          antonyms: [],
          phrases: [],
        }));
        const combined = [
          ...curatedWords,
          ...normalized.filter((item) => !curatedSet.has(item.word)).slice(0, LIBRARY_SIZE - curatedWords.length),
        ];
        setAllWords(combined);
        if (fromUrl && combined.some((item) => item.word === fromUrl)) setSelected(fromUrl);
      })
      .catch(() => {
        if (fromUrl && curatedWords.some((item) => item.word === fromUrl)) setSelected(fromUrl);
      })
      .finally(() => setLoadingLibrary(false));
  }, []);

  const visibleWords = useMemo(() => {
    const text = query.trim().toLowerCase();
    return allWords.filter((item) => {
      const matchesFilter = filter === '全部'
        || (filter === '已收藏' ? saved.includes(item.word) : item.tags.includes(filter));
      const haystack = [item.word, item.meaning, item.example, ...item.synonyms, ...item.phrases.map((p) => p.phrase)].join(' ').toLowerCase();
      return matchesFilter && (!text || haystack.includes(text));
    });
  }, [allWords, filter, query, saved]);

  const currentIndex = Math.max(0, visibleWords.findIndex((item) => item.word === selected));
  const current = visibleWords[currentIndex] ?? allWords[0] ?? curatedWords[0];

  useEffect(() => {
    setListPage(0);
    setListJump('');
    setJumpedSequence(null);
  }, [filter, query, mode]);

  const listStart = listPage * LIST_PAGE_SIZE;
  const listEnd = Math.min(listStart + LIST_PAGE_SIZE, visibleWords.length);
  const listPageCount = Math.max(1, Math.ceil(visibleWords.length / LIST_PAGE_SIZE));

  useEffect(() => {
    if (mode !== 'list' || jumpedSequence === null) return;
    requestAnimationFrame(() => {
      document.getElementById(`word-row-${jumpedSequence}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }, [jumpedSequence, listPage, mode]);

  useEffect(() => {
    if (visibleWords.length && !visibleWords.some((item) => item.word === selected)) {
      setSelected(visibleWords[0].word);
    }
  }, [visibleWords, selected]);

  useEffect(() => {
    if (mode !== 'card') return;
    const url = new URL(window.location.href);
    url.searchParams.set('word', current.word);
    window.history.replaceState({}, '', url);
  }, [current.word, mode]);

  const move = useCallback((direction: number) => {
    if (!visibleWords.length) return;
    const next = (currentIndex + direction + visibleWords.length) % visibleWords.length;
    setSelected(visibleWords[next].word);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [currentIndex, visibleWords]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (mode !== 'card' || ['INPUT', 'TEXTAREA'].includes((event.target as HTMLElement).tagName)) return;
      if (event.key === 'ArrowRight') move(1);
      if (event.key === 'ArrowLeft') move(-1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [mode, move]);

  function switchTheme() {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    document.documentElement.dataset.theme = next;
    localStorage.setItem('lexiflow-theme', next);
  }

  function speak(word: string) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(word);
    utterance.lang = 'en-US';
    utterance.rate = 0.88;
    window.speechSynthesis.speak(utterance);
  }

  function toggleSaved(word: string) {
    const next = saved.includes(word) ? saved.filter((item) => item !== word) : [...saved, word];
    setSaved(next);
    localStorage.setItem('lexiflow-saved', JSON.stringify(next));
  }

  function markKnown() {
    const next = known.includes(current.word) ? known : [...known, current.word];
    setKnown(next);
    localStorage.setItem('lexiflow-known', JSON.stringify(next));
    move(1);
  }

  function openWord(word: string) {
    setSelected(word);
    setMode('card');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function jumpToSequence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const requested = Number.parseInt(listJump, 10);
    if (!Number.isFinite(requested) || !visibleWords.length) return;
    const target = Math.min(visibleWords.length, Math.max(1, requested));
    setListJump(String(target));
    setListPage(Math.floor((target - 1) / LIST_PAGE_SIZE));
    setJumpedSequence(target);
  }

  function changeListPage(page: number) {
    setListPage(Math.min(listPageCount - 1, Math.max(0, page)));
    setJumpedSequence(null);
    requestAnimationFrame(() => document.getElementById('list-tools')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#main" aria-label="词流首页">
          <span className="brand-mark">L</span><span>词流</span><small>LEXIFLOW</small>
        </a>
        <div className="daily-progress" aria-label={`今日已学 ${known.length} 个，目标 30 个`}>
          <span>今日</span><strong>{known.length}</strong><span>/ 30</span>
          <i><b style={{ width: `${Math.min(100, known.length / 30 * 100)}%` }} /></i>
        </div>
        <div className="header-actions">
          <button className="header-link" onClick={() => setFilter('已收藏')}>收藏 {saved.length}</button>
          <button className="icon-button" onClick={switchTheme} aria-label="切换黑白背景">{theme === 'light' ? '☾' : '☀'}</button>
        </div>
      </header>

      <section className="toolbar" aria-label="词库筛选">
        <div className="filter-tabs">
          {(['全部', '口语高频', 'IELTS', '已收藏'] as Filter[]).map((item) => (
            <button key={item} className={filter === item ? 'active' : ''} onClick={() => setFilter(item)}>{item}</button>
          ))}
        </div>
        <label className="search-box">
          <span>⌕</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="查单词、中文或短语" aria-label="搜索单词" />
          {query && <button onClick={() => setQuery('')} aria-label="清空搜索">×</button>}
        </label>
      </section>

      <section id="main" className="study-wrap">
        <div className="study-meta">
          <div>
            <span className="eyebrow">{loadingLibrary ? '正在载入词库' : `${filter === '全部' ? 'DAILY WORDS' : filter.toUpperCase()} · ${visibleWords.length} WORDS`}</span>
            <h1>{mode === 'card' ? '今天继续，把好词用进对话里。' : '一眼多看，快速建立词义连接。'}</h1>
          </div>
          <div className="mode-switch" aria-label="背诵模式">
            <button className={mode === 'card' ? 'active' : ''} onClick={() => setMode('card')}>▣ 单词卡</button>
            <button className={mode === 'list' ? 'active' : ''} onClick={() => setMode('list')}>☷ 高效速览</button>
          </div>
        </div>

        {!visibleWords.length ? (
          <div className="empty-state">
            <strong>没有找到匹配的词</strong>
            <p>换一个关键词，或回到全部词库。</p>
            <button onClick={() => { setQuery(''); setFilter('全部'); }}>查看全部</button>
          </div>
        ) : mode === 'card' ? (
          <>
            <article
              className="word-card"
              onTouchStart={(event) => { touchStart.current = event.touches[0].clientX; }}
              onTouchEnd={(event) => {
                if (touchStart.current === null) return;
                const distance = event.changedTouches[0].clientX - touchStart.current;
                if (Math.abs(distance) > 70) move(distance < 0 ? 1 : -1);
                touchStart.current = null;
              }}
            >
              <div className="card-topline">
                <div className="chips">{current.tags.map((tag) => <span key={tag}>{tag}</span>)}{current.basic && <span>基础词条</span>}<span>{current.level}</span></div>
                <button className={`text-button ${saved.includes(current.word) ? 'is-saved' : ''}`} onClick={() => toggleSaved(current.word)}>
                  {saved.includes(current.word) ? '♥ 已收藏' : '♡ 收藏'}
                </button>
              </div>

              <div className="word-heading">
                <div>
                  <h2>{current.word}</h2>
                  <p>{current.ipa} · {current.part}</p>
                </div>
                <button className="sound-button" onClick={() => speak(current.word)} aria-label={`播放 ${current.word} 的美式发音`}>▶<small>US</small></button>
              </div>

              <div className="definition-block">
                <span className="section-label">常用义</span>
                <p className="definition">{current.meaning}</p>
              </div>

              {current.basic ? (
                <div className="basic-note">
                  <span>基础词条 · 使用频率 #{current.rank}</span>
                  <p>当前提供核心词义、音标和美式朗读，适合快速浏览与自测。</p>
                </div>
              ) : (
                <>
                  <blockquote>
                    “{current.example}”
                    <span>{current.translation}</span>
                  </blockquote>

                  <div className="spoken-note">
                    <span>口语中的用法</span>
                    <div className="spoken-copy">
                      <p>{current.note}</p>
                      <div className="spoken-examples">
                        {current.spoken.map((item) => (
                          <button key={item.line} onClick={() => speak(item.line)} title="点击朗读">
                            <strong>{item.line}</strong><small>{item.meaning}</small><i>▶</i>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="relation-grid">
                    <section><span className="section-label">形近词</span><div className="word-pills">{current.similar.map((item) => <span key={item}>{item}</span>)}</div></section>
                    <section><span className="section-label">近义词</span><div className="word-pills good">{current.synonyms.map((item) => <span key={item}>{item}</span>)}</div></section>
                    <section><span className="section-label">反义词</span><div className="word-pills contrast">{current.antonyms.map((item) => <span key={item}>{item}</span>)}</div></section>
                  </div>

                  <section className="phrases-section">
                    <span className="section-label">相关口语短语</span>
                    <div className="phrase-list">
                      {current.phrases.map((item, index) => (
                        <div key={item.phrase}><b>{String(index + 1).padStart(2, '0')}</b><strong>{item.phrase}</strong><span>{item.meaning}</span><button onClick={() => speak(item.phrase)} aria-label={`播放 ${item.phrase}`}>▶</button></div>
                      ))}
                    </div>
                  </section>
                </>
              )}

              <div className="card-foot"><span>{known.includes(current.word) ? '✓ 今天已记过' : '左右滑动也可切换'}</span><strong>{currentIndex + 1} / {visibleWords.length}</strong></div>
            </article>

            <nav className="study-controls" aria-label="单词切换">
              <button onClick={() => move(-1)}>← 上一个</button>
              <button className="primary" onClick={markKnown}>认识了 · 下一个 →</button>
            </nav>
            <p className="keyboard-hint">电脑用 ← → 切换 · 手机上左右滑动</p>
          </>
        ) : (
          <div className="list-view">
            <div className="list-tools" id="list-tools">
              <form className="sequence-jump" onSubmit={jumpToSequence}>
                <label htmlFor="sequence-number">序号跳转</label>
                <input
                  id="sequence-number"
                  type="number"
                  inputMode="numeric"
                  min="1"
                  max={visibleWords.length}
                  value={listJump}
                  onChange={(event) => setListJump(event.target.value)}
                  placeholder={`输入 1–${visibleWords.length}`}
                  aria-label={`输入当前列表中的单词序号，范围 1 到 ${visibleWords.length}`}
                />
                <button type="submit" disabled={!listJump}>定位</button>
              </form>
              <span className="list-range">当前显示 {listStart + 1}–{listEnd} / {visibleWords.length}</span>
            </div>
            <div className="list-head"><span>单词 / 音标</span><span>常用义与口语例句</span><span>词义连接</span><span>状态</span></div>
            {visibleWords.slice(listStart, listEnd).map((item, index) => {
              const sequence = listStart + index + 1;
              return (
              <article id={`word-row-${sequence}`} className={`word-row ${jumpedSequence === sequence ? 'is-jump-target' : ''}`} key={item.word}>
                <div className="row-word">
                  <b>{String(sequence).padStart(String(visibleWords.length).length, '0')}</b>
                  <button onClick={() => openWord(item.word)}>{item.word}</button>
                  <span>{item.ipa} · {item.level}</span>
                </div>
                <div className="row-meaning">
                  <strong>{item.meaning}</strong>
                  <p>{item.basic ? `使用频率 #${item.rank}` : item.example}</p>
                  <small>{item.basic ? '基础词条 · 点击单词查看与朗读' : item.translation}</small>
                </div>
                <div className="row-links">
                  {item.basic ? (
                    <><p><b>级</b>{item.level}</p><p><b>类</b>{item.tags.join(' · ') || '母语扩展'}</p></>
                  ) : (
                    <><p><b>近</b>{item.synonyms.slice(0, 2).join(' · ')}</p><p><b>反</b>{item.antonyms.slice(0, 2).join(' · ')}</p><p><b>搭</b>{item.phrases[0]?.phrase}</p></>
                  )}
                </div>
                <div className="row-actions">
                  <button onClick={() => speak(item.word)} aria-label={`播放 ${item.word}`}>▶</button>
                  <button className={saved.includes(item.word) ? 'is-saved' : ''} onClick={() => toggleSaved(item.word)} aria-label="收藏">{saved.includes(item.word) ? '♥' : '♡'}</button>
                  <span className={known.includes(item.word) ? 'known' : ''}>{known.includes(item.word) ? '已学' : '待学'}</span>
                </div>
              </article>
              );
            })}
            {listPageCount > 1 && (
              <nav className="list-pagination" aria-label="速览分页">
                <button onClick={() => changeListPage(listPage - 1)} disabled={listPage === 0}>← 上一组</button>
                <span>第 {listPage + 1} / {listPageCount} 组</span>
                <button onClick={() => changeListPage(listPage + 1)} disabled={listPage >= listPageCount - 1}>下一组 →</button>
              </nav>
            )}
          </div>
        )}
      </section>

      <aside className="library-strip" aria-label="目标词库构成">
        <div><span>当前词库</span><strong>20,000</strong><small>按英语母语环境中的实用频率整理</small></div>
        {libraryStats.map((item) => <div key={item.label}><span>{item.label}</span><strong>{item.count}</strong><small>目标词条</small></div>)}
        <p>已收录20,000个基础词条，并保留重点单词的精编口语内容。</p>
      </aside>
    </main>
  );
}
