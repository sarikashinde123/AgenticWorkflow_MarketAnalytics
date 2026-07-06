from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime
from config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class RunRecord(Base):
    __tablename__ = "pipeline_runs"

    run_id     = Column(String(64), primary_key=True)
    status     = Column(String(32), default="pending")
    input_data = Column(JSON)
    agents     = Column(JSON, default=list)
    report_html= Column(Text, nullable=True)
    pdf_url    = Column(String(500), nullable=True)
    error      = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
