"""judge-pipeline — 抖音收藏判读六步闭环的可安装 skill + CLI。

核心承诺：判读稿的结构一致性不是「记得去检查」，而是有退出码的机器闸
（表行/小节/档段/分布/id 清单五组断言，注入违规必红）。
"""
from __future__ import annotations

__all__ = ["__version__"]
__version__ = "0.1.0"
