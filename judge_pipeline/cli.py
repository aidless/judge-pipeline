"""judge_pipeline.cli — 抖音收藏判读结构闸。

把「六步闭环」的第 ④ 步（结构断言）做成有退出码的机器闸：
表行/小节/档段/分布/id 清单一致才 OK，任一断言 FAIL 即 exit 1。

    python3 -m judge_pipeline.cli check --file 收藏档-tier63判读.md [--expect N] [--ids list.json]
    python3 -m judge_pipeline.cli selftest

退出码：0 全过 / 1 任一断言 FAIL。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

# 四条正则逐字抄自真实 tier63 判读文件；改口径前先跑 selftest。
RE_ROW = r'^\|\s*\d+\s*\|\s*`(\d{15,20})`'
RE_SECTION = r'^###\s+(\d+)\.\s+`(\d{15,20})`'
RE_TIER_SPLIT = r'^##\s*([ABC])档\s*$'
RE_DIST = r'\*\*分布\*\*[：:].*?A\s*档\s*(\d+)\s*条.*?B\s*档\s*(\d+)\s*条.*?C\s*档\s*(\d+)\s*条'
RE_ANY_ID = r'\d{15,20}'

GROUPS = ("counts", "order", "numbering", "tiers", "ids")

# 内联夹具：三条记录，A/B/C 各一条；id 取自真实 tier63 的前三条。
FIXTURE_IDS = (
    "7698083929953258778",
    "7667464372691755234",
    "7679708872822607123",
)
FIXTURE_TIERS = ("A", "B", "C")


def real_sample_path() -> Path:
    """selftest 正控优先用的真实文件；跨机可移植，找不到时回退内联夹具。"""
    return Path.home() / "F:\\deepseek" / "notes" / "douyin-study" / "收藏档-tier63判读.md"


def build_fixture(
    row_ids: Optional[Sequence[str]] = None,
    numbers: Optional[Sequence[int]] = None,
    dist: Optional[Tuple[int, int, int]] = None,
    drop_tier: Optional[str] = None,
) -> str:
    """生成满足全部断言的内联判读文本；参数用于注入违规。"""
    rows = list(row_ids) if row_ids is not None else list(FIXTURE_IDS)
    nums = list(numbers) if numbers is not None else [1, 2, 3]
    declared = dist if dist is not None else (1, 1, 1)

    lines = [
        "# 判读 fixture",
        "",
        "## 汇总表",
        "",
        "| # | id | 级 | 一句话判据 |",
        "|---|---|---|---|",
    ]
    for i, (rid, tier) in enumerate(zip(rows, FIXTURE_TIERS), start=1):
        lines.append("| %d | `%s` | %s | fixture 第 %d 条 |" % (i, rid, tier, i))
    lines += [
        "",
        "**分布**：A 档 %d 条、B 档 %d 条、C 档 %d 条" % declared,
        "",
    ]
    for idx, (sid, tier) in enumerate(zip(FIXTURE_IDS, FIXTURE_TIERS)):
        if tier == drop_tier:
            continue
        lines += [
            "## %s档" % tier,
            "",
            "### %d. `%s` — fixture 第 %d 条" % (nums[idx], sid, idx + 1),
            "",
            "正文：可复核判据 fixture。",
            "",
        ]
    return "\n".join(lines) + "\n"


def parse_manifest(raw: object) -> Set[str]:
    """清单兼容 list[str] 与 list[dict{id:...}]；也容忍 dict 包一层 ids/items。"""
    if isinstance(raw, dict):
        raw = raw.get("ids") or raw.get("items") or []
    if not isinstance(raw, list):
        raise ValueError("--ids 清单须为 JSON 数组")
    out: Set[str] = set()
    for item in raw:
        value = item.get("id") if isinstance(item, dict) else item
        if isinstance(value, str) and re.fullmatch(RE_ANY_ID, value.strip()):
            out.add(value.strip())
    return out


def check_text(
    text: str,
    expect: Optional[int] = None,
    allowed_ids: Optional[Set[str]] = None,
) -> List[Tuple[str, str]]:
    """对一份判读文本跑五组断言，返回 [(组名, 失败原因)]；空列表=全过。"""
    fails: List[Tuple[str, str]] = []

    row_ids = re.findall(RE_ROW, text, re.M)
    sections = re.findall(RE_SECTION, text, re.M)
    sec_nums = [int(n) for n, _ in sections]
    sec_ids = [sid for _, sid in sections]
    expected_n = len(row_ids) if expect is None else expect

    # a) 表行数 == 小节数 == N
    if not (len(row_ids) == len(sections) == expected_n):
        fails.append((
            "counts",
            "表行数 %d != 小节数 %d != 期望 %d" % (len(row_ids), len(sections), expected_n),
        ))

    # b) 表行 id 顺序 == 小节 id 顺序（逐位）
    if row_ids != sec_ids:
        i = next(
            (k for k in range(min(len(row_ids), len(sec_ids))) if row_ids[k] != sec_ids[k]),
            min(len(row_ids), len(sec_ids)),
        )
        r = row_ids[i] if i < len(row_ids) else "<缺失>"
        s = sec_ids[i] if i < len(sec_ids) else "<缺失>"
        fails.append(("order", "第 %d 位 id 顺序错位: 表行=%s 小节=%s" % (i + 1, r, s)))

    # c) 小节编号 == 1..N 连续
    if sec_nums != list(range(1, expected_n + 1)):
        fails.append((
            "numbering",
            "小节编号非 1..%d 连续: 实际 %s" % (expected_n, sec_nums),
        ))

    # d) 各档小节数 == 分布声明；档间 id 无重叠；并集 == 全部 id
    parts = re.split(RE_TIER_SPLIT, text, flags=re.M)
    # re.split 带捕获组返回 [前段, 标签A, A段, 标签B, B段, ...]：标签要配它后面的段。
    tags, segs = parts[1::2], parts[0::2]
    tier_counts: Dict[str, int] = {t: 0 for t in "ABC"}
    tier_ids: Dict[str, Set[str]] = {t: set() for t in "ABC"}
    for tag, seg in zip(tags, segs[1:]):
        found = re.findall(RE_SECTION, seg, re.M)
        tier_counts[tag] += len(found)
        tier_ids[tag].update(sid for _, sid in found)

    if len(tags) != len(set(tags)):
        fails.append(("tiers", "档段标签重复: %s" % list(tags)))

    dist = re.search(RE_DIST, text, re.S)
    if dist is None:
        fails.append(("tiers", "缺 **分布** 声明或格式不匹配"))
    else:
        declared = dict(zip("ABC", (int(x) for x in dist.groups())))
        for tier in "ABC":
            if tier_counts[tier] != declared[tier]:
                fails.append((
                    "tiers",
                    "%s 档小节数 %d != 分布声明 %d" % (tier, tier_counts[tier], declared[tier]),
                ))

    for i, t1 in enumerate("ABC"):
        for t2 in "ABC"[i + 1:]:
            overlap = tier_ids[t1] & tier_ids[t2]
            if overlap:
                fails.append(("tiers", "%s/%s 档 id 重叠: %s" % (t1, t2, sorted(overlap))))

    union: Set[str] = set().union(*tier_ids.values())
    if union != set(sec_ids):
        fails.append((
            "tiers",
            "三档 id 并集 != 全部小节 id: 漏 %s / 多 %s"
            % (sorted(set(sec_ids) - union), sorted(union - set(sec_ids))),
        ))

    # e) 文中 15-20 位 id 全是「真实」：无游离 id；给了清单则小节 id 须全在清单内
    all_seen = set(re.findall(RE_ANY_ID, text))
    stray = all_seen - (set(row_ids) | set(sec_ids))
    if stray:
        fails.append(("ids", "文中出现未登记的 15-20 位 id: %s" % sorted(stray)))
    if allowed_ids is not None:
        unknown = set(sec_ids) - allowed_ids
        if unknown:
            fails.append(("ids", "小节 id 不在 --ids 清单: %s" % sorted(unknown)))

    return fails


def stats_of(text: str) -> str:
    """OK 行上的可复算计数。"""
    rows = len(re.findall(RE_ROW, text, re.M))
    secs = len(re.findall(RE_SECTION, text, re.M))
    parts = re.split(RE_TIER_SPLIT, text, flags=re.M)
    counts = {
        tag: len(re.findall(RE_SECTION, seg, re.M))
        for tag, seg in zip(parts[1::2], parts[0::2][1:])
    }
    return "rows=%d sections=%d tiers=A:%d,B:%d,C:%d" % (
        rows, secs, counts.get("A", 0), counts.get("B", 0), counts.get("C", 0)
    )


def _result_lines(label: str, fails: List[Tuple[str, str]], quiet: bool, ok_detail: str = "") -> List[str]:
    if not fails:
        head = " ".join(x for x in (label, ok_detail) if x)
        return ["OK %s checks=%d/%d failed=0" % (head, len(GROUPS), len(GROUPS))]
    bad = sorted({g for g, _ in fails})
    summary = "[FAIL] %s groups=%d/%d failed=%d (%s)" % (
        label, len(GROUPS) - len(bad), len(GROUPS), len(bad), ",".join(bad)
    )
    if quiet:
        return [summary]
    return ["[FAIL] %s" % msg for _, msg in fails] + [summary]


def run_check(file: str, expect: Optional[int], ids: Optional[str], quiet: bool) -> Tuple[int, List[str]]:
    """执行一次 check，返回 (退出码, 输出行)。不直接打印，便于 selftest 复用。"""
    label = file
    try:
        text = Path(file).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return 1, _result_lines(label, [("io", "无法读取 --file: %s" % exc)], quiet)

    allowed: Optional[Set[str]] = None
    if ids is not None:
        try:
            allowed = parse_manifest(json.loads(Path(ids).read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
            return 1, _result_lines(label, [("ids", "无法读取 --ids 清单: %s" % exc)], quiet)
        if not allowed:
            return 1, _result_lines(label, [("ids", "--ids 清单为空或无合法 id")], quiet)

    fails = check_text(text, expect=expect, allowed_ids=allowed)
    detail = stats_of(text)
    if allowed is not None:
        detail += " manifest=%d" % len(allowed)
    return (1 if fails else 0), _result_lines(label, fails, quiet, detail)


def run_selftest(quiet: bool = False) -> Tuple[int, List[str]]:
    """正控 + 三注入 + 漏根负控；每个用例的 expected/observed 都必须吻合。"""
    sample = real_sample_path()
    if sample.is_file():
        try:
            positive_text = sample.read_text(encoding="utf-8")
            positive_label = "正控(真实tier63)"
        except OSError:
            positive_text = build_fixture()
            positive_label = "正控(内联fixture-真实文件读失败)"
    else:
        positive_text = build_fixture()
        positive_label = "正控(内联fixture)"

    swapped = [FIXTURE_IDS[1], FIXTURE_IDS[0], FIXTURE_IDS[2]]
    cases = [
        (positive_label, "OK", check_text(positive_text)),
        ("注入1-表行/小节id错位", "FAIL", check_text(build_fixture(row_ids=swapped))),
        ("注入2-分布声明写错A3/B6/C1", "FAIL", check_text(build_fixture(dist=(3, 6, 1)))),
        ("注入3-小节编号跳号", "FAIL", check_text(build_fixture(numbers=[1, 3, 4]))),
        ("漏根负控-删C档段", "FAIL", check_text(build_fixture(drop_tier="C"))),
    ]

    lines: List[str] = []
    passed = 0
    for name, expected, fails in cases:
        observed = "FAIL" if fails else "OK"
        groups = sorted({g for g, _ in fails})
        ok = observed == expected
        passed += int(ok)
        if not quiet:
            lines.append(
                "[case %s] %s expected=%s observed=%s%s"
                % ("OK" if ok else "FAIL", name, expected, observed,
                   " groups=%s" % ",".join(groups) if groups else "")
            )
    lines.append("SELFTEST cases=%d/%d passed exit=%d" % (passed, len(cases), 0 if passed == len(cases) else 1))
    return (0 if passed == len(cases) else 1), lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="judge-pipeline",
        description="抖音收藏判读结构闸：表行/小节/档段/分布/id 一致性断言",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    check = sub.add_parser("check", help="对一份判读 md 跑五组结构断言")
    check.add_argument("--file", required=True, help="判读 md 路径")
    check.add_argument("--expect", type=int, help="期望条数 N，默认=表行数")
    check.add_argument("--ids", help="真实 id 清单 JSON（list[str] 或 list[dict{id}]）")
    check.add_argument("--quiet", action="store_true", help="只输出 OK/FAIL 汇总")
    selftest = sub.add_parser("selftest", help="正控 + 三注入 + 漏根负控")
    selftest.add_argument("--quiet", action="store_true", help="只输出汇总")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "check":
        rc, lines = run_check(args.file, args.expect, args.ids, args.quiet)
    else:
        rc, lines = run_selftest(args.quiet)
    for line in lines:
        print(line)
    return rc


if __name__ == "__main__":
    sys.exit(main())
