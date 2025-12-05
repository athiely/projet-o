from sqlmodel import SQLModel, Session, create_engine, select
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import hashlib
from pathlib import Path
from models.models import (
    TipoUsuario, Usuario, CadastroInput, LoginInput,
    Sala, SalaBase
)

# Configuração e Inicialização do App
DATABASE_FILE = "labkey.db"
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / DATABASE_FILE
url = f"sqlite:///{DB_PATH}"

args = {"check_same_thread": False}
engine = create_engine(url, connect_args=args)

def create_db():
    SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    yield

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

# Dependências Comuns e Middleware

def get_session():
    """Dependência para fornecer uma sessão de banco de dados."""
    with Session(engine) as session:
        yield session

def verificar_admin(request: Request):
    """Dependência para verificar se o usuário é Administrador."""
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autenticado.")
    tipo_usuario = request.session.get("tipo_usuario")
    if tipo_usuario != TipoUsuario.ADMINISTRADOR.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado: Requer privilégio de Administrador.")
    return True

# 🖥️ Rotas de Visualização (Páginas HTML)

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
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    tipo = request.session.get("tipo_usuario")
    nome = request.session.get("nome")
    return templates.TemplateResponse("dashboard.html", {"request": request, "tipo_usuario": tipo, "nome": nome})

@app.get("/salas", summary="Página de Salas")
def salas_page(request: Request, session: Session = Depends(get_session)):
    if "usuario_id" not in request.session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    nome = request.session.get("nome")
    tipo = request.session.get("tipo_usuario")
    salas = session.exec(select(Sala)).all()

    return templates.TemplateResponse("salas.html", {"request": request, "nome": nome, "tipo_usuario": tipo, "salas": salas})

@app.get("/reservas", summary="Página de Reservas")
def reservas_page(request: Request):
    if "usuario_id" not in request.session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    nome = request.session.get("nome")
    tipo = request.session.get("tipo_usuario")
    return templates.TemplateResponse("reservas.html", {"request": request, "nome": nome, "tipo_usuario": tipo})

# Rotas da API de Autenticação

@app.post("/api/v1/cadastro")
def cadastrar_usuario(dados: CadastroInput, request: Request, session: Session = Depends(get_session)):
    existente = session.exec(select(Usuario).where(Usuario.email == dados.email)).first()
    if existente:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail já cadastrado.")

    try:
        tipo_usuario = TipoUsuario(dados.tipo)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de usuário inválido.")

    senha_hash = hashlib.sha256(dados.senha.encode()).hexdigest()
    usuario = Usuario(nome=dados.nome, email=dados.email, tipo=tipo_usuario, senha_hash=senha_hash)
    session.add(usuario)
    session.commit()
    session.refresh(usuario)

    request.session["usuario_id"] = usuario.id
    request.session["nome"] = usuario.nome
    request.session["tipo_usuario"] = usuario.tipo.value

    return JSONResponse({"mensagem": f"Cadastro realizado com sucesso, {usuario.nome}!", "redirect": "/dashboard"})


@app.post("/api/v1/login")
def login(dados: LoginInput, request: Request, session: Session = Depends(get_session)):
    usuario = session.exec(select(Usuario).where(Usuario.email == dados.email)).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail não encontrado.")

    senha_hash = hashlib.sha256(dados.senha.encode()).hexdigest()
    if usuario.senha_hash != senha_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha incorreta.")

    request.session["usuario_id"] = usuario.id
    request.session["nome"] = usuario.nome
    request.session["tipo_usuario"] = usuario.tipo.value

    return {"mensagem": f"Login bem-sucedido! Bem-vindo(a), {usuario.nome}."}


@app.get("/logout", summary="Encerrar sessão do usuário")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

# Rotas da API de Gerenciamento de Salas

@app.post(
    "/api/v1/salas",
    summary="Cadastrar nova Sala",
    response_model=SalaBase,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verificar_admin)]
)
def criar_sala(
    sala_input: SalaBase,
    session: Session = Depends(get_session)
):
    """Endpoint para cadastrar uma nova sala. Requer privilégio de Administrador."""
    
    # 1. Verificar se a sala com o mesmo nome já existe
    existente = session.exec(select(Sala).where(Sala.nome == sala_input.nome)).first()
    if existente:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Sala com o nome '{sala_input.nome}' já cadastrada.")

    # 2. Cria e salva a instância da Sala
    sala = Sala.model_validate(sala_input)

    session.add(sala)
    session.commit()
    session.refresh(sala)

    return sala