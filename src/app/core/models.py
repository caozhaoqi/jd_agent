from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class InterviewRecord(Base):
    """面试记录表"""
    __tablename__ = 'interview_records'

    id = Column(Integer, primary_key=True)
    company_name = Column(String(100))
    jd_content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Record {self.company_name}>"