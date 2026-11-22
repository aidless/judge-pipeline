# CENSUS.md — 建造前普查结论

## 判决

**`MUST_BUILD_NEW`**。主会话普查（2026-11-22，产物
`notes/2026-11-22-普查-判读流水线是否已打包-v3.json`）在 home 一级目录（排除工作区根）
与 `~/.dsh/skills` 一级目录、depth=1 自身文件的域内，扫描 **663 个候选**，无一满足谓词。
`hits = []`；只有两个 partial：`dsh-workspace`（仅有说明 md 与无关测试文件）、
`qoder-hot100-trial`（仅有一份 gate 脚本备份），都缺整套三件套。

**本仓即满足谓词的那份**：同目录同时有 A（六步判读流水线说明 + 判读 + 断言 + 核销/golden + 用法）、
B（`judge_pipeline.cli` 结构断言 CLI，带退出码）、C（顶层 `tests/` 与 `cli selftest`）。

## 谓词（逐字取自普查产物）

```
同目录同时有 A(判读流水线说明md:六步+判读+断言+golden/核销+用法)
  + B(judge/run/gate结构断言CLI带退出码) + C(顶层test/selftest)
```

扫描域：`home 一级目录(排除工作区根) + ~/.dsh/skills 一级目录，depth=1 自身文件`。

## 普查自检

- **正控绿**：已知满足判据的产物被判满足（selftest 正控 = 真实 tier63 判读文件，10 条 / A2-B6-C2）。
- **三注入红**：表行/小节 id 错位、分布声明写错、小节编号跳号，各自必须 FAIL。
- **漏根负控**：删掉 C 档段必须 FAIL。

本仓把这套自检原样落进 `python3 -m judge_pipeline.cli selftest`（5/5 cases）与
`tests/test_cli.py`（8 个 unittest），CI 每次 push/PR 都跑。

## 读法边界

普查只答「这个东西盘上有没有」，不答额度、身份闸、发布通道。
本仓的 `check`/`selftest` 退出码只答「判读稿结构是否自洽」，不答判级内容是否正确——
A/B/C 的内容质量仍需人工判读与 golden 对照。
