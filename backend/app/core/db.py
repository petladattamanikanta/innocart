import logging
from app.core.config import settings

logger = logging.getLogger("innocart.db")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2.pool import ThreadedConnectionPool
    HAS_POSTGRES = True
except ImportError:
    psycopg2 = None
    RealDictCursor = None
    ThreadedConnectionPool = None
    HAS_POSTGRES = False

try:
    import mysql.connector
    HAS_MYSQL = True
except ImportError:
    mysql = None
    HAS_MYSQL = False

try:
    import redis
except ImportError:
    redis = None

class DatabasePool:
    def __init__(self):
        self.host = settings.MYSQL_HOST
        self.port = settings.MYSQL_PORT
        self.user = settings.MYSQL_USER
        self.password = settings.MYSQL_PASSWORD
        self.database = settings.MYSQL_DB
        self.is_postgres = (
            str(self.port) == "5432" or 
            str(self.port) == "6543" or 
            "supabase" in str(self.host).lower() or 
            "postgres" in str(self.host).lower()
        )
        self._pg_pool = None
        if self.is_postgres and HAS_POSTGRES and ThreadedConnectionPool:
            try:
                self._pg_pool = ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    dbname=self.database,
                    sslmode="require",
                    connect_timeout=10
                )
                logger.info("✓ PostgreSQL ThreadedConnectionPool initialized (1-10 connections)")
            except Exception as e:
                logger.warning(f"PostgreSQL ThreadedConnectionPool init notice: {e}")

    def get_connection(self):
        if self.is_postgres:
            if not HAS_POSTGRES or psycopg2 is None:
                raise RuntimeError("psycopg2-binary package not installed for PostgreSQL connection")
            if self._pg_pool:
                try:
                    return self._pg_pool.getconn()
                except Exception as pool_err:
                    logger.warning(f"Connection pool fetch fallback: {pool_err}")
            return psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname=self.database,
                sslmode="require",
                connect_timeout=5
            )
        else:
            if not HAS_MYSQL or mysql is None:
                raise RuntimeError("mysql-connector-python not installed for MySQL connection")
            return mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=True
            )

    def release_connection(self, conn):
        if conn:
            if self.is_postgres and self._pg_pool:
                try:
                    self._pg_pool.putconn(conn)
                    return
                except Exception:
                    pass
            try:
                conn.close()
            except Exception:
                pass

    def _translate_sql_for_postgres(self, sql: str) -> str:
        if not self.is_postgres or "ON DUPLICATE KEY UPDATE" not in sql.upper():
            return sql

        import re
        translated = re.sub(r'VALUES\(([a-zA-Z0-9_]+)\)', r'EXCLUDED.\1', sql, flags=re.IGNORECASE)
        sql_upper = sql.upper()

        if "INTO CART_SESSIONS" in sql_upper:
            translated = re.sub(r'ON DUPLICATE KEY UPDATE', r'ON CONFLICT (session_id) DO UPDATE SET', translated, flags=re.IGNORECASE)
        elif "INTO CART_ITEMS" in sql_upper:
            translated = re.sub(r'ON DUPLICATE KEY UPDATE', r'ON CONFLICT (session_id, sku) DO UPDATE SET', translated, flags=re.IGNORECASE)
        elif "INTO PRODUCT_MASTER" in sql_upper:
            translated = re.sub(r'ON DUPLICATE KEY UPDATE', r'ON CONFLICT (sku) DO UPDATE SET', translated, flags=re.IGNORECASE)
        elif "INTO INVENTORY_LIVE" in sql_upper:
            translated = re.sub(r'ON DUPLICATE KEY UPDATE', r'ON CONFLICT (epc_id) DO UPDATE SET', translated, flags=re.IGNORECASE)
        elif "INTO USERS" in sql_upper:
            translated = re.sub(r'ON DUPLICATE KEY UPDATE', r'ON CONFLICT (user_id) DO UPDATE SET', translated, flags=re.IGNORECASE)
        else:
            translated = re.sub(r'ON DUPLICATE KEY UPDATE', r'DO UPDATE SET', translated, flags=re.IGNORECASE)

        translated = re.sub(r'\bis_active=1\b', 'is_active=TRUE', translated, flags=re.IGNORECASE)
        translated = re.sub(r'\bis_active=0\b', 'is_active=FALSE', translated, flags=re.IGNORECASE)
        return translated.rstrip().rstrip(';')

    def query(self, sql: str, params: tuple = ()) -> list:
        conn = None
        cursor = None
        exec_sql = self._translate_sql_for_postgres(sql)
        try:
            conn = self.get_connection()
            if self.is_postgres:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(exec_sql, params)
                rows = cursor.fetchall() if cursor.description else []
                return [dict(r) for r in rows] if rows else []
            else:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(exec_sql, params)
                if cursor.description:
                    return cursor.fetchall()
                return []
        except Exception as e:
            db_type = "PostgreSQL" if self.is_postgres else "MySQL"
            logger.error(f"DB query failed ({db_type}): {e} | SQL: {exec_sql}")
            return []
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            self.release_connection(conn)

    def execute(self, sql: str, params: tuple = ()) -> int:
        conn = None
        cursor = None
        exec_sql = self._translate_sql_for_postgres(sql)
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(exec_sql, params)
            affected = cursor.rowcount
            if self.is_postgres:
                conn.commit()
            return affected
        except Exception as e:
            db_type = "PostgreSQL" if self.is_postgres else "MySQL"
            logger.error(f"DB execute failed ({db_type}): {e} | SQL: {exec_sql}")
            return 0
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            self.release_connection(conn)

db = DatabasePool()

# Redis connection with fallback
redis_client = None
if redis and settings.REDIS_HOST and settings.REDIS_HOST not in ["127.0.0.1", "localhost", "none", "disabled"]:
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=0.5
        )
        redis_client.ping()
        logger.info("Connected to Cloud Redis successfully.")
    except Exception as e:
        logger.info(f"Cloud Redis connection notice ({e}). Using in-memory cache fallback.")
        redis_client = None
else:
    logger.info("Using high-speed in-memory session cache.")
