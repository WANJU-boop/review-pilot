# 前面的点表示从当前 review_pilot 包中导入 cli 模块的 main 函数。
from .cli import main

# 执行 `python -m review_pilot` 时，Python 会把 __name__ 设为 "__main__"。
# 普通导入时它不是这个值，因此导入包不会顺便启动命令行程序。
if __name__ == "__main__":
    # main() 返回整数退出码；SystemExit 把它交给终端。
    # 这里复用安装后的 review-pilot 命令所调用的同一个 main()。
    raise SystemExit(main())
