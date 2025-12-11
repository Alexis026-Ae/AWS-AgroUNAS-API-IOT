# tests/test_api_sensores.py
import os

# Forzar BD SQLite durante CI/CD
os.environ["DB_HOST"] = "sqlite"
os.environ["DB_NAME"] = ":memory:"
os.environ["DB_USER"] = ""
os.environ["DB_PASSWORD"] = ""
os.environ["DB_PORT"] = ""

from fastapi.testclient import TestClient
from app.main import app, Base, engine

# Crear las tablas de prueba en SQLite
Base.metadata.create_all(bind=engine)

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
        "ph": 20,   # Inválido
        "humedad": 60
    }
    r = client.post("/sensores", json=payload)
    assert r.status_code == 422
