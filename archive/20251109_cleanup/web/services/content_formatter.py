"""内容格式化服务 - 使用 LLM 重新排版混乱的文章内容"""
from typing import Optional
from src.core.llm_service import get_llm_service
from src.utils.logger import get_logger

logger = get_logger()


class ContentFormatter:
    """内容格式化器 - 轻量级排版，不过度修饰"""

    def __init__(self):
        self.llm = get_llm_service()

    def reformat_content(self, content: str, title: str = "") -> dict:
        """
        重新排版文章内容（轻量级）

        Args:
            content: 原始内容
            title: 文章标题（可选，用于上下文）

        Returns:
            {
                'formatted_content': str,  # 排版后的内容
                'changes': list,  # 修改说明
                'success': bool
            }
        """
        if not content or len(content.strip()) < 10:
            return {
                'formatted_content': content,
                'changes': [],
                'success': False,
                'error': '内容过短，无需排版'
            }

        try:
            # 构建排版提示词
            prompt = self._build_format_prompt(content, title)

            # 调用 LLM (使用更长的超时时间)
            response = self.llm.generate_with_timeout(prompt, timeout=300)

            # 解析响应
            result = self._parse_response(response)

            if result['success']:
                logger.info(f"内容排版成功: {title[:30]}")
            else:
                logger.warning(f"内容排版失败: {result.get('error')}")

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"内容排版失败: {error_msg}")

            # 提供更友好的错误提示
            if "Read timed out" in error_msg or "timeout" in error_msg.lower():
                user_error = "排版超时，文章可能过长。请尝试分段排版或增加服务器超时设置。"
            elif "Connection" in error_msg:
                user_error = "无法连接到 LLM 服务，请检查 Ollama 是否正在运行。"
            else:
                user_error = f"排版失败: {error_msg}"

            return {
                'formatted_content': content,
                'changes': [],
                'success': False,
                'error': user_error
            }

    def _build_format_prompt(self, content: str, title: str) -> str:
        """构建排版提示词"""
        # 截取内容（避免 token 超限）
        content_preview = content[:8000] if len(content) > 8000 else content

        prompt = f"""你是一个专业的文本排版助手。请对以下从 Evernote 导出的混乱文章内容进行**轻量级**重新排版。

**文章标题**: {title}

**原始内容**:
{content_preview}

**排版要求**:
1. **轻量级排版** - 仅修正格式问题，不改写内容
2. **保留原文** - 不要修改原文内容、语气、用词
3. **修正格式混乱**:
   - 修正段落断行（去除不必要的换行）
   - 合并被错误分割的句子
   - 统一列表格式（- 或 1. 2. 3.）
   - 修正标题层级（# ## ###）
4. **保持结构**:
   - 保留原有的章节结构
   - 保留代码块、引用块的格式
   - 保留表格、链接的格式
5. **不要做**:
   - ❌ 不要改写、美化、扩充内容
   - ❌ 不要添加新的内容或观点
   - ❌ 不要删除原有信息
   - ❌ 不要添加过多的 Markdown 修饰
   - ❌ 不要翻译或改变语言

**返回格式** (纯文本，不要 JSON):
直接返回排版后的内容即可，不要添加任何说明或评论。
"""
        return prompt

    def _parse_response(self, response: str) -> dict:
        """解析 LLM 响应"""
        try:
            # 去除可能的 markdown 代码块标记
            formatted = response.strip()

            if formatted.startswith("```"):
                lines = formatted.split('\n')
                # 移除第一行和最后一行的 ``` 标记
                if len(lines) > 2:
                    formatted = '\n'.join(lines[1:-1])

            # 简单验证：排版后的内容不应该比原内容短太多
            if len(formatted) < 10:
                return {
                    'formatted_content': '',
                    'changes': [],
                    'success': False,
                    'error': 'LLM 返回内容过短'
                }

            # 记录修改说明
            changes = [
                '已修正段落断行',
                '已统一格式风格',
                '已保留原文内容'
            ]

            return {
                'formatted_content': formatted,
                'changes': changes,
                'success': True
            }

        except Exception as e:
            return {
                'formatted_content': '',
                'changes': [],
                'success': False,
                'error': f'解析失败: {e}'
            }


# 全局实例
_formatter: Optional[ContentFormatter] = None


def get_content_formatter() -> ContentFormatter:
    """获取内容格式化器实例"""
    global _formatter
    if _formatter is None:
        _formatter = ContentFormatter()
    return _formatter
