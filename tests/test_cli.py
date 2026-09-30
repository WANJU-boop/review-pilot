# 延后处理函数的类型注解；pytest 仍按 test_ 名称寻找测试。
from __future__ import annotations

# io.StringIO 是“放在内存里的文字输出框”，可代替终端收集打印内容。
import io
import json
from unittest.mock import patch

# 测试调用真实的包版本号和 main() 函数，而不是复制一份实现。
from review_pilot import __version__
from review_pilot.cli import main
from review_pilot.git_client import GitError, NotGitRepositoryError
from review_pilot.models import RawDiff, RepoInfo


# `args: list[str]` 表示传入字符串列表；`tuple[int, str, str]`
# 表示依次返回退出码、正常输出、错误输出这三个值。
def run_cli(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    # 直接给 main() 传参数和两个输出框，就能观察命令行为。
    exit_code = main(args, stdout=stdout, stderr=stderr)
    # getvalue() 取回写入 StringIO 的文字；逗号分隔三项返回值。
    return exit_code, stdout.getvalue(), stderr.getvalue()


# pytest 会自动找到以 test_ 开头的函数并执行。
def test_help_shows_review_and_doctor_commands() -> None:
    # 左边三个变量按顺序接收 run_cli 返回的三个值，称为“解包”。
    exit_code, stdout, stderr = run_cli(["--help"])

    # assert 后的条件若为 False，pytest 会把这一项标记为失败。
    # `in` 检查某段文字是否出现在输出中。
    assert exit_code == 0
    assert "doctor" in stdout
    assert "review" in stdout
    assert "repo-info" in stdout
    assert "diff" in stdout
    assert "--version" in stdout
    assert stderr == ""


def test_version_uses_package_version() -> None:
    exit_code, stdout, stderr = run_cli(["--version"])

    assert exit_code == 0
    # strip() 去掉输出末尾的换行，再与包里的版本号比较。
    assert stdout.strip() == __version__
    assert stderr == ""


def test_doctor_command_succeeds_in_normal_environment() -> None:
    # 这里使用当前电脑的真实 Python/Git 环境，是一次基本的运行验证。
    exit_code, stdout, stderr = run_cli(["doctor"])

    assert exit_code == 0
    assert "[OK] python:" in stdout
    assert "[OK] git:" in stdout
    assert stderr == ""


def test_no_subcommand_prints_help() -> None:
    # [] 是空参数列表，模拟只输入 review-pilot 而不跟子命令。
    exit_code, stdout, stderr = run_cli([])

    assert exit_code == 0
    assert "doctor" in stdout
    assert "review" in stdout
    assert stderr == ""


def test_review_help_shows_future_local_review_shape() -> None:
    # review 的帮助仍说明命令形式，实际读取逻辑已在 M02 接入。
    exit_code, stdout, stderr = run_cli(["review", "--help"])

    assert exit_code == 0
    assert "review-pilot review" in stdout
    assert "--staged" in stdout
    assert "--base" in stdout
    assert "M02 reads staged Git changes" in stdout
    assert stderr == ""


def test_review_command_reuses_empty_staged_diff_path() -> None:
    # 用假结果固定“暂存区为空”，避免测试受本机 Git 状态影响。
    with patch("review_pilot.cli.DiffReader") as reader_class:
        reader_class.return_value.staged_raw_diff.return_value = RawDiff("")
        exit_code, stdout, stderr = run_cli(["review", "--staged"])

    assert exit_code == 1
    assert stdout == ""
    assert stderr == "no staged changes\n"


def test_repo_info_prints_json_on_stdout() -> None:
    info = RepoInfo("/example/repo", "main", "abc123", False, True)
    with patch("review_pilot.cli.GitClient.from_cwd") as from_cwd:
        from_cwd.return_value.repo_info.return_value = info
        exit_code, stdout, stderr = run_cli(["repo-info", "--json"])

    assert exit_code == 0
    assert json.loads(stdout) == {
        "root": "/example/repo",
        "branch": "main",
        "head": "abc123",
        "has_staged_changes": False,
        "has_unstaged_changes": True,
    }
    assert stderr == ""


def test_repo_info_reports_non_repository_on_stderr() -> None:
    with patch("review_pilot.cli.GitClient.from_cwd") as from_cwd:
        from_cwd.return_value.repo_info.side_effect = NotGitRepositoryError(
            "missing .git"
        )
        exit_code, stdout, stderr = run_cli(["repo-info", "--json"])

    assert exit_code == 2
    assert stdout == ""
    assert stderr == "not a git repository: missing .git\n"


def test_diff_reports_empty_staging_area() -> None:
    with patch("review_pilot.cli.DiffReader") as reader_class:
        reader_class.return_value.staged_raw_diff.return_value = RawDiff("")
        exit_code, stdout, stderr = run_cli(["diff", "--staged", "--raw"])

    assert exit_code == 1
    assert stdout == ""
    assert stderr == "no staged changes\n"


def test_diff_prints_nonempty_raw_diff_once() -> None:
    raw_text = "diff --git a/demo.py b/demo.py\n"
    with patch("review_pilot.cli.DiffReader") as reader_class:
        reader_class.return_value.staged_raw_diff.return_value = RawDiff(raw_text)
        exit_code, stdout, stderr = run_cli(["diff", "--staged", "--raw"])

    assert exit_code == 0
    assert stdout == raw_text  # 已有换行时不能再额外添加空行。
    assert stderr == ""


def test_diff_reports_git_error_on_stderr() -> None:
    with patch("review_pilot.cli.DiffReader") as reader_class:
        reader_class.return_value.staged_raw_diff.side_effect = GitError(
            "bad git command"
        )
        exit_code, stdout, stderr = run_cli(["diff", "--staged", "--raw"])

    assert exit_code == 2
    assert stdout == ""
    assert stderr == "git error: bad git command\n"


def test_review_base_does_not_silently_read_staged_diff() -> None:
    # --base 仍是未来选项，应明确拒绝，而不是输出另一个范围的 diff。
    exit_code, stdout, stderr = run_cli(["review", "--base", "main"])

    assert exit_code == 2
    assert stdout == ""
    assert stderr == "review --base is not implemented yet\n"
