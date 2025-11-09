# Phase 1 Data Model Draft

## 1. Goals
- 支撑最小可用导入链路：Evernote 样本解析 → 清洗 → 结构化存储。
- 清晰区分原始内容、清洗内容、结构化结果，便于后续多 Agent 并行与版本管理。
- 在 Phase 1 内聚焦单用户场景，保留扩展空间以适配更多来源与多语言内容。

## 2. PostgreSQL Schema（建议）

### 2.1 `ingest_source`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID (PK) | 源记录唯一标识 |
| source_type | TEXT | `evernote_html` / `evernote_markdown` / ... |
| source_path | TEXT | 文件系统路径或 URL |
| external_id | TEXT | 若有可用的原始 ID（例如 ENEX GUID） |
| title_hint | TEXT | 从文件或元数据提取的标题提示 |
| language_hint | TEXT | 初步语言探测结果 |
| captured_at | TIMESTAMP | 内容最初生成时间（若可得） |
| collected_at | TIMESTAMP NOT NULL DEFAULT now() | 纳入系统的时间 |
| checksum | TEXT | 原文哈希（去重） |
| status | TEXT | `pending` / `processed` / `failed` |
| notes | JSONB | 额外上下文（例如原始标签、笔记本名称） |

### 2.2 `note`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID (PK) |
| ingest_source_id | UUID FK → ingest_source.id |
| canonical_title | TEXT | 清洗后标题 |
| language | TEXT | 主语言（ISO 639-1） |
| created_at | TIMESTAMP | 原文创建时间（若可得） |
| ingested_at | TIMESTAMP NOT NULL | 入库时间 |
| status | TEXT | `active` / `archived` / `deleted` |
| importance | SMALLINT | 手动或模型打分（0-5） |
| attributes | JSONB | 扩展字段（地点、作者、来源等） |

### 2.3 `content_variant`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID (PK) |
| note_id | UUID FK |
| variant_type | TEXT | `raw_html` / `raw_markdown` / `clean_markdown` / `clean_text` |
| version | INTEGER | 从 1 开始递增 |
| created_by | TEXT | `evernote_agent` / `human` / `gpt-4` |
| created_at | TIMESTAMP |
| content | TEXT | 内容正文（小于 64KB 时可直接存 PG） |
| content_path | TEXT | 若内容较大，指向 `json` 目录或对象存储位置 |
| diff_base_variant_id | UUID Nullable | 若为人工修订，标记基线版本 |
| metadata | JSONB | 长度、摘要片段、hash、语言检测等 |

### 2.4 `extraction`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID (PK) |
| note_id | UUID FK |
| extractor | TEXT | `summary_llm` / `keywords_llm` / `tasks_llm` / `human` |
| payload | JSONB | 结构化结果（摘要、关键词、引用、待办等） |
| quality_score | NUMERIC(5,2) | 0-1 评分或置信度 |
| version | INTEGER | 支持多次抽取 |
| created_at | TIMESTAMP |
| created_by | TEXT |

### 2.5 `processing_journal`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | BIGSERIAL PK |
| note_id | UUID FK |
| stage | TEXT | `ingest` / `clean` / `extract` / ... |
| agent_id | TEXT | Agent 名称与版本 |
| started_at | TIMESTAMP |
| finished_at | TIMESTAMP |
| status | TEXT | `success` / `failed` / `skipped` |
| input_ref | JSONB | 输入摘要（文件路径、variant id 等） |
| output_ref | JSONB | 输出摘要（variant/extraction id） |
| error_detail | TEXT | 失败时的错误信息 |

> 说明：Phase 1 可根据实现成本裁剪字段，但建议保持表结构以便后续扩展。

## 3. JSON 存储布局（`data/` 目录占位）
```
data/
  json/
    notes/
      {note_id}/
        raw/
          v1.html
          metadata.json
        clean/
          v1.md
          v2.md
        extractions/
          summary_v1.json
          keywords_v1.json
```
- 本地 JSON 用于存大体积正文、LLM 输出与日志片段。
- `metadata.json` 用于记录原始文件属性（大小、字符集、旧标签等）。
- Postgres 中的 `content_variant.content_path` 指向具体文件，确保可定位。

## 4. Agent 输入 / 输出契约（概览）

### 4.1 `IngestAgentTask`
```json
{
  "task_id": "uuid",
  "agent": "evernote_ingest",
  "payload": {
    "source_path": "backups/2023年6月/.../note.html",
    "source_type": "evernote_html",
    "batch_id": "2023-06-import",
    "hints": {
      "language": "zh",
      "title": "..."
    }
  },
  "requested_outputs": ["raw_variant", "clean_variant", "extraction_stub"]
}
```

### 4.2 `IngestAgentResult`
```json
{
  "task_id": "uuid",
  "status": "success",
  "note": {
    "ingest_source": { ... },
    "note": { ... },
    "content_variants": [ ... ],
    "extractions": [ ... ]
  },
  "journal": {
    "stage": "ingest",
    "started_at": "...",
    "finished_at": "...",
    "logs": ["detected language zh", "cleaned length 1800 chars"]
  }
}
```

失败时：
```json
{
  "task_id": "uuid",
  "status": "failed",
  "error": {
    "type": "ParseError",
    "message": "missing body tag"
  }
}
```

## 5. 版本管理与命名约定
- 所有 UUID 使用 `uuid4`。
- `variant_type`、`extractor` 使用 snake_case 标识；版本号自增。
- Agent 在写入新版本前需检测内容差异（hash 比对），避免冗余版本。
- `processing_journal` 强制记录所有步骤，无论成功或失败。

## 6. Phase 1 成功标准
1. 从 Evernote 备份中选取样本文件，运行最小 Agent，产生上述表结构和 JSON 文件。
2. Postgres 中能查询到 `ingest_source`、`note`、`content_variant`、`processing_journal` 关联记录。
3. CLI（或简单脚本）可读取某 Note 的原文与清洗文本示例。
4. `processing_journal` 中能看到任务耗时、Agent 版本与错误信息。

## 7. 后续扩展提醒
- 添加 `relation` 表或图数据库以存笔记间引用与关联。
- 引入 `annotation` 表存储人工补充的标签、评论。
- 对 `content_variant` 增加全文索引或对接向量库（Phase 2+）。
- Agent 契约将来可接入队列系统（例如 Redis / RabbitMQ）。
