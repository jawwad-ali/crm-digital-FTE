"""Tests for database.migrations.002_seed_knowledge_base — article data."""

import importlib

_mod = importlib.import_module("database.migrations.002_seed_knowledge_base")
ARTICLES = _mod.ARTICLES


def test_seed_has_minimum_articles():
    """KB must have at least 15 articles (spec SC-010)."""
    assert len(ARTICLES) >= 15


def test_seed_articles_have_required_fields():
    """Each article has title, content, and category."""
    for article in ARTICLES:
        assert "title" in article
        assert "content" in article
        assert "category" in article
        assert len(article["title"]) > 0
        assert len(article["content"]) > 0


def test_seed_articles_cover_multiple_categories():
    """Articles span at least 5 distinct categories."""
    categories = {a["category"] for a in ARTICLES}
    assert len(categories) >= 5
