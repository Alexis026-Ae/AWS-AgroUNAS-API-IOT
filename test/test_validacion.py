# tests/test_validacion.py
from app.main import validar_sensor, SensorCreate

def test_r1_todo_valido():
    datos = SensorCreate(
        nitrogeno=10, fosforo=5, potasio=8,
        temperatura=25, ph=6.5, humedad=60
    )
    assert validar_sensor(datos) == []

def test_r2_nutrientes_negativos():
    datos = SensorCreate(
        nitrogeno=-1, fosforo=5, potasio=8,
        temperatura=25, ph=6.5, humedad=60
    )
    errores = validar_sensor(datos)
    assert "N, P y K deben ser >= 0" in errores

def test_r3_ph_invalido():
    datos = SensorCreate(
        nitrogeno=10, fosforo=5, potasio=8,
        temperatura=25, ph=20, humedad=60
    )
    errores = validar_sensor(datos)
    assert "pH debe estar entre 0 y 14" in errores

def test_r4_humedad_invalida():
    datos = SensorCreate(
        nitrogeno=10, fosforo=5, potasio=8,
        temperatura=25, ph=6.5, humedad=120
    )
    errores = validar_sensor(datos)
    assert "Humedad debe estar entre 0 y 100" in errores
