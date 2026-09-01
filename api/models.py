from sqlalchemy import (
  TIMESTAMP,
  Boolean,
  Column,
  Integer,
  Numeric,
  String,
)
from sqlalchemy.sql import text

from api.database import Base

DEFAULT_TIMESTAMP = text('now()')
  
class Produto(Base):
  __tablename__ = "produto"
  id = Column(Integer, primary_key=True, nullable=False)
  nome = Column(String, nullable=True)
  preco = Column(Numeric(10, 2), nullable=True)
  preco_parcelado = Column(Numeric(10, 2), nullable=True)
  link = Column(String, nullable=True)
  cupom = Column(String, nullable=True)
  imagem = Column(String, nullable=True)
  publicado = Column(Boolean, server_default='True', nullable=False)
  created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=DEFAULT_TIMESTAMP)
  
class Cupom(Base):
  __tablename__ = "cupom"
  id = Column(Integer, primary_key=True, nullable=False)
  nome = Column(String, nullable=True)
  codigo = Column(String, nullable=True)
  desconto = Column(String, nullable=True)
  limite_minimo = Column(Numeric(10, 2), nullable=True)
  link = Column(String, nullable=True)
  imagem = Column(String, nullable=True)
  publicado = Column(Boolean, server_default='True', nullable=False)
  created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=DEFAULT_TIMESTAMP)
  