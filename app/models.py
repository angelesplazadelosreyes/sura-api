from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Poliza(Base):
    __tablename__ = "polizas"

    id = Column(Integer, primary_key=True, index=True)
    numero_poliza = Column(String(20), unique=True, nullable=False)
    tipo = Column(String(50), nullable=False)
    titular = Column(String(100), nullable=False)
    prima_mensual = Column(Float, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    estado = Column(String(20), nullable=False, default="vigente")
    created_at = Column(DateTime(timezone=True), server_default=func.now())