from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class Produto(BaseModel):
  nome: str
  preco: Decimal | None = None
  preco_parcelado: Decimal | None = None
  link: str | None = None
  cupom: str | None = None
  imagem: str | None = None
  publicado: bool = True
  
class Cupom(BaseModel):
  nome: str
  codigo: str | None = None
  desconto: str | None = None
  limite_minimo: Decimal | None = None
  link: str | None = None
  imagem: str | None = None
  publicado: bool = True

class ProdutoResponse(Produto):
  id: int
  model_config = ConfigDict(from_attributes=True)

class CupomResponse(Cupom):
  id: int
  model_config = ConfigDict(from_attributes=True)
  