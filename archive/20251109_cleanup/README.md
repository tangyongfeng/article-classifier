<div align="center">

# 📚 Article Classifier

### Intelligent LLM-Powered Article Classification System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)

[English](README.md) | [简体中文](docs/README_CN.md) | [Deutsch](docs/README_DE.md)

</div>

---

## ✨ Features

- 🤖 **AI-Powered Classification** - Leverages LLM to intelligently categorize articles
- 🌍 **Multilingual Support** - Chinese, English, or auto-detect category naming ([guide](docs/MULTILINGUAL.md))
- 🌳 **Dynamic Category Hierarchy** - Automatically builds and optimizes multi-level category trees
- 📄 **Multi-Format Support** - Handles HTML, Markdown, and plain text files
- 💾 **Dual Storage** - PostgreSQL for metadata + JSON for full content
- ⚡ **Batch Processing** - Efficiently processes thousands of articles
- 🔄 **Auto-Optimization** - Continuously refines category structure based on content patterns
- 🎯 **Confidence Scoring** - Assigns confidence levels to classifications
- 📊 **Comprehensive Logging** - Detailed processing logs and error tracking

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 13 or higher
- [Ollama](https://ollama.ai/) with a compatible LLM model

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/tangyongfeng/article-classifier.git
   cd article-classifier
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up the database**
   ```bash
   psql -U postgres -f scripts/setup_database.sql
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and set your PostgreSQL password
   ```

5. **Configure the system**
   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml to adjust settings (optional)
   ```

### Usage

#### Single File Processing
```bash
python scripts/single_process.py path/to/article.html
```

#### Batch Processing
```bash
# Process all files in a directory
python scripts/batch_process.py --input /path/to/articles

# Run in background
nohup python scripts/batch_process.py --input /path/to/articles > output.log 2>&1 &
```

#### Category Management

After processing articles, use these tools to manage and optimize your category system:

```bash
# Analyze category distribution and find potential duplicates
python scripts/analyze_categories.py

# Detect and merge similar categories (dry run first)
python scripts/merge_similar_categories.py --dry-run --threshold 0.8

# Execute merge after review
python scripts/merge_similar_categories.py --threshold 0.8
```

## 📁 Project Structure

```
article-classifier/
├── src/                      # Source code
│   ├── core/                # Core classification engine
│   │   ├── classifier.py    # Main classifier
│   │   ├── llm_service.py   # LLM integration
│   │   ├── category_manager.py    # Category management
│   │   └── category_optimizer.py  # Auto-optimization
│   ├── loaders/             # File loaders
│   │   ├── html_loader.py
│   │   ├── markdown_loader.py
│   │   └── text_loader.py
│   ├── storage/             # Storage layer
│   │   ├── database.py      # PostgreSQL operations
│   │   ├── json_storage.py  # JSON file operations
│   │   └── models.py        # Data models
│   └── utils/               # Utilities
│       ├── config.py        # Configuration management
│       └── logger.py        # Logging utilities
├── scripts/                  # Executable scripts
│   ├── batch_process.py     # Batch processing
│   ├── single_process.py    # Single file processing
│   ├── test_setup.py        # Setup verification
│   └── setup_database.sql   # Database schema
├── docs/                     # Documentation
│   ├── USAGE_GUIDE.md       # Detailed usage guide
│   ├── README_CN.md         # Chinese README
│   └── README_DE.md         # German README
├── data/                     # Data directory (gitignored)
│   ├── json/                # JSON storage
│   ├── logs/                # Processing logs
│   └── failed/              # Failed files tracking
├── config.yaml.example       # Configuration template
├── .env.example             # Environment variables template
└── requirements.txt         # Python dependencies
```

## 🔧 Configuration

### Environment Variables (.env)
```env
POSTGRES_PASSWORD=your_secure_password
OLLAMA_API_KEY=             # Optional for local Ollama
```

### System Configuration (config.yaml)
```yaml
ollama:
  base_url: "http://localhost:11434"
  model: "gpt-oss:20b"
  temperature: 0.3

classifier:
  max_category_levels: 3
  min_confidence: 0.6
  initial_training_size: 100
  optimization_interval: 100
  auto_optimize: true
  category_language: "zh"    # Language for category names: "zh" (Chinese), "en" (English), "auto" (auto-detect)

database:
  host: "localhost"
  port: 5432
  database: "article_classifier"
  user: "article_classifier_user"

storage:
  json_root: "data/json"
  organize_by_date: true
  save_raw_content: true

processing:
  batch_size: 10
  enable_parallel: false
  checkpoint_interval: 100
  log_level: "INFO"
```

### Configuration Details

#### Category Language (`category_language`)
Controls the language used for category names. This is especially important for international users:

- **`"zh"`** (Chinese) - All category names will be in Chinese
  - Example: `["技术", "编程语言", "Python"]`
  - English categories are automatically normalized to Chinese using built-in mappings
  - Best for Chinese-language content libraries

- **`"en"`** (English) - All category names will be in English
  - Example: `["Technology", "Programming Languages", "Python"]`
  - Best for English-language content libraries
  - International standard naming

- **`"auto"`** (Auto-detect) - Category language matches article content
  - Chinese articles → Chinese categories
  - English articles → English categories
  - Best for multilingual content libraries

**Note**: Changing this setting only affects newly classified articles. Use the provided migration scripts to update existing categories if needed.

## 🎯 How It Works

### Classification Pipeline

1. **File Scanning** - Discovers articles in target directory
2. **Content Loading** - Extracts title, content, and metadata
3. **LLM Analysis** - Sends content to LLM for categorization
4. **Category Creation** - Builds hierarchical categories (up to 3 levels)
5. **Storage** - Saves to PostgreSQL and JSON
6. **Optimization** - Refines category structure every N articles

### Category Strategy

#### Initial Phase (First 100 Articles)
- LLM freely creates category structure
- Builds organic hierarchy based on content patterns
- Establishes foundational taxonomy

#### Continuous Classification (After 100 Articles)
- Classifies into existing categories
- Creates new categories when confidence < 0.6
- Maintains category consistency

#### Auto-Optimization (Every 100 Articles)
- **Split** - Subdivides categories with many articles
- **Merge** - Combines categories with few articles
- **Evolve** - Identifies emerging topics and creates new categories

## 📊 Data Storage

### PostgreSQL Schema
```sql
articles              -- Article metadata
categories            -- Category hierarchy
keywords              -- Extracted keywords
article_categories    -- Article-category relationships
article_keywords      -- Article-keyword relationships
```

### JSON Structure
```
data/json/
├── articles/
│   └── YYYY/
│       └── MM/
│           ├── 000001.json
│           └── 000002.json
└── categories.json
```

## 📈 Performance

- **Processing Speed**: 3-6 seconds per article
- **Batch Performance**: ~2 hours for 1,300 articles
- **LLM**: Tested with gpt-oss:20b on local Ollama
- **Storage**: Efficient dual-storage approach

## 🔍 Query Examples

### SQL Queries
```sql
-- View category tree
WITH RECURSIVE category_tree AS (
  SELECT id, name, parent_id, 1 as level
  FROM categories WHERE parent_id IS NULL
  UNION ALL
  SELECT c.id, c.name, c.parent_id, ct.level + 1
  FROM categories c
  JOIN category_tree ct ON c.parent_id = ct.id
)
SELECT * FROM category_tree ORDER BY level, name;

-- Top keywords
SELECT keyword, usage_count
FROM keywords
ORDER BY usage_count DESC
LIMIT 20;

-- Articles by category
SELECT a.title, c.name as category
FROM articles a
JOIN article_categories ac ON a.id = ac.article_id
JOIN categories c ON ac.category_id = c.id
WHERE c.name = 'Technology';
```

### Python Queries
```python
import json
from pathlib import Path

# Load category tree
with open('data/json/categories.json') as f:
    categories = json.load(f)

# Find articles by category
for article_file in Path('data/json/articles').rglob('*.json'):
    with open(article_file) as f:
        data = json.load(f)
        if 'Technology' in data['classification']['category_path']:
            print(f"{data['metadata']['title']}")
```

## 🛠️ Advanced Usage

### Custom LLM Models
Edit `config.yaml` to use different models:
```yaml
ollama:
  model: "llama2:70b"  # or any other model
```

### Reprocessing Files
```sql
-- Remove article to reprocess
DELETE FROM articles WHERE file_path = '/path/to/article.html';
```

### Backup
```bash
# Backup JSON files
tar -czf backup_$(date +%Y%m%d).tar.gz data/json/

# Backup database
pg_dump -U postgres article_classifier > backup_$(date +%Y%m%d).sql
```

## 🐛 Troubleshooting

### Common Issues

**Q: LLM connection fails**
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve
```

**Q: Database connection error**
```bash
# Verify PostgreSQL is running
pg_isready

# Check credentials in .env
cat .env
```

**Q: Classification quality is poor**
- Adjust `temperature` in config.yaml (lower = more deterministic)
- Use a larger LLM model
- Increase `initial_training_size` for better category foundation

## 🗺️ Roadmap

- [ ] Web UI dashboard
- [ ] Vector search for similar articles
- [ ] Multi-language UI support
- [ ] PDF document support
- [ ] API endpoints for integration
- [ ] Real-time classification service
- [ ] Category suggestion API

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [LangChain](https://langchain.com/)
- Powered by [Ollama](https://ollama.ai/)
- Database: [PostgreSQL](https://www.postgresql.org/)

## 📧 Contact

Project Link: [https://github.com/tangyongfeng/article-classifier](https://github.com/tangyongfeng/article-classifier)

---

<div align="center">

Made with ❤️ by the Article Classifier team

</div>
