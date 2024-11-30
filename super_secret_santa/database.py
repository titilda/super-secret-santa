import psycopg
import psycopg_pool
from psycopg import AsyncCursor

from .config import config


async def create_santa_assignment(cur: AsyncCursor, guild_id: int, user_id: int, giftee_id: int):
    await cur.execute(
        """INSERT INTO Giftees (user_id, guild_id) VALUES (%s, %s);""",
        (giftee_id, guild_id),
    )
    await cur.execute(
        """UPDATE Memberships SET giftee = (select id from Giftees where user_id = %s) WHERE user_id = %s AND guild_id = %s;""",
        (giftee_id, user_id, guild_id),
    )


# Monkey patch the advisory lock method into the async cursor
psycopg.AsyncCursor.advisory_lock = lambda self, id: self.execute("SELECT pg_advisory_xact_lock(%s);", (id,))

# Connection string constructor for the database
conninfo = psycopg.conninfo.make_conninfo(
    conninfo="",
    host=config.get("Postgres", "host"),
    port=config.get("Postgres", "port"),
    user=config.get("Postgres", "user"),
    password=config.get("Postgres", "password"),
    dbname=config.get("Postgres", "database"),
)

# Must be created inside main event loop
connection_pool = psycopg_pool.AsyncConnectionPool(conninfo, open=False)

# Shorthand for getting a connection from our connection pool
get_connection = connection_pool.connection
