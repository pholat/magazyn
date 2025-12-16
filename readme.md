# Migrations done with alembic
    
alembic revision --autogenerate -m "Add price column"
      
alembic upgrade head

# Setup  

1. create venv
2. install requirements.txt

# Run with uvicorn

uvicorn main:app --reload
