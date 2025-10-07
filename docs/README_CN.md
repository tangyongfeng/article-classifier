<div align="center">

# 📚 智能文章分类系统

### 基于大语言模型的智能文章分类系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)

[English](../README.md) | [简体中文](README_CN.md) | [Deutsch](README_DE.md)

</div>

---

## ✨ 核心特性

- 🤖 **AI 智能分类** - 利用大语言模型智能分类文章内容
- 🌳 **动态分类体系** - 自动构建和优化多层级分类树
- 📄 **多格式支持** - 支持 HTML、Markdown 和纯文本文件
- 💾 **双重存储** - PostgreSQL 存储元数据 + JSON 存储完整内容
- ⚡ **批量处理** - 高效处理数千篇文章
- 🔄 **自动优化** - 根据内容模式持续优化分类结构
- 🎯 **置信度评分** - 为每次分类分配置信度级别
- 📊 **完整日志** - 详细的处理日志和错误追踪

## 🚀 快速开始

### 环境要求

- Python 3.10 或更高版本
- PostgreSQL 13 或更高版本
- [Ollama](https://ollama.ai/) 及兼容的 LLM 模型

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/tangyongfeng/article-classifier.git
   cd article-classifier
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **初始化数据库**
   ```bash
   psql -U postgres -f scripts/setup_database.sql
   ```

4. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，设置 PostgreSQL 密码
   ```

5. **配置系统**
   ```bash
   cp config.yaml.example config.yaml
   # 根据需要编辑 config.yaml（可选）
   ```

### 使用方法

#### 单文件处理
```bash
python scripts/single_process.py path/to/article.html
```

#### 批量处理
```bash
# 处理目录中的所有文件
python scripts/batch_process.py --input /path/to/articles

# 后台运行
nohup python scripts/batch_process.py --input /path/to/articles > output.log 2>&1 &
```

## 📁 项目结构

```
article-classifier/
├── src/                      # 源代码
│   ├── core/                # 核心分类引擎
│   │   ├── classifier.py    # 主分类器
│   │   ├── llm_service.py   # LLM 集成
│   │   ├── category_manager.py    # 分类管理
│   │   └── category_optimizer.py  # 自动优化
│   ├── loaders/             # 文件加载器
│   │   ├── html_loader.py
│   │   ├── markdown_loader.py
│   │   └── text_loader.py
│   ├── storage/             # 存储层
│   │   ├── database.py      # PostgreSQL 操作
│   │   ├── json_storage.py  # JSON 文件操作
│   │   └── models.py        # 数据模型
│   └── utils/               # 工具模块
│       ├── config.py        # 配置管理
│       └── logger.py        # 日志工具
├── scripts/                  # 可执行脚本
│   ├── batch_process.py     # 批量处理
│   ├── single_process.py    # 单文件处理
│   ├── test_setup.py        # 环境验证
│   └── setup_database.sql   # 数据库架构
├── docs/                     # 文档
│   ├── USAGE_GUIDE.md       # 详细使用指南
│   ├── README_CN.md         # 中文文档
│   └── README_DE.md         # 德语文档
├── data/                     # 数据目录（已忽略）
│   ├── json/                # JSON 存储
│   ├── logs/                # 处理日志
│   └── failed/              # 失败文件追踪
├── config.yaml.example       # 配置模板
├── .env.example             # 环境变量模板
└── requirements.txt         # Python 依赖
```

## 🔧 配置说明

### 环境变量 (.env)
```env
POSTGRES_PASSWORD=你的安全密码
OLLAMA_API_KEY=             # 本地 Ollama 可选
```

### 系统配置 (config.yaml)
```yaml
ollama:
  base_url: "http://localhost:11434"
  model: "gpt-oss:20b"
  temperature: 0.3

classifier:
  max_category_levels: 3      # 最大分类层级
  min_confidence: 0.6         # 最低置信度阈值
  initial_training_size: 100  # 初始训练文章数
  optimization_interval: 100  # 优化间隔
  auto_optimize: true         # 自动优化开关

database:
  host: "localhost"
  port: 5432
  database: "article_classifier"
  user: "article_classifier_user"

storage:
  json_root: "data/json"
  organize_by_date: true      # 按日期组织目录
  save_raw_content: true      # 保存原始内容

processing:
  batch_size: 10              # 批处理大小
  enable_parallel: false      # 并行处理（单机 Ollama 建议关闭）
  checkpoint_interval: 100    # 检查点间隔
  log_level: "INFO"
```

## 🎯 工作原理

### 分类流程

1. **文件扫描** - 发现目标目录中的文章
2. **内容加载** - 提取标题、内容和元数据
3. **LLM 分析** - 将内容发送给 LLM 进行分类
4. **创建分类** - 构建层级分类（最多 3 层）
5. **数据存储** - 保存到 PostgreSQL 和 JSON
6. **自动优化** - 每处理 N 篇文章后优化分类结构

### 分类策略

#### 初始阶段（前 100 篇文章）
- LLM 自由创建分类结构
- 根据内容模式构建有机层级结构
- 建立基础分类体系

#### 持续分类（100 篇文章后）
- 根据现有分类进行归类
- 置信度低于 0.6 时创建新分类
- 保持分类一致性

#### 自动优化（每 100 篇文章）
- **拆分** - 细分文章数量多的分类
- **合并** - 合并文章数量少的分类
- **演化** - 识别新兴主题并创建新分类

## 📊 数据存储

### PostgreSQL 数据库架构
```sql
articles              -- 文章元数据
categories            -- 分类层级结构
keywords              -- 提取的关键词
article_categories    -- 文章-分类关联
article_keywords      -- 文章-关键词关联
```

### JSON 文件结构
```
data/json/
├── articles/
│   └── YYYY/          # 年份
│       └── MM/        # 月份
│           ├── 000001.json
│           └── 000002.json
└── categories.json    # 分类树
```

## 📈 性能指标

- **处理速度**: 每篇文章 3-6 秒
- **批量性能**: 1,300 篇文章约 2 小时
- **LLM**: 使用本地 Ollama 的 gpt-oss:20b 模型测试
- **存储**: 高效的双重存储方案

## 🔍 查询示例

### SQL 查询
```sql
-- 查看分类树
WITH RECURSIVE category_tree AS (
  SELECT id, name, parent_id, 1 as level
  FROM categories WHERE parent_id IS NULL
  UNION ALL
  SELECT c.id, c.name, c.parent_id, ct.level + 1
  FROM categories c
  JOIN category_tree ct ON c.parent_id = ct.id
)
SELECT * FROM category_tree ORDER BY level, name;

-- 热门关键词
SELECT keyword, usage_count
FROM keywords
ORDER BY usage_count DESC
LIMIT 20;

-- 按分类查询文章
SELECT a.title, c.name as category
FROM articles a
JOIN article_categories ac ON a.id = ac.article_id
JOIN categories c ON ac.category_id = c.id
WHERE c.name = '技术';
```

### Python 查询
```python
import json
from pathlib import Path

# 加载分类树
with open('data/json/categories.json') as f:
    categories = json.load(f)

# 按分类查找文章
for article_file in Path('data/json/articles').rglob('*.json'):
    with open(article_file) as f:
        data = json.load(f)
        if '技术' in data['classification']['category_path']:
            print(f"{data['metadata']['title']}")
```

## 🛠️ 高级用法

### 自定义 LLM 模型
编辑 `config.yaml` 使用不同的模型：
```yaml
ollama:
  model: "llama2:70b"  # 或其他模型
```

### 重新处理文件
```sql
-- 删除文章记录以重新处理
DELETE FROM articles WHERE file_path = '/path/to/article.html';
```

### 备份数据
```bash
# 备份 JSON 文件
tar -czf backup_$(date +%Y%m%d).tar.gz data/json/

# 备份数据库
pg_dump -U postgres article_classifier > backup_$(date +%Y%m%d).sql
```

## 🐛 故障排除

### 常见问题

**问：LLM 连接失败**
```bash
# 检查 Ollama 是否运行
curl http://localhost:11434/api/tags

# 如需启动 Ollama
ollama serve
```

**问：数据库连接错误**
```bash
# 验证 PostgreSQL 是否运行
pg_isready

# 检查 .env 中的凭据
cat .env
```

**问：分类质量不佳**
- 调整 config.yaml 中的 `temperature`（更低 = 更确定）
- 使用更大的 LLM 模型
- 增加 `initial_training_size` 以建立更好的分类基础

## 🗺️ 路线图

- [ ] Web UI 管理面板
- [ ] 向量搜索相似文章
- [ ] 多语言界面支持
- [ ] PDF 文档支持
- [ ] API 接口集成
- [ ] 实时分类服务
- [ ] 分类建议 API

## 🤝 贡献

欢迎贡献！请随时提交 Pull Request。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](../LICENSE) 文件

## 🙏 致谢

- 基于 [LangChain](https://langchain.com/) 构建
- 由 [Ollama](https://ollama.ai/) 驱动
- 数据库：[PostgreSQL](https://www.postgresql.org/)

## 📧 联系方式

项目地址：[https://github.com/tangyongfeng/article-classifier](https://github.com/tangyongfeng/article-classifier)

---

<div align="center">

用 ❤️ 打造的智能文章分类系统

</div>
