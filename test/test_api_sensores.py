# test/test_api_sensores.py
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, Base, get_db

# --- CONFIG DB PARA TEST (SQLite en memoria) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"  # ARCHIVO, NO MEMORIA

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crear tablas UNA sola vez
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# --- Override de dependencia ---
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


client = TestClient(app)


# --- TESTS ---
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
    print(r.text)  # DEBUG si falla
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
