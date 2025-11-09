# 🌍 Multilingual Support Guide

## Overview

The Article Classifier supports multiple languages for category names, making it suitable for international users and multilingual content libraries.

## Configuration

### Setting the Category Language

Edit `config.yaml` and set the `category_language` parameter:

```yaml
classifier:
  category_language: "zh"    # Options: "zh", "en", "auto"
```

## Language Options

### 1. Chinese (`"zh"`)

**Use when**: Your content library is primarily in Chinese.

**Behavior**:
- All category names will be in Chinese
- LLM is instructed to generate Chinese categories
- English category names are automatically normalized to Chinese
- Keywords and summaries are also in Chinese

**Example Output**:
```json
{
  "category_path": ["技术", "编程语言", "Python"],
  "keywords": ["人工智能", "机器学习", "深度学习"],
  "summary": "本文介绍了机器学习的基本概念..."
}
```

**Built-in Normalization**:
- `Technology` → `技术`
- `Travel` → `旅行`
- `Finance` → `金融`
- `Education` → `教育`
- `Language Learning` → `语言学习`
- And 60+ more mappings...

---

### 2. English (`"en"`)

**Use when**: Your content library is primarily in English or you need international standard naming.

**Behavior**:
- All category names will be in English
- LLM is instructed to generate English categories
- Keywords and summaries are in English

**Example Output**:
```json
{
  "category_path": ["Technology", "Programming Languages", "Python"],
  "keywords": ["artificial intelligence", "machine learning", "deep learning"],
  "summary": "This article introduces the basic concepts of machine learning..."
}
```

---

### 3. Auto-detect (`"auto"`)

**Use when**: You have a multilingual content library with both Chinese and English articles.

**Behavior**:
- Category language matches article content language
- Chinese articles → Chinese categories
- English articles → English categories
- LLM automatically detects content language

**Example Outputs**:

For Chinese article:
```json
{
  "category_path": ["技术", "人工智能", "深度学习"],
  "keywords": ["神经网络", "卷积", "训练"],
  "summary": "本文探讨了深度学习的应用..."
}
```

For English article:
```json
{
  "category_path": ["Technology", "Artificial Intelligence", "Deep Learning"],
  "keywords": ["neural networks", "convolution", "training"],
  "summary": "This article explores applications of deep learning..."
}
```

---

## Changing Language Settings

### For New Articles

Simply update `config.yaml` and restart your classification process. All new articles will use the new language setting.

### For Existing Articles

If you change the language setting and want to update existing categories:

1. **Update JSON files**:
   ```bash
   python scripts/fix_json_categories.py
   ```

2. **Note**: This only affects the JSON storage. The database categories will remain in their original language unless you run a full migration.

---

## Adding Custom Language Mappings

If you need to add custom English-to-Chinese category mappings, edit `src/utils/category_normalizer.py`:

```python
# Add your custom mappings
CATEGORY_MAPPING = {
    # ... existing mappings ...
    "your_category": "你的分类",
    "another_category": "另一个分类",
}
```

Or use the dynamic API:

```python
from src/utils/category_normalizer import add_category_mapping

add_category_mapping("Machine Learning", "机器学习")
add_category_mapping("Deep Learning", "深度学习")
```

---

## Testing Your Configuration

Run the multilingual test script:

```bash
python scripts/test_multilang.py
```

This will show your current configuration and optionally test prompt generation for all three language modes.

---

## Best Practices

### For Chinese Users (中文用户)
- Set `category_language: "zh"`
- This provides the best experience for Chinese content
- Automatic normalization handles any English categories from LLM

### For International Users
- Set `category_language: "en"`
- Ensures consistent English naming
- Better for collaboration and sharing

### For Multilingual Libraries
- Set `category_language: "auto"`
- Most flexible option
- May result in mixed categories if content is multilingual

---

## Troubleshooting

**Q: I changed the setting but categories are still in the old language**

A: The setting only affects new classifications. Run `scripts/fix_json_categories.py` to update existing JSON files.

**Q: Can I have both Chinese and English categories in the same library?**

A: Yes, use `category_language: "auto"`. However, this may make category organization more complex.

**Q: How do I add support for other languages (e.g., Spanish, French)?**

A: Currently, only Chinese and English are fully supported. Adding other languages would require:
1. Adding a new language config in `llm_service.py`
2. Creating normalization mappings (optional)
3. Testing with your LLM model

---

## Examples

### Example 1: Chinese-only Library

```yaml
# config.yaml
classifier:
  category_language: "zh"
```

Result: All categories in Chinese, even if LLM occasionally returns English names.

### Example 2: English-only Library

```yaml
# config.yaml
classifier:
  category_language: "en"
```

Result: All categories in English, consistent international naming.

### Example 3: Bilingual Library

```yaml
# config.yaml
classifier:
  category_language: "auto"
```

Result:
- `中文技术文章.md` → `["技术", "人工智能"]`
- `English Tech Article.md` → `["Technology", "Artificial Intelligence"]`

---

## Contributing

If you need support for additional languages or have improved normalization mappings, please contribute:

1. Fork the repository
2. Add your language support
3. Submit a pull request

We welcome contributions for:
- Additional language mappings
- Support for new languages
- Improved language detection
