import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# the API tests point this at a throwaway file so they don't touch your test.db
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")


engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

NEW_COLUMNS = [
    ("users", "full_name", "VARCHAR"),
    ("trains", "stops", "VARCHAR DEFAULT ''"),
    ("trains", "duration_minutes", "INTEGER"),
]


def add_missing_columns():
    with engine.begin() as conn:
        for table, column, sql_type in NEW_COLUMNS:
            existing = {
                row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")
            }
            if existing and column not in existing:
                conn.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"
                )
