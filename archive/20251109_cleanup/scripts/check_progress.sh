#!/bin/bash
# 检查处理进度的脚本

echo "=========================================="
echo "文章处理进度监控"
echo "=========================================="
echo ""

# 检查数据库中的文章数量
if command -v psql &> /dev/null; then
    echo "📊 数据库统计:"
    PGPASSWORD=AcUs3r#2025!Px7Qm psql -h localhost -U acuser -d article_classifier -t -c "SELECT COUNT(*) as total_articles FROM articles;" 2>/dev/null | xargs echo "  总文章数:"
    echo ""
fi

# 检查JSON文件数量
echo "📁 JSON文件统计:"
json_count=$(find data/json/articles -name "*.json" -type f 2>/dev/null | wc -l | xargs)
echo "  JSON文件数: $json_count"
echo ""

# 检查失败文件
echo "❌ 失败文件统计:"
if [ -f data/failed/failed_files.json ]; then
    failed_count=$(python3 -c "import json; data=json.load(open('data/failed/failed_files.json')); print(len(data))" 2>/dev/null)
    failed_unique=$(python3 -c "import json; data=json.load(open('data/failed/failed_files.json')); print(len(set(item['file_path'] for item in data)))" 2>/dev/null)
    echo "  失败记录数: $failed_count"
    echo "  失败文件数（去重）: $failed_unique"
else
    echo "  无失败记录"
fi
echo ""

# 检查处理进程
echo "🔄 处理进程:"
if pgrep -f "batch_process.py\|retry_failed.py" > /dev/null; then
    echo "  ✓ 处理进程运行中"
    ps aux | grep -E "batch_process.py|retry_failed.py" | grep -v grep | awk '{print "    PID:", $2, "| CMD:", $11, $12, $13}'
else
    echo "  ✗ 没有处理进程运行"
fi
echo ""

# 显示最新日志
echo "📝 最新日志 (最后10行):"
latest_log=$(ls -t data/logs/*.log 2>/dev/null | head -1)
if [ -n "$latest_log" ]; then
    echo "  日志文件: $latest_log"
    tail -10 "$latest_log" | sed 's/^/    /'
else
    echo "  未找到日志文件"
fi
echo ""

echo "=========================================="
echo "提示："
echo "  - 查看实时日志: tail -f nohup_retry.out"
echo "  - 查看批处理日志: tail -f data/logs/*.log"
echo "  - 终止处理: pkill -f retry_failed.py"
echo "=========================================="
