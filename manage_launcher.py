"""Chami Site Manager — Windows batch launcher"""
import os, sys, subprocess, webbrowser

BASE = os.path.dirname(os.path.abspath(__file__))


def ensure_deps():
    try:
        import flask, markdown, PIL  # noqa: F401
    except ImportError:
        print("  安装依赖...")
        subprocess.run([sys.executable, "-m", "pip", "install", "flask", "markdown", "Pillow"],
                       capture_output=True)


def start_server():
    ensure_deps()
    print("  启动服务器...")
    webbrowser.open("http://127.0.0.1:5000")
    webbrowser.open("http://127.0.0.1:5000/index.html")
    subprocess.run(["python", "manage.py"], cwd=BASE)


def git_status():
    print()
    subprocess.run(["git", "status"], cwd=BASE)
    print()
    subprocess.run(["git", "diff", "--stat"], cwd=BASE)


def git_commit():
    print()
    subprocess.run(["git", "status"], cwd=BASE)
    msg = input("\n  Commit 消息: ").strip()
    if not msg:
        print("  消息不能为空")
        return
    subprocess.run(["git", "add", "-A"], cwd=BASE)
    r = subprocess.run(["git", "commit", "-m", msg], cwd=BASE, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  提交失败: {r.stderr.strip()}")
        return
    print("  已提交。")
    if input("  推送? [y/n] ").strip().lower() == "y":
        r = subprocess.run(["git", "push"], cwd=BASE, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  推送失败: {r.stderr.strip()}")
        else:
            print("  已推送。")


def git_push():
    r = subprocess.run(["git", "fetch"], cwd=BASE, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  Fetch 失败: {r.stderr.strip()}")
        return
    print()
    subprocess.run(["git", "status", "-sb"], cwd=BASE)
    if input("\n  确认推送? [y/n] ").strip().lower() == "y":
        r = subprocess.run(["git", "push"], cwd=BASE, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  推送失败: {r.stderr.strip()}")
        else:
            print("  已推送。")


def install_deps():
    subprocess.run([sys.executable, "-m", "pip", "install", "flask", "markdown", "Pillow"])
    print("\n  完成。")


MENU = """
  ═══ Chami 个人网站管理 ═══

  [1] 启动服务器（管理面板 + 网站预览）
  [2] 只打开管理面板
  [3] 只预览网站
  [4] Git 状态
  [5] Git 提交
  [6] Git 推送
  [7] 安装 / 更新依赖
  [0] 退出
"""

ACTIONS = {
    "1": lambda: start_server(),
    "2": lambda: webbrowser.open("http://127.0.0.1:5000"),
    "3": lambda: webbrowser.open("http://127.0.0.1:5000/index.html"),
    "4": git_status,
    "5": git_commit,
    "6": git_push,
    "7": install_deps,
}


def run():
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(MENU)
        opt = input("  > ").strip()
        if opt == "0":
            break
        action = ACTIONS.get(opt)
        if action:
            action()
            input("\n  按 Enter 继续...")
        else:
            print("  无效选项")
            input("  按 Enter 继续...")


if __name__ == "__main__":
    run()
