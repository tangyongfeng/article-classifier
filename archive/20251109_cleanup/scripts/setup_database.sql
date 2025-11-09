-- 创建数据库和用户
-- 使用方式: psql -U postgres -f scripts/setup_database.sql

-- 创建数据库
CREATE DATABASE article_classifier;

-- 创建用户 (密码: AcUs3r#2025!Px7Qm)
CREATE USER article_classifier_user WITH ENCRYPTED PASSWORD 'AcUs3r#2025!Px7Qm';

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE article_classifier TO article_classifier_user;

-- 连接到新数据库
\c article_classifier

-- 授予 schema 权限
GRANT ALL ON SCHEMA public TO article_classifier_user;

-- 授予默认权限（对未来创建的表）
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO article_classifier_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO article_classifier_user;

-- 创建表结构

-- 1. articles 表
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    json_path TEXT UNIQUE NOT NULL,
    title TEXT,
    summary TEXT,
    created_at TIMESTAMP,
    processed_at TIMESTAMP DEFAULT NOW(),
    file_format VARCHAR(10),
    file_size INTEGER,
    confidence REAL
);

CREATE INDEX idx_articles_created ON articles(created_at);
CREATE INDEX idx_articles_processed ON articles(processed_at);
CREATE INDEX idx_articles_file_format ON articles(file_format);

-- 2. categories 表
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES categories(id),
    level INTEGER CHECK (level IN (1, 2, 3)),
    description TEXT,
    article_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, parent_id)
);

CREATE INDEX idx_categories_parent ON categories(parent_id);
CREATE INDEX idx_categories_level ON categories(level);
CREATE INDEX idx_categories_name ON categories(name);

-- 3. article_categories 表
CREATE TABLE article_categories (
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, category_id)
);

CREATE INDEX idx_ac_article ON article_categories(article_id);
CREATE INDEX idx_ac_category ON article_categories(category_id);

-- 4. keywords 表
CREATE TABLE keywords (
    id SERIAL PRIMARY KEY,
    keyword TEXT UNIQUE NOT NULL,
    usage_count INTEGER DEFAULT 0
);

CREATE INDEX idx_keywords_keyword ON keywords(keyword);
CREATE INDEX idx_keywords_usage ON keywords(usage_count DESC);

-- 5. article_keywords 表
CREATE TABLE article_keywords (
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    keyword_id INTEGER REFERENCES keywords(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, keyword_id)
);

CREATE INDEX idx_ak_article ON article_keywords(article_id);
CREATE INDEX idx_ak_keyword ON article_keywords(keyword_id);

-- 6. category_snapshots 表
CREATE TABLE category_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date TIMESTAMP DEFAULT NOW(),
    total_articles INTEGER,
    category_tree JSONB,
    statistics JSONB
);

CREATE INDEX idx_snapshots_date ON category_snapshots(snapshot_date DESC);

-- 授予所有表的权限
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO article_classifier_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO article_classifier_user;

-- 完成
\echo '数据库初始化完成！'
\echo '数据库: article_classifier'
\echo '用户: article_classifier_user'
\echo '密码: AcUs3r#2025!Px7Qm'
