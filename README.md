# judge-pipeline

[![CI](https://github.com/aidless/judge-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/aidless/judge-pipeline/actions/workflows/ci.yml)

把"抖音收藏判读六步闭环"打包成可安装的 skill + CLI：从 5334 条收藏的 63 批判读里固化下来的方法，最后一步是**有退出码的结构闸**。

## 一句话定位

**判级不是注释，是退出码**：判读稿 + 清单 → 表行/小节/档段/分布/id 五组断言 → `OK`(rc=0) 才进入核销；注入违规必红。

可核对的数字：**6** 步闭环、**5** 组断言、**8** 个 unittest、**5/5** selftest cases（1 正控 + 3 注入 + 1 漏根）、tier63 真实样例 **10** 条（A2/B6/C2）。

## 安装

```bash
pip install -e .                 # 可选；纯标准库，不装也能跑
judge-pipeline check --file <判读md>
# 完全离线最短路径：
python3 -m judge_pipeline.cli check --file <判读md>
```

也可把仓根的 `SKILL.md` 装进 agent 的 skills 目录，六步流程随 skill 走。

## CLI 用法

```bash
# 基础：对真实 tier63 判读稿跑断言
python3 -m judge_pipeline.cli check --file '/home/liuzewen/F:\deepseek/notes/douyin-study/收藏档-tier63判读.md'

# 带真实 id 清单（list[dict{id}] 或 list[str] 都兼容）
python3 -m judge_pipeline.cli check --file <判读md> --ids '/home/liuzewen/F:\deepseek/data/douyin/C-tier63.json'

# 指定期望条数 + 只要汇总
python3 -m judge_pipeline.cli check --file <判读md> --expect 10 --quiet

# 闸自身的可信度：正控 OK + 三注入 FAIL + 漏根 FAIL
python3 -m judge_pipeline.cli selftest

python3 -m unittest discover -s tests
```

退出码只有两种：`0` = 全过（打印 `OK ...`），`1` = 至少一组断言失败（每条打 `[FAIL] <原因>`，末尾带 groups 汇总）。

## 六步闭环摘要

| 步 | 动作 | 产物 |
|---|---|---|
| ① 建清单 | 从待判池取一批，落 `list[dict{id}]` | `C-tierNN.json` |
| ② 抽素材 | 取 `body`，按粉丝/获赞正则截取、删首个"关注"、按 `\n展开\|\n发布时间\|展开全文` 截断 | `tierNN_mat.txt` |
| ③ 写判读 | **先定每条级别，再写分布声明**；汇总表顺序=正文顺序，六段式展开 | `收藏档-tierNN判读.md` |
| ④ 结构断言 | 本仓 CLI：counts/order/numbering/tiers/ids 五组，红即停 | `OK` rc=0 / `[FAIL]` rc=1 |
| ⑤ 核销 | `dy_uncollect_target.py --ids <逗号分隔> --scope <作用域>` | 待判池销账 |
| ⑥ 重建 | 重建索引 + golden 闸 + 台账（主会话统一落） | 下批可选材状态 |

判级标准与坑位见 [SKILL.md](SKILL.md)，建造前普查见 [CENSUS.md](CENSUS.md)。

## 目录

- `judge_pipeline/cli.py`：`check` / `selftest`、五组断言、退出码；四条正则逐字取自真实判读文件。
- `tests/test_cli.py`：8 个 unittest，内联 fixture，不依赖外部真实文件。
- `SKILL.md`：六步闭环、判级标准、清洗正则、坑位、迁移说明。
- `CENSUS.md`：`MUST_BUILD_NEW` 判决与谓词。
- `.github/workflows/ci.yml`：Python 3.11，push/PR 跑 unittest + selftest。

## 同套工具：判据工具链四仓

judge-pipeline 把六步判读闭环固化成带退出码的结构闸，另外三仓分别管"判据从哪来 / 省了多少 token / 任意产物过不过规则"——同一主题：把判据从注释变成会变红的退出码。都是从抖音收藏 63 批判读里长出来的可复用资产：

| 仓 | 回答的问题 | 核验数字 |
|---|---|---|
| [agent-judgment-skills](https://github.com/aidless/agent-judgment-skills) | 判据 skill 从哪来？ | 44 个逐字保留的 SKILL.md，6 类 |
| [token-ruler](https://github.com/aidless/token-ruler) | 省了多少 token、什么口径？ | char4/word/tiktoken 三方法，8 unittest |
| [gate-runner](https://github.com/aidless/gate-runner) | 任意产物过不过一组规则？ | 四类规则 + 正控/三注入违规 selftest |
| [judge-pipeline](https://github.com/aidless/judge-pipeline) | 一份判读稿结构合格吗？ | 五组断言 + tier63 真样例 A2/B6/C2 |

顶层汇总：[JUDGMENT_TOOLKIT.md](https://github.com/aidless/aidless/blob/master/JUDGMENT_TOOLKIT.md)。四仓均 v0.1.0、CI 全绿。

MIT © liuzewen.
