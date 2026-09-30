# 延后处理类型注解；这里只影响注解，不会自动建立 RepoInfo 对象。
from __future__ import annotations

# `dataclass` 会根据字段自动生成构造方法和便于查看的对象表示。
from dataclasses import dataclass


# 这个类描述“一次查询得到的仓库信息”；类本身不会执行 Git 命令。
# `frozen=True` 阻止对象创建后再给字段直接赋值。
@dataclass(frozen=True)
class RepoInfo:
    # `字段名: 类型` 声明字段及其预期类型。
    # `str` 表示文字，`bool` 表示 True 或 False。这些只是类型注解，
    # 不会自动在运行时检查数据，也不会自动查询 Git 状态。
    root: str
    branch: str
    head: str
    has_staged_changes: bool
    has_unstaged_changes: bool


# RawDiff 把原始 diff 保存为一段文字，供后续步骤处理。
@dataclass(frozen=True)
class RawDiff:
    text: str

    # `@property` 让调用者写 `raw_diff.is_empty`，无需加 `()`。
    # 每次访问时，都根据 text 的当前值计算结果。
    @property
    def is_empty(self) -> bool:
        # `self` 指当前这一个 RawDiff 对象；`==` 比较左右两个值。
        # 只有文字恰好为 `""` 才返回 True；空格或换行也算有内容。
        return self.text == ""
