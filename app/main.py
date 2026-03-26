# =============================================================================
# SURA API — main.py
# API REST para gestión de pólizas de seguros
# Versión: 1.0.0 | Stack: FastAPI + SQLAlchemy + PostgreSQL (Cloud SQL)
# =============================================================================

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from datetime import date, datetime, timedelta
from typing import Optional

from app.database import get_db, engine, Base
from app import models

# Crea las tablas en la BD si no existen (respaldo de seguridad — Alembic es el método principal)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SURA API", version="1.0.0")


# =============================================================================
# SCHEMAS — Definen la estructura de datos de entrada y salida de cada endpoint
# Pydantic valida automáticamente tipos y campos requeridos antes de llegar a la BD
# TODO: mover a app/schemas.py en próxima versión
# =============================================================================

# --- Pólizas ---

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
        from_attributes = True  # Permite convertir objetos SQLAlchemy a JSON


class PolizaUpdate(BaseModel):
    # Todos los campos son opcionales — solo se actualizan los que se envían
    numero_poliza: Optional[str] = None
    tipo: Optional[str] = None
    titular: Optional[str] = None
    prima_mensual: Optional[float] = None
    fecha_inicio: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    estado: Optional[str] = None


# --- Siniestros ---

class SiniestroCreate(BaseModel):
    poliza_id: int
    descripcion: str
    fecha_siniestro: date
    estado: Optional[str] = "pendiente"


class SiniestroResponse(BaseModel):
    id: int
    poliza_id: int
    descripcion: str
    estado: str
    fecha_siniestro: date
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SiniestroUpdateEstado(BaseModel):
    estado: str  # Valores válidos: pendiente | en_revision | resuelto | rechazado


# =============================================================================
# ENDPOINTS — Pólizas
# TODO: mover a app/routers/polizas.py en próxima versión
# =============================================================================

@app.get("/")
def health_check(db: Session = Depends(get_db)):
    """Verifica que la API y la conexión a la BD están funcionando."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "mensaje": "API SURA funcionando", "db": "conectada"}


@app.post("/api/v1/polizas", response_model=PolizaResponse, status_code=201)
def crear_poliza(poliza: PolizaCreate, db: Session = Depends(get_db)):
    """Registra una nueva póliza en la base de datos."""
    db_poliza = models.Poliza(**poliza.model_dump())
    db.add(db_poliza)
    db.commit()
    db.refresh(db_poliza)
    return db_poliza


@app.get("/api/v1/polizas", response_model=list[PolizaResponse])
def listar_polizas(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Devuelve la lista paginada de pólizas. Por defecto: primeras 10."""
    return db.query(models.Poliza).offset(skip).limit(limit).all()


@app.get("/api/v1/polizas/{poliza_id}", response_model=PolizaResponse)
def obtener_poliza(poliza_id: int, db: Session = Depends(get_db)):
    """Devuelve el detalle de una póliza específica por su ID."""
    poliza = db.query(models.Poliza).filter(models.Poliza.id == poliza_id).first()
    if not poliza:
        raise HTTPException(status_code=404, detail="Póliza no encontrada")
    return poliza


@app.put("/api/v1/polizas/{poliza_id}", response_model=PolizaResponse)
def actualizar_poliza(poliza_id: int, poliza: PolizaUpdate, db: Session = Depends(get_db)):
    """Actualiza uno o más campos de una póliza. Solo modifica los campos enviados."""
    db_poliza = db.query(models.Poliza).filter(models.Poliza.id == poliza_id).first()
    if not db_poliza:
        raise HTTPException(status_code=404, detail="Póliza no encontrada")
    datos_actualizados = poliza.model_dump(exclude_unset=True)
    for campo, valor in datos_actualizados.items():
        setattr(db_poliza, campo, valor)
    db.commit()
    db.refresh(db_poliza)
    return db_poliza


@app.put("/api/v1/polizas/{poliza_id}/renovar", response_model=PolizaResponse)
def renovar_poliza(poliza_id: int, nueva_fecha_vencimiento: date, db: Session = Depends(get_db)):
    """Renueva una póliza vigente actualizando su fecha de vencimiento."""
    db_poliza = db.query(models.Poliza).filter(models.Poliza.id == poliza_id).first()
    if not db_poliza:
        raise HTTPException(status_code=404, detail="Póliza no encontrada")
    if db_poliza.estado != "vigente":
        raise HTTPException(status_code=400, detail="Solo se pueden renovar pólizas vigentes")
    db_poliza.fecha_vencimiento = nueva_fecha_vencimiento
    db_poliza.estado = "vigente"
    db.commit()
    db.refresh(db_poliza)
    return db_poliza


@app.delete("/api/v1/polizas/{poliza_id}", response_model=PolizaResponse)
def eliminar_poliza(poliza_id: int, db: Session = Depends(get_db)):
    """Soft delete — marca la póliza como inactiva sin eliminarla físicamente.
    Las pólizas tienen valor legal y deben mantenerse para auditoría (CMF)."""
    db_poliza = db.query(models.Poliza).filter(models.Poliza.id == poliza_id).first()
    if not db_poliza:
        raise HTTPException(status_code=404, detail="Póliza no encontrada")
    db_poliza.estado = "inactiva"
    db.commit()
    db.refresh(db_poliza)
    return db_poliza


# =============================================================================
# ENDPOINTS — Siniestros
# TODO: mover a app/routers/siniestros.py en próxima versión
# =============================================================================

@app.post("/api/v1/siniestros", response_model=SiniestroResponse, status_code=201)
def crear_siniestro(siniestro: SiniestroCreate, db: Session = Depends(get_db)):
    """Registra un nuevo siniestro asociado a una póliza existente."""
    poliza = db.query(models.Poliza).filter(models.Poliza.id == siniestro.poliza_id).first()
    if not poliza:
        raise HTTPException(status_code=404, detail="Póliza no encontrada")
    db_siniestro = models.Siniestro(**siniestro.model_dump())
    db.add(db_siniestro)
    db.commit()
    db.refresh(db_siniestro)
    return db_siniestro


@app.get("/api/v1/siniestros/{siniestro_id}", response_model=SiniestroResponse)
def obtener_siniestro(siniestro_id: int, db: Session = Depends(get_db)):
    """Devuelve el detalle y estado actual de un siniestro por su ID."""
    siniestro = db.query(models.Siniestro).filter(models.Siniestro.id == siniestro_id).first()
    if not siniestro:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado")
    return siniestro


@app.put("/api/v1/siniestros/{siniestro_id}/estado", response_model=SiniestroResponse)
def actualizar_estado_siniestro(siniestro_id: int, datos: SiniestroUpdateEstado, db: Session = Depends(get_db)):
    """Actualiza el estado de un siniestro dentro del flujo definido."""
    siniestro = db.query(models.Siniestro).filter(models.Siniestro.id == siniestro_id).first()
    if not siniestro:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado")
    estados_validos = ["pendiente", "en_revision", "resuelto", "rechazado"]
    if datos.estado not in estados_validos:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Valores permitidos: {estados_validos}")
    siniestro.estado = datos.estado
    db.commit()
    db.refresh(siniestro)
    return siniestro


# =============================================================================
# ENDPOINTS — Reportes
# TODO: mover a app/routers/reportes.py en próxima versión
# =============================================================================

@app.get("/api/v1/reportes/siniestros")
def reporte_siniestros(fecha_inicio: date, fecha_fin: date, db: Session = Depends(get_db)):
    """Devuelve el agregado de siniestros registrados dentro de un período."""
    siniestros = db.query(models.Siniestro).filter(
        models.Siniestro.fecha_siniestro >= fecha_inicio,
        models.Siniestro.fecha_siniestro <= fecha_fin
    ).all()
    return {
        "periodo": {"desde": fecha_inicio, "hasta": fecha_fin},
        "total": len(siniestros),
        "siniestros": [
            {
                "id": s.id,
                "poliza_id": s.poliza_id,
                "estado": s.estado,
                "fecha_siniestro": s.fecha_siniestro
            } for s in siniestros
        ]
    }


@app.get("/api/v1/reportes/polizas/vencimiento")
def reporte_vencimiento(dias: int = 30, db: Session = Depends(get_db)):
    """Devuelve las pólizas vigentes próximas a vencer. Por defecto: próximos 30 días."""
    hoy = datetime.today().date()
    limite = hoy + timedelta(days=dias)
    polizas = db.query(models.Poliza).filter(
        models.Poliza.fecha_vencimiento >= hoy,
        models.Poliza.fecha_vencimiento <= limite,
        models.Poliza.estado == "vigente"
    ).all()
    return {
        "consulta": f"Pólizas que vencen en los próximos {dias} días",
        "total": len(polizas),
        "polizas": [
            {
                "id": p.id,
                "numero_poliza": p.numero_poliza,
                "titular": p.titular,
                "fecha_vencimiento": p.fecha_vencimiento
            } for p in polizas
        ]
    }