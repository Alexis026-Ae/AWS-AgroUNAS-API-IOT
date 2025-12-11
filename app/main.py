# app/main.py
from datetime import datetime
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# 1. CONFIGURACIÓN
load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "iot_suelo")
DB_PORT = os.getenv("DB_PORT", "5432")

SQLALCHEMY_DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 2. MODELO BD
class SensorRegistro(Base):
    __tablename__ = "registros_sensores"
    id = Column(Integer, primary_key=True, index=True)
    nitrogeno = Column(Float, nullable=False)
    fosforo = Column(Float, nullable=False)
    potasio = Column(Float, nullable=False)
    temperatura = Column(Float, nullable=False)
    ph = Column(Float, nullable=False)
    humedad = Column(Float, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Error conectando a BD (esperable durante el build de docker): {e}")

# 3. ESQUEMAS PYDANTIC
class SensorCreate(BaseModel):
    nitrogeno: float
    fosforo: float
    potasio: float
    temperatura: float
    ph: float
    humedad: float

class SensorRead(SensorCreate):
    id: int
    creado_en: datetime

    class Config:
        from_attributes = True

# 4. LÓGICA DE NEGOCIO (para tabla de decisión)
def validar_sensor(datos: SensorCreate) -> list[str]:
    errores = []

    # C1: Nutrientes no negativos
    if datos.nitrogeno < 0 or datos.fosforo < 0 or datos.potasio < 0:
        errores.append("N, P y K deben ser >= 0")

    # C2: pH válido
    if not (0 <= datos.ph <= 14):
        errores.append("pH debe estar entre 0 y 14")

    # C3: Humedad válida
    if not (0 <= datos.humedad <= 100):
        errores.append("Humedad debe estar entre 0 y 100")

    return errores

# 5. FASTAPI
app = FastAPI(title="API Sensores IoT")

@app.get("/")
def root():
    return {"mensaje": "API funcionando correctamente en EKS 🚀"}

@app.post("/sensores", response_model=SensorRead)
def crear_registro(datos: SensorCreate, db: Session = Depends(get_db)):
    errores = validar_sensor(datos)
    if errores:
        raise HTTPException(status_code=422, detail=errores)

    registro = SensorRegistro(**datos.model_dump())
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro

@app.get("/sensores", response_model=list[SensorRead])
def listar_registros(db: Session = Depends(get_db)):
    return db.query(SensorRegistro).order_by(SensorRegistro.id.desc()).all()
