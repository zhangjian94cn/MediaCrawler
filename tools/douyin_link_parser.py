# -*- coding: utf-8 -*-
# 抖音链接解析工具
# 用于从抖音分享文本中提取短链接，解析获取博主信息，并更新 batch_config.yaml

import argparse
import asyncio
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
from ruamel.yaml import YAML

# 尝试导入 Playwright（可选依赖）
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "batch_config.yaml"
DEFAULT_SAVE_DIR_PREFIX = "/Volumes/video-02-documentary/抖音"


def extract_short_links(text: str) -> List[str]:
    """
    从分享文本中提取抖音短链接
    
    Args:
        text: 包含抖音分享信息的文本
        
    Returns:
        去重后的短链接列表
    """
    # 匹配 https://v.douyin.com/xxx/ 格式的链接
    pattern = r'https://v\.douyin\.com/[a-zA-Z0-9_-]+/?'
    links = re.findall(pattern, text)
    
    # 标准化链接格式（确保以 / 结尾）
    normalized = []
    for link in links:
        if not link.endswith('/'):
            link += '/'
        normalized.append(link)
    
    # 去重并保持顺序
    seen = set()
    unique_links = []
    for link in normalized:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)
    
    return unique_links


async def resolve_short_link(short_url: str, timeout: float = 10.0) -> Optional[Dict]:
    """
    解析抖音短链接，获取完整URL和博主信息
    
    Args:
        short_url: 抖音短链接
        timeout: 请求超时时间
        
    Returns:
        包含 short_url, full_url, user_id, nickname 的字典，失败返回 None
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
    }
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
            # 发送 GET 请求获取重定向后的页面
            response = await client.get(short_url)
            full_url = str(response.url)
            
            # 检查是否是用户主页链接
            # 支持 douyin.com/user/ 和 iesdouyin.com/share/user/ 两种格式
            user_match = re.search(r'(?:douyin\.com|iesdouyin\.com)/(?:share/)?user/([a-zA-Z0-9_-]+)', full_url)
            if not user_match:
                print(f"  ⚠️ 链接不是用户主页: {short_url} -> {full_url}")
                return None
            
            user_id = user_match.group(1)
            
            # 构建标准的 douyin.com URL
            standard_url = f"https://www.douyin.com/user/{user_id}"
            
            # 访问标准 URL 获取博主名称（因为重定向页面可能没有完整信息）
            nickname = None
            try:
                user_response = await client.get(standard_url)
                user_html = user_response.text
                
                # 从页面 title 中提取博主名称
                # 格式通常为: "xxx的抖音 - 抖音"
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', user_html, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1).strip()
                    # 提取 "xxx的抖音" 中的 xxx
                    name_match = re.match(r'^(.+?)的(?:抖音|主页)', title)
                    if name_match:
                        nickname = name_match.group(1).strip()
                    elif ' - ' in title:
                        nickname = title.split(' - ')[0].strip()
                
                # 如果 title 没有获取到，尝试从 JSON 数据中提取
                if not nickname:
                    nick_match = re.search(r'"nickname"\s*:\s*"([^"]+)"', user_html)
                    if nick_match:
                        nickname = nick_match.group(1)
            except Exception:
                pass  # 忽略第二次请求的错误
            
            # 最终使用用户ID作为默认名称
            if not nickname:
                nickname = f"博主_{user_id[:8]}"
            
            return {
                'short_url': short_url,
                'full_url': standard_url,
                'user_id': user_id,
                'nickname': nickname
            }
            
    except httpx.TimeoutException:
        print(f"  ❌ 请求超时: {short_url}")
        return None
    except Exception as e:
        print(f"  ❌ 解析失败: {short_url}, 错误: {e}")
        return None


async def fetch_nicknames_with_browser(creators: List[Dict], concurrency: int = 3) -> List[Dict]:
    """
    使用浏览器批量获取博主真实名称
    
    Args:
        creators: 已解析的博主信息列表
        concurrency: 并发数
        
    Returns:
        更新了 nickname 的博主列表
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("  ⚠️ Playwright 未安装，跳过获取真实名称")
        return creators
    
    print("\n🌐 使用浏览器获取博主真实名称...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        semaphore = asyncio.Semaphore(concurrency)
        total = len(creators)
        
        async def fetch_single(creator: Dict, index: int) -> Dict:
            async with semaphore:
                try:
                    print(f"  [{index + 1}/{total}] 获取名称: {creator['user_id'][:20]}...")
                    page = await context.new_page()
                    await page.goto(creator['full_url'], wait_until='domcontentloaded', timeout=15000)
                    
                    # 等待页面加载
                    await page.wait_for_timeout(2000)
                    
                    # 获取 title
                    title = await page.title()
                    
                    # 提取名称
                    name_match = re.match(r'^(.+?)的(?:抖音|主页)', title)
                    if name_match:
                        creator['nickname'] = name_match.group(1).strip()
                        print(f"    ✅ {creator['nickname']}")
                    elif ' - ' in title:
                        creator['nickname'] = title.split(' - ')[0].strip()
                        print(f"    ✅ {creator['nickname']}")
                    
                    await page.close()
                except Exception as e:
                    print(f"    ⚠️ 获取失败: {e}")
                
                return creator
        
        tasks = [fetch_single(creator, i) for i, creator in enumerate(creators)]
        results = await asyncio.gather(*tasks)
        
        await browser.close()
        
    return results


async def resolve_all_links(short_urls: List[str], concurrency: int = 3) -> List[Dict]:
    """
    批量解析短链接
    
    Args:
        short_urls: 短链接列表
        concurrency: 并发数
        
    Returns:
        成功解析的博主信息列表
    """
    results = []
    total = len(short_urls)
    
    # 使用信号量控制并发
    semaphore = asyncio.Semaphore(concurrency)
    
    async def resolve_with_semaphore(url: str, index: int):
        async with semaphore:
            print(f"  [{index + 1}/{total}] 解析: {url}")
            result = await resolve_short_link(url)
            if result:
                print(f"    ✅ {result['nickname']} ({result['user_id'][:20]}...)")
            return result
    
    tasks = [resolve_with_semaphore(url, i) for i, url in enumerate(short_urls)]
    task_results = await asyncio.gather(*tasks)
    
    for result in task_results:
        if result:
            results.append(result)
    
    return results


def load_existing_config(config_path: Path) -> Tuple[Dict, List[str]]:
    """
    加载现有配置并提取已配置的用户ID
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        (配置字典, 已配置的用户ID列表)
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.load(f)
    
    existing_ids = []
    
    # 提取抖音创作者的用户ID
    if config and 'douyin_creators' in config and config['douyin_creators']:
        for creator in config['douyin_creators']:
            if creator and 'ids' in creator and creator['ids']:
                for url in creator['ids']:
                    # 从完整URL或短链接中提取用户ID
                    user_match = re.search(r'douyin\.com/user/([a-zA-Z0-9_-]+)', url)
                    if user_match:
                        existing_ids.append(user_match.group(1))
                    # 也保存短链接用于对比
                    short_match = re.search(r'v\.douyin\.com/([a-zA-Z0-9_-]+)', url)
                    if short_match:
                        existing_ids.append(short_match.group(1))
    
    return config, existing_ids


def check_duplicates(new_creators: List[Dict], existing_ids: List[str]) -> Tuple[List[Dict], List[Dict]]:
    """
    检查重复的博主
    
    Args:
        new_creators: 新解析的博主列表
        existing_ids: 已存在的用户ID列表
        
    Returns:
        (新博主列表, 重复博主列表)
    """
    new_list = []
    duplicate_list = []
    
    for creator in new_creators:
        user_id = creator['user_id']
        if user_id in existing_ids:
            duplicate_list.append(creator)
        else:
            new_list.append(creator)
    
    return new_list, duplicate_list


def add_to_config(config_path: Path, creators: List[Dict], save_dir_prefix: str = DEFAULT_SAVE_DIR_PREFIX):
    """
    将新博主添加到配置文件

    Args:
        config_path: 配置文件路径
        creators: 要添加的博主列表
        save_dir_prefix: 保存目录前缀
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=2, offset=2)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.load(f)
    
    if config is None:
        config = {}
    
    if 'douyin_creators' not in config or config['douyin_creators'] is None:
        config['douyin_creators'] = []
    
    for creator in creators:
        new_entry = {
            'name': creator['nickname'],
            'platform': 'dy',
            'type': 'creator',
            'ids': [creator['full_url']],
            'save_dir': f"{save_dir_prefix}/{creator['nickname']}",
            'get_media': True,
            'max_notes': 2000
        }
        config['douyin_creators'].append(new_entry)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f)


async def update_config_names(config_path: Path, dry_run: bool = False):
    """
    更新现有配置中的博主名称
    
    Args:
        config_path: 配置文件路径
        dry_run: 是否仅预览不修改
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright 未安装，无法更新名称")
        print("   请先运行: pip install playwright && playwright install chromium")
        return
    
    print(f"📄 加载配置文件: {config_path}")
    
    yaml_handler = YAML()
    yaml_handler.preserve_quotes = True
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml_handler.load(f)
    
    if not config or 'douyin_creators' not in config or not config['douyin_creators']:
        print("❌ 配置文件中没有抖音博主")
        return
    
    # 找出需要更新名称的博主（名称以"博主_"开头的）
    to_update = []
    for i, creator in enumerate(config['douyin_creators']):
        if creator and 'name' in creator and creator['name'].startswith('博主_'):
            if 'ids' in creator and creator['ids']:
                to_update.append((i, creator))
    
    if not to_update:
        print("✅ 没有需要更新名称的博主（所有博主都已有真实名称）")
        return
    
    print(f"🔍 发现 {len(to_update)} 个博主需要更新名称")
    
    # 使用浏览器获取真实名称
    print("\n🌐 使用浏览器获取博主真实名称...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        total = len(to_update)
        updated_count = 0
        
        for idx, (config_idx, creator) in enumerate(to_update):
            url = creator['ids'][0]
            old_name = creator['name']
            
            try:
                print(f"  [{idx + 1}/{total}] 获取: {url[:60]}...")
                page = await context.new_page()
                await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                await page.wait_for_timeout(2000)
                
                title = await page.title()
                
                # 提取名称
                new_name = None
                name_match = re.match(r'^(.+?)的(?:抖音|主页)', title)
                if name_match:
                    new_name = name_match.group(1).strip()
                elif ' - ' in title:
                    new_name = title.split(' - ')[0].strip()
                
                if new_name and new_name != old_name:
                    print(f"    ✅ {old_name} -> {new_name}")
                    if not dry_run:
                        config['douyin_creators'][config_idx]['name'] = new_name
                        # 更新 save_dir 中的名称
                        old_save_dir = creator.get('save_dir', '')
                        if old_save_dir and old_name in old_save_dir:
                            config['douyin_creators'][config_idx]['save_dir'] = old_save_dir.replace(old_name, new_name)
                    updated_count += 1
                else:
                    print(f"    ⚠️ 无法获取名称，保持原样: {old_name}")
                
                await page.close()
            except Exception as e:
                print(f"    ❌ 获取失败: {e}")
        
        await browser.close()
    
    if dry_run:
        print(f"\n🔍 Dry run 模式，发现 {updated_count} 个名称可更新")
    else:
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml_handler.dump(config, f)
        print(f"\n✅ 已更新 {updated_count} 个博主名称")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='抖音链接解析工具')
    parser.add_argument('--input', '-i', help='包含分享文本的文件路径')
    parser.add_argument('--config', '-c', default=str(DEFAULT_CONFIG_PATH), help='配置文件路径')
    parser.add_argument('--save-dir', '-s', default=DEFAULT_SAVE_DIR_PREFIX, help='保存目录前缀')
    parser.add_argument('--dry-run', '-n', action='store_true', help='仅显示结果，不修改配置')
    parser.add_argument('--browser', '-b', action='store_true', help='使用浏览器获取真实博主名称（较慢但更准确）')
    parser.add_argument('--update-names', '-u', action='store_true', help='更新现有配置中的博主名称（使用浏览器）')
    parser.add_argument('--yes', '-y', action='store_true', help='自动确认，不询问')
    parser.add_argument('--test', '-t', action='store_true', help='运行测试')
    
    args = parser.parse_args()
    
    # 测试模式
    if args.test:
        print("🧪 运行测试...")
        test_text = "5- 长按复制此条消息，打开抖音搜索，查看TA的更多作品。 https://v.douyin.com/xxuKh8bOTww/ 1@5.com :3pm"
        links = extract_short_links(test_text)
        print(f"  提取到链接: {links}")
        if links:
            result = await resolve_short_link(links[0])
            print(f"  解析结果: {result}")
        print("✅ 测试完成")
        return
    
    # 更新现有配置中的博主名称
    if args.update_names:
        await update_config_names(Path(args.config), args.dry_run)
        return
    
    # 获取输入文本
    if args.input:
        with open(args.input, 'r', encoding='utf-8') as f:
            input_text = f.read()
    else:
        print("📝 请粘贴抖音分享文本（输入空行结束）:")
        lines = []
        while True:
            try:
                line = input()
                if line == '':
                    break
                lines.append(line)
            except EOFError:
                break
        input_text = '\n'.join(lines)
    
    if not input_text.strip():
        print("❌ 未输入任何内容")
        return
    
    # 1. 提取短链接
    print("\n📎 正在提取短链接...")
    short_links = extract_short_links(input_text)
    print(f"  提取到 {len(short_links)} 个唯一链接")
    
    if not short_links:
        print("❌ 未找到任何抖音链接")
        return
    
    # 2. 解析短链接获取博主信息
    print("\n🔍 正在解析链接...")
    creators = await resolve_all_links(short_links)
    print(f"\n  成功解析 {len(creators)}/{len(short_links)} 个链接")
    
    if not creators:
        print("❌ 没有成功解析任何链接")
        return
    
    # 2.5 可选：使用浏览器获取真实名称
    if args.browser:
        creators = await fetch_nicknames_with_browser(creators)
    
    # 3. 加载现有配置并检查重复
    config_path = Path(args.config)
    print(f"\n📄 加载配置文件: {config_path}")
    
    try:
        _, existing_ids = load_existing_config(config_path)
        print(f"  现有配置中有 {len(existing_ids)} 个用户")
    except Exception as e:
        print(f"  ⚠️ 加载配置失败: {e}，将创建新配置")
        existing_ids = []
    
    # 4. 检查重复
    new_creators, duplicates = check_duplicates(creators, existing_ids)
    
    if duplicates:
        print(f"\n⚠️ 发现 {len(duplicates)} 个重复博主:")
        for c in duplicates:
            print(f"    - {c['nickname']}")
    
    if not new_creators:
        print("\n✅ 没有新的博主需要添加")
        return
    
    # 5. 显示将要添加的博主
    print(f"\n🆕 将添加 {len(new_creators)} 个新博主:")
    for c in new_creators:
        print(f"    - {c['nickname']} ({c['user_id'][:20]}...)")
    
    # Dry run 模式
    if args.dry_run:
        print("\n🔍 Dry run 模式，未修改配置文件")
        return
    
    # 6. 确认添加
    if not args.yes:
        confirm = input("\n确认添加到配置文件? (y/N): ")
        if confirm.lower() != 'y':
            print("❌ 已取消")
            return
    
    # 7. 添加到配置
    add_to_config(config_path, new_creators, args.save_dir)
    print(f"\n✅ 已添加 {len(new_creators)} 个博主到配置文件")


if __name__ == '__main__':
    asyncio.run(main())
