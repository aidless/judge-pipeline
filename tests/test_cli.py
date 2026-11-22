"""judge-pipeline CLI 单元测试：全部使用内联 fixture，不依赖外部真实文件。"""
from __future__ import annotations

import unittest

from judge_pipeline.cli import (
    FIXTURE_IDS,
    build_fixture,
    check_text,
    parse_manifest,
    run_selftest,
)


class PipelineTests(unittest.TestCase):
    @staticmethod
    def _groups(fails):
        return {g for g, _ in fails}

    def test_01_selftest_positive_control(self):
        """正控：内联 fixture 全过，且完整 selftest 正控/三注入/漏根全绿。"""
        self.assertEqual(check_text(build_fixture()), [])
        rc, lines = run_selftest(quiet=True)
        self.assertEqual(rc, 0, lines)
        self.assertIn("cases=5/5", lines[-1])

    def test_02_injection_order(self):
        """注入①：表行 id 与小节 id 顺序错位 → FAIL(order)。"""
        swapped = [FIXTURE_IDS[1], FIXTURE_IDS[0], FIXTURE_IDS[2]]
        fails = check_text(build_fixture(row_ids=swapped))
        self.assertIn("order", self._groups(fails))
        self.assertNotIn("counts", self._groups(fails))

    def test_03_injection_distribution(self):
        """注入②：分布声明写错 A3/B6/C1 → FAIL(tiers)。"""
        fails = check_text(build_fixture(dist=(3, 6, 1)))
        self.assertIn("tiers", self._groups(fails))

    def test_04_injection_numbering(self):
        """注入③：小节编号 1,3,4 跳号 → FAIL(numbering)。"""
        fails = check_text(build_fixture(numbers=[1, 3, 4]))
        self.assertIn("numbering", self._groups(fails))

    def test_05_missing_root_negative(self):
        """漏根负控：删掉 C 档段 → FAIL，且必须命中 tiers。"""
        fails = check_text(build_fixture(drop_tier="C"))
        self.assertTrue(fails)
        self.assertIn("tiers", self._groups(fails))

    def test_06_id_reality_with_manifest(self):
        """id 真实性：list[dict{id}] 与 list[str] 两种清单都兼容。"""
        dict_manifest = [{"id": i, "desc": "x"} for i in FIXTURE_IDS]
        self.assertEqual(check_text(build_fixture(), allowed_ids=parse_manifest(dict_manifest)), [])
        str_manifest = parse_manifest(list(FIXTURE_IDS[:2]))
        fails = check_text(build_fixture(), allowed_ids=str_manifest)
        self.assertIn("ids", self._groups(fails))

    def test_07_numbering_continuous(self):
        """编号连续：1..N 必须逐位相等，2,3,4 同样判红。"""
        self.assertEqual(check_text(build_fixture()), [])
        self.assertIn("numbering", self._groups(check_text(build_fixture(numbers=[2, 3, 4]))))

    def test_08_stray_id_detection(self):
        """文中出现未登记的 15-20 位 id → FAIL(ids)。"""
        text = build_fixture().replace(
            "正文：可复核判据 fixture。",
            "正文：1234567890123456789 是游离 id。",
            1,
        )
        self.assertIn("ids", self._groups(check_text(text)))


if __name__ == "__main__":
    unittest.main()
