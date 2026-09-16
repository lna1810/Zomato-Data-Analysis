from pathlib import Path

import duckdb
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
QUERIES_FILE = Path(__file__).parent / "queries.sql"


def _load_queries() -> dict[str, str]:
    """Parse queries.sql into {name: sql} using `-- name: <name>` markers."""
    queries: dict[str, str] = {}
    name = None
    buf: list[str] = []
    for line in QUERIES_FILE.read_text().splitlines():
        if line.strip().startswith("-- name:"):
            if name:
                queries[name] = "\n".join(buf).strip()
            name = line.split("-- name:", 1)[1].strip()
            buf = []
        elif name is not None:
            buf.append(line)
    if name:
        queries[name] = "\n".join(buf).strip()
    return queries


_QUERIES = _load_queries()


def get_connection() -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB connection with the Zomato tables loaded.

    Callers should hold onto the returned connection and reuse it across
    multiple run_query() calls rather than reopening it each time — the
    CSV load is the expensive part, not the queries.
    """
    con = duckdb.connect(database=":memory:")

    restaurants = pd.read_csv(DATA_DIR / "zomato.csv", encoding="latin-1")
    con.register("restaurants", restaurants)

    country_codes = pd.read_excel(DATA_DIR / "Country-Code.xlsx")
    con.register("country_codes", country_codes)

    return con


def run_query(
    name: str,
    con: duckdb.DuckDBPyConnection | None = None,
    **params,
) -> pd.DataFrame:
    """Run a named query from queries.sql and return the result as a DataFrame."""
    owns_connection = con is None
    con = con or get_connection()
    sql = _QUERIES[name]
    try:
        if params:
            return con.execute(sql, params).df()
        return con.execute(sql).df()
    finally:
        if owns_connection:
            con.close()

def list_query_names() -> list[str]:
    return list(_QUERIES.keys())
