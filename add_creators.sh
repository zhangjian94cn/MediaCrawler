#!/bin/bash
# 抖音链接一键处理脚本
# 使用方法: 
#   1. 将抖音分享文本粘贴到 pending_links.txt
#   2. 运行 ./add_creators.sh

cd "$(dirname "$0")"

PENDING_FILE="pending_links.txt"
PYTHON="/opt/miniconda3/bin/python"

# 检查待处理文件是否存在
if [ ! -f "$PENDING_FILE" ]; then
    echo "❌ 未找到 $PENDING_FILE 文件"
    echo "📝 请创建该文件并粘贴抖音分享链接"
    exit 1
fi

# 检查文件是否为空或只有注释
content=$(grep -v '^#' "$PENDING_FILE" | grep -v '^$' | head -1)
if [ -z "$content" ]; then
    echo "⚠️ $PENDING_FILE 文件为空或只有注释"
    echo "📝 请粘贴抖音分享链接到该文件"
    exit 1
fi

echo "🔍 正在处理 $PENDING_FILE ..."
echo ""

# 运行解析脚本（使用浏览器获取真实名称，自动确认）
$PYTHON -m tools.douyin_link_parser --input "$PENDING_FILE" --browser --yes

if [ $? -eq 0 ]; then
    # 成功后清空待处理文件
    echo "# 待处理的抖音链接" > "$PENDING_FILE"
    echo "# 将抖音分享文本粘贴到这里，然后运行 ./add_creators.sh" >> "$PENDING_FILE"
    echo "" >> "$PENDING_FILE"
    echo "✅ 已清空 $PENDING_FILE"
fi

echo ""
echo "🎉 处理完成！"
echo ""
echo "📥 提示: 运行以下命令开始爬取视频:"
echo "   python batch_crawler.py"
