from fastapi import FastAPI, Depends, Request, Form, Response, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel 
import os

# Import container directly
from di import container
from services import AuthService, ItemService
from database import Database

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SECRET_KEY = "lagom-secret-key"
ALGORITHM = "HS256"

# --- Models for JSON Updates ---
class LocationUpdate(BaseModel):
    location: str

class NoteUpdate(BaseModel):
    note: str

class DateUpdate(BaseModel):
    date: str


# --- Startup ---
@app.on_event("startup")
def startup():
    db = container.resolve(Database)
    db.init_tables()
    auth = container.resolve(AuthService)
    auth.create_user("admin", "admin")

# --- Helpers ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_auth_service():
    return container.resolve(AuthService)

def get_item_service():
    return container.resolve(ItemService)

def get_current_user_cookie(request: Request, service: AuthService = Depends(get_auth_service)):
    token = request.cookies.get("access_token")
    if not token: return None
    try:
        scheme, _, param = token.partition(" ")
        payload = jwt.decode(param, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        return service.get_user(username)
    except JWTError:
        return None

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
def root(user = Depends(get_current_user_cookie)):
    if not user: return RedirectResponse("/login", status_code=302)
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
    response.set_cookie("access_token", f"Bearer {token}", httponly=True)
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("access_token")
    return response

# --- ITEM ROUTES ---

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    q: Optional[str] = None,
    loc: Optional[str] = None,
    user = Depends(get_current_user_cookie),
    item_service: ItemService = Depends(get_item_service)
):
    if not user: return RedirectResponse("/login", status_code=302)
    
    items = item_service.get_all_items(search_query=q, location_filter=loc)
    # IMPORTANT: Fetch locations for the dropdown
    locations = item_service.get_unique_locations()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "username": user.username, 
        "items": items,
        "search_query": q,
        "selected_location": loc,
        "locations": locations # <--- Passed to template here
    })

@app.post("/items")
def create_item(
    name: str = Form(...),
    location: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    user = Depends(get_current_user_cookie),
    item_service: ItemService = Depends(get_item_service)
):
    if not user: return RedirectResponse("/login", status_code=302)
    item_service.create_item(name, location, photo)
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
    
    # IMPORTANT: Fetch locations for the dropdown in Item View too
    locations = item_service.get_unique_locations()

    return templates.TemplateResponse("item.html", {
        "request": request, 
        "item": item,
        "locations": locations # <--- Passed to template here
    })

# --- JSON API Endpoints for JS ---

@app.patch("/items/{uid}/location")
def update_item_location(
    uid: str, 
    update_data: LocationUpdate,
    user = Depends(get_current_user_cookie),
    item_service: ItemService = Depends(get_item_service)
):
    if not user: return Response(status_code=401)
    success = item_service.update_location(uid, update_data.location)
    if not success: return Response(status_code=404)
    return {"msg": "Updated"}

@app.patch("/items/{uid}/note")
def update_item_note(
    uid: str, 
    update_data: NoteUpdate,
    user = Depends(get_current_user_cookie),
    item_service: ItemService = Depends(get_item_service)
):
    if not user: return Response(status_code=401)
    success = item_service.update_note(uid, update_data.note)
    if not success: return Response(status_code=404)
    return {"msg": "Updated"}

@app.delete("/items/{uid}")
def delete_item(
    uid: str,
    user = Depends(get_current_user_cookie),
    item_service: ItemService = Depends(get_item_service)
):
    if not user: return Response(status_code=401)
    
    success = item_service.delete_item(uid)
    if not success: return Response(status_code=404)
    return {"msg": "Deleted"}

# --- NEW: DATE UPDATE ROUTE ---
@app.patch("/items/{uid}/date")
def update_item_date(
    uid: str, 
    update_data: DateUpdate,
    user = Depends(get_current_user_cookie),
    item_service: ItemService = Depends(get_item_service)
):
    if not user: return Response(status_code=401)
    
    success = item_service.update_date(uid, update_data.date)
    if not success: return Response(status_code=400)
    return {"msg": "Updated"}

@app.post("/items/{uid}/photo")
def update_item_photo(
    uid: str,
    photo: UploadFile = File(...),
    user = Depends(get_current_user_cookie),
    item_service: ItemService = Depends(get_item_service)
):
    if not user: return Response(status_code=401)

    success = item_service.update_photo(uid, photo)
    if not success: return Response(status_code=400)

    # Return a success message or redirect
    return {"msg": "Photo updated"}

@app.get("/items/{uid}/thumbnail")
def get_item_thumbnail(uid: str, item_service: ItemService = Depends(get_item_service)):
    item = item_service.get_item_by_uid(uid)
    if not item or not item.photo:
        return Response(status_code=404)

    thumb_path = f"static/thumbs/{item.photo}"

    if os.path.exists(thumb_path):
        from fastapi.responses import FileResponse
        return FileResponse(thumb_path)

    # Fallback: If thumb missing but full photo exists (old data), generate on fly
    full_path = f"static/uploads/{item.photo}" # Note: 'uploads' subfolder
    if os.path.exists(full_path):
        # ... logic to generate on fly ...
        pass

    return Response(status_code=404)
