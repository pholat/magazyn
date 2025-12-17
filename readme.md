# Migrations done with alembic
    
alembic revision --autogenerate -m "Add price column"
      
alembic upgrade head

# Setup  

1. create venv
2. install requirements.txt

# Run with uvicorn

uvicorn main:app --reload

or, on server

nohup uvicorn main:app --host 0.0.0.0 --port 8888 --proxy-headers --forwarded-allow-ips '*' &
