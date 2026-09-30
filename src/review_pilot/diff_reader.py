# 延后处理类型注解；不会改变下方方法的执行顺序。
from __future__ import annotations

# dataclass 会根据类中声明的字段自动生成初始化方法。
from dataclasses import dataclass

# 前面的点表示从同一个 review_pilot 包中导入。
from .git_client import GitClient
from .models import RawDiff


# 这一层只负责把 GitClient 取得的 diff 文字包装成 RawDiff。
# frozen=True 阻止创建后重新给 reader.git 赋值；不会冻结 Git 仓库。
@dataclass(frozen=True)
class DiffReader:
    # 字段名是 git，预期放一个 GitClient 对象。
    # 创建时可以写 DiffReader(git=GitClient.from_cwd())。
    git: GitClient

    # self 是当前 DiffReader 对象；-> RawDiff 标注返回值的类型。
    def staged_raw_diff(self) -> RawDiff:
        # self.git 取出保存在对象里的 GitClient。
        # .staged_raw_diff() 调用它的方法，得到已暂存 diff 的原始文字。
        # RawDiff(...) 把文字放进 text 字段；return 交回这个数据对象。
        # 此处不解析 diff，也不决定哪些改动值得审查。
        return RawDiff(self.git.staged_raw_diff())
