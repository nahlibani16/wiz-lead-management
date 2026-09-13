from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Menggunakan SQLite database bernama leads.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./leads.db"

# connect_args={"check_same_thread": False} khusus untuk SQLite di FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency untuk FastAPI (diambil saat ada request API)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()