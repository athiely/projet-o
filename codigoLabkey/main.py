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
from datetime import datetime, date # <-- ADICIONADO PARA O FILTRO

from models.models import (
    TipoUsuario, Usuario, CadastroInput, LoginInput,
    Sala, SalaBase, Reserva, ReservaInput, ReservaUpdate, StatusReserva
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


# ----------------------------------------------------
# 📌 Filtro Jinja2 (Correção do erro TemplateAssertionError)
# ----------------------------------------------------
def date_format(value, format="%d/%m/%Y"):
    """Formata um objeto date/datetime ou string ISO para o formato desejado."""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value.split('T')[0], '%Y-%m-%d').date()
        except ValueError:
            return value
    
    if isinstance(value, (datetime, date)):
        return value.strftime(format)
    
    return str(value) 

templates.env.filters["date_format"] = date_format
# ----------------------------------------------------


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


# ROTA DE RESERVAS (COMUM E ADMIN) - CORRIGIDA
@app.get("/reservas", summary="Página de Reservas (Unificada)")
def reservas_page(request: Request, session: Session = Depends(get_session)):
    if "usuario_id" not in request.session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    nome = request.session.get("nome")
    tipo = request.session.get("tipo_usuario") # Tipo é 'COMUM' ou 'ADMINISTRADOR'
    usuario_id = request.session.get("usuario_id")
    
    # 1. Busca as reservas dependendo do tipo de usuário
    if tipo == TipoUsuario.ADMINISTRADOR.value:
        # Admin: Busca TODAS as reservas
        reservas_exibidas = session.exec(
            select(Reserva).order_by(Reserva.data.desc())
        ).all()
    else:
        # Comum: Filtra SOMENTE pelas suas reservas
        reservas_exibidas = session.exec(
            select(Reserva).where(Reserva.usuario_id == usuario_id).order_by(Reserva.data.desc())
        ).all()
    
    # 2. Busca as salas (para o modal)
    salas = session.exec(select(Sala)).all() 
    
    # 3. Retorna o Template, passando a lista de reservas sempre sob o nome "todas_as_reservas"
    return templates.TemplateResponse(
        "reservas.html", 
        {
            "request": request, 
            "nome": nome, 
            "tipo_usuario": tipo,
            # Lista de reservas unificada
            "todas_as_reservas": reservas_exibidas, 
            "salas_disponiveis": salas,
        }
    )

# Rotas da API de Autenticação (Mantidas sem alteração)
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

# Rotas da API de Gerenciamento de Salas (Mantidas sem alteração)
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
    
    existente = session.exec(select(Sala).where(Sala.nome == sala_input.nome)).first()
    if existente:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Sala com o nome '{sala_input.nome}' já cadastrada.")

    sala = Sala.model_validate(sala_input)

    session.add(sala)
    session.commit()
    session.refresh(sala)

    return sala

@app.put(
    "/api/v1/salas/{sala_id}",
    summary="Atualizar dados de uma Sala",
    response_model=SalaBase, 
    dependencies=[Depends(verificar_admin)]
)
def atualizar_sala(
    sala_id: int,
    sala_input: SalaBase,
    session: Session = Depends(get_session)
):
    """Endpoint para atualizar uma sala existente. Requer privilégio de Administrador."""
    
    sala = session.get(Sala, sala_id)
    if not sala:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala não encontrada.")

    update_data = sala_input.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(sala, key, value)

    session.add(sala)
    session.commit()
    session.refresh(sala)
    
    return sala

@app.delete(
    "/api/v1/salas/{sala_id}",
    summary="Excluir uma Sala",
    status_code=status.HTTP_204_NO_CONTENT, 
    dependencies=[Depends(verificar_admin)]
)
def excluir_sala(
    sala_id: int,
    session: Session = Depends(get_session)
):
    """Endpoint para excluir uma sala. Requer privilégio de Administrador e não permite exclusão se houver reservas ativas."""
    
    sala = session.get(Sala, sala_id)
    if not sala:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala não encontrada.")
    
    reservas_ativas = session.exec(
        select(Reserva)
        .where(Reserva.sala_id == sala_id)
        .where(Reserva.status.in_([StatusReserva.PENDENTE, StatusReserva.APROVADA]))
    ).first()

    if reservas_ativas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir a sala: existem reservas PENDENTES ou APROVADAS vinculadas."
        )

    session.delete(sala)
    session.commit()
    
    return


# ----------------------------------------
# Rotas da API de Reservas (Usuário Comum) - Mantidas sem alteração
# ----------------------------------------

# Solicitar nova reserva
@app.post(
    "/api/v1/reservas",
    summary="Solicitar reserva de uma sala",
    status_code=status.HTTP_201_CREATED
)
def solicitar_reserva(
    dados: ReservaInput,
    request: Request,
    session: Session = Depends(get_session)
):
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")

    usuario_id = request.session["usuario_id"]

    sala = session.get(Sala, dados.sala_id)
    if not sala:
        raise HTTPException(status_code=404, detail="Sala não encontrada.")

    reserva = Reserva(
        data=dados.data,
        hora_inicio=dados.hora_inicio,
        hora_fim=dados.hora_fim,
        sala_id=dados.sala_id,
        usuario_id=usuario_id,
        status=StatusReserva.PENDENTE
    )

    session.add(reserva)
    session.commit()
    session.refresh(reserva)

    return {"mensagem": "Solicitação de reserva enviada com sucesso!", "reserva_id": reserva.id, "status": reserva.status.value}


# Editar reserva 
@app.put(
    "/api/v1/reservas/{reserva_id}",
    summary="Editar uma reserva existente do usuário"
)
def editar_reserva(
    reserva_id: int,
    dados: ReservaUpdate,
    request: Request,
    session: Session = Depends(get_session)
):
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")

    usuario_id = request.session["usuario_id"]

    reserva = session.get(Reserva, reserva_id)
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva não encontrada.")

    if reserva.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar esta reserva.")

    update_data = dados.model_dump(exclude_unset=True)
    for campo, valor in update_data.items():
        setattr(reserva, campo, valor)

    reserva.status = StatusReserva.PENDENTE # Sempre volta para pendente

    session.add(reserva)
    session.commit()
    session.refresh(reserva)

    return {"mensagem": "Reserva atualizada e reenviada para análise.", "reserva": reserva, "status": reserva.status.value}


# Endpoint de Cancelamento (PUT para mudar status) para o usuário comum
@app.put(
    "/api/v1/reservas/{reserva_id}/cancelar",
    summary="Solicitar cancelamento de reserva pelo usuário"
)
def solicitar_cancelamento_reserva(
    reserva_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")

    usuario_id = request.session["usuario_id"]
    
    reserva = session.get(Reserva, reserva_id)
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva não encontrada.")

    if reserva.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="Você não pode cancelar esta reserva.")

    if reserva.status == StatusReserva.CANCELADA:
         raise HTTPException(status_code=400, detail="Reserva já está cancelada.")

    reserva.status = StatusReserva.CANCELADA

    session.add(reserva)
    session.commit()
    session.refresh(reserva)

    return {"mensagem": "Reserva cancelada com sucesso.", "status": reserva.status.value}


# Listar reservas do próprio usuário (Usada pela rota de visualização)
@app.get(
    "/api/v1/minhas_reservas",
    summary="Listar todas as reservas do usuário logado"
)
def listar_minhas_reservas(
    request: Request,
    session: Session = Depends(get_session)
):
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")

    usuario_id = request.session["usuario_id"]

    reservas = session.exec(
        select(Reserva).where(Reserva.usuario_id == usuario_id)
    ).all()

    return reservas


# ----------------------------------------
# Rotas da API de Reservas (Administrador) - Atualizadas
# ----------------------------------------

# Listar TODAS as reservas (somente admin)
@app.get(
    "/api/v1/admin/reservas",
    summary="Listar todas as reservas (ADMIN)",
    dependencies=[Depends(verificar_admin)]
)
def listar_reservas_admin_api(session: Session = Depends(get_session)):
    # Retorna todas as reservas (agora com o nome da rota corrigido para evitar conflitos)
    reservas = session.exec(select(Reserva)).all()
    return reservas


# Rota Unificada para Mudar Status (Usada pela tela Admin)
@app.put(
    "/api/v1/reservas/{reserva_id}/status",
    summary="Mudar o status da reserva (ADMIN)",
    dependencies=[Depends(verificar_admin)]
)
def mudar_status_reserva(
    reserva_id: int,
    status_input: dict, # Recebe o novo status (ex: {"status": "APROVADA"})
    session: Session = Depends(get_session)
):
    reserva = session.get(Reserva, reserva_id)
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva não encontrada.")

    novo_status_str = status_input.get("status")
    if not novo_status_str:
        raise HTTPException(status_code=400, detail="Status não fornecido.")

    try:
        novo_status = StatusReserva(novo_status_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Status inválido.")

    reserva.status = novo_status

    session.add(reserva)
    session.commit()
    session.refresh(reserva)

    return {"mensagem": f"Status alterado para {novo_status_str} com sucesso!", "status": reserva.status.value}