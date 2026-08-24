import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from db import models
from db.database import engine, get_db
from db.schemas import (
    Cupom,
    CupomResponse,
    Produto,
    ProdutoResponse,
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DbSession = Annotated[Session, Depends(get_db)]


@app.post("/produtos", status_code=status.HTTP_201_CREATED)
async def criar_produto(produto: Produto, db: Session = DbSession):
    novo_produto = models.Produto(**produto.model_dump())
    db.add(novo_produto)
    db.commit()
    db.refresh(novo_produto)
    print(produto)
    return {"Produto": novo_produto}


@app.post("/cupons", status_code=status.HTTP_201_CREATED)
async def criar_cupom(cupom: Cupom, db: Session = DbSession):
    novo_cupom = models.Cupom(**cupom.model_dump())
    db.add(novo_cupom)
    db.commit()
    db.refresh(novo_cupom)
    print(cupom)
    return {"Cupom": novo_cupom}


@app.get(
    "/produtos", response_model=list[ProdutoResponse], status_code=status.HTTP_200_OK
)
async def buscar_produtos(db: Session = DbSession, skip: int = 0, limit: int = 100):
    return db.query(models.Produto).offset(skip).limit(limit).all()


@app.get("/cupons", response_model=list[CupomResponse], status_code=status.HTTP_200_OK)
async def buscar_cupons(db: Session = DbSession, skip: int = 0, limit: int = 100):
    return db.query(models.Cupom).offset(skip).limit(limit).all()


@app.put(
    "/produtos/{produto_id}",
    response_model=ProdutoResponse,
    status_code=status.HTTP_200_OK,
)
async def atualizar_produto(produto_id: int, produto: Produto, db: Session = DbSession):
    produto_query = db.query(models.Produto).filter(models.Produto.id == produto_id)
    produto_existente = produto_query.first()
    if produto_existente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado"
        )
    produto_query.update(produto.model_dump(), synchronize_session=False)
    db.commit()
    return produto_query.first()


@app.put(
    "/cupons/{cupom_id}", response_model=CupomResponse, status_code=status.HTTP_200_OK
)
async def atualizar_cupom(cupom_id: int, cupom: Cupom, db: Session = DbSession):
    cupom_query = db.query(models.Cupom).filter(models.Cupom.id == cupom_id)
    cupom_existente = cupom_query.first()
    if cupom_existente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cupom não encontrado"
        )
    cupom_query.update(cupom.model_dump(), synchronize_session=False)
    db.commit()
    return cupom_query.first()


@app.delete("/produtos/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_produto(produto_id: int, db: Session = DbSession):
    produto_query = db.query(models.Produto).filter(models.Produto.id == produto_id)
    if produto_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado"
        )
    produto_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/cupons/{cupom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_cupom(cupom_id: int, db: Session = DbSession):
    cupom_query = db.query(models.Cupom).filter(models.Cupom.id == cupom_id)
    if cupom_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cupom não encontrado"
        )
    cupom_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
