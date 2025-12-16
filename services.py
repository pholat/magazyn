import shutil
import uuid
import os
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy import or_
from passlib.context import CryptContext

from models import User, Item
from database import Database

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Ensure static directory exists
Path("static").mkdir(parents=True, exist_ok=True)

class AuthService:
    def __init__(self, db: Database):
        self.db = db

    def verify_password(self, plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password):
        return pwd_context.hash(password)

    def get_user(self, username: str):
        with self.db.session() as session:
            return session.query(User).filter(User.username == username).first()

    def create_user(self, username, password):
        with self.db.session() as session:
            if session.query(User).filter(User.username == username).first():
                return False
            user = User(username=username, hashed_password=self.get_password_hash(password))
            session.add(user)
            session.commit()
            return True

    def authenticate(self, username, password):
        user = self.get_user(username)
        if not user or not self.verify_password(password, user.hashed_password):
            return None
        return user

class ItemService:
    def __init__(self, db: Database):
        self.db = db

    def create_item(self, name: str, location: str, photo: UploadFile):
        photo_filename = None
        
        # Save file to disk if provided
        if photo and photo.filename:
            # Generate unique filename
            photo_filename = f"{uuid.uuid4()}_{photo.filename}"
            file_location = f"static/{photo_filename}"
            
            with open(file_location, "wb+") as file_object:
                shutil.copyfileobj(photo.file, file_object)

        # Save to DB
        with self.db.session() as session:
            new_item = Item(name=name, location=location, photo=photo_filename)
            session.add(new_item)
            session.commit()
            session.refresh(new_item)
            return new_item

    def get_item_by_uid(self, uid: str):
        with self.db.session() as session:
            return session.query(Item).filter(Item.uid == uid).first()

    def get_all_items(self, search_query: str = None):
        with self.db.session() as session:
            query = session.query(Item)
            
            if search_query:
                # Filter: Name contains query OR Location contains query (case insensitive)
                fmt = f"%{search_query}%"
                query = query.filter(
                    or_(Item.name.ilike(fmt), Item.location.ilike(fmt))
                )
            
            return query.all()

    def update_location(self, uid: str, new_location: str):
        with self.db.session() as session:
            item = session.query(Item).filter(Item.uid == uid).first()
            if item:
                item.location = new_location
                session.commit()
                return True
            return False

    def update_note(self, uid: str, new_note: str):
        with self.db.session() as session:
            item = session.query(Item).filter(Item.uid == uid).first()
            if item:
                item.note = new_note
                session.commit()
                return True
            return False
