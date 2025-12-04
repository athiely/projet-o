from typing import Annotated, Optional
from sqlmodel import SQLModel, Session, create_engine, select
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import hashlib
from datetime import date, time

from models.models import (
    TipoUsuario, Usuario, CadastroInput, LoginInput,
    Sala, SalaBase, Reserva, ReservaBase, StatusReserva
)

# -------------------------
# Banco / engine / sessão
# -------------------------
url = "sqlite:///labkey.db"
args = {"check_same_thread": False}
engine = create_engine(url, connect_args=args)

def get_session():
    """Dependência para fornecer uma sessão de banco de dados."""
    with Session(engine) as session:
        yield session

# opcional convenience type (mantive se quiser usar)
SessionDep = Annotated[Session, Depends(get_session)]

def create_db():
    """Cria o banco de dados e todas as tabelas (se não existir)."""
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


# -------------------------
# Auxiliares
# -------------------------
def verificar_admin(request: Request):
    """Verifica se o usuário logado é um Admin."""
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=403, detail="Não autenticado.")
    tipo_usuario = request.session.get("tipo_usuario")
    if tipo_usuario != TipoUsuario.ADMINISTRADOR.value:
        raise HTTPException(status_code=403, detail="Acesso negado: Requer privilégio de Administrador.")
    return True


# -------------------------
# Rotas de páginas
# -------------------------
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
    return templates.TemplateResponse("dashboard.html", {"request": request, "tipo_usuario": tipo, "nome": nome})

@app.get("/salas", summary="Página de Salas")
def salas_page(request: Request, session: Session = Depends(get_session)):
    """Página que lista todas as salas para o usuário logado."""
    if "usuario_id" not in request.session:
        return RedirectResponse(url="/login", status_code=303)

    nome = request.session.get("nome")
    tipo = request.session.get("tipo_usuario")

    salas = session.exec(select(Sala)).all()

    return templates.TemplateResponse("salas.html", {"request": request, "nome": nome, "tipo_usuario": tipo, "salas": salas})

@app.get("/reservas", summary="Página de Reservas")
def reservas_page(request: Request):
    if "usuario_id" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    nome = request.session.get("nome")
    tipo = request.session.get("tipo_usuario")
    return templates.TemplateResponse("reservas.html", {"request": request, "nome": nome, "tipo_usuario": tipo})


# -------------------------
# Autenticação (API)
# -------------------------
@app.post("/api/v1/cadastro")
def cadastrar_usuario(dados: CadastroInput, request: Request, session: Session = Depends(get_session)):
    existente = session.exec(select(Usuario).where(Usuario.email == dados.email)).first()
    if existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    try:
        tipo_usuario = TipoUsuario(dados.tipo)
    except ValueError:
        raise HTTPException(status_code=400, detail="Tipo de usuário inválido.")

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
        raise HTTPException(status_code=401, detail="E-mail não encontrado.")

    senha_hash = hashlib.sha256(dados.senha.encode()).hexdigest()
    if usuario.senha_hash != senha_hash:
        raise HTTPException(status_code=401, detail="Senha incorreta.")

    request.session["usuario_id"] = usuario.id
    request.session["nome"] = usuario.nome
    request.session["tipo_usuario"] = usuario.tipo.value

    return {"mensagem": f"Login bem-sucedido! Bem-vindo(a), {usuario.nome}."}


@app.get("/logout", summary="Encerrar sessão do usuário")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


# -------------------------
# CRUD SALAS (aceita JSON ou form)
# -------------------------
@app.post("/api/v1/salas", summary="Criar nova sala (Admin)")
async def criar_sala(request: Request, session: Session = Depends(get_session), admin_check: Annotated[bool, Depends(verificar_admin)] = True):
    """
    Cria uma sala. Aceita:
      - JSON no body (Content-Type: application/json)
      - form-urlencoded / multipart-form (submissão de formulário HTML)
    """
    # extrai dados do body conforme Content-Type
    content_type = (request.headers.get("content-type") or "").lower()
    data = {}
    try:
        if "application/json" in content_type:
            data = await request.json()
        else:
            # form-data / x-www-form-urlencoded
            form = await request.form()
            data = dict(form)
    except Exception:
        raise HTTPException(status_code=400, detail="Corpo inválido.")

    # validação mínima
    nome = data.get("nome")
    capacidade_raw = data.get("capacidade")
    descricao = data.get("descricao")
    localizacao = data.get("localizacao")
    recursos = data.get("recursos")

    if not nome:
        raise HTTPException(status_code=400, detail="Campo 'nome' é obrigatório.")
    if capacidade_raw is None:
        raise HTTPException(status_code=400, detail="Campo 'capacidade' é obrigatório.")
    try:
        capacidade = int(capacidade_raw)
        if capacidade < 1:
            raise ValueError()
    except Exception:
        raise HTTPException(status_code=400, detail="Campo 'capacidade' inválido.")

    existente = session.exec(select(Sala).where(Sala.nome == nome)).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"A sala '{nome}' já existe.")

    sala = Sala(nome=nome, descricao=descricao, localizacao=localizacao, capacidade=capacidade, recursos=recursos)
    session.add(sala)
    session.commit()
    session.refresh(sala)

    return {"mensagem": f"Sala '{sala.nome}' cadastrada com sucesso!", "sala": sala}


@app.get("/api/v1/salas/{sala_id}", summary="Obter detalhes de uma sala")
def obter_sala(sala_id: int, request: Request, session: Session = Depends(get_session)):
    """Obtém detalhes de uma sala específica (acessível por usuários logados)."""
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=403, detail="Não autenticado.")

    sala = session.get(Sala, sala_id)
    if not sala:
        raise HTTPException(status_code=404, detail="Sala não encontrada.")

    return sala


@app.put("/api/v1/salas/{sala_id}", summary="Atualizar uma sala (Admin)")
def atualizar_sala(sala_id: int, dados: SalaBase, request: Request, session: Session = Depends(get_session), admin_check: Annotated[bool, Depends(verificar_admin)] = True):
    sala = session.get(Sala, sala_id)
    if not sala:
        raise HTTPException(status_code=404, detail="Sala não encontrada.")

    if sala.nome != dados.nome:
        existente = session.exec(select(Sala).where(Sala.nome == dados.nome)).first()
        if existente:
            raise HTTPException(status_code=400, detail=f"O nome '{dados.nome}' já está em uso.")

    sala_data = dados.model_dump(exclude_unset=True)
    for key, value in sala_data.items():
        setattr(sala, key, value)

    session.add(sala)
    session.commit()
    session.refresh(sala)

    return {"mensagem": f"Sala '{sala.nome}' atualizada com sucesso!", "sala": sala}


@app.delete("/api/v1/salas/{sala_id}", summary="Excluir uma sala (Admin)")
def excluir_sala(sala_id: int, request: Request, session: Session = Depends(get_session), admin_check: Annotated[bool, Depends(verificar_admin)] = True):
    sala = session.get(Sala, sala_id)
    if not sala:
        raise HTTPException(status_code=404, detail="Sala não encontrada.")

    reservas_ativas = session.exec(select(Reserva).where(Reserva.sala_id == sala_id)).first()
    if reservas_ativas:
        raise HTTPException(status_code=400, detail="Sala não pode ser excluída: possui reservas associadas.")

    session.delete(sala)
    session.commit()

    return {"mensagem": f"Sala '{sala.nome}' excluída com sucesso!"}


# -------------------------
# Verificação de conflito e CRUD Reservas
# -------------------------
def verificar_conflito(session: Session, sala_id: int, data: date, hora_inicio: time, hora_fim: time) -> bool:
    """Verifica se há sobreposição de horário em uma determinada sala."""
    conflitos = session.exec(
        select(Reserva)
        .where(Reserva.sala_id == sala_id)
        .where(Reserva.data == data)
        .where(Reserva.hora_inicio < hora_fim)
        .where(Reserva.hora_fim > hora_inicio)
        .where(Reserva.status.in_([StatusReserva.APROVADA, StatusReserva.PENDENTE]))
    ).all()
    return len(conflitos) > 0


@app.post("/api/v1/reservas", summary="Criar nova reserva")
def criar_reserva(dados: ReservaBase, request: Request, sala_id: int, session: Session = Depends(get_session)):
    """Cria uma nova reserva para o usuário logado."""
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=403, detail="Não autenticado.")

    usuario_id = request.session["usuario_id"]

    if not session.get(Sala, sala_id):
        raise HTTPException(status_code=404, detail="Sala não encontrada.")

    if verificar_conflito(session, sala_id, dados.data, dados.hora_inicio, dados.hora_fim):
        raise HTTPException(status_code=409, detail="Conflito de horário: Já existe uma reserva para esta sala e horário.")

    reserva = Reserva.model_validate(dados)
    reserva.usuario_id = usuario_id
    reserva.sala_id = sala_id

    tipo_usuario = request.session.get("tipo_usuario")
    # Ajuste: se for usuário comum, coloca PENDENTE; admins aprovam automaticamente
    if tipo_usuario == TipoUsuario.COMUM.value:
        reserva.status = StatusReserva.PENDENTE
    else:
        reserva.status = StatusReserva.APROVADA

    session.add(reserva)
    session.commit()
    session.refresh(reserva)

    return {"mensagem": f"Reserva criada com status: {reserva.status.value}", "reserva": reserva}


@app.get("/api/v1/reservas/minhas", summary="Listar reservas do usuário logado")
def listar_minhas_reservas(request: Request, session: Session = Depends(get_session)):
    """Lista as reservas criadas pelo usuário logado."""
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=403, detail="Não autenticado.")

    usuario_id = request.session["usuario_id"]

    reservas = session.exec(select(Reserva).where(Reserva.usuario_id == usuario_id)).all()
    return reservas
