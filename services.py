import os
import shutil
import uuid
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy import or_, and_, distinct
from passlib.context import CryptContext
from PIL import Image, ImageOps

from models import User, Item
from database import Database

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 1. Define Absolute Paths (Fixes "Where did my file go?" issues)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
THUMB_DIR = os.path.join(BASE_DIR, "static", "thumbs")

# Ensure directories exist
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(THUMB_DIR).mkdir(parents=True, exist_ok=True)

print(f"📂 Storage initialized at: {UPLOAD_DIR}")

class AuthService:
    def __init__(self, db: Database):
        self.db = db

    def verify_password(self, username: str, plain_password: str):
        user = self.get_user(username)
        if not user:
            return False
        return pwd_context.verify(plain_password, user.hashed_password)

    def update_password(self, username: str, new_password: str):
        with self.db.session() as session:
            user = session.query(User).filter(User.username == username).first()
            if user:
                user.hashed_password = self.get_password_hash(new_password)
                session.commit()
                return True
            return False

    def get_password_hash(self, password):
        return pwd_context.hash(password)

    def get_user(self, username: str):
        with self.db.session() as session:
            return session.query(User).filter(User.username == username).first()

    def create_user(self, username, password, role="user"):
        with self.db.session() as session:
            if session.query(User).filter(User.username == username).first():
                return False
            user = User(username=username, hashed_password=self.get_password_hash(password), role=role)
            session.add(user)
            session.commit()
            return True

    def get_all_users(self):
        with self.db.session() as session:
            return session.query(User).all()

    def delete_user(self, username: str):
        with self.db.session() as session:
            user = session.query(User).filter(User.username == username).first()
            if user:
                session.delete(user)
                session.commit()
                return True
            return False

    def update_user_role(self, username: str, new_role: str):
        with self.db.session() as session:
            user = session.query(User).filter(User.username == username).first()
            if user:
                user.role = new_role
                session.commit()
                return True
            return False

    def authenticate(self, username, password):
        user = self.get_user(username)
        if not user or not self.verify_password(username, password):
            return None
        return user

class ItemService:
    def __init__(self, db: Database):
        self.db = db

    def _process_image(self, photo: UploadFile):
        """Optimizes image to stay under ~2MB and creates a thumbnail."""
        try:
            print(f"📸 Processing image: {photo.filename}")
            
            # 1. Reset file pointer (Crucial fix!)
            photo.file.seek(0)
            
            ext = photo.filename.split(".")[-1].lower()
            if ext not in ["jpg", "jpeg", "png", "webp"]:
                ext = "jpg"
            
            base_name = f"{uuid.uuid4()}.{ext}"
            full_path = os.path.join(UPLOAD_DIR, base_name)
            thumb_path = os.path.join(THUMB_DIR, base_name)

            # 2. Open image with Pillow
            img = Image.open(photo.file)
            
            # 3. Fix orientation (Mobile photos often need this)
            img = ImageOps.exif_transpose(img)

            # 4. Convert to RGB if necessary (e.g. PNGs with transparency)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # 5. Downscale full image (Max 1920px)
            max_size = (1920, 1920)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # 6. Save Optimized Full Image
            img.save(full_path, optimize=True, quality=85)
            print(f"   ✅ Saved full image: {full_path}")

            # 7. Create Miniature (200x200 crop)
            thumb = ImageOps.fit(img, (200, 200), Image.Resampling.LANCZOS)
            thumb.save(thumb_path, optimize=True, quality=75)
            print(f"   ✅ Saved thumbnail: {thumb_path}")

            return base_name

        except Exception as e:
            print(f"❌ Image processing failed: {e}")
            return None

    def _delete_old_photos(self, filename: str):
        if not filename: return
        try:
            p1 = os.path.join(UPLOAD_DIR, filename)
            p2 = os.path.join(THUMB_DIR, filename)
            if os.path.exists(p1): os.remove(p1)
            if os.path.exists(p2): os.remove(p2)
            print(f"🗑️ Deleted old photo: {filename}")
        except Exception as e:
            print(f"⚠️ Failed to delete old photo: {e}")

    def create_item(self, name: str, location: str, photo: UploadFile):
        photo_filename = None
        
        # Only process if a file was actually uploaded (has a filename)
        if photo and photo.filename:
            photo_filename = self._process_image(photo)

        with self.db.session() as session:
            new_item = Item(name=name, location=location, photo=photo_filename)
            session.add(new_item)
            session.commit()
            session.refresh(new_item)
            return new_item

    def update_photo(self, uid: str, photo: UploadFile):
        # Process new image first
        new_filename = self._process_image(photo)
        if not new_filename:
            return False
        
        with self.db.session() as session:
            item = session.query(Item).filter(Item.uid == uid).first()
            if item:
                # Delete old files from disk
                self._delete_old_photos(item.photo)
                # Update DB
                item.photo = new_filename
                session.commit()
                return True
            return False

    def delete_item(self, uid: str):
        with self.db.session() as session:
            item = session.query(Item).filter(Item.uid == uid).first()
            if item:
                self._delete_old_photos(item.photo)
                session.delete(item)
                session.commit()
                return True
            return False

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

    def update_date(self, uid: str, new_date: str):
        from datetime import datetime
        try:
            dt_object = datetime.fromisoformat(new_date)
        except ValueError:
            return False

        with self.db.session() as session:
            item = session.query(Item).filter(Item.uid == uid).first()
            if item:

                session.commit()
                return True
            return False

    def get_item_by_uid(self, uid: str):
        with self.db.session() as session:
            return session.query(Item).filter(Item.uid == uid).first()

    def get_all_items(self, search_query: str = None, location_filter: str = None):
        # TODO this is probably unused as there is definition after it that's in use...
        # consider removing
        with self.db.session() as session:
            query = session.query(Item)

            if location_filter:
                query = query.filter(Item.location == location_filter)

            if search_query:
                # Supports "term1 && term2 || term3" logic
                or_groups = search_query.split('||')
                or_filters = []
                for group in or_groups:
                    and_parts = group.split('&&')
                    and_filters = []
                    for part in and_parts:
                        term = part.strip()
                        if term:
                            fmt = f"%{term}%"
                            and_filters.append(or_(
                                Item.name.ilike(fmt), 
                                Item.location.ilike(fmt),
                                Item.note.ilike(fmt)
                            ))
                    if and_filters:
                        or_filters.append(and_(*and_filters))
                if or_filters:
                    query = query.filter(or_(*or_filters))

            query = query.order_by(Item.date.desc())
            return query.all()

    def get_unique_locations(self):
        with self.db.session() as session:
            locations = session.query(distinct(Item.location))\
                               .filter(Item.location != None, Item.location != "")\
                               .order_by(Item.location).all()
            return [loc[0] for loc in locations]

    def update_tags(self, uid: str, tags_list: list):
        # Convert list ["a", "b"] -> string "a,b"
        tags_str = ",".join(tags_list) if tags_list else None

        with self.db.session() as session:
            item = session.query(Item).filter(Item.uid == uid).first()
            if item:
                item.tags = tags_str
                session.commit()
                return True
            return False

    def get_unique_tags(self):
        """Returns a flat list of all unique tags used in the system."""
        with self.db.session() as session:
            # Get all non-empty tag strings
            results = session.query(Item.tags).filter(Item.tags != None, Item.tags != "").all()
            
            unique_set = set()
            for r in results:
                # r[0] is "tag1,tag2". Split and add.
                for t in r[0].split(','):
                    if t.strip():
                        unique_set.add(t.strip())
            
            return sorted(list(unique_set))

    def get_all_items(self, search_query: str = None, location_filter: str = None):
        with self.db.session() as session:
            query = session.query(Item)

            if location_filter:
                query = query.filter(Item.location == location_filter)

            if search_query:
                or_groups = search_query.split('||')
                or_filters = []
                for group in or_groups:
                    and_parts = group.split('&&')
                    and_filters = []
                    for part in and_parts:
                        term = part.strip()
                        if term:
                            fmt = f"%{term}%"
                            # UPDATED: Added Item.tags to the search filter
                            and_filters.append(or_(
                                Item.name.ilike(fmt), 
                                Item.location.ilike(fmt),
                                Item.note.ilike(fmt),
                                Item.tags.ilike(fmt) 
                            ))
                    if and_filters:
                        or_filters.append(and_(*and_filters))
                if or_filters:
                    query = query.filter(or_(*or_filters))

            query = query.order_by(Item.date.desc())
            return query.all()
