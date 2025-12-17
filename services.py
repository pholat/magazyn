import shutil
import uuid
import os
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy import or_, and_, distinct 
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

    def get_unique_locations(self):
        """Fetches a list of all distinct locations currently in the DB."""
        with self.db.session() as session:
            # Get distinct locations, excluding None/Empty
            locations = session.query(distinct(Item.location))\
                               .filter(Item.location != None, Item.location != "")\
                               .order_by(Item.location).all()
            # Unpack list of tuples [('LocA',), ('LocB',)] -> ['LocA', 'LocB']
            return [loc[0] for loc in locations]

    def get_all_items(self, search_query: str = None, location_filter: str = None):
        with self.db.session() as session:
            query = session.query(Item)
            
            # 1. Apply Exact Location Filter (from the dropdown)
            if location_filter:
                query = query.filter(Item.location == location_filter)

            # 2. Apply Advanced Text Search (&& and ||)
            if search_query:
                # Logic: Split by OR (||), then inside those, split by AND (&&)
                # Example: "chair && wood || table"
                # Means: (Item matches chair AND wood) OR (Item matches table)
                
                or_groups = search_query.split('||')
                or_filters = []

                for group in or_groups:
                    and_parts = group.split('&&')
                    and_filters = []
                    
                    for part in and_parts:
                        term = part.strip()
                        if term:
                            fmt = f"%{term}%"
                            # Match Name OR Location OR Note for this specific term
                            part_filter = or_(
                                Item.name.ilike(fmt), 
                                Item.location.ilike(fmt),
                                Item.note.ilike(fmt)
                            )
                            and_filters.append(part_filter)
                    
                    if and_filters:
                        # Combine terms with AND
                        or_filters.append(and_(*and_filters))
                
                if or_filters:
                    # Combine groups with OR
                    query = query.filter(or_(*or_filters))
            
            return query.all()

    def delete_item(self, uid: str):
        with self.db.session() as session:
            item = session.query(Item).filter(Item.uid == uid).first()
            if item:
                session.delete(item)
                session.commit()
                return True
            return False

    def update_date(self, uid: str, new_date: str):
        # new_date will come in as an ISO string (e.g. 2023-12-01T10:00)
        from datetime import datetime
        try:
            # Parse HTML5 datetime-local format
            dt_object = datetime.fromisoformat(new_date)
        except ValueError:
            return False

        with self.db.session() as session:
            item = session.query(Item).filter(Item.uid == uid).first()
            if item:
                item.date = dt_object
                session.commit()
                return True
            return False
