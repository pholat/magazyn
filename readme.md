# Magazyn - Simple Inventory Manager

Simple, minimalistic inventory management with hassle-free setup, featuring items filtering and UID QR code quick access.
I needed some better than excell tool to organise all my tools. As I couldn't find anything to my liking, simple and working I just made it.

Core concepts were:
* I need to be able to tell where my item is - hence location
* I need to be able to add notes to the item - hence note per item
* I need to be able to check how should the item look like - hence item photo
* I need to be able to open item page instantly - hence QR containing item UUID I'll print and have on the item.

With that I can do both:
* Check where is my chainsaw
* By opening QR code quickly check items note - i.e. when was the oil changed.

**Caution!** Be aware:
* This is pure human design, AI halucinated code.
    * Kept in line as long as it was sane.
    * Most of the features are manualy tested.
* if you ever ask AI about migrations, mention orm and alembic use. For some reason AI first answers were always: remove the db, then: do manual migration.
* There will be bugs creeping - I made it for my use, so I'll probably fix what I need in the long run.

## Features

*   **QR Code Integration**: 
    *   Generate printable QR labels for items.
    *   Built-in Camera Scanner to open item page instantly.
*   **Photo Management**: 
    *   Automatic image optimization (downscaling to <2MB).
    *   Thumbnail generation for fast dashboard loading.
    *   Mobile-friendly photo uploading.
    * NOTE: it may be nicer to have option to add multiple photos
*   **Smart Search & Organization**:
    *   Filter by Location.
    *   Logic search (e.g., `chair && wood || table`).
        * NOTE: it would be better with addition of `in` and `()` - may be added in the future.
    *   Tagging system with multi-select support.
*   **Inline Editing**: Click-to-edit for Notes, Locations, Dates, and Tags directly on the dashboard.
*   **Offline Ready**: All JS/CSS assets are hosted locally (no CDN dependencies).

### Future ideas I may embrace:

* tags vs hierachy or maybe both
* sql-like queries instead simple ones
* more users
* more compact mobile view - I dislike the pretty, wastefull mobile views.

### Few screenshots here

[images](./doc/images.md)

## Technology

*   **Backend**: Python, FastAPI, SQLAlchemy (SQLite), Pydantic.
*   **Frontend**: HTML, CSS, JavaScript (jQuery, Select2).
*   **Dependency Injection**: Custom DI container (Manual resolution pattern).
*   **Imaging**: Pillow (PIL) for processing and Qrcode for generation.

## Installation

### Prerequisites
*   Python 3.10+
*   pip

### 1. Setup Environment
```bash
# Clone repository
git clone <your-repo-url>
cd magazyn

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup the user

```bash
python seed.py
```

Note: There is only one user role now. And it's not that it's needed at the moment at all.

## Migrations are done with alembic

i.e.:

alembic revision --autogenerate -m "Add price column"
alembic upgrade head

## Run with uvicorn

Localhost:

```
uvicorn main:app --reload
```

or, on server:

```
nohup uvicorn main:app --host 0.0.0.0 --port 8888 --proxy-headers --forwarded-allow-ips '*' &
```

or create a docker instance or vm - not that I care :)

# Discamler

Use with caution - I take no resposnbility.
