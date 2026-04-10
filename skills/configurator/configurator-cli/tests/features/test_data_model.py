"""Tests for the Data Model feature."""

from configurator.features.data_model import DataModelFeature, _parse_sql, _parse_drizzle_schema
from configurator.features.base import RenderContext


class TestDataModelFeature:
    def setup_method(self):
        self.feature = DataModelFeature()

    def test_meta(self):
        meta = self.feature.meta()
        assert meta.id == "data_model"
        assert meta.category == "data-model"
        assert "backend" in meta.dependencies

    def test_no_backend_shows_message(self):
        ctx = RenderContext(deployed_keys=set(), urls={}, live_domains=set(), config={})
        html = self.feature.config_html(ctx)
        assert "No backend configured" in html

    def test_backend_enabled_no_schema(self):
        ctx = RenderContext(
            deployed_keys=set(), urls={}, live_domains=set(),
            config={"backend": {"enabled": True}},
        )
        html = self.feature.config_html(ctx)
        assert "No schema found" in html

    def test_read_only(self):
        assert self.feature.config_js_read() == ""
        assert self.feature.config_js_populate() == ""
        assert self.feature.config_js_update_disabled() == ""
        assert self.feature.default_config() == {}
        assert self.feature.deployed_keys({}) == set()


class TestParseSql:
    def test_basic_create_table(self):
        sql = """
        CREATE TABLE users (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        tables = _parse_sql(sql)
        assert len(tables) == 1
        assert tables[0]["name"] == "users"
        assert len(tables[0]["columns"]) == 4
        assert tables[0]["columns"][0]["name"] == "id"
        assert tables[0]["columns"][1]["name"] == "email"

    def test_multiple_tables(self):
        sql = """
        CREATE TABLE users (
          id UUID PRIMARY KEY
        );
        CREATE TABLE posts (
          id UUID PRIMARY KEY,
          user_id UUID REFERENCES users(id)
        );
        """
        tables = _parse_sql(sql)
        assert len(tables) == 2
        assert tables[0]["name"] == "users"
        assert tables[1]["name"] == "posts"

    def test_if_not_exists(self):
        sql = "CREATE TABLE IF NOT EXISTS users (id UUID PRIMARY KEY);"
        tables = _parse_sql(sql)
        assert len(tables) == 1
        assert tables[0]["name"] == "users"

    def test_empty_sql(self):
        assert _parse_sql("") == []
        assert _parse_sql("SELECT 1;") == []


class TestParseDrizzle:
    def test_basic_schema(self):
        ts = """
        export const users = pgTable('users', {
          id: uuid('id').primaryKey().defaultRandom(),
          email: text('email').notNull().unique(),
          role: text('role').notNull().default('user'),
        });
        """
        tables = _parse_drizzle_schema(ts)
        assert len(tables) == 1
        assert tables[0]["name"] == "users"
        cols = tables[0]["columns"]
        assert any(c["name"] == "id" for c in cols)
        assert any(c["name"] == "email" for c in cols)

    def test_empty_ts(self):
        assert _parse_drizzle_schema("") == []
