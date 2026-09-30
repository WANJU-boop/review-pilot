# 延后处理类型注解；环境检查仍在调用函数时才会发生。
from __future__ import annotations

# `import` 把 Python 标准库中的模块引入当前文件，之后才能使用其中的功能。
import shutil
import sys
from dataclasses import dataclass


# 圆括号里的两个数字组成元组：最低要求为 Python 3.11。
MIN_PYTHON = (3, 11)


# 每项检查都用相同的三个字段保存结果，CLI 因而可以统一显示。
# `frozen=True` 阻止创建结果后重新给字段赋值。
@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    message: str


# `= None` 使版本参数可省略；测试时也可传入指定版本。
# `-> CheckResult` 是返回值类型注解，说明函数会返回一个检查结果。
def check_python_version(
    version_info: tuple[int, int, int] | None = None
) -> CheckResult:
    # `or` 优先使用传入的非空元组，否则使用当前 Python 的实际版本。
    # `[:3]` 只取前三项：大版本号、小版本号、修订号。
    version = version_info or sys.version_info[:3]
    # `str(part) for part in ...` 逐个把数字变成文字；join 在中间加点。
    # 例如 (3, 11, 0) 会得到字符串 "3.11.0"。
    current = ".".join(str(part) for part in version[:3])
    required = ".".join(str(part) for part in MIN_PYTHON)
    # `*MIN_PYTHON` 把 (3, 11) 拆开，再补 0，组成 (3, 11, 0)。
    # 元组从左到右比较，因此 (3, 12, 0) 大于 (3, 11, 0)。
    ok = version >= (*MIN_PYTHON, 0)
    if ok:
        # f 字符串把花括号里的变量值插入结果消息。
        return CheckResult("python", True, f"Python {current} >= {required}")
    return CheckResult("python", False, f"Python {current} < {required}")


def check_git_available(git_path: str | None = None) -> CheckResult:
    # `is not None` 用于区分“没传路径”和“传了空字符串”。
    # 空字符串在测试中用来模拟找不到 Git 程序。
    # 只有没传路径时，才用 `shutil.which("git")` 到 PATH 里查找。
    path = git_path if git_path is not None else shutil.which("git")
    if path:
        return CheckResult("git", True, f"git found at {path}")
    return CheckResult("git", False, "git executable was not found in PATH")


def run_checks(git_path: str | None = None) -> list[CheckResult]:
    # 方括号创建列表；调用两个函数会立刻执行两项检查，
    # 并按列表里的顺序返回结果，便于 CLI 依次显示。
    return [
        check_python_version(),
        check_git_available(git_path=git_path),
    ]
