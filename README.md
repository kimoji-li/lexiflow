# 词流 LexiFlow

面向英语口语与雅思高频词汇的移动端友好学习网站。

## 词库

- 25,000 个按英语使用频率整理的基础词条
- 前 15,000 名显示**口语常用程度**（频率档位 + 使用场景）、拆分的口语义项，以及可核实的近义词、反义词和派生词
- 前 15,000 名优先显示经过筛选的真实中英双语口语句；没有合格句子时不使用批量模板凑数
- 同音词（如 knead / need、to / two / too、for / four）自动显示发音辨析提示
- 对用途明确的雅思口语、Task 1 或 Task 2 词汇显示场景提示
- 保留重点单词的精编口语用法、例句和短语
- 25,000 词按 1,000 词一组渐进载入，弱网手机可逐批显示并自动重试
- 基础数据派生自 [ECDICT](https://github.com/skywind3000/ECDICT)，按 MIT License 使用
- 词义关系、场景、派生词派生自 [Open English WordNet 2024](https://en-word.net/)，按 CC BY 4.0 使用
- 双语例句选自 [Tatoeba](https://tatoeba.org/)，按 CC BY 2.0 FR 使用；仓库只保留筛选后的紧凑数据
- 如需重建例句数据，先下载 Tatoeba 的 `per_language/eng`、`per_language/cmn` 句子导出和 `links.tar.bz2`，运行 `scripts/build_tatoeba_examples.py /path/to/exports`
- 安装 `wn==1.1.1` 并下载 `oewn:2024` 后，运行 `scripts/generate_basic_words.py /path/to/ecdict.csv` 可重新生成词库

## 免费发布

代码已配置 GitHub Pages 自动发布。推送到 GitHub 仓库的 `main` 分支后，
在仓库 Settings → Pages 中将 Source 设为 GitHub Actions 即可。
