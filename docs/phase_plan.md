# Phase Plan Adjustment

## Phase 1a · Evernote Ingest Skeleton
- 建立基础数据模型（PostgreSQL / JSON 布局）
- 制作 Evernote 样本采集脚本，输出结构化的样本报告
- 实现最小 Ingest Agent：格式探测 → 清洗 → 存储 → processing_journal
- 确保 CLI 可检索导入的 Note，并显示原文/清洗文本示例

## Phase 1b · LLM Tooling & Enhanced Cleaning
- 设计 LLM 调度框架：模型注册、Prompt 模板、重跑策略
- 将 Phase 1a 的清洗/分类步骤改写为调用 LLM Agent（带降级方案）
- 加入内容质量评估：摘要长度、关键字段完备性、错误日志
- 扩展清洗规则库：针对不同来源样本更新处理策略

## Phase 2 · Unified Storage & Search Foundations
- 完善存储分层（content_variant、多版本 Diff、向量库占位）
- 初始化全文检索服务（倒排 + 关键字段过滤）
- 拓展处理日志：指标统计、失败重试监控
- 打通基础 Web 视图或 API 用于浏览 / 搜索 / 编辑
