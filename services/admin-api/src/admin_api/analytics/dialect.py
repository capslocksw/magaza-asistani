"""SQL dialects for the analytics_events table. Dashboards are written once against this small API and run on
DuckDB locally (fixture) and BigQuery in production."""

from __future__ import annotations


class Dialect:
    name = "base"

    def __init__(self, table: str) -> None:
        self.table = table

    # parameters / literals
    def p(self, name: str) -> str:
        raise NotImplementedError

    # payload accessors
    def s(self, field: str) -> str:
        raise NotImplementedError

    def n(self, field: str) -> str:
        raise NotImplementedError

    def b(self, field: str) -> str:
        raise NotImplementedError

    def arr(self, field: str) -> str:
        raise NotImplementedError

    def item_skus(self) -> str:
        raise NotImplementedError

    def arr_len(self, expr: str) -> str:
        raise NotImplementedError

    def unnest(self, expr: str, alias: str) -> str:
        raise NotImplementedError

    # aggregates
    def count_if(self, cond: str) -> str:
        raise NotImplementedError

    def sum_if(self, expr: str, cond: str) -> str:
        raise NotImplementedError

    def avg_if(self, expr: str, cond: str) -> str:
        raise NotImplementedError

    def p95_if(self, expr: str, cond: str) -> str:
        raise NotImplementedError

    def count_distinct_if(self, expr: str, cond: str) -> str:
        raise NotImplementedError

    # time
    def week(self, col: str = "ts") -> str:
        raise NotImplementedError

    def month(self, col: str = "ts") -> str:
        raise NotImplementedError

    def in_list(self, col: str, param: str) -> str:
        raise NotImplementedError


class DuckDbDialect(Dialect):
    name = "duckdb"

    def p(self, name: str) -> str:
        return f"${name}"

    def s(self, field: str) -> str:
        return f"json_extract_string(payload, '$.{field}')"

    def n(self, field: str) -> str:
        return f"TRY_CAST(json_extract(payload, '$.{field}') AS DOUBLE)"

    def b(self, field: str) -> str:
        return f"coalesce(TRY_CAST(json_extract(payload, '$.{field}') AS BOOLEAN), false)"

    def arr(self, field: str) -> str:
        return f"coalesce(TRY_CAST(json_extract(payload, '$.{field}') AS VARCHAR[]), [])"

    def item_skus(self) -> str:
        return "coalesce(json_extract_string(payload, '$.items[*].sku'), [])"

    def arr_len(self, expr: str) -> str:
        return f"len({expr})"

    def unnest(self, expr: str, alias: str) -> str:
        return f"CROSS JOIN unnest({expr}) AS u({alias})"

    def count_if(self, cond: str) -> str:
        return f"count(*) FILTER (WHERE {cond})"

    def sum_if(self, expr: str, cond: str) -> str:
        return f"coalesce(sum({expr}) FILTER (WHERE {cond}), 0)"

    def avg_if(self, expr: str, cond: str) -> str:
        return f"avg({expr}) FILTER (WHERE {cond})"

    def p95_if(self, expr: str, cond: str) -> str:
        return f"quantile_cont({expr}, 0.95) FILTER (WHERE {cond})"

    def count_distinct_if(self, expr: str, cond: str) -> str:
        return f"count(DISTINCT {expr}) FILTER (WHERE {cond})"

    def week(self, col: str = "ts") -> str:
        return f"strftime(date_trunc('week', {col}), '%Y-%m-%d')"

    def month(self, col: str = "ts") -> str:
        return f"strftime({col}, '%Y-%m')"

    def in_list(self, col: str, param: str) -> str:
        return f"list_contains({self.p(param)}, {col})"


class BigQueryDialect(Dialect):
    name = "bigquery"

    def p(self, name: str) -> str:
        return f"@{name}"

    def s(self, field: str) -> str:
        return f"JSON_VALUE(payload, '$.{field}')"

    def n(self, field: str) -> str:
        return f"SAFE_CAST(JSON_VALUE(payload, '$.{field}') AS FLOAT64)"

    def b(self, field: str) -> str:
        return f"IFNULL(SAFE_CAST(JSON_VALUE(payload, '$.{field}') AS BOOL), FALSE)"

    def arr(self, field: str) -> str:
        return f"IFNULL(JSON_VALUE_ARRAY(payload, '$.{field}'), [])"

    def item_skus(self) -> str:
        return "ARRAY(SELECT JSON_VALUE(i, '$.sku') FROM UNNEST(JSON_QUERY_ARRAY(payload, '$.items')) AS i)"

    def arr_len(self, expr: str) -> str:
        return f"ARRAY_LENGTH({expr})"

    def unnest(self, expr: str, alias: str) -> str:
        return f"CROSS JOIN UNNEST({expr}) AS {alias}"

    def count_if(self, cond: str) -> str:
        return f"COUNTIF({cond})"

    def sum_if(self, expr: str, cond: str) -> str:
        return f"IFNULL(SUM(IF({cond}, {expr}, NULL)), 0)"

    def avg_if(self, expr: str, cond: str) -> str:
        return f"AVG(IF({cond}, {expr}, NULL))"

    def p95_if(self, expr: str, cond: str) -> str:
        return f"APPROX_QUANTILES(IF({cond}, {expr}, NULL), 100)[OFFSET(95)]"

    def count_distinct_if(self, expr: str, cond: str) -> str:
        return f"COUNT(DISTINCT IF({cond}, {expr}, NULL))"

    def week(self, col: str = "ts") -> str:
        return f"FORMAT_TIMESTAMP('%Y-%m-%d', TIMESTAMP_TRUNC({col}, WEEK(MONDAY)))"

    def month(self, col: str = "ts") -> str:
        return f"FORMAT_TIMESTAMP('%Y-%m', {col})"

    def in_list(self, col: str, param: str) -> str:
        return f"{col} IN UNNEST({self.p(param)})"
