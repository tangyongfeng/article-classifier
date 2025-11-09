"""分类标准化工具"""
from typing import List


# 英文到中文的分类映射
CATEGORY_MAPPING = {
    # 技术相关
    "technology": "技术",
    "tech": "技术",
    "programming": "编程",
    "coding": "编程",
    "development": "开发",
    "software": "软件",
    "ai": "人工智能",
    "artificial intelligence": "人工智能",
    "machine learning": "机器学习",
    "ml": "机器学习",
    "data science": "数据科学",

    # 商务相关
    "business": "商务",
    "commerce": "商务",
    "entrepreneurship": "创业",
    "startup": "创业",
    "management": "管理",
    "company analysis": "公司分析",
    "stock market": "股票市场",

    # 教育相关
    "education": "教育",
    "learning": "学习",
    "study": "学习",
    "teaching": "教学",

    # 语言学习
    "language learning": "语言学习",
    "language": "语言学习",
    "grammar": "语法",
    "vocabulary": "词汇",
    "verb conjugation": "动词变位",
    "german": "德语",
    "german language exams": "德语考试",

    # 旅行
    "travel": "旅行",
    "tourism": "旅游",
    "trip": "旅行",
    "travel experience": "旅行经历",
    "travel preferences": "旅行偏好",
    "solo travel": "独自旅行",
    "group vs solo travel": "团队游与独自游",
    "solo vs group travel": "独自游与团队游",
    "hotel booking inquiry": "酒店预订咨询",
    "accommodation": "住宿",
    "frequent flyer": "常旅客",

    # 金融
    "finance": "金融",
    "financial": "金融",
    "investment": "投资",
    "investing": "投资",
    "money": "理财",
    "payment services": "支付服务",
    "td ameritrade": "TD Ameritrade",

    # 健康
    "health": "健康",
    "fitness": "健身",
    "wellness": "健康",
    "medical": "医疗",

    # 生活
    "lifestyle": "生活",
    "life": "生活",
    "daily": "日常",

    # 社交与家庭
    "social": "社交",
    "family relationships": "家庭关系",
    "family events": "家庭活动",
    "family discussions": "家庭讨论",
    "wedding congratulations": "婚礼祝贺",

    # 娱乐
    "entertainment": "娱乐",
    "fun": "娱乐",
    "hobby": "兴趣爱好",

    # 其他
    "unclassified": "未分类",
    "uncategorized": "未分类",
    "misc": "杂项",
    "miscellaneous": "杂项",
    "other": "其他",
    "general": "通用",
    "personal experience": "个人经历",
}


def normalize_category_name(category: str) -> str:
    """
    标准化单个分类名称

    Args:
        category: 分类名称（可能是中文或英文）

    Returns:
        标准化后的中文分类名称
    """
    if not category:
        return "未分类"

    # 转小写进行匹配
    category_lower = category.lower().strip()

    # 如果是英文，转换为中文
    if category_lower in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[category_lower]

    # 如果已经是中文或者不在映射表中，返回原值（去除首尾空格）
    return category.strip()


def normalize_category_path(category_path: List[str]) -> List[str]:
    """
    标准化分类路径

    Args:
        category_path: 分类路径列表，如 ["Technology", "Programming", "Python"]

    Returns:
        标准化后的分类路径，如 ["技术", "编程", "Python"]
    """
    if not category_path:
        return ["未分类"]

    return [normalize_category_name(cat) for cat in category_path]


def add_category_mapping(english: str, chinese: str):
    """
    动态添加分类映射

    Args:
        english: 英文分类名
        chinese: 中文分类名
    """
    CATEGORY_MAPPING[english.lower()] = chinese


def get_all_mappings() -> dict:
    """获取所有分类映射"""
    return CATEGORY_MAPPING.copy()
