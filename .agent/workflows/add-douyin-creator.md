---
description: 添加抖音博主到批量抓取配置
---
# 添加抖音博主工作流

本工作流用于从抖音分享文本中提取博主链接，并添加到 `batch_config.yaml` 配置文件。

## 使用方法

### 方式一：交互式输入

1. 运行脚本：
   ```bash
   cd /Volumes/home2/Code/MediaCrawler
   python -m tools.douyin_link_parser
   ```

2. 粘贴抖音分享文本（可以粘贴多条），输入空行结束

3. 确认添加到配置

### 方式二：从文件读取

1. 将分享文本保存到文件（如 `links.txt`）

2. 运行：
   ```bash
   python -m tools.douyin_link_parser --input links.txt
   ```

### 方式三：Dry Run 模式（仅预览不修改）

```bash
python -m tools.douyin_link_parser --input links.txt --dry-run
```

## 命令行参数

| 参数 | 缩写 | 说明 |
|------|------|------|
| `--input` | `-i` | 包含分享文本的文件路径 |
| `--config` | `-c` | 配置文件路径（默认：batch_config.yaml） |
| `--save-dir` | `-s` | 保存目录前缀（默认：/Volumes/video-02-documentary/抖音） |
| `--dry-run` | `-n` | 仅显示结果，不修改配置 |
| `--browser` | `-b` | 使用浏览器获取真实博主名称（较慢但更准确） |
| `--test` | `-t` | 运行测试 |

## 功能特点

1. **自动提取链接**：从分享文本中提取 `https://v.douyin.com/xxx/` 格式的短链接
2. **自动去重**：同一批次的链接去重，以及与现有配置去重
3. **解析用户ID**：将短链接解析为完整的用户主页链接
4. **可选浏览器模式**：使用 Playwright 获取真实博主名称

## 示例

输入：
```
5- 长按复制此条消息，打开抖音搜索，查看TA的更多作品。 https://v.douyin.com/xxuKh8bOTww/ 1@5.com :3pm
```

输出配置：
```yaml
- name: "博主名称"
  platform: dy
  type: creator
  ids:
    - "https://www.douyin.com/user/MS4wLjABAAAA..."
  save_dir: "/Volumes/video-02-documentary/抖音/博主名称"
  get_media: true
  max_notes: 2000
```

## 使用浏览器获取真实名称

如果需要获取真实博主名称，需要先安装 Playwright 浏览器：

```bash
playwright install chromium
```

然后使用 `--browser` 参数：
```bash
python -m tools.douyin_link_parser --browser --input links.txt
```
