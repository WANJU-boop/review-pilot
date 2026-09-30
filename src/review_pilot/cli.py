# 延后处理类型注解，不改变下方命令分支的实际执行顺序。
from __future__ import annotations

# argparse 把终端输入的文字解析成选项与子命令。
import argparse

# json 把 Python 字典转换成可以给其他程序读取的 JSON 文字。
import json

# sys 提供当前进程收到的参数，以及正常输出和错误输出通道。
import sys
from collections.abc import Sequence
from typing import TextIO

# 前面的点表示从当前 review_pilot 包导入，而非从别的顶层文件导入。
from . import __version__

# DiffReader 负责取得并包装暂存区的原始 diff。
from .diff_reader import DiffReader
from .doctor import run_checks

# GitClient 查询仓库；两个错误类让 CLI 能输出简短提示并给出退出码。
from .git_client import GitClient, GitError, NotGitRepositoryError


# 这个函数建立命令菜单，并不执行代码审查。
# `-> argparse.ArgumentParser` 是返回值类型注解。
def build_parser() -> argparse.ArgumentParser:
    # 创建解析器时指定名称和说明，这些文字会出现在 --help 中。
    parser = argparse.ArgumentParser(
        prog="review-pilot",
        description="Code review agent for local diffs, CI, and PR workflows.",
    )
    # 以 -- 开头的是有名字的命令行选项。
    # action="version" 告诉 argparse：遇到它就输出指定的版本号。
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
    )

    # 子命令写在 `review-pilot` 后面，例如 `doctor`。
    # `dest="command"` 让解析后的命令名称保存在 args.command。
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "doctor", help="Check whether the local environment can run review-pilot."
    )
    review_parser = subparsers.add_parser(
        "review", help="Read staged Git changes for review."
    )
    # `store_true`：出现 --staged 时为 True，没出现时为 False。
    review_parser.add_argument(
        "--staged", action="store_true", help="Review staged Git changes."
    )
    # --base 后面要跟一个值；REF 是帮助文档中给这个值的占位名称。
    review_parser.add_argument(
        "--base",
        metavar="REF",
        help="Review changes against a base ref. Implemented later.",
    )
    # repo-info 与 diff 是两个新增子命令；这里只登记可接受的写法。
    repo_parser = subparsers.add_parser(
        "repo-info",
        help="Print Git repository metadata.",
    )
    # required=True 表示必须明确输入 --json；store_true 表示无需再跟值。
    repo_parser.add_argument(
        "--json",
        action="store_true",
        required=True,
        help="Print repository metadata as JSON.",
    )
    diff_parser = subparsers.add_parser(
        "diff",
        help="Read Git diffs for later review steps.",
    )
    # 本阶段只支持已暂存的原始 diff，因此要求两个开关都出现。
    diff_parser.add_argument(
        "--staged",
        action="store_true",
        required=True,
        help="Read staged Git changes.",
    )
    diff_parser.add_argument(
        "--raw",
        action="store_true",
        required=True,
        help="Print the raw unified diff.",
    )
    return parser


# 这个单独的解析器专门输出 `review-pilot review --help` 的说明。
# review --staged 已接入读取逻辑；--base 仍是以后阶段的选项。
def build_review_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="review-pilot review",
        description="Local review workflow entry. M02 reads staged Git changes.",
    )
    parser.add_argument(
        "--staged", action="store_true", help="Review staged Git changes."
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        help="Review changes against a base ref. Implemented later.",
    )
    return parser


# 函数名前的下划线表示它主要供本模块内部调用。
# `TextIO` 表示文字输出通道；`int` 表示返回整数退出码。
def _run_doctor(out: TextIO, err: TextIO) -> int:
    exit_code = 0
    # `for` 逐个处理 run_checks() 返回的 CheckResult。
    for result in run_checks():
        if result.ok:
            # `file=out` 把成功信息写到正常输出通道。
            print(f"[OK] {result.name}: {result.message}", file=out)
        else:
            # `file=err` 把失败信息写到错误输出通道；1 表示检查失败。
            print(f"[FAIL] {result.name}: {result.message}", file=err)
            exit_code = 1
    return exit_code


# 把仓库查询结果变成 JSON；stdout 放数据，stderr 放错误。
def _run_repo_info(stdout: TextIO, stderr: TextIO) -> int:
    try:
        # 创建 GitClient 后立刻调用 repo_info()，取得当前仓库的一份快照。
        info = GitClient.from_cwd().repo_info()
    except NotGitRepositoryError as exc:
        # `as exc` 把捕获到的异常保存为变量，便于输出错误原因。
        print(f"not a git repository: {exc}", file=stderr)
        return 2
    except GitError as exc:
        # 其他 Git 命令失败时，保留不同的错误前缀，仍返回退出码 2。
        print(f"git error: {exc}", file=stderr)
        return 2

    # 花括号创建字典：左边是 JSON 字段名，右边是 info 对象里的值。
    # dumps() 把字典转换成 JSON 字符串；缩进 2 格便于人阅读。
    # ensure_ascii=False 让中文等非 ASCII 字符保持原样显示。
    print(
        json.dumps(
            {
                "root": info.root,
                "branch": info.branch,
                "head": info.head,
                "has_staged_changes": info.has_staged_changes,
                "has_unstaged_changes": info.has_unstaged_changes,
            },
            ensure_ascii=False,
            indent=2,
        ),
        file=stdout,
    )
    return 0


# diff 和 review --staged 共用这条读取路径；这里仍不做审查判断。
def _run_diff(stdout: TextIO, stderr: TextIO) -> int:
    try:
        # DiffReader 用 GitClient 读取暂存区，再包装成 RawDiff 对象。
        raw_diff = DiffReader(GitClient.from_cwd()).staged_raw_diff()
    except NotGitRepositoryError as exc:
        print(f"not a git repository: {exc}", file=stderr)
        return 2
    except GitError as exc:
        print(f"git error: {exc}", file=stderr)
        return 2

    # 空暂存区是可预期的情况：给出明确提示和退出码 1。
    if raw_diff.is_empty:
        print("no staged changes", file=stderr)
        return 1

    # print 默认会补一个换行；原始 diff 已以换行结尾时不要再补。
    # `A if 条件 else B` 根据末尾是否已有换行，选择 end 的值。
    print(raw_diff.text, end="" if raw_diff.text.endswith("\n") else "\n", file=stdout)
    return 0


# `| None` 表示值可以没有；`= None` 表示调用时可以省略参数。
# 测试可自行传入 argv/stdout/stderr，无需每次启动真实终端命令。
def main(
    argv: Sequence[str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    # 有测试提供的输出通道时就使用它，否则使用终端默认通道。
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = build_parser()
    # sys.argv[0] 是程序名，因此 [1:] 只保留用户输入的参数。
    # 调用者传了 argv 时，list(argv) 把它变成独立的列表。
    command_args = list(argv) if argv is not None else sys.argv[1:]

    # `or` 连接几种情况：没给参数（空列表 []）或请求帮助。
    if not command_args or command_args == ["--help"] or command_args == ["-h"]:
        parser.print_help(out)
        # 返回 0 表示这次命令正常完成。
        return 0

    if command_args == ["--version"]:
        print(__version__, file=out)
        return 0

    # `in` 检查整个参数列表是否等于右边列出的某一种情况。
    if command_args in (["review"], ["review", "--help"], ["review", "-h"]):
        build_review_parser().print_help(out)
        return 0

    # 其他输入交给 argparse 解析，解析后可通过 args.command 看子命令。
    args = parser.parse_args(command_args)

    if args.command == "doctor":
        return _run_doctor(out, err)

    # 解析器已把第一个词放进 args.command；按它选择真正的处理函数。
    if args.command == "repo-info":
        return _run_repo_info(out, err)

    if args.command == "diff":
        return _run_diff(out, err)

    if args.command == "review":
        # --base 是预留选项；不能把它误当成 --staged 的范围来读取。
        if args.base is not None:
            print("review --base is not implemented yet", file=err)
            return 2
        # M02 让 review 复用暂存区 diff 读取；仍未生成审查报告。
        return _run_diff(out, err)

    parser.print_help(out)
    return 0
