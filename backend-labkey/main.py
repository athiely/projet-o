from typing import List, Annotated
from sqlmodel import SQLModel, Session, create_engine, select
from fastapi import FastAPI, Depends
from models import Usuario, Chave, Reserva
from contextlib import asynccontextmanager

# Configuração do banco
url = "sqlite:///labkey.db"
args = {"check_same_thread": False}
engine = create_engine(url, connect_args=args)

# Dependência da sessão
def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

# Criar tabelas
def create_db():
    SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    yield

app = FastAPI(lifespan=lifespan)

# ROTAS USUÁRIOS 
@app.get("/usuarios")
def listar_usuarios(session: SessionDep) -> List[Usuario]:
    return session.exec(select(Usuario)).all()

@app.post("/usuarios")
def cadastrar_usuario(session: SessionDep, usuario: Usuario) -> Usuario:
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario

@app.put("/usuarios/{id}")
def atualizar_usuario(session: SessionDep, id: int, nome: str) -> Usuario:
    consulta = select(Usuario).where(Usuario.id == id)
    usuario = session.exec(consulta).one()
    usuario.nome = nome
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario

@app.delete("/usuarios/{id}")
def deletar_usuario(session: SessionDep, id: int) -> str:
    consulta = select(Usuario).where(Usuario.id == id)
    usuario = session.exec(consulta).one()
    session.delete(usuario)
    session.commit()
    return "Usuário excluído com sucesso."


#  ROTAS CHAVES 
@app.get("/chaves")
def listar_chaves(session: SessionDep) -> List[Chave]:
    return session.exec(select(Chave)).all()

@app.post("/chaves")
def cadastrar_chave(session: SessionDep, chave: Chave) -> Chave:
    session.add(chave)
    session.commit()
    session.refresh(chave)
    return chave


#  ROTAS RESERVAS 
@app.get("/reservas")
def listar_reservas(session: SessionDep) -> List[Reserva]:
    return session.exec(select(Reserva)).all()

@app.post("/reservas")
def cadastrar_reserva(session: SessionDep, reserva: Reserva) -> Reserva:
    session.add(reserva)
    session.commit()
    session.refresh(reserva)
    return reserva
