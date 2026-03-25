from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from datetime import date
from typing import Optional

from app.database import get_db, engine, Base
from app import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SURA API", version="1.0.0")


# --- Schemas Pydantic ---

class PolizaCreate(BaseModel):
    numero_poliza: str
    tipo: str
    titular: str
    prima_mensual: float
    fecha_inicio: date
    fecha_vencimiento: date
    estado: Optional[str] = "vigente"


class PolizaResponse(BaseModel):
    id: int
    numero_poliza: str
    tipo: str
    titular: str
    prima_mensual: float
    fecha_inicio: date
    fecha_vencimiento: date
    estado: str

    class Config:
        from_attributes = True


# --- Endpoints ---

@app.get("/")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "mensaje": "API SURA funcionando", "db": "conectada"}


@app.post("/api/v1/polizas", response_model=PolizaResponse, status_code=201)
def crear_poliza(poliza: PolizaCreate, db: Session = Depends(get_db)):
    db_poliza = models.Poliza(**poliza.model_dump())
    db.add(db_poliza)
    db.commit()
    db.refresh(db_poliza)
    return db_poliza


@app.get("/api/v1/polizas", response_model=list[PolizaResponse])
def listar_polizas(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(models.Poliza).offset(skip).limit(limit).all()


@app.get("/api/v1/polizas/{poliza_id}", response_model=PolizaResponse)
def obtener_poliza(poliza_id: int, db: Session = Depends(get_db)):
    poliza = db.query(models.Poliza).filter(models.Poliza.id == poliza_id).first()
    if not poliza:
        raise HTTPException(status_code=404, detail="Póliza no encontrada")
    return poliza