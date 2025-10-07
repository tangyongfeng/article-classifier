# 智能文章分类系统

基于 LangChain 和 Ollama 的智能文章分类系统，支持自动分类、动态调整分类体系。

## 功能特性

- ✅ 自动智能分类（LLM 驱动）
- ✅ 动态分类体系（自动调整）
- ✅ 多文件格式支持（HTML/Markdown/TXT）
- ✅ PostgreSQL + JSON 双重存储
- ✅ 批量处理 + 单文件处理
- ✅ 后台运行支持（nohup）

## 技术栈

- **LangChain**: LLM 编排框架
- **Ollama**: 本地 LLM 服务（gpt-oss:20b）
- **PostgreSQL**: 关系型数据库
- **Python 3.10+**

## 快速开始

### 1. 安装依赖

\`\`\`bash
cd article-classifier
pip install -r requirements.txt
\`\`\`

### 2. 初始化数据库

\`\`\`bash
psql -U postgres -f scripts/setup_database.sql
\`\`\`

**数据库信息：**
- 数据库: article_classifier
- 用户: article_classifier_user
- 密码: AcUs3r#2025!Px7Qm（已保存在 .env 文件）

### 3. 配置

配置文件 `config.yaml` 已经预设好，通常不需要修改。

如需修改 Ollama 模型或数据库配置，编辑 `config.yaml`。

### 4. 运行

#### 批量处理（推荐）

\`\`\`bash
# 前台运行
python scripts/batch_process.py --input "2023年6月"

# 后台运行（nohup）
nohup python scripts/batch_process.py --input "2023年6月" > nohup.out 2>&1 &

# 查看实时日志
tail -f data/logs/batch_*.log
\`\`\`

#### 单文件处理

\`\`\`bash
python scripts/single_process.py "path/to/file.html"
\`\`\`

## 项目结构

\`\`\`
article-classifier/
├── src/
│   ├── core/               # 核心模块
│   │   ├── classifier.py   # 分类引擎
│   │   ├── llm_service.py  # LLM 服务
│   │   ├── category_manager.py  # 分类管理
│   │   └── category_optimizer.py  # 分类优化
│   ├── loaders/            # 文件加载器
│   │   ├── html_loader.py
│   │   ├── markdown_loader.py
│   │   └── text_loader.py
│   ├── storage/            # 存储模块
│   │   ├── database.py     # PostgreSQL
│   │   ├── json_storage.py # JSON 文件
│   │   └── models.py       # 数据模型
│   └── utils/              # 工具模块
│       ├── config.py
│       └── logger.py
├── scripts/                # 脚本
│   ├── batch_process.py    # 批量处理
│   ├── single_process.py   # 单文件处理
│   └── setup_database.sql  # 数据库初始化
├── data/                   # 数据目录
│   ├── json/               # JSON 存储
│   │   ├── articles/       # 文章（按年月）
│   │   └── categories.json # 分类体系
│   ├── logs/               # 日志
│   └── failed/             # 失败文件
├── config.yaml             # 配置文件
├── .env                    # 环境变量
└── README.md
\`\`\`

## 工作流程

1. **扫描目录** → 收集待处理文件
2. **加载文件** → 提取标题、内容、元数据
3. **LLM 分类** → 调用 Ollama 分析内容
4. **创建分类** → 自动创建分类路径（最多3层）
5. **保存结果** → PostgreSQL（元数据） + JSON（完整内容）
6. **自动优化** → 每100篇触发分类优化

## 分类策略

### 初始阶段（前100篇）
- LLM 分析文章内容，自由创建分类体系
- 自动建立 1-3 层分类结构

### 持续分类（101篇后）
- 按现有分类体系分类
- 置信度低于 0.6 时建议新分类

### 自动优化（每100篇）
- 文章数多的类别 → 细分子类
- 文章数少的类别 → 合并到其他类
- 识别新兴主题 → 创建新类别

## 数据存储

### PostgreSQL 数据库
- **articles**: 文章元数据
- **categories**: 分类体系
- **keywords**: 关键词
- **article_categories**: 文章-分类关联
- **article_keywords**: 文章-关键词关联

### JSON 文件系统
```
data/json/articles/
├── 2023/
│   └── 06/
│       ├── 000001.json
│       └── 000002.json
└── categories.json
```

## 查询示例

### SQL 查询

\`\`\`sql
-- 查看分类树
WITH RECURSIVE category_tree AS (
  SELECT id, name, parent_id, 1 as level
  FROM categories WHERE parent_id IS NULL
  UNION ALL
  SELECT c.id, c.name, c.parent_id, ct.level + 1
  FROM categories c
  JOIN category_tree ct ON c.parent_id = ct.id
)
SELECT * FROM category_tree;

-- 热门关键词
SELECT keyword, usage_count FROM keywords
ORDER BY usage_count DESC LIMIT 20;
\`\`\`

### Python 查询

\`\`\`python
import json
from pathlib import Path

# 加载分类树
categories = json.load(open('data/json/categories.json'))

# 查找特定分类的文章
for file in Path('data/json/articles').rglob('*.json'):
    data = json.load(open(file))
    if '技术' in data['classification']['category_path']:
        print(data['metadata']['title'])
\`\`\`

## 常见问题

### 如何修改 LLM 模型？

编辑 `config.yaml`：

\`\`\`yaml
ollama:
  model: "your-model-name"
\`\`\`

### 如何重新处理已处理的文件？

删除数据库记录：

\`\`\`sql
DELETE FROM articles WHERE file_path = '/path/to/file';
\`\`\`

### 如何备份数据？

\`\`\`bash
# 备份 JSON
tar -czf backup.tar.gz data/json/

# 备份数据库
pg_dump -U postgres article_classifier > backup.sql
\`\`\`

### 如何查看失败文件？

\`\`\`bash
cat data/failed/failed_files.json
\`\`\`

## 性能

- **单文件处理**: 3-6 秒/篇
- **1342 篇文章**: 约 1.5-2 小时
- **LLM**: gpt-oss:20b (本地 Ollama)

## 未来扩展

- [ ] 邮件自动处理
- [ ] Web 管理界面
- [ ] 向量检索（相似文章推荐）
- [ ] 多语言支持
- [ ] PDF 文件支持

## License

MIT
