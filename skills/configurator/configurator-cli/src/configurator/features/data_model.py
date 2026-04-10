"""Data Model feature — displays SQL schema from the backend."""

from __future__ import annotations

import re
from pathlib import Path

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"


class DataModelFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="data_model",
            label="Data Model",
            version=_VERSION,
            order=25,
            dependencies=["backend"],
            category="data-model",
        )

    def config_html(self, ctx: RenderContext) -> str:
        backend = ctx.config.get("backend", {})
        if not backend.get("enabled"):
            return (
                '<fieldset>\n<legend>Data Model</legend>\n'
                '<p class="readonly" style="color: var(--fg-dim);">'
                'No backend configured. Enable a backend to view the data model.'
                '</p>\n</fieldset>'
            )

        # Try to read schema from the project
        tables = _read_schema(ctx.config.get("local_path"))

        if not tables:
            return (
                '<fieldset>\n<legend>Data Model</legend>\n'
                '<p class="readonly" style="color: var(--fg-dim);">'
                'No schema found. Deploy the backend to generate the database schema.'
                '</p>\n</fieldset>'
            )

        rows = ""
        for table in tables:
            rows += f'<div class="db-table">\n'
            rows += f'<div class="db-table-name">{_esc(table["name"])}</div>\n'
            rows += '<table class="db-columns">\n'
            rows += '<tr><th>Column</th><th>Type</th><th>Constraints</th></tr>\n'
            for col in table["columns"]:
                rows += (
                    f'<tr><td class="db-col-name">{_esc(col["name"])}</td>'
                    f'<td class="db-col-type">{_esc(col["type"])}</td>'
                    f'<td class="db-col-constraints">{_esc(col["constraints"])}</td></tr>\n'
                )
            rows += '</table>\n</div>\n'

        return (
            '<fieldset>\n<legend>Data Model</legend>\n'
            f'{rows}'
            '</fieldset>'
        )

    def config_js_read(self) -> str:
        return ""

    def config_js_populate(self) -> str:
        return ""

    def config_js_update_disabled(self) -> str:
        return ""

    def default_config(self) -> dict:
        return {}

    def manifest_to_config(self, manifest: dict) -> dict:
        return {}

    def deployed_keys(self, manifest: dict) -> set[str]:
        return set()


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _read_schema(local_path: str | None) -> list[dict]:
    """Read SQL schema from the project directory.

    Looks for:
    1. Drizzle schema.ts files
    2. SQL migration files
    """
    if not local_path:
        return []

    base = Path(local_path)
    tables: list[dict] = []

    # Try SQL migration files first (most reliable)
    for pattern in [
        "backend/src/db/migrations/*.sql",
        "backend/drizzle/*.sql",
        "src/db/migrations/*.sql",
        "migrations/*.sql",
    ]:
        for sql_file in sorted(base.glob(pattern)):
            tables.extend(_parse_sql(sql_file.read_text()))
        if tables:
            return _dedupe_tables(tables)

    # Try Drizzle schema.ts
    for pattern in [
        "backend/src/db/schema.ts",
        "src/db/schema.ts",
    ]:
        for schema_file in base.glob(pattern):
            tables.extend(_parse_drizzle_schema(schema_file.read_text()))
        if tables:
            return tables

    return []


def _parse_sql(sql: str) -> list[dict]:
    """Parse CREATE TABLE statements from SQL."""
    tables = []
    for match in re.finditer(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["\']?(\w+)["\']?\s*\((.*?)\);',
        sql,
        re.DOTALL | re.IGNORECASE,
    ):
        name = match.group(1)
        body = match.group(2)
        columns = _parse_columns(body)
        if columns:
            tables.append({"name": name, "columns": columns})
    return tables


def _parse_columns(body: str) -> list[dict]:
    """Parse column definitions from a CREATE TABLE body."""
    columns = []
    for line in body.split("\n"):
        line = line.strip().rstrip(",")
        if not line or line.upper().startswith(("PRIMARY KEY", "UNIQUE", "CONSTRAINT", "FOREIGN KEY", "CHECK")):
            continue
        # Match: column_name TYPE [constraints...]
        m = re.match(r'^["\']?(\w+)["\']?\s+(\w+(?:\([^)]*\))?)\s*(.*)', line)
        if m:
            constraints = m.group(3).strip().rstrip(",")
            columns.append({
                "name": m.group(1),
                "type": m.group(2).upper(),
                "constraints": constraints,
            })
    return columns


def _parse_drizzle_schema(ts: str) -> list[dict]:
    """Parse Drizzle ORM schema.ts for table definitions."""
    tables = []
    for match in re.finditer(
        r'export\s+const\s+(\w+)\s*=\s*pg(?:Table|Enum)\s*\(\s*["\'](\w+)["\']',
        ts,
    ):
        var_name = match.group(1)
        table_name = match.group(2)
        # Find the column definitions in the object literal after the table name
        start = match.end()
        brace = ts.find("{", start)
        if brace == -1:
            continue
        depth = 1
        pos = brace + 1
        while pos < len(ts) and depth > 0:
            if ts[pos] == "{":
                depth += 1
            elif ts[pos] == "}":
                depth -= 1
            pos += 1
        cols_body = ts[brace + 1 : pos - 1]

        columns = []
        for col_match in re.finditer(r'(\w+)\s*:\s*(\w+)\s*\(', cols_body):
            col_name = col_match.group(1)
            col_type = col_match.group(2)
            # Extract chained methods like .notNull(), .default(), .primaryKey()
            chain_start = col_match.end()
            chain_end = cols_body.find("\n", chain_start)
            if chain_end == -1:
                chain_end = len(cols_body)
            chain = cols_body[chain_start:chain_end]
            constraints = []
            if ".primaryKey()" in chain:
                constraints.append("PRIMARY KEY")
            if ".notNull()" in chain:
                constraints.append("NOT NULL")
            if ".unique()" in chain:
                constraints.append("UNIQUE")
            if ".default(" in chain:
                dm = re.search(r'\.default\(([^)]+)\)', chain)
                if dm:
                    constraints.append(f"DEFAULT {dm.group(1)}")
            if ".references(" in chain:
                constraints.append("REFERENCES ...")

            columns.append({
                "name": col_name,
                "type": col_type,
                "constraints": " ".join(constraints),
            })

        if columns:
            tables.append({"name": table_name, "columns": columns})

    return tables


def _dedupe_tables(tables: list[dict]) -> list[dict]:
    """Keep only the latest definition for each table name."""
    seen: dict[str, dict] = {}
    for t in tables:
        seen[t["name"]] = t
    return list(seen.values())
