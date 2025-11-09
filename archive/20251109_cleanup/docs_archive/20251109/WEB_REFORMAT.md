# Web界面 - 内容重新排版功能

## 功能概述

为Web界面添加了"重新排版"功能，专门用于处理从 Evernote 导出的混乱格式文章。使用本地 LLM 对内容进行**轻量级**排版，不过度修饰。

## 功能特点

### ✅ 轻量级排版
- 仅修正格式问题，不改写内容
- 保留原文语气、用词、信息
- 不添加新内容或过度修饰

### 🎯 修正内容
- 修正段落断行（去除不必要的换行）
- 合并被错误分割的句子
- 统一列表格式（- 或 1. 2. 3.）
- 修正标题层级（# ## ###）
- 保持代码块、引用、表格、链接格式

### 🔄 用户友好
- 实时排版反馈
- 支持一键撤销
- 自动保存排版结果
- Markdown 自动渲染

## 使用方法

### 1. 查看文章

访问任意文章详情页面，例如：
```
http://localhost:7888/article/123
```

### 2. 点击"重新排版"按钮

在文章内容上方，点击 **"重新排版"** 按钮：
```
[编辑文章] [重新排版]
```

### 3. 等待排版完成

- 按钮显示"禁用"状态
- 顶部显示"正在排版..."
- 通常需要 10-20 秒（取决于文章长度）

### 4. 查看排版结果

排版完成后：
- ✅ 显示成功提示："排版成功！已修正段落断行，已统一格式风格"
- 📝 文章内容自动更新为排版后的版本
- 💾 排版结果自动保存到数据库
- ↩️ 出现"撤销排版"按钮

### 5. 撤销排版（可选）

如果不满意排版结果，点击 **"撤销排版"** 按钮即可恢复原始内容。

## 技术实现

### 后端架构

#### 1. 内容格式化服务
**文件**: `web/services/content_formatter.py`

```python
class ContentFormatter:
    def reformat_content(self, content: str, title: str) -> dict:
        """使用 LLM 重新排版内容"""
        # 调用 Ollama LLM
        # 返回排版后的内容
```

**核心功能**：
- 构建专门的排版提示词
- 调用本地 LLM (gpt-oss:20b)
- 解析返回结果
- 错误处理和降级

#### 2. API 路由
**文件**: `web/app.py`

```python
@app.route('/api/article/<int:article_id>/reformat', methods=['POST'])
def article_reformat(article_id):
    """重新排版文章内容"""
```

**请求格式**：
```json
{
  "content": "原始文章内容...",
  "title": "文章标题"
}
```

**响应格式**：
```json
{
  "success": true,
  "formatted_content": "排版后的内容...",
  "changes": ["已修正段落断行", "已统一格式风格"]
}
```

#### 3. 内容保存
**文件**: `web/services/article_service.py`

```python
def update_article(
    self,
    article_id: int,
    content: Optional[str] = None,
    ...
) -> bool:
    """更新文章内容（包括排版后的内容）"""
```

### 前端实现

#### 1. 用户界面
**文件**: `web/templates/article.html`

**新增元素**：
- "重新排版"按钮 (`#reformatBtn`)
- 状态提示区 (`#reformatStatus`)
- 消息提示区 (`#message`)
- "撤销排版"按钮（动态添加）

#### 2. JavaScript 逻辑

**核心功能**：
```javascript
// 1. 发送排版请求
$.ajax({
    url: '/api/article/<id>/reformat',
    method: 'POST',
    data: JSON.stringify({content, title})
});

// 2. Markdown 转 HTML
function markdownToHtml(markdown) {
    // 支持标题、粗体、斜体、列表
}

// 3. 保存排版结果
function saveFormattedContent(content) {
    // 自动保存到数据库
}

// 4. 撤销功能
$('#undoBtn').click(function() {
    // 恢复原始内容
});
```

## LLM 提示词策略

### 排版提示词设计

```
你是一个专业的文本排版助手。请对以下从 Evernote 导出的混乱文章内容进行**轻量级**重新排版。

**排版要求**:
1. **轻量级排版** - 仅修正格式问题，不改写内容
2. **保留原文** - 不要修改原文内容、语气、用词
3. **修正格式混乱**:
   - 修正段落断行
   - 合并被错误分割的句子
   - 统一列表格式
   - 修正标题层级
4. **保持结构**:
   - 保留原有章节结构
   - 保留代码块、引用块
5. **不要做**:
   - ❌ 不要改写、美化、扩充内容
   - ❌ 不要添加新的内容或观点
   - ❌ 不要删除原有信息
```

### 关键策略

1. **强调"轻量级"** - 多次提醒不要过度修饰
2. **明确禁止项** - 使用 ❌ 标记禁止操作
3. **保留原文** - 强调不改写、不删除
4. **纯文本输出** - 不需要 JSON 格式，直接返回内容

## 配置说明

### LLM 配置

重新排版功能使用与文章分类相同的 LLM 配置：

**文件**: `config.yaml`

```yaml
ollama:
  base_url: http://localhost:11434
  model: gpt-oss:20b
  temperature: 0.7
  timeout: 120
```

### 内容长度限制

为避免 token 超限，内容会被截断：

```python
content_preview = content[:8000] if len(content) > 8000 else content
```

## 使用场景

### 适用情况
✅ Evernote 导出的混乱格式文章
✅ 段落断行错误的文档
✅ 列表格式不统一的内容
✅ 标题层级混乱的文章

### 不适用情况
❌ 需要内容改写的情况
❌ 需要翻译的文档
❌ 需要扩充内容的文章
❌ 代码文件或日志文件

## 性能考虑

### 处理时间
- **短文章** (<1000字): 5-10 秒
- **中等文章** (1000-5000字): 10-20 秒
- **长文章** (>5000字): 20-30 秒

### 优化建议
1. **并发控制** - 限制同时排版的文章数量
2. **缓存机制** - 缓存已排版的内容
3. **异步处理** - 对于长文章使用后台任务
4. **进度反馈** - 显示处理进度条

## 错误处理

### 常见错误

1. **LLM 服务不可用**
   ```
   排版失败: LLM API 调用失败
   ```
   - 检查 Ollama 服务是否运行
   - 检查模型是否已加载

2. **内容过短**
   ```
   排版失败: 内容过短，无需排版
   ```
   - 文章内容少于 10 个字符

3. **LLM 返回格式错误**
   ```
   排版失败: LLM 返回内容过短
   ```
   - LLM 返回了不完整的内容
   - 可以重试

### 降级策略

如果排版失败：
- 保留原始内容不变
- 显示友好的错误提示
- 用户可以重试或手动编辑

## 扩展功能建议

### 1. 批量排版
支持对整个分类下的文章批量排版：
```python
def batch_reformat_category(category_id: int):
    """批量排版分类下的所有文章"""
```

### 2. 排版历史
保存排版历史，支持查看和回退：
```sql
CREATE TABLE reformat_history (
    id SERIAL PRIMARY KEY,
    article_id INT,
    original_content TEXT,
    formatted_content TEXT,
    created_at TIMESTAMP
);
```

### 3. 自定义排版规则
允许用户自定义排版规则：
```yaml
reformat_rules:
  remove_empty_lines: true
  unify_list_style: true
  fix_heading_levels: true
```

### 4. 预览模式
排版前预览效果，确认后再保存：
```javascript
function previewReformat() {
    // 显示排版预览对比
}
```

## 相关文件

- **格式化服务**: `web/services/content_formatter.py`
- **API 路由**: `web/app.py` (article_reformat)
- **文章服务**: `web/services/article_service.py`
- **前端页面**: `web/templates/article.html`
- **使用文档**: `docs/WEB_REFORMAT.md`

## 总结

重新排版功能提供了一个简单而强大的方式来修正从 Evernote 导出的混乱格式文章。通过使用本地 LLM 和轻量级排版策略，既保证了内容的准确性，又提升了阅读体验。

**核心理念**：修正格式，不改内容！✨
