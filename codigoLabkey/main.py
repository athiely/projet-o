from typing import Annotated, Optional
from sqlmodel import SQLModel, Session, create_engine, select
from fastapi import FastAPI, Depends, HTTPException, Request, status, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from passlib.context import CryptContext 
from models.models import Usuario, CadastroInput, LoginInput
from datetime import datetime, timedelta
import os
import uuid

# --- CONFIGURAÇÃO DE SEGURANÇA (RNF002) ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Secret Key para o cookie de sessão (DEVE SER ALTERADA EM AMBIENTE DE PRODUÇÃO!)
SECRET_KEY = os.environ.get("SESSION_SECRET", str(uuid.uuid4()))

def verify_password(plain_password: str, hashed_password: str):
    """Verifica se a senha em texto simples corresponde ao hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    """Cria um hash seguro para a senha. (RF001/NF002)"""
    # 1. Validação de tipo
    if not isinstance(password, str):
        print(f"ERRO DE TIPO: Senha fornecida não é uma string, é {type(password)}")
        raise ValueError("A senha fornecida não é uma string válida. Verifique o payload do formulário.")
    
    # 2. Truncagem defensiva (re-introduzida)
    # Garante que a string nunca exceda o limite de 72 bytes do bcrypt,
    # prevenindo o ValueError, mesmo que a biblioteca esteja instável.
    safe_password = password[:72]
    
    # 3. Log de depuração para entender o tamanho real
    if len(password) > 72:
        # Este print aparecerá no terminal, indicando que a string original era gigante.
        print(f"AVISO: Senha muito longa ({len(password)} bytes). Foi truncada para 72 bytes antes do hash.")
    else:
        # Este print deve aparecer para sua senha de 5 dígitos.
        print(f"DEBUG: Senha com {len(password)} caracteres ({len(password.encode('utf-8'))} bytes) sendo processada.")
        
    return pwd_context.hash(safe_password) # Usa a senha segura (truncada se necessário)

# --- CONFIGURAÇÃO DO BANCO DE DADOS (SQLModel/SQLite) ---

DB_URL = "sqlite:///labkey.db"
DB_ARGS = {"check_same_thread": False}
engine = create_engine(DB_URL, connect_args=DB_ARGS)

def create_db_and_tables():
    """Cria o banco de dados e todas as tabelas definidas nos modelos."""
    SQLModel.metadata.create_all(engine)

# Dependência para gerenciamento da sessão
def get_session():
    with Session(engine) as session:
        yield session
SessionDep = Annotated[Session, Depends(get_session)]

# --- AUTENTICAÇÃO E SESSÃO ---

def get_current_user_id(request: Request) -> Optional[int]:
    """Tenta obter o ID do usuário a partir do cookie de sessão."""
    try:
        user_id_str = request.cookies.get("session_id")
        if user_id_str:
            return int(user_id_str)
    except ValueError:
        pass
    return None

def get_current_user(session: SessionDep, request: Request) -> Optional[Usuario]:
    """Retorna o objeto Usuario se estiver autenticado, ou None."""
    user_id = get_current_user_id(request)
    if user_id is None:
        return None
        
    consulta = select(Usuario).where(Usuario.id == user_id)
    usuario = session.exec(consulta).first()
    return usuario
    
CurrentUser = Annotated[Optional[Usuario], Depends(get_current_user)]


# --- CONFIGURAÇÃO DO FASTAPI (App, Lifespan, Templates) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Context manager que garante a criação das tabelas ao iniciar o app."""
    print("Criando tabelas...")
    create_db_and_tables()
    yield

app = FastAPI(title="LabKey MVP API", lifespan=lifespan)

# Configuração para servir arquivos estáticos (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuração do motor de templates Jinja2
templates = Jinja2Templates(directory="templates")

# --- ROTAS DE VIEW (PÁGINAS HTML) ---

@app.get("/")
def pagina_home(request: Request, user: CurrentUser):
    """Renderiza a página inicial."""
    context = {"request": request, "user": user}
    return templates.TemplateResponse("index.html", context)

@app.get("/cadastro")
def pagina_cadastro(request: Request, user: CurrentUser):
    """Renderiza a página HTML de Cadastro."""
    if user:
        # Se o usuário já está logado, redireciona para a home
        return Response(status_code=status.HTTP_302_FOUND, headers={"Location": "/"})
    return templates.TemplateResponse("cadastro.html", {"request": request, "user": user})

@app.get("/login")
def pagina_login(request: Request, user: CurrentUser):
    """Renderiza a página HTML de Login."""
    if user:
        # Se o usuário já está logado, redireciona para a home
        return Response(status_code=status.HTTP_302_FOUND, headers={"Location": "/"})
    return templates.TemplateResponse("login.html", {"request": request, "user": user})

@app.post("/logout")
def logout(response: Response):
    """RF003: Efetua o Logout (remove o cookie de sessão)."""
    response.delete_cookie(key="session_id")
    # Redireciona o usuário para a página de login
    response.headers["Location"] = "/login"
    return Response(status_code=status.HTTP_302_FOUND)


# --- ROTAS DE API (Endpoints JSON) ---

@app.post("/cadastro", status_code=status.HTTP_201_CREATED)
def cadastrar_usuario(session: SessionDep, dados_cadastro: CadastroInput):
    """RF001: Recebe dados, faz o hash da senha e cria o usuário."""
    
    # 1. Verifica se o e-mail já existe
    consulta = select(Usuario).where(Usuario.email == dados_cadastro.email)
    existente = session.exec(consulta).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="E-mail já cadastrado."
        )

    # 2. Gera o hash da senha (DEIXANDO O ERRO VAZAR TEMPORARIAMENTE PARA DIAGNÓSTICO)
    hashed_password = get_password_hash(dados_cadastro.senha)
    # Se um erro ocorrer acima, o traceback completo será impresso no terminal.

    # 3. Cria a instância de Usuario com o hash
    novo_usuario = Usuario(
        nome=dados_cadastro.nome,
        email=dados_cadastro.email,
        tipo=dados_cadastro.tipo,
        senha_hash=hashed_password # SALVA O HASH SEGURO
    )

    session.add(novo_usuario)
    session.commit()
    session.refresh(novo_usuario)
    
    return {"mensagem": "Usuário cadastrado com sucesso!", "id": novo_usuario.id}

@app.post("/login")
def login(dados_login: LoginInput, session: SessionDep, response: Response):
    # ... (lógica de login permanece a mesma) ...
    
    consulta = select(Usuario).where(Usuario.email == dados_login.email)
    usuario = session.exec(consulta).first()

    # 1. Usuário não encontrado
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos.")

    # 2. Verifica a senha usando o hash
    if not verify_password(dados_login.senha, usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos.")

    # 3. SUCESSO: Cria o cookie de sessão (RF002 implementado)
    expires_time = datetime.now() + timedelta(days=1)
    
    response.set_cookie(
        key="session_id", 
        value=str(usuario.id), 
        expires=expires_time.timestamp(),
        httponly=True,
        samesite="lax",
        secure=False,
    )

    # Sucesso - Retorna uma mensagem e o cookie é setado no cabeçalho da resposta
    return {"mensagem": f"Login bem-sucedido! Bem-vindo(a), {usuario.nome}.", "redirect_url": "/"}
