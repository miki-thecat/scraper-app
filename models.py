from sqlalchemy import create_engine, Column, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
from flask import Config
from sqlalchemy import DateTime

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Article(Base):
    __tablename__ = 'articles'
    id = Column(Integer, primary_key=True)
    url = Column(String(512), nullable=False)
    title = Column(String(512), nullable=False)
    published_at = Column(String(128), nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        UniqueConstraint('url', name='uq_articles_url'),
    )
    
def init_db():
    Base.metadata.create_all(bind=engine)
    
    