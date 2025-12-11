# tests/test_api_sensores.py
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db import Base, get_db

# Crear engine SQLite para tests
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crear tablas en SQLite
Base.metadata.create_all(bind=engine)

# Override de la BD real con la BD de test
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_post_sensores_ok():
    payload = {
        "nitrogeno": 10,
        "fosforo": 5,
        "potasio": 8,
        "temperatura": 25,
        "ph": 6.5,
        "humedad": 60
    }
    r = client.post("/sensores", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["ph"] == 6.5

def test_post_sensores_ph_invalido():
    payload = {
        "nitrogeno": 10,
        "fosforo": 5,
        "potasio": 8,
        "temperatura": 25,
        "ph": 20,
        "humedad": 60
    }
    r = client.post("/sensores", json=payload)
    assert r.status_code == 422
