# 这句让类型注解延后处理，所以类定义内部可以先写 `-> GitClient`。
# 它只影响注解的处理方式，不会改变下面函数执行的顺序。
from __future__ import annotations

# `subprocess` 让 Python 启动电脑上安装的 `git` 程序。
import subprocess

# `from 模块 import 名字` 只导入模块里需要的那个名字。
from dataclasses import dataclass

# Path 用对象表示路径，并提供 `.resolve()` 等路径操作。
from pathlib import Path

# Sequence[str] 表示由字符串组成的序列，例如 ["diff", "--quiet"]。
from typing import Sequence

# 前面的点表示“从当前 review_pilot 包里导入”。
# GitClient 查询仓库后，RepoInfo 用来保存查询结果。
from .models import RepoInfo


# `class 子类(父类)` 表示子类也是一种父类，可进一步区分错误。
# 定义错误类型本身不会报错；执行 `raise GitError(...)` 才会抛出。
class GitError(RuntimeError):
    pass  # 暂时不添加新行为，只用这个类名标识 Git 相关错误。


class NotGitRepositoryError(GitError):
    pass  # 它属于 GitError；捕获 GitError 时也能捕获这种错误。


# `@dataclass` 根据下面的字段自动生成初始化方法 `__init__(cwd)`。
# `frozen=True` 表示创建后不能通过 `client.cwd = 新路径` 重新赋值。
@dataclass(frozen=True)
class GitClient:
    # `cwd: Path`：对象里有一个名为 cwd、预期类型为 Path 的字段。
    # cwd 是以后执行 Git 命令的起始目录，可以是仓库的子目录；
    # 它不一定是 Git 仓库根目录。
    cwd: Path

    # 类方法可以直接由类调用：GitClient.from_cwd("src")。
    # Python 自动把 GitClient 类传给 cls；此时还没有创建实例。
    @classmethod
    def from_cwd(cls, cwd: str | Path | None = None) -> GitClient:
        # `str | Path | None`：传入值可为路径字符串、Path 对象或 None。
        # `= None` 表示调用时可以省略 cwd；`-> GitClient` 标注返回类型。
        # 类型注解只描述预期，不会自动检查这里是否为 Git 仓库。
        # `cwd or "."`：cwd 为 None 或空字符串时，用 "." 表示当前目录。
        # `Path(...)` 将字符串变成路径对象，`.resolve()` 得到绝对路径；
        # 这一步不会自动找到 Git 仓库根目录，也不会验证 Git 状态。
        # `cls(...)` 调用 dataclass 自动生成的构造方法，保存 cwd 字段。
        return cls(Path(cwd or ".").resolve())

    # 这个方法负责“收集答案并填表”。定义方法时不查询 Git；
    # 调用 client.repo_info() 时，才会依次执行下面的查询。
    def repo_info(self) -> RepoInfo:
        # `self` 是当前 GitClient 对象；末尾的 () 表示调用方法。
        # 单个 = 把每次查询得到的值保存到左边的局部变量。
        root = self.repo_root()
        branch = self.current_branch()
        head = self.head_sha()
        # RepoInfo(...) 创建一份数据记录，return 把它交给调用者。
        # 左边的 root/branch/head 是 RepoInfo 字段名，右边是查询结果。
        # root 原本是 Path；str(root) 把它转成 RepoInfo.root 需要的文字。
        # 两种修改状态的方法在本类下方定义；它们分别比较不同位置。
        return RepoInfo(
            root=str(root),
            branch=branch,
            head=head,
            has_staged_changes=self.has_staged_changes(),
            has_unstaged_changes=self.has_unstaged_changes(),
        )

    # cwd 是 Git 命令的起始目录；这里要问 Git 仓库真正的根目录。
    def repo_root(self) -> Path:
        # _run() 执行 `git rev-parse --show-toplevel`。
        # allow_not_git=True 让 _run() 在非零退出码时先返回结果，
        # 以便本方法根据 returncode 抛出更具体的错误。
        result = self._run(["rev-parse", "--show-toplevel"], allow_not_git=True)
        # returncode 为 0 通常表示命令成功；!= 0 表示失败。
        if result.returncode != 0:
            # _clean_error() 提取 Git 错误的最后一行；若为空，
            # or 使用右边的备用文字。raise 会中断方法并抛出异常。
            raise NotGitRepositoryError(
                _clean_error(result.stderr) or "not a git repository"
            )
        # stdout 是 Git 的正常输出；strip() 去掉末尾换行。
        # Path(...) 创建路径对象，resolve() 将其规范化为绝对路径。
        return Path(result.stdout.strip()).resolve()

    # 查询当前分支名；无普通分支时，改用短提交编号表示位置。
    def current_branch(self) -> str:
        # 对应终端命令 `git branch --show-current`。
        result = self._run(["branch", "--show-current"])
        branch = result.stdout.strip()
        # 非空字符串在 if 中视为 True；例如 branch 为 "main"。
        if branch:
            return branch
        # 如果分支名为空，截图用短 HEAD 标识 detached HEAD 状态。
        # 对应 `git rev-parse --short HEAD`；f 字符串插入短编号。
        detached = self._run(["rev-parse", "--short", "HEAD"]).stdout.strip()
        return f"HEAD detached at {detached}"

    # SHA 是提交的编号；这里查询当前 HEAD 对应的完整编号。
    def head_sha(self) -> str:
        # 对应 `git rev-parse HEAD`，得到的文字去掉末尾换行后返回。
        return self._run(["rev-parse", "HEAD"]).stdout.strip()

    # 暂存区（staged）保存已执行 git add、准备进入下次提交的内容。
    # 这里比较 HEAD（上次提交）与暂存区，回答“有差异吗”。
    def has_staged_changes(self) -> bool:
        # 对应 `git diff --staged --quiet`。
        # --quiet 不输出补丁内容，只用退出码报告是否存在差异。
        # 传入 check=False，让 _run() 保留退出码 1 供我们判断。
        result = self._run(["diff", "--staged", "--quiet"], check=False)
        # == 是比较，不是赋值：退出码恰好为 1 时返回 True，
        # 为 0 时返回 False。此处沿用教程写法；其他错误码也会是 False。
        return result.returncode == 1

    # 工作区是文件目前在磁盘上的内容；unstaged 指尚未进入暂存区的差异。
    # 这里比较暂存区与工作区，回答“还有未暂存的差异吗”。
    def has_unstaged_changes(self) -> bool:
        # 对应 `git diff --quiet`；省略 --staged，就比较另一组位置。
        result = self._run(["diff", "--quiet"], check=False)
        return result.returncode == 1

    # 前两个方法只返回“有没有变化”；这里返回实际的暂存区 diff 文字。
    def staged_raw_diff(self) -> str:
        # 对应 `git diff --staged --no-ext-diff --binary`。
        # --staged 只取已暂存的变化；--no-ext-diff 禁止调用外部 diff 工具；
        # --binary 让二进制文件的变化也尽量保留在 Git 补丁输出中。
        # .stdout 是命令的正常输出；此处按教程预期它是字符串。
        return self._run(["diff", "--staged", "--no-ext-diff", "--binary"]).stdout

    # 所有需要 Git 的方法都调用这里，避免各处重复写启动程序的代码。
    def _run(
        self,
        args: Sequence[str],
        *,
        check: bool = True,
        allow_not_git: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        # args 是 Git 后面的参数，例如 ["branch", "--show-current"]。
        # 单独一行的 * 表示后面两个参数只能按名字传入，如 check=False。
        # -> ... 是返回类型注解；CompletedProcess 会保存输出和退出码。
        result = subprocess.run(
            # *args 把序列逐项展开：最终列表类似 ["git", "branch", "--show-current"]。
            # 用列表传参，不必自己拼接一整条 shell 命令。
            ["git", *args],
            # 只让启动的 Git 程序从 self.cwd 目录运行，不改变 Python 的工作目录。
            cwd=self.cwd,
            # 把 Git 输出解码成字符串，和 CompletedProcess[str] 对应。
            text=True,
            # PIPE 表示捕获正常输出与错误输出，而非直接打印到终端。
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # 先让 subprocess 返回所有退出码；下面再按本类规则处理。
            check=False,
        )
        # and 要求两个条件同时成立：调用者要求检查，且 Git 返回非零。
        if check and result.returncode != 0:
            # 这个开关让 repo_root() 自己检查失败结果并抛出专门的异常。
            # 按截图实现，它放行的是所有非零码，并未区分具体 Git 错误。
            if allow_not_git:
                return result
            # _clean_error(...) 优先取 Git 给出的错误；没有错误文字时，
            # f 字符串中的 ' '.join(args) 拼出命令参数作为备用提示。
            raise GitError(
                _clean_error(result.stderr) or f"git {' '.join(args)} failed"
            )
        # 成功时，或调用者设置 check=False 时，把原始结果交回去。
        return result


# 这里没有缩进到 GitClient 内，所以它是模块级函数，不是对象的方法。
def _clean_error(stderr: str) -> str:
    # stderr 是 Git 的错误输出。strip() 去掉前后空白；
    # splitlines() 按行拆开，[-1] 取最后一行；若原文为空则返回 ""。
    # `前面的值 if 条件 else 后面的值` 是单行条件表达式。
    return stderr.strip().splitlines()[-1] if stderr.strip() else ""
