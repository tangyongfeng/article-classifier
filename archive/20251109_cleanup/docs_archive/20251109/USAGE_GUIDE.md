# 使用指南

## 完整安装和运行步骤

### 第一步：安装依赖

```bash
cd article-classifier
pip install -r requirements.txt
```

### 第二步：初始化数据库

```bash
# 以 postgres 用户运行 SQL 脚本
psql -U postgres -f scripts/setup_database.sql
```

**重要信息（已保存）：**
- 数据库名: `article_classifier`
- 用户名: `article_classifier_user`
- 密码: `AcUs3r#2025!Px7Qm` （已写入 `.env` 文件）

### 第三步：确认 Ollama 服务运行

```bash
# 检查 Ollama 是否运行
curl http://localhost:11434/api/tags

# 确认 gpt-oss:20b 模型已安装
ollama list
```

### 第四步：批量处理文章

#### 方式一：前台运行（推荐测试时使用）

```bash
python scripts/batch_process.py --input "../2023年6月"
```

#### 方式二：后台运行（推荐正式处理）

```bash
# 使用 nohup 后台运行
nohup python scripts/batch_process.py --input "../2023年6月" > nohup.out 2>&1 &

# 记录进程 ID
echo $! > batch_process.pid

# 查看实时日志
tail -f data/logs/batch_*.log

# 或查看 nohup 输出
tail -f nohup.out
```

#### 监控处理进度

```bash
# 查看处理进度
tail -f data/logs/batch_*.log | grep "已处理"

# 查看数据库中已处理文章数
psql -U article_classifier_user -d article_classifier -c "SELECT COUNT(*) FROM articles;"
```

#### 停止后台进程

```bash
# 使用保存的 PID
kill $(cat batch_process.pid)

# 或查找进程并停止
ps aux | grep batch_process.py
kill <PID>
```

### 第五步：查看结果

#### 查看分类树

```bash
cat data/json/categories.json | python -m json.tool | head -50
```

#### 查看处理报告

```bash
# 最新的摘要报告
ls -lt data/logs/summary_*.json | head -1 | awk '{print $9}' | xargs cat | python -m json.tool
```

#### 查看失败文件

```bash
cat data/failed/failed_files.json 2>/dev/null | python -m json.tool
```

#### SQL 查询

```bash
# 连接数据库
psql -U article_classifier_user -d article_classifier

# 查看分类统计
SELECT c.name, c.article_count
FROM categories c
WHERE c.level = 1
ORDER BY c.article_count DESC;

# 查看热门关键词
SELECT keyword, usage_count
FROM keywords
ORDER BY usage_count DESC
LIMIT 20;

# 退出
\q
```

## 常见任务

### 单文件处理

```bash
python scripts/single_process.py "../2023年6月/IT技术/Ubuntu US CA.html"
```

### 重新处理某个文件

```bash
# 1. 删除数据库记录
psql -U article_classifier_user -d article_classifier
DELETE FROM articles WHERE file_path = '/path/to/file.html';
\q

# 2. 重新处理
python scripts/single_process.py "/path/to/file.html"
```

### 备份数据

```bash
# 备份 JSON 文件
cd article-classifier
tar -czf ../backup_json_$(date +%Y%m%d).tar.gz data/json/

# 备份数据库
pg_dump -U article_classifier_user article_classifier > ../backup_db_$(date +%Y%m%d).sql
```

### 恢复数据

```bash
# 恢复 JSON
tar -xzf backup_json_20251007.tar.gz

# 恢复数据库
psql -U article_classifier_user -d article_classifier < backup_db_20251007.sql
```

### 清空数据重新开始

```bash
# 清空数据库
psql -U article_classifier_user -d article_classifier
TRUNCATE articles, categories, keywords, article_categories, article_keywords, category_snapshots CASCADE;
\q

# 删除 JSON 文件
rm -rf data/json/articles/*
rm -f data/json/categories.json
rm -rf data/json/snapshots/*
```

## 配置调整

### 修改 LLM 模型

编辑 `config.yaml`:

```yaml
ollama:
  model: "llama3.1:8b"  # 修改为其他模型
```

### 调整优化频率

```yaml
classifier:
  optimization_interval: 50  # 每50篇触发优化（默认100）
```

### 调整温度参数

```yaml
ollama:
  temperature: 0.2  # 更低 = 更稳定，更高 = 更有创意
```

## 性能优化

### 加速处理

1. 减少内容长度（默认已截断到2000字）
2. 使用更快的模型（如 llama3.1:8b）
3. 关闭原始内容保存（`save_raw_content: false`）

### 减少磁盘占用

编辑 `config.yaml`:

```yaml
storage:
  save_raw_content: false  # 不保存原始 HTML
  compression: true        # 启用压缩
```

## 故障排除

### 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
ps aux | grep postgres

# 检查密码是否正确
cat .env | grep POSTGRES_PASSWORD

# 测试连接
psql -U article_classifier_user -d article_classifier -h localhost
```

### Ollama 连接失败

```bash
# 检查 Ollama 服务
curl http://localhost:11434/api/tags

# 重启 Ollama
ollama serve
```

### Python 导入错误

```bash
# 确保在项目根目录运行
cd article-classifier
python scripts/batch_process.py --input "../2023年6月"
```

### 内存不足

```bash
# 减小批处理大小
# 编辑 config.yaml
processing:
  batch_size: 5  # 默认 10
```

## 下一步

处理完成后，你可以：

1. 查看分类结果统计
2. 导出数据到其他系统
3. 开发 Web 界面（第二期）
4. 添加邮件自动处理（第二期）

祝使用愉快！
