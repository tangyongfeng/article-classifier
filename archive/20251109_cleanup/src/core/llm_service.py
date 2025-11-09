"""Ollama LLM 服务"""
import json
import requests
from typing import Dict, Any, Optional
from ..utils.config import get_config
from ..utils.logger import get_logger
from ..utils.category_normalizer import normalize_category_path

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
        return self.generate_with_timeout(prompt, system_prompt, timeout=self.timeout)

    def generate_with_timeout(self, prompt: str, system_prompt: Optional[str] = None, timeout: int = None) -> str:
        """
        调用 Ollama 生成文本（可指定超时时间）

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            timeout: 超时时间（秒），None 则使用配置的默认值

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

        actual_timeout = timeout if timeout is not None else self.timeout

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=actual_timeout
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
        try:
            response = self.generate(prompt)
        except Exception as e:
            logger.error(f"LLM API 调用失败: {e}")
            return self._get_default_classification(title)

        # 解析 JSON 响应
        try:
            result = self._parse_json_response(response)

            # 验证返回结果的完整性
            if not self._validate_classification_result(result):
                logger.warning(f"分类结果不完整，使用默认值。原始结果: {result}")
                return self._get_default_classification(title)

            # 只在配置为中文时才进行标准化（统一中英文）
            if self.config.classifier.category_language == "zh":
                if "category_path" in result and result["category_path"]:
                    result["category_path"] = normalize_category_path(result["category_path"])
                # 标准化新分类建议
                if "new_category_suggestion" in result and result["new_category_suggestion"]:
                    if isinstance(result["new_category_suggestion"], list):
                        result["new_category_suggestion"] = normalize_category_path(result["new_category_suggestion"])

            return result
        except Exception as e:
            logger.error(f"解析分类结果失败: {e}\n响应内容: {response[:500] if response else 'None'}")
            return self._get_default_classification(title)

    def _validate_classification_result(self, result: Dict[str, Any]) -> bool:
        """验证分类结果的完整性"""
        if not isinstance(result, dict):
            return False

        # 必需字段检查
        required_fields = ["category_path", "summary", "keywords", "confidence"]
        for field in required_fields:
            if field not in result:
                logger.warning(f"缺少必需字段: {field}")
                return False

        # category_path 必须是非空列表
        if not isinstance(result["category_path"], list) or len(result["category_path"]) == 0:
            logger.warning(f"category_path 无效: {result.get('category_path')}")
            return False

        # keywords 必须是列表
        if not isinstance(result["keywords"], list):
            logger.warning(f"keywords 必须是列表: {result.get('keywords')}")
            return False

        # confidence 必须是数字
        if not isinstance(result["confidence"], (int, float)):
            logger.warning(f"confidence 必须是数字: {result.get('confidence')}")
            return False

        return True

    def _get_default_classification(self, title: str) -> Dict[str, Any]:
        """获取默认分类结果"""
        default_category = "未分类" if self.config.classifier.category_language == "zh" else "Unclassified"
        return {
            "category_path": [default_category],
            "new_category_suggestion": None,
            "summary": title[:50] if title else "无标题",
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

        # 根据配置获取分类语言
        category_lang = self.config.classifier.category_language

        # 语言配置映射
        lang_config = {
            "zh": {
                "lang_name": "中文",
                "example_path": ["技术", "编程语言", "Python"],
                "instruction": "所有分类名称必须使用中文",
                "examples": '例如：使用"技术"而不是"Technology"，使用"旅行"而不是"Travel"',
                "keyword_instruction": "提取 3-5 个中文关键词",
                "summary_instruction": "生成 50 字内的中文摘要"
            },
            "en": {
                "lang_name": "English",
                "example_path": ["Technology", "Programming Languages", "Python"],
                "instruction": "All category names must be in English",
                "examples": "For example: use 'Technology' not '技术', use 'Travel' not '旅行'",
                "keyword_instruction": "Extract 3-5 English keywords",
                "summary_instruction": "Generate a summary within 50 words in English"
            },
            "auto": {
                "lang_name": "自动检测 / auto-detect",
                "example_path": ["Technology", "Programming Languages", "Python"],
                "instruction": "使用与文章内容相同的语言作为分类名称",
                "examples": "中文文章使用中文分类，英文文章使用英文分类",
                "keyword_instruction": "提取 3-5 个关键词（与文章语言一致）",
                "summary_instruction": "生成 50 字内的摘要（与文章语言一致）"
            }
        }

        # 获取当前语言配置（默认中文）
        lang_settings = lang_config.get(category_lang, lang_config["zh"])

        prompt = f"""你是一个专业的文档分类助手。请分析以下文章内容，返回 JSON 格式的分类结果。

**当前分类体系：**
{categories_str}

**文章信息：**
标题: {title}
内容预览: {content}

**分类规则（按优先级排序）：**
1. **{lang_settings['instruction']}**（{lang_settings['examples']}）
2. **必须优先使用现有分类**：仔细查看上面的分类体系，如果文章内容与任何现有分类相关，必须使用现有分类路径
3. **避免创建重复分类**：不要创建与现有分类意思相近的新分类。例如：
   - 如果已有"教育 > 语言学习"，不要创建"语言"、"语言学"等分类
   - 如果已有"金融 > 股市"，不要创建"股票市场"、"证券"等分类
   - 如果已有"旅行 > 旅行经历"，不要创建"旅行经验"、"旅游体验"等分类
4. 只有在现有分类完全不适合时，才在 new_category_suggestion 中建议新类别
5. 分类层级最多3层（例如 {lang_settings['example_path']}）
6. {lang_settings['keyword_instruction']}
7. {lang_settings['summary_instruction']}
8. 评估分类置信度 (0-1)，置信度应该真实反映匹配程度

**返回格式（必须是有效的 JSON）：**
{{
  "category_path": {lang_settings['example_path']},
  "new_category_suggestion": null,
  "summary": "文章摘要",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "confidence": 0.85
}}

**重要：**
- 分类、关键词、摘要的语言必须符合上述要求
- 优先使用现有分类，不要随意创建新分类
- 只返回 JSON，不要包含任何其他文字说明
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
