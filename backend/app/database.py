from sqlalchemy import create_engine, Column, String, Integer, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.sql import func
from contextlib import contextmanager
from typing import Optional
from datetime import datetime
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ── Models ─────────────────────────────────────────────────────

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String(36), primary_key=True, index=True)
    url = Column(Text, nullable=False, index=True)
    height = Column(Integer, nullable=True)
    audio_only = Column(Boolean, default=False)
    filename = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="queued", index=True)
    progress = Column(Float, nullable=True, default=0.0)
    message = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)
    proxy_used = Column(String(255), nullable=True)
    user_agent = Column(String(255), nullable=True)
    client_ip = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    retries = Column(Integer, default=0)
    metadata_json = Column(JSON, nullable=True)
    deleted = Column(Boolean, default=False, index=True)

class BatchJob(Base):
    __tablename__ = "batch_jobs"
    
    id = Column(String(36), primary_key=True, index=True)
    urls = Column(JSON, nullable=False)
    height = Column(Integer, nullable=True)
    audio_only = Column(Boolean, default=False)
    status = Column(String(20), default="queued", index=True)
    completed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    total_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

class DownloadHistory(Base):
    __tablename__ = "download_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, nullable=False)
    title = Column(String(500), nullable=True)
    height = Column(Integer, nullable=True)
    audio_only = Column(Boolean, default=False)
    file_size = Column(Integer, nullable=True)
    thumbnail = Column(Text, nullable=True)
    duration = Column(Float, nullable=True)
    downloaded_at = Column(DateTime(timezone=True), server_default=func.now())
    client_ip = Column(String(45), nullable=True)

# ── Init ─────────────────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def db_session() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class JobRepository:
    """CRUD operations for jobs."""
    
    @staticmethod
    def create(db: Session, **kwargs) -> Job:
        job = Job(**kwargs)
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    
    @staticmethod
    def get(db: Session, job_id: str) -> Optional[Job]:
        return db.query(Job).filter(Job.id == job_id).first()
    
    @staticmethod
    def update(db: Session, job_id: str, **kwargs) -> Optional[Job]:
        job = JobRepository.get(db, job_id)
        if job:
            for k, v in kwargs.items():
                setattr(job, k, v)
            db.commit()
            db.refresh(job)
        return job
    
    @staticmethod
    def list_recent(db: Session, limit: int = 50):
        return db.query(Job).filter(Job.deleted == False).order_by(Job.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def count_by_status(db: Session, status: str) -> int:
        return db.query(Job).filter(Job.status == status, Job.deleted == False).count()
    
    @staticmethod
    def list_orphan_files(db: Session, cutoff: datetime):
        return db.query(Job).filter(
            Job.status.in_(["completed", "failed"]),
            Job.completed_at < cutoff,
            Job.deleted == False,
        ).all()

class DownloadHistoryRepository:
    
    @staticmethod
    def create(db: Session, **kwargs) -> DownloadHistory:
        entry = DownloadHistory(**kwargs)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    
    @staticmethod
    def list_recent(db: Session, limit: int = 100):
        return db.query(DownloadHistory).order_by(DownloadHistory.downloaded_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_stats(db: Session) -> dict:
        total = db.query(DownloadHistory).count()
        total_size = db.query(func.sum(DownloadHistory.file_size)).scalar() or 0
        return {"total_downloads": total, "total_bytes": total_size}
