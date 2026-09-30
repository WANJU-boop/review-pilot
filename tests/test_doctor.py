# 延后处理函数的类型注解，不会改变断言的判断结果。
from __future__ import annotations

# 直接测试负责环境判断的函数，便于分别覆盖成功与失败情况。
from review_pilot.doctor import check_git_available, check_python_version


def test_python_version_check_accepts_supported_version() -> None:
    # 手动传入假定版本，不需要真的更换电脑上的 Python。
    result = check_python_version((3, 11, 0))

    # `is True` 核对布尔结果；点号读取 CheckResult 的字段。
    assert result.ok is True
    assert result.name == "python"
    assert ">= 3.11" in result.message


def test_python_version_check_rejects_old_version() -> None:
    result = check_python_version((3, 10, 9))

    # 同一函数也要验证低版本的失败分支。
    assert result.ok is False
    assert result.name == "python"
    assert "< 3.11" in result.message


def test_git_check_accepts_existing_path() -> None:
    # 传入非空字符串只测试“有路径”分支，并未真的检查该文件存在。
    result = check_git_available("/usr/bin/git")

    assert result.ok is True
    assert result.name == "git"
    assert "/usr/bin/git" in result.message


def test_git_check_rejects_missing_path() -> None:
    # 空字符串模拟“没有找到 git”，使测试不依赖当前电脑的 PATH。
    result = check_git_available("")

    assert result.ok is False
    assert result.name == "git"
    assert "not found" in result.message
