from typing import Annotated
from sqlmodel import SQLModel, Session, create_engine, select
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import hashlib

from models.models import TipoUsuario, Usuario, CadastroInput, LoginInput

# ------------------------
# CONFIGURAÇÕES DO BANCO
# ------------------------
url = "sqlite:///labkey.db"
args = {"check_same_thread": False}
engine = create_engine(url, connect_args=args)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

def create_db():
    SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    yield

# ------------------------
# CONFIGURAÇÃO DO APP
# ------------------------
app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key="chave_muito_segura_labkey")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ------------------------
# ROTAS DE PÁGINAS (FRONT)
# ------------------------
@app.get("/", summary="Página Inicial")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", summary="Página de Login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/cadastro", summary="Página de Cadastro")
def cadastro_page(request: Request):
    return templates.TemplateResponse("cadastro.html", {"request": request})

@app.get("/dashboard", summary="Página do Dashboard")
def dashboard_page(request: Request):
    if "usuario_id" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    tipo = request.session.get("tipo_usuario")
    nome = request.session.get("nome")
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "tipo_usuario": tipo, "nome": nome}
    )

@app.get("/cadastro_sala", summary="Página de Cadastro de Sala")
def cadastro_sala_page(request: Request):
    return templates.TemplateResponse("salas.html", {"request": request})

@app.get("/reserva", summary="Página de Reserva de Sala")
def cadastro_sala_page(request: Request):
    return templates.TemplateResponse("reservas.html", {"request": request})

# ------------------------
# ROTAS DE AUTENTICAÇÃO
# ------------------------
@app.post("/api/v1/cadastro")
def cadastrar_usuario(session: SessionDep, dados: CadastroInput, request: Request):
    # Verifica se o e-mail já existe
    existente = session.exec(select(Usuario).where(Usuario.email == dados.email)).first()
    if existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    # Valida tipo de usuário usando Enum
    try:
        tipo_usuario = TipoUsuario(dados.tipo)
    except ValueError:
        raise HTTPException(status_code=400, detail="Tipo de usuário inválido.")

    # Cria hash da senha
    senha_hash = hashlib.sha256(dados.senha.encode()).hexdigest()
    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        tipo=tipo_usuario,
        senha_hash=senha_hash
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)

    # Cria a sessão do usuário automaticamente
    request.session["usuario_id"] = usuario.id
    request.session["nome"] = usuario.nome
    request.session["tipo_usuario"] = usuario.tipo.value

    # Redireciona para o dashboard
    return JSONResponse({"mensagem": f"Cadastro realizado com sucesso, {usuario.nome}!", "redirect": "/dashboard"})

@app.post("/api/v1/login")
def login(dados: LoginInput, session: SessionDep, request: Request):
    usuario = session.exec(select(Usuario).where(Usuario.email == dados.email)).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="E-mail não encontrado.")

    senha_hash = hashlib.sha256(dados.senha.encode()).hexdigest()
    if usuario.senha_hash != senha_hash:
        raise HTTPException(status_code=401, detail="Senha incorreta.")

    # Armazena sessão
    request.session["usuario_id"] = usuario.id
    request.session["nome"] = usuario.nome
    request.session["tipo_usuario"] = usuario.tipo.value

    return {"mensagem": f"Login bem-sucedido! Bem-vindo(a), {usuario.nome}.", "tipo": usuario.tipo.value}

@app.post("/api/v1/logout")
def logout(request: Request):
    request.session.clear()
    return {"mensagem": "Logout realizado com sucesso."}

# ------------------------
# ROTAS PROTEGIDAS
# ------------------------
@app.get("/api/v1/usuario")
def get_usuario_atual(request: Request):
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")
    return {
        "id": request.session.get("usuario_id"),
        "nome": request.session.get("nome"),
        "tipo": request.session.get("tipo_usuario"),
    }

@app.get("/api/v1/admin-only")
def admin_only(request: Request):
    tipo = request.session.get("tipo_usuario")
    if tipo != "ADMINISTRADOR":
        raise HTTPException(status_code=403, detail="Acesso negado. Área restrita a administradores.")
    return {"mensagem": "Acesso autorizado. Você é um administrador."}
