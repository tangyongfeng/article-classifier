#!/usr/bin/env python3
"""分类相似度检测工具"""

from typing import List, Tuple, Dict
import difflib


class CategorySimilarityDetector:
    """分类相似度检测器"""

    # 同义词映射表
    SYNONYM_GROUPS = [
        {"语言", "语言学", "语言学习"},
        {"股市", "股票市场", "证券市场", "股票交易"},
        {"旅行经历", "旅行经验", "旅游体验"},
        {"独自游与团队游", "团队游与独自游", "独自旅行"},
        {"技术创新", "创新技术", "科技创新"},
        {"社交", "社会交往"},
        {"家庭活动", "家庭事件"},
        {"驾驶规则", "驾驶指令", "驾驶知识"},
        {"驾照", "驾驶执照"},
        {"公司分析", "企业分析"},
        {"通用", "一般", "常规"},
    ]

    def __init__(self, similarity_threshold: float = 0.8):
        """
        初始化相似度检测器

        Args:
            similarity_threshold: 相似度阈值（0-1），超过此值认为相似
        """
        self.threshold = similarity_threshold

    def find_similar_categories(
        self, categories: List[List[str]]
    ) -> List[Tuple[List[str], List[str], float]]:
        """
        找出相似的分类路径

        Args:
            categories: 分类路径列表，如 [["技术", "AI"], ["技术", "人工智能"]]

        Returns:
            相似分类对列表，每个元素是 (分类1, 分类2, 相似度)
        """
        similar_pairs = []

        for i in range(len(categories)):
            for j in range(i + 1, len(categories)):
                similarity = self.calculate_path_similarity(
                    categories[i], categories[j]
                )
                if similarity >= self.threshold:
                    similar_pairs.append((categories[i], categories[j], similarity))

        return similar_pairs

    def calculate_path_similarity(
        self, path1: List[str], path2: List[str]
    ) -> float:
        """
        计算两个分类路径的相似度

        Args:
            path1: 分类路径1，如 ["技术", "编程语言", "Python"]
            path2: 分类路径2，如 ["技术", "编程", "Python"]

        Returns:
            相似度 (0-1)
        """
        # 如果长度差异太大，认为不相似
        if abs(len(path1) - len(path2)) > 1:
            return 0.0

        # 检查同义词
        if self._are_synonyms_path(path1, path2):
            return 1.0

        # 逐层比较
        similarities = []
        max_len = max(len(path1), len(path2))

        for i in range(max_len):
            if i >= len(path1) or i >= len(path2):
                # 路径长度不同的部分
                similarities.append(0.0)
            else:
                # 比较当前层级的相似度
                sim = self._calculate_name_similarity(path1[i], path2[i])
                similarities.append(sim)

        # 返回平均相似度
        return sum(similarities) / len(similarities) if similarities else 0.0

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        计算两个分类名称的相似度

        Args:
            name1: 分类名称1
            name2: 分类名称2

        Returns:
            相似度 (0-1)
        """
        # 完全相同
        if name1 == name2:
            return 1.0

        # 检查是否是同义词
        if self._are_synonyms(name1, name2):
            return 1.0

        # 使用字符串相似度算法
        return difflib.SequenceMatcher(None, name1, name2).ratio()

    def _are_synonyms(self, word1: str, word2: str) -> bool:
        """检查两个词是否是同义词"""
        for group in self.SYNONYM_GROUPS:
            if word1 in group and word2 in group:
                return True
        return False

    def _are_synonyms_path(self, path1: List[str], path2: List[str]) -> bool:
        """检查两个路径是否全部由同义词组成"""
        if len(path1) != len(path2):
            return False

        for i in range(len(path1)):
            if not (path1[i] == path2[i] or self._are_synonyms(path1[i], path2[i])):
                return False

        return True

    def suggest_merge(
        self, path1: List[str], path2: List[str]
    ) -> Dict[str, any]:
        """
        建议如何合并两个相似的分类

        Args:
            path1: 分类路径1
            path2: 分类路径2

        Returns:
            合并建议，包含 keep（保留）和 merge_from（合并源）
        """
        # 优先级规则：
        # 1. 保留更常见的术语
        # 2. 保留更短的名称
        # 3. 保留中文（如果一个是中文一个是英文）

        def get_priority_score(path: List[str]) -> int:
            """计算路径优先级分数，分数越高越应该保留"""
            score = 0

            for name in path:
                # 更常见的术语加分
                if self._is_preferred_term(name):
                    score += 10

                # 更短的名称加分
                score -= len(name)

                # 中文加分
                if self._is_chinese(name):
                    score += 5

            return score

        score1 = get_priority_score(path1)
        score2 = get_priority_score(path2)

        if score1 >= score2:
            return {"keep": path1, "merge_from": path2}
        else:
            return {"keep": path2, "merge_from": path1}

    def _is_preferred_term(self, term: str) -> bool:
        """判断是否是更常用的术语"""
        # 定义首选术语（在同义词组中排第一个）
        preferred_terms = set()
        for group in self.SYNONYM_GROUPS:
            if isinstance(group, set) and group:
                preferred_terms.add(list(group)[0])

        # 手动定义一些首选术语
        manual_preferred = {
            "教育", "语言学习", "金融", "股市", "旅行",
            "旅行经历", "技术", "社会", "交通", "驾驶"
        }

        return term in preferred_terms or term in manual_preferred

    def _is_chinese(self, text: str) -> bool:
        """判断文本是否主要是中文"""
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        return chinese_chars > len(text) / 2


def add_synonym_group(words: List[str]):
    """
    添加新的同义词组

    Args:
        words: 同义词列表
    """
    CategorySimilarityDetector.SYNONYM_GROUPS.append(set(words))


if __name__ == '__main__':
    # 测试
    detector = CategorySimilarityDetector(similarity_threshold=0.8)

    test_paths = [
        ["教育", "语言学习", "德语"],
        ["语言", "德语"],
        ["语言学", "德语", "语法"],
        ["金融", "股市", "公司分析"],
        ["金融", "股票市场", "公司分析"],
    ]

    print("=== 相似分类检测 ===")
    similar_pairs = detector.find_similar_categories(test_paths)

    for path1, path2, similarity in similar_pairs:
        print(f"\n相似度: {similarity:.2f}")
        print(f"  路径1: {' > '.join(path1)}")
        print(f"  路径2: {' > '.join(path2)}")

        suggestion = detector.suggest_merge(path1, path2)
        print(f"  建议: 保留 '{' > '.join(suggestion['keep'])}', 合并 '{' > '.join(suggestion['merge_from'])}'")
