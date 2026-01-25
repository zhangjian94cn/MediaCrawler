#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MediaCrawler 统一管理脚本
提供友好的命令行界面，整合所有功能
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
VENV_PYTHON = PROJECT_ROOT / "venv" / "bin" / "python"
BATCH_CRAWLER = PROJECT_ROOT / "batch_crawler.py"
LINK_PARSER = PROJECT_ROOT / "tools" / "douyin_link_parser.py"
PENDING_LINKS = PROJECT_ROOT / "pending_links.txt"
CONFIG_FILE = PROJECT_ROOT / "batch_config.yaml"


def print_header(text: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def run_command(cmd: list, description: str = "") -> bool:
    """运行命令并返回是否成功"""
    if description:
        print(f"🚀 {description}...")

    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n⚠️ 操作被用户中断")
        return False


def list_tasks():
    """列出所有配置的任务"""
    print_header("📋 任务列表")
    cmd = [str(VENV_PYTHON), str(BATCH_CRAWLER), "--list"]
    run_command(cmd)


def add_creators(use_browser: bool = False, auto_yes: bool = False):
    """添加新的创作者"""
    print_header("➕ 添加新创作者")

    if not PENDING_LINKS.exists():
        print(f"❌ 文件不存在: {PENDING_LINKS}")
        print(f"请创建文件并添加抖音分享链接")
        return False

    # 检查文件是否有内容
    content = PENDING_LINKS.read_text(encoding='utf-8').strip()
    if not content or content.startswith('#'):
        print(f"⚠️ {PENDING_LINKS} 文件为空或只有注释")
        print(f"请添加抖音分享链接后再运行")
        return False

    cmd = [
        str(VENV_PYTHON),
        str(LINK_PARSER),
        "-i", str(PENDING_LINKS)
    ]

    if use_browser:
        cmd.append("--browser")
        print("🌐 将使用浏览器获取真实博主名称（较慢但更准确）")

    if auto_yes:
        cmd.append("-y")

    success = run_command(cmd, "解析链接并添加到配置")

    if success:
        print("\n✅ 创作者添加成功")
        print("💡 提示: 运行 'python media_manager.py list' 查看所有任务")

    return success


def update_names():
    """更新博主真实名称"""
    print_header("🔄 更新博主名称")
    cmd = [
        str(VENV_PYTHON),
        str(LINK_PARSER),
        "--update-names",
        "-y"
    ]
    success = run_command(cmd, "使用浏览器获取真实名称")

    if success:
        print("\n✅ 名称更新成功")

    return success


def run_crawler(task_name: Optional[str] = None, dry_run: bool = False):
    """运行批量抓取"""
    print_header("🎬 开始批量抓取")

    cmd = [str(VENV_PYTHON), str(BATCH_CRAWLER)]

    if task_name:
        cmd.extend(["--task", task_name])
        print(f"📌 只运行任务: {task_name}")

    if dry_run:
        cmd.append("--dry-run")
        print("🔍 Dry run 模式（不实际执行）")

    success = run_command(cmd, "执行批量抓取")

    if success:
        print("\n✅ 批量抓取完成")

    return success


def validate_config():
    """验证配置文件"""
    print_header("✅ 验证配置文件")

    if not CONFIG_FILE.exists():
        print(f"❌ 配置文件不存在: {CONFIG_FILE}")
        return False

    # 尝试加载配置
    try:
        import yaml
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        print(f"✅ 配置文件格式正确")

        # 统计任务数
        total_tasks = 0
        if config and 'douyin_creators' in config:
            creators = config['douyin_creators']
            if creators:
                total_tasks = len([c for c in creators if c])

        print(f"📊 配置的任务数: {total_tasks}")

        return True
    except Exception as e:
        print(f"❌ 配置文件格式错误: {e}")
        return False


def show_workflow():
    """显示完整工作流程"""
    print_header("📖 完整工作流程")

    workflow = """
1️⃣  添加创作者链接
   将抖音分享文本粘贴到 pending_links.txt

2️⃣  解析并添加到配置
   python media_manager.py add [--browser]

3️⃣  验证配置（可选）
   python media_manager.py validate

4️⃣  查看任务列表
   python media_manager.py list

5️⃣  运行批量抓取
   python media_manager.py run

💡 快捷命令:
   python media_manager.py quick  # 一键执行 2-5 步
"""
    print(workflow)


def quick_start():
    """快速开始：自动执行所有步骤"""
    print_header("🚀 快速开始模式")

    print("将自动执行以下步骤:")
    print("  1. 解析链接并添加创作者")
    print("  2. 更新博主名称")
    print("  3. 验证配置")
    print("  4. 显示任务列表")
    print()

    # 步骤1: 添加创作者
    if not add_creators(use_browser=True, auto_yes=True):
        print("❌ 添加创作者失败，停止执行")
        return False

    # 步骤2: 更新名称（如果有需要）
    print("\n" + "="*60)
    update_names()

    # 步骤3: 验证配置
    print("\n" + "="*60)
    if not validate_config():
        print("❌ 配置验证失败")
        return False

    # 步骤4: 显示任务列表
    print("\n" + "="*60)
    list_tasks()

    print("\n" + "="*60)
    print("✅ 快速开始完成！")
    print("💡 运行 'python media_manager.py run' 开始批量抓取")

    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='MediaCrawler 统一管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python media_manager.py list              # 列出所有任务
  python media_manager.py add               # 添加新创作者
  python media_manager.py add --browser     # 使用浏览器获取真实名称
  python media_manager.py update            # 更新博主名称
  python media_manager.py validate          # 验证配置文件
  python media_manager.py run               # 运行批量抓取
  python media_manager.py run --task "博主名"  # 只运行指定任务
  python media_manager.py quick             # 快速开始（自动执行所有步骤）
  python media_manager.py workflow          # 显示完整工作流程
        """
    )

    parser.add_argument(
        'command',
        choices=['list', 'add', 'update', 'run', 'validate', 'workflow', 'quick'],
        help='要执行的命令'
    )

    parser.add_argument(
        '--browser', '-b',
        action='store_true',
        help='使用浏览器获取真实博主名称（仅用于 add 命令）'
    )

    parser.add_argument(
        '--task', '-t',
        help='指定要运行的任务名称（仅用于 run 命令）'
    )

    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Dry run 模式，不实际执行（仅用于 run 命令）'
    )

    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='自动确认，不询问'
    )

    args = parser.parse_args()

    # 执行对应的命令
    if args.command == 'list':
        list_tasks()

    elif args.command == 'add':
        add_creators(use_browser=args.browser, auto_yes=args.yes)

    elif args.command == 'update':
        update_names()

    elif args.command == 'run':
        run_crawler(task_name=args.task, dry_run=args.dry_run)

    elif args.command == 'validate':
        validate_config()

    elif args.command == 'workflow':
        show_workflow()

    elif args.command == 'quick':
        quick_start()


if __name__ == '__main__':
    main()
