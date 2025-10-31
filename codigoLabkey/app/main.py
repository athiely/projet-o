from typing import List, Annotated
from sqlmodel import SQLModel, Session, create_engine, select
from fastapi import FastAPI, Depends, HTTPException, Request
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from models.models import Usuario, Sala, Reserva

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

# --- CONFIGURAÇÕES DE ARQUIVOS ESTÁTICOS E TEMPLATES (Adicionadas/Corrigidas) ---

# 1. Monta o diretório 'static' no caminho /static
# O name="static" é usado pelo url_for no Jinja2.
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. Inicializa o motor de templates, apontando para a pasta 'templates'
templates = Jinja2Templates(directory="templates")

# --------------------------------------------------------------------------------

# --- ROTAS DE VIEW (PÁGINAS HTML) ---

@app.get("/cadastro")
def pagina_cadastro(request: Request):
    """Renderiza a página de Cadastro."""
    return templates.TemplateResponse("cadastro.html", {"request": request})

@app.get("/login")
def pagina_login(request: Request):
    """Renderiza a página de Login."""
    return templates.TemplateResponse("login.html", {"request": request})


# --- ROTAS DE LOGIN E CADASTRO (APIs JSON) ---

@app.post("/cadastro")
def cadastrar_usuario(session: SessionDep, usuario: Usuario):
    # Verifica se o e-mail já existe
    consulta = select(Usuario).where(Usuario.email == usuario.email)
    existente = session.exec(consulta).first()
    if existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return {"mensagem": "Usuário cadastrado com sucesso!", "usuario": usuario}

@app.post("/login")
def login(email: str, senha: str, session: SessionDep):
    consulta = select(Usuario).where(Usuario.email == email)
    usuario = session.exec(consulta).first()
    if not usuario or usuario.senha != senha:
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
    # NOTA: Em um app real, você retornaria um token JWT aqui.
    return {"mensagem": f"Login bem-sucedido! Bem-vindo(a), {usuario.nome}."}


# --- ROTAS USUÁRIOS ---

@app.get("/usuarios")
def listar_usuarios(session: SessionDep) -> List[Usuario]:
    return session.exec(select(Usuario)).all()

@app.put("/usuarios/{id}")
def atualizar_usuario(session: SessionDep, id: int, nome: str):
    consulta = select(Usuario).where(Usuario.id == id)
    usuario = session.exec(consulta).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    usuario.nome = nome
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return {"mensagem": "Usuário atualizado com sucesso!", "usuario": usuario}

@app.delete("/usuarios/{id}")
def deletar_usuario(session: SessionDep, id: int):
    consulta = select(Usuario).where(Usuario.id == id)
    usuario = session.exec(consulta).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    session.delete(usuario)
    session.commit()
    return {"mensagem": "Usuário excluído com sucesso."}
    
# --- ROTAS SALAS ---

@app.get("/salas") 
def listar_salas(session: SessionDep) -> List[Sala]: 
    return session.exec(select(Sala)).all()

@app.post("/salas") 
def cadastrar_sala(session: SessionDep, sala: Sala): 
    session.add(sala)
    session.commit()
    session.refresh(sala)
    return {"mensagem": "Sala cadastrada com sucesso!", "sala": sala}
    
# --- ROTAS RESERVAS --- 

@app.get("/reservas")
def listar_reservas(session: SessionDep) -> List[Reserva]:
    return session.exec(select(Reserva)).all()

@app.post("/reservas")
def cadastrar_reserva(session: SessionDep, reserva: Reserva):
    session.add(reserva)
    session.commit()
    session.refresh(reserva)
    return {"mensagem": "Reserva cadastrada com sucesso!", "reserva": reserva}