#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MediaCrawler 批量抓取脚本
读取 batch_config.yaml 配置文件，批量执行抓取任务
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    print("请先安装 PyYAML: pip install pyyaml")
    sys.exit(1)


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def run_crawler(task: dict, global_settings: dict, dry_run: bool = False) -> bool:
    """
    运行单个抓取任务
    
    Args:
        task: 任务配置
        global_settings: 全局设置
        dry_run: 是否只打印命令不执行
    
    Returns:
        是否成功
    """
    name = task.get('name', '未命名任务')
    platform = task.get('platform', 'dy')
    crawler_type = task.get('type', 'creator')
    save_dir = task.get('save_dir', '')
    get_media = task.get('get_media', False)
    max_notes = task.get('max_notes', 20)
    
    # 构建命令
    cmd = [
        sys.executable, 'main.py',
        '--platform', platform,
        '--type', crawler_type,
        '--lt', global_settings.get('login_type', 'qrcode'),
        '--save_data_option', global_settings.get('save_format', 'json'),
    ]
    
    # 添加评论相关参数
    if global_settings.get('get_comments', True):
        cmd.extend(['--get_comment', 'true'])
        cmd.extend(['--max_comments_count_singlenotes', str(global_settings.get('max_comments', 10))])
    else:
        cmd.extend(['--get_comment', 'false'])
    
    # 根据类型添加不同参数
    if crawler_type == 'creator':
        ids = task.get('ids', [])
        if ids:
            cmd.extend(['--creator_id', ','.join(ids)])
    elif crawler_type == 'search':
        keywords = task.get('keywords', [])
        if keywords:
            cmd.extend(['--keywords', ','.join(keywords)])
    elif crawler_type == 'detail':
        ids = task.get('ids', [])
        if ids:
            cmd.extend(['--specified_id', ','.join(ids)])
    
    # 无头模式
    if global_settings.get('headless', False):
        cmd.extend(['--headless', 'true'])
    
    print(f"\n{'='*60}")
    print(f"📋 任务: {name}")
    print(f"📱 平台: {platform}")
    print(f"🔍 类型: {crawler_type}")
    print(f"💾 保存目录: {save_dir or '默认路径'}")
    print(f"📹 下载媒体: {'是' if get_media else '否'}")
    print(f"📊 最大数量: {max_notes}")
    print(f"{'='*60}")
    
    if dry_run:
        print(f"🔧 命令: {' '.join(cmd)}")
        return True
    
    # 设置环境变量（用于自定义保存路径和媒体下载）
    env = os.environ.copy()
    if save_dir:
        env['MEDIA_CRAWLER_SAVE_DIR'] = save_dir
        # 设置抖音视频保存路径
        if platform == 'dy':
            env['DOUYIN_VIDEO_SAVE_DIR'] = save_dir
    if get_media:
        env['MEDIA_CRAWLER_GET_MEDIA'] = 'true'
    env['MEDIA_CRAWLER_MAX_NOTES'] = str(max_notes)
    
    try:
        print(f"🚀 开始执行...")
        print(f"🔧 命令: {' '.join(cmd)}\n")
        
        # 执行命令 - 实时显示输出
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            env=env,
            stdout=None,  # 直接输出到终端
            stderr=None,  # 直接输出到终端
        )
        
        if result.returncode == 0:
            print(f"\n✅ 任务 [{name}] 完成!")
            return True
        else:
            print(f"\n❌ 任务 [{name}] 失败，返回码: {result.returncode}")
            return False
            
    except KeyboardInterrupt:
        print(f"\n⚠️ 任务 [{name}] 被用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 任务 [{name}] 出错: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='MediaCrawler 批量抓取脚本')
    parser.add_argument(
        '-c', '--config',
        default='batch_config.yaml',
        help='配置文件路径 (默认: batch_config.yaml)'
    )
    parser.add_argument(
        '-t', '--task',
        help='只运行指定名称的任务'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='只打印命令，不实际执行'
    )
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='列出所有配置的任务'
    )
    
    args = parser.parse_args()
    
    # 加载配置
    config_path = Path(__file__).parent / args.config
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        print("请先编辑 batch_config.yaml 配置文件")
        sys.exit(1)
    
    config = load_config(config_path)
    global_settings = config.get('global_settings', {})
    
    # 收集所有任务
    all_tasks = []
    
    # 抖音创作者任务
    douyin_creators = config.get('douyin_creators') or []
    for task in douyin_creators:
        if task:
            all_tasks.append(task)
    
    # 小红书创作者任务
    xhs_creators = config.get('xhs_creators') or []
    for task in xhs_creators:
        if task:
            all_tasks.append(task)
    
    # 搜索任务
    search_tasks = config.get('search_tasks') or []
    for task in search_tasks:
        if task:
            all_tasks.append(task)
    
    if not all_tasks:
        print("⚠️ 没有找到任何配置的任务")
        print("请编辑 batch_config.yaml 添加任务配置")
        sys.exit(1)
    
    # 列出任务
    if args.list:
        print("\n📋 配置的任务列表:")
        print("-" * 50)
        for i, task in enumerate(all_tasks, 1):
            name = task.get('name', '未命名')
            platform = task.get('platform', '?')
            task_type = task.get('type', '?')
            print(f"  {i}. [{platform}] {name} ({task_type})")
        print("-" * 50)
        print(f"共 {len(all_tasks)} 个任务")
        return
    
    # 过滤任务
    if args.task:
        all_tasks = [t for t in all_tasks if t.get('name') == args.task]
        if not all_tasks:
            print(f"❌ 未找到名为 '{args.task}' 的任务")
            sys.exit(1)
    
    # 执行任务
    print(f"\n🎯 准备执行 {len(all_tasks)} 个任务")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success_count = 0
    fail_count = 0
    
    for task in all_tasks:
        try:
            if run_crawler(task, global_settings, args.dry_run):
                success_count += 1
            else:
                fail_count += 1
        except KeyboardInterrupt:
            print("\n\n⚠️ 用户中断，停止执行后续任务")
            break
    
    # 汇总
    print(f"\n{'='*60}")
    print(f"📊 执行结果汇总")
    print(f"   ✅ 成功: {success_count}")
    print(f"   ❌ 失败: {fail_count}")
    print(f"   ⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
