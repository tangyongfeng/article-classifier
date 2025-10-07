"""Ollama LLM 服务"""
import json
import requests
from typing import Dict, Any, Optional
from ..utils.config import get_config
from ..utils.logger import get_logger

logger = get_logger()


class OllamaService:
    """Ollama LLM 服务"""

    def __init__(self):
        self.config = get_config()
        self.base_url = self.config.ollama.base_url
        self.model = self.config.ollama.model
        self.temperature = self.config.ollama.temperature
        self.timeout = self.config.ollama.timeout

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        调用 Ollama 生成文本

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词

        Returns:
            生成的文本
        """
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": self.temperature,
            "stream": False
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            return result.get('response', '')
        except Exception as e:
            logger.error(f"Ollama API 调用失败: {e}")
            raise

    def classify_article(
        self,
        title: str,
        content: str,
        current_categories: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分类文章

        Args:
            title: 文章标题
            content: 文章内容（会被截断到前2000字）
            current_categories: 当前分类体系

        Returns:
            分类结果字典
        """
        # 截断内容（避免 token 超限）
        content_preview = content[:2000] if len(content) > 2000 else content

        # 构建 prompt
        prompt = self._build_classification_prompt(title, content_preview, current_categories)

        # 调用 LLM
        response = self.generate(prompt)

        # 解析 JSON 响应
        try:
            result = self._parse_json_response(response)
            return result
        except Exception as e:
            logger.error(f"解析分类结果失败: {e}\n响应: {response}")
            # 返回默认分类
            return {
                "category_path": ["未分类"],
                "new_category_suggestion": None,
                "summary": title[:50],
                "keywords": [],
                "confidence": 0.3
            }

    def _build_classification_prompt(
        self,
        title: str,
        content: str,
        current_categories: Optional[Dict[str, Any]]
    ) -> str:
        """构建分类 prompt"""
        categories_str = ""
        if current_categories and current_categories.get("categories"):
            categories_str = self._format_categories(current_categories["categories"])
        else:
            categories_str = "当前无分类体系，请自由创建合适的分类（最多3层）"

        prompt = f"""你是一个专业的文档分类助手。请分析以下文章内容，返回 JSON 格式的分类结果。

**当前分类体系：**
{categories_str}

**文章信息：**
标题: {title}
内容预览: {content}

**要求：**
1. 如果能匹配现有分类，返回最合适的类别路径（最多3层，例如 ["技术", "编程语言", "Python"]）
2. 如果现有分类不合适，可以在 new_category_suggestion 中建议新类别
3. 提取 3-5 个关键词
4. 生成 50 字内的摘要
5. 评估分类置信度 (0-1)，置信度应该真实反映匹配程度

**返回格式（必须是有效的 JSON）：**
{{
  "category_path": ["一级类别", "二级类别", "三级标签"],
  "new_category_suggestion": null,
  "summary": "文章摘要（50字内）",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "confidence": 0.85
}}

**注意：只返回 JSON，不要包含任何其他文字说明。**
"""
        return prompt

    def _format_categories(self, categories: list) -> str:
        """格式化分类树"""
        lines = []
        for cat in categories:
            self._format_category_recursive(cat, lines, 0)
        return "\n".join(lines) if lines else "暂无分类"

    def _format_category_recursive(self, cat: Dict[str, Any], lines: list, level: int):
        """递归格式化分类"""
        indent = "  " * level
        count = cat.get('article_count', 0)
        lines.append(f"{indent}{'├─' if level > 0 else ''} {cat['name']} ({count}篇)")

        for child in cat.get('children', []):
            self._format_category_recursive(child, lines, level + 1)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析 JSON 响应"""
        # 尝试提取 JSON 块
        response = response.strip()

        # 移除可能的 markdown 代码块标记
        if response.startswith("```"):
            lines = response.split('\n')
            response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response

        # 尝试解析 JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试从响应中提取 JSON 对象
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise

    def optimize_categories(
        self,
        total_articles: int,
        category_distribution: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分类优化建议

        Args:
            total_articles: 总文章数
            category_distribution: 分类分布统计

        Returns:
            优化建议
        """
        prompt = f"""你是一个分类体系优化专家。请分析当前的文章分类分布，提供优化建议。

**当前统计：**
- 总文章数: {total_articles}
- 分类分布:
{json.dumps(category_distribution, ensure_ascii=False, indent=2)}

**优化规则：**
1. 如果某个一级类别占比超过 30%，建议细分为子类别
2. 如果某个类别文章数少于总数的 2%，建议合并到其他类别
3. 识别新兴主题（最近文章集中的领域），建议新类别
4. 保持层级不超过3层

**返回格式（必须是有效的 JSON）：**
{{
  "optimization_actions": [
    {{"action": "split", "category": "技术", "new_subcategories": ["前端", "后端", "运维"]}},
    {{"action": "merge", "categories": ["段子", "佛学"], "into": "杂文"}},
    {{"action": "create", "category": "投资理财", "reason": "投资相关文章占比15%"}}
  ]
}}

**注意：只返回 JSON，不要包含任何其他文字说明。**
"""

        response = self.generate(prompt)

        try:
            return self._parse_json_response(response)
        except Exception as e:
            logger.error(f"解析优化建议失败: {e}")
            return {"optimization_actions": []}


# 全局实例
_llm_service: Optional[OllamaService] = None


def get_llm_service() -> OllamaService:
    """获取 LLM 服务实例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = OllamaService()
    return _llm_service
