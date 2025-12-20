import os
import qrcode
from io import BytesIO
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, Request, Form, Response, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from pydantic import BaseModel
from PIL import Image

# Dependency Injection Imports
from di import container
from services import AuthService, ItemService
from database import Database
from typing import List

# --- APP SETUP ---
app = FastAPI()

# Mount static files (ensure directories exist via services.py logic)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- CONFIGURATION ---
SECRET_KEY = "lagom-secret-key-change-this-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# --- PYDANTIC MODELS (For JSON Updates) ---
class LocationUpdate(BaseModel):
    location: str

class NoteUpdate(BaseModel):
    note: str

class DateUpdate(BaseModel):
    date: str

class TagsUpdate(BaseModel):
    tags: List[str]

# --- STARTUP EVENT ---
@app.on_event("startup")
def startup():
    # 1. Initialize Database Tables
    db = container.resolve(Database)
    db.init_tables()
    
    # 2. Create Default Admin User (if not exists)
    auth = container.resolve(AuthService)
    auth.create_user("admin", "admin")
    print("✅ Startup complete. Admin user checked.")

# --- DEPENDENCY HELPERS ---
def get_auth_service():
    return container.resolve(AuthService)

def get_item_service():
    return container.resolve(ItemService)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user_cookie(request: Request, service: AuthService = Depends(get_auth_service)):
    token = request.cookies.get("access_token")
    if not token: return None
    try:
        # Token format: "Bearer <token>"
        scheme, _, param = token.partition(" ")
        payload = jwt.decode(param, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        return service.get_user(username)
    except JWTError:
        return None

# ==================================================================
# ROUTES: AUTHENTICATION
# ==================================================================

@app.get("/", response_class=HTMLResponse)
def root(user = Depends(get_current_user_cookie)):
    if not user: 
        return RedirectResponse("/login", status_code=302)
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service)
):
    user = auth_service.authenticate(username, password)
    if not user:
        return RedirectResponse("/login?msg=Fail", status_code=302)
    
    token = create_access_token({"sub": user.username})
    response = RedirectResponse("/dashboard", status_code=302)
    
    # Secure Cookie Settings
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {token}", 
        httponly=True,
        #secure=True, # Required for HTTPS (Nginx)
        #samesite="Lax",
        max_age=60*60*24*7, # 7 Days
    )
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("access_token")
    return response

# ==================================================================
# ROUTES: DASHBOARD & ITEMS
# ==================================================================

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    q: Optional[str] = None,
    loc: Optional[str] = None,
    user = Depends(get_current_user_cookie),
    item_service: ItemService = Depends(get_item_service)
):
    if not user: return RedirectResponse("/login", status_code=302)
    
    # 1. Get filtered items
    items = item_service.get_all_items(search_query=q, location_filter=loc)
    
    # 2. Get Metadata for Dropdowns (Locations & Tags)
    locations = item_service.get_unique_locations()
    tags = item_service.get_unique_tags()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "username": user.username, 
        "items": items,
        "search_query": q,
        "selected_location": loc,
        "locations": locations,
        "unique_tags": tags # Fixed: Passed to prevent JS error
    })

@app.post("/items")
def create_item(
    name: str = Form(...),
    location: Optional[str] = Form(None),
    tags: List[str] = Form([]), # <--- Ensure this is List[str]
    photo: Optional[UploadFile] = File(None),
    user = Depends(get_current_user_cookie),
    item_service: ItemService = Depends(get_item_service)
):
    if not user: return RedirectResponse("/login", status_code=302)
    
    # Create item (handles photo processing)
    item = item_service.create_item(name, location, photo)
    
    # Update tags if provided
    if tags:
        item_service.update_tags(item.uid, tags)
        
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/items/{uid}", response_class=HTMLResponse)
def get_item(
    request: Request, 
    uid: str, 
    user = Depends(get_current_user_cookie),
    item_service: ItemService = Depends(get_item_service)
):
    if not user: return RedirectResponse("/login", status_code=302)
    
    item = item_service.get_item_by_uid(uid)
    if not item:
        return HTMLResponse("Item not found", status_code=404)
    
    # Metadata for edit dropdowns
    locations = item_service.get_unique_locations()
    tags = item_service.get_unique_tags()

    return templates.TemplateResponse("item.html", {
        "request": request, 
        "item": item,
        "locations": locations,
        "unique_tags": tags # Fixed: Passed to prevent JS error
    })

@app.delete("/items/{uid}")
def delete_item_route(
    uid: str,
    user = Depends(get_current_user_cookie),
    item_service: ItemService = Depends(get_item_service)
):
    if not user: return Response(status_code=401)
    if item_service.delete_item(uid):
        return {"msg": "Deleted"}
    return Response(status_code=404)

# ==================================================================
# ROUTES: UPDATES (API - JSON)
# ==================================================================

@app.patch("/items/{uid}/location")
def update_location(uid: str, data: LocationUpdate, item_service: ItemService = Depends(get_item_service), user = Depends(get_current_user_cookie)):
    if not user: return Response(status_code=401)
    if item_service.update_location(uid, data.location): return {"msg": "Updated"}
    return Response(status_code=404)

@app.patch("/items/{uid}/note")
def update_note(uid: str, data: NoteUpdate, item_service: ItemService = Depends(get_item_service), user = Depends(get_current_user_cookie)):
    if not user: return Response(status_code=401)
    if item_service.update_note(uid, data.note): return {"msg": "Updated"}
    return Response(status_code=404)

@app.patch("/items/{uid}/date")
def update_date(uid: str, data: DateUpdate, item_service: ItemService = Depends(get_item_service), user = Depends(get_current_user_cookie)):
    if not user: return Response(status_code=401)
    if item_service.update_date(uid, data.date): return {"msg": "Updated"}
    return Response(status_code=400)

@app.patch("/items/{uid}/tags")
def update_tags(uid: str, data: TagsUpdate, item_service: ItemService = Depends(get_item_service), user = Depends(get_current_user_cookie)):
    if not user: return Response(status_code=401)
    if item_service.update_tags(uid, data.tags): return {"msg": "Updated"}
    return Response(status_code=400)

@app.post("/items/{uid}/photo")
def update_photo(uid: str, photo: UploadFile = File(...), item_service: ItemService = Depends(get_item_service), user = Depends(get_current_user_cookie)):
    if not user: return Response(status_code=401)
    if item_service.update_photo(uid, photo): return {"msg": "Updated"}
    return Response(status_code=400)

# ==================================================================
# ROUTES: IMAGES & QR
# ==================================================================

@app.get("/items/{uid}/thumbnail")
def get_thumbnail(uid: str, item_service: ItemService = Depends(get_item_service)):
    item = item_service.get_item_by_uid(uid)
    if not item or not item.photo:
        return Response(status_code=404)
    
    # 1. Try serving pre-generated thumbnail from disk (Fastest)
    thumb_path = f"static/thumbs/{item.photo}"
    if os.path.exists(thumb_path):
        return FileResponse(thumb_path)
    
    # 2. Fallback: If thumb missing but full image exists, generate on fly (Slower)
    full_path = f"static/uploads/{item.photo}"
    if os.path.exists(full_path):
        try:
            with Image.open(full_path) as img:
                img.thumbnail((200, 200))
                buf = BytesIO()
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img.save(buf, format="JPEG", quality=70)
                buf.seek(0)
                return StreamingResponse(buf, media_type="image/jpeg")
        except Exception:
            pass
            
    return Response(status_code=404)

@app.get("/items/{uid}/qr")
def generate_qr(uid: str, request: Request):
    item_url = str(request.url_for('get_item', uid=uid))
    
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(item_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

@app.get("/items/{uid}/label", response_class=HTMLResponse)
def print_label(uid: str, request: Request, user = Depends(get_current_user_cookie), item_service: ItemService = Depends(get_item_service)):
    if not user: return RedirectResponse("/login", status_code=302)
    item = item_service.get_item_by_uid(uid)
    return templates.TemplateResponse("label.html", {"request": request, "item": item})
