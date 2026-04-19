import uuid
from sqlalchemy import Column, Integer, String, DateTime, func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Item(Base):
    __tablename__ = "items"

    # UID: Primary key, generated automatically
    uid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Name: Indexed for faster searching
    name = Column(String, index=True)
    
    # Date: Auto-set on creation, auto-updated on change
    date = Column(DateTime, default=func.now(), onupdate=func.now())
    
    location = Column(String, nullable=True)
    photo = Column(String, nullable=True)
    note = Column(String, nullable=True)
    tags = Column(String, nullable=True)

    def __repr__(self):
        return f'{self.uid} {self.name=} {self.date=} {self.location=}>'
