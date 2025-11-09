"""Flask Web 应用主文件"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, request, jsonify, redirect, url_for
from src.utils.config import get_config
from src.utils.logger import get_logger
from web.services.category_service import CategoryService
from web.services.article_service import ArticleService
from web.services.content_formatter import get_content_formatter

logger = get_logger()

# 创建 Flask 应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'article-classifier-secret-key-change-in-production'

# 加载配置
config = get_config()

# 初始化服务
category_service = CategoryService()
article_service = ArticleService()
content_formatter = get_content_formatter()


@app.route('/')
def index():
    """首页 - 显示分类树"""
    try:
        # 获取分类树
        category_tree = category_service.get_category_tree()

        # 获取统计信息
        stats = {
            'total_articles': article_service.get_total_count(),
            'total_categories': category_service.get_total_count()
        }

        return render_template('index.html',
                             category_tree=category_tree,
                             stats=stats)
    except Exception as e:
        logger.error(f"首页加载失败: {e}")
        return render_template('error.html', error=str(e)), 500


@app.route('/category/<int:category_id>')
def category_view(category_id):
    """分类浏览页"""
    try:
        page = request.args.get('page', 1, type=int)
        sort_by = request.args.get('sort', 'created_at')  # created_at, confidence

        # 获取分类信息
        category = category_service.get_category_by_id(category_id)
        if not category:
            return render_template('error.html', error='分类不存在'), 404

        # 获取分类路径（面包屑）
        category_path = category_service.get_category_path(category_id)

        # 获取该分类下的文章
        articles_per_page = config.web.articles_per_page if hasattr(config, 'web') else 20
        articles, total = article_service.get_articles_by_category(
            category_id,
            page=page,
            per_page=articles_per_page,
            sort_by=sort_by
        )

        # 计算分页
        total_pages = (total + articles_per_page - 1) // articles_per_page

        return render_template('category.html',
                             category=category,
                             category_path=category_path,
                             articles=articles,
                             page=page,
                             total_pages=total_pages,
                             total=total,
                             sort_by=sort_by)
    except Exception as e:
        logger.error(f"分类页加载失败: {e}")
        return render_template('error.html', error=str(e)), 500


@app.route('/article/<int:article_id>')
def article_view(article_id):
    """文章详情页"""
    try:
        # 获取文章详情
        article = article_service.get_article_by_id(article_id)
        if not article:
            return render_template('error.html', error='文章不存在'), 404

        # 获取文章的分类路径
        category_paths = article_service.get_article_category_paths(article_id)

        return render_template('article.html',
                             article=article,
                             category_paths=category_paths)
    except Exception as e:
        logger.error(f"文章页加载失败: {e}")
        return render_template('error.html', error=str(e)), 500


@app.route('/article/<int:article_id>/edit', methods=['GET', 'POST'])
def article_edit(article_id):
    """文章编辑"""
    try:
        if request.method == 'POST':
            # 处理编辑提交
            data = request.get_json()

            success = article_service.update_article(
                article_id,
                summary=data.get('summary'),
                keywords=data.get('keywords'),
                confidence=data.get('confidence'),
                category_ids=data.get('category_ids'),
                content=data.get('content')
            )

            if success:
                return jsonify({'success': True, 'message': '保存成功'})
            else:
                return jsonify({'success': False, 'message': '保存失败'}), 500
        else:
            # 显示编辑页面
            article = article_service.get_article_by_id(article_id)
            if not article:
                return render_template('error.html', error='文章不存在'), 404

            # 获取所有分类（用于选择）
            all_categories = category_service.get_all_categories_flat()

            return render_template('article_edit.html',
                                 article=article,
                                 all_categories=all_categories)
    except Exception as e:
        logger.error(f"文章编辑失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/article/<int:article_id>/reformat', methods=['POST'])
def article_reformat(article_id):
    """重新排版文章内容"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        title = data.get('title', '')

        if not content:
            return jsonify({
                'success': False,
                'message': '内容为空'
            }), 400

        # 调用格式化服务
        result = content_formatter.reformat_content(content, title)

        if result['success']:
            return jsonify({
                'success': True,
                'formatted_content': result['formatted_content'],
                'changes': result['changes']
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('error', '排版失败')
            }), 500

    except Exception as e:
        logger.error(f"文章排版失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/search')
def search():
    """搜索"""
    try:
        query = request.args.get('q', '')
        category_id = request.args.get('category', None, type=int)
        page = request.args.get('page', 1, type=int)

        if not query:
            return render_template('search.html', articles=[], total=0, query='')

        # 执行搜索
        articles_per_page = config.web.articles_per_page if hasattr(config, 'web') else 20
        articles, total = article_service.search_articles(
            query=query,
            category_id=category_id,
            page=page,
            per_page=articles_per_page
        )

        # 计算分页
        total_pages = (total + articles_per_page - 1) // articles_per_page

        return render_template('search.html',
                             articles=articles,
                             query=query,
                             category_id=category_id,
                             page=page,
                             total_pages=total_pages,
                             total=total)
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return render_template('error.html', error=str(e)), 500


@app.errorhandler(404)
def not_found(error):
    """404 错误处理"""
    return render_template('error.html', error='页面不存在'), 404


@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    return render_template('error.html', error='服务器内部错误'), 500


if __name__ == '__main__':
    # 从配置读取端口
    port = config.web.port if hasattr(config, 'web') else 7888
    host = config.web.host if hasattr(config, 'web') else '0.0.0.0'
    debug = config.web.debug if hasattr(config, 'web') else False

    logger.info(f"启动 Web 服务: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
