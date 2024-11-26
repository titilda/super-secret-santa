import psycopg
import psycopg_pool

from .config import config

# Monkey patch the advisory lock method into the async cursor
psycopg.AsyncCursor.advisory_lock = lambda self, id: self.execute("SELECT pg_advisory_xact_lock(%s);", (id,))

async_cursor_execute = psycopg.AsyncCursor.execute


# multiple commands with placeholders
# scientists were so preoccupied with whether or not they could, they didn't stop to think if they should
# async def execute(self, *args, **kwargs):
#     statements = args[0].split(";")
#     placeholders = args[1:]

#     placeholder_offset = 0

#     for statement in statements:
#         placeholder_count = statement.count("%s")
#         await async_cursor_execute(
#             self, statement, *(placeholders[placeholder_offset : (placeholder_count + placeholder_offset)]), **kwargs
#         )
#         placeholder_offset += placeholder_count


# psycopg.AsyncCursor.execute = execute  # this is a crime against humanity

conninfo = psycopg.conninfo.make_conninfo(
    conninfo="",
    host=config.get("Postgres", "host"),
    port=config.get("Postgres", "port"),
    user=config.get("Postgres", "user"),
    password=config.get("Postgres", "password"),
    dbname=config.get("Postgres", "database"),
)

connection_pool = psycopg_pool.AsyncConnectionPool(conninfo, open=False)

get_connection = connection_pool.connection
