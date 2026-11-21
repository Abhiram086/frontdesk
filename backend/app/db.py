import os
from contextlib import contextmanager
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    os.environ["DATABASE_URL"],
    min_size=1,
    max_size=5,
    kwargs={"row_factory": dict_row},
    open=True,
)


@contextmanager
def tx():
    """Run queries in a single transaction; commits on success, rolls back on error."""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            yield cur