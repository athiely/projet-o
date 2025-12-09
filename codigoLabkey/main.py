from sqlmodel import SQLModel, Session, create_engine, select
# Importa o essencial para construir a API: App, dependências, exceções e respostas
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
# Middleware para gerenciar requisições CORS
from fastapi.middleware.cors import CORSMiddleware
# Para servir arquivos estáticos (CSS, JS, Imagens)
from fastapi.staticfiles import StaticFiles
# Para renderizar páginas HTML usando Jinja2
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse, JSONResponse
# Middleware para gerenciar sessões do usuário
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import hashlib
from pathlib import Path
from datetime import datetime, date

# Importa os schemas (modelos de dados) definidos
from models.models import (
    TipoUsuario, Usuario, CadastroInput, LoginInput,
    Sala, SalaBase, Reserva, ReservaInput, ReservaUpdate, StatusReserva
)

# Configuração do Banco de Dados

DATABASE_FILE = "labkey.db"
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / DATABASE_FILE
# String de conexão SQLite
url = f"sqlite:///{DB_PATH}"

# Argumentos específicos para SQLite no FastAPI
args = {"check_same_thread": False}
engine = create_engine(url, connect_args=args)

def create_db():
    """Cria as tabelas no banco de dados se ainda não existirem."""
    SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Função de ciclo de vida: executa antes do início e no encerramento do app."""
    create_db()
    yield

# Inicialização do Aplicativo

# Cria a instância principal do FastAPI com o gerenciador de ciclo de vida
app = FastAPI(lifespan=lifespan)
# Adiciona middleware de sessão para gerenciar estados do usuário
app.add_middleware(SessionMiddleware, secret_key="chave_muito_segura_labkey")

# Configura o middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permite acesso de qualquer origem
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta o diretório 'static' para servir arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
# Configura o motor de templates Jinja2
templates = Jinja2Templates(directory="templates")


# Funções Auxiliares e Filtros de Template

def date_format(value, format="%d/%m/%Y"):
    """Formata um objeto date/datetime ou string ISO para o formato desejado."""
    if isinstance(value, str):
        try:
            # Tenta converter string ISO para date
            value = datetime.strptime(value.split('T')[0], '%Y-%m-%d').date()
        except ValueError:
            return value
    
    if isinstance(value, (datetime, date)):
        return value.strftime(format)
    
    return str(value) 

# Registra a função date_format como um filtro Jinja2
templates.env.filters["date_format"] = date_format


# Dependências

def get_session():
    """
    Dependência que fornece uma sessão de banco de dados do SQLModel.
    Garante que a sessão seja fechada após o uso.
    """
    with Session(engine) as session:
        yield session

def verificar_admin(request: Request):
    """
    Dependência para verificar se o usuário logado possui o tipo ADMINISTRADOR.
    Levanta HTTPException se não estiver logado ou não for admin.
    """
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autenticado.")
    tipo_usuario = request.session.get("tipo_usuario")
    if tipo_usuario != TipoUsuario.ADMINISTRADOR.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado: Requer privilégio de Administrador.")
    return True


# Rotas de Páginas (Views HTML)

@app.get("/equipe", response_class=HTMLResponse)
async def ver_equipe(request: Request):
    """
    Renderiza a página 'equipe.html' contendo o resumo do projeto e o carrossel da equipe.
    """
    
    
    return templates.TemplateResponse("equipe.html", {"request": request})

@app.get("/", summary="Página Inicial")
def home(request: Request):
    # Retorna o template 'index.html'
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", summary="Página de Login")
def login_page(request: Request):
    # Retorna o template 'login.html'
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/cadastro", summary="Página de Cadastro")
def cadastro_page(request: Request):
    # Retorna o template 'cadastro.html'
    return templates.TemplateResponse("cadastro.html", {"request": request})

@app.get("/dashboard", summary="Página do Dashboard")
def dashboard_page(request: Request):
    # Redireciona para login se o usuário não estiver na sessão
    if "usuario_id" not in request.session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    # Retorna o template 'dashboard.html' com dados do usuário
    tipo = request.session.get("tipo_usuario")
    nome = request.session.get("nome")
    return templates.TemplateResponse("dashboard.html", {"request": request, "tipo_usuario": tipo, "nome": nome})

@app.get("/salas", summary="Página de Salas")
def salas_page(request: Request, session: Session = Depends(get_session)):
    # Requer autenticação
    if "usuario_id" not in request.session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    nome = request.session.get("nome")
    tipo = request.session.get("tipo_usuario")
    # Busca todas as salas no BD
    salas = session.exec(select(Sala)).all()

    # Retorna o template 'salas.html' com a lista de salas
    return templates.TemplateResponse("salas.html", {"request": request, "nome": nome, "tipo_usuario": tipo, "salas": salas})


@app.get("/reservas", summary="Página de Reservas (Unificada)")
def reservas_page(request: Request, session: Session = Depends(get_session)):
    # Requer autenticação
    if "usuario_id" not in request.session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    nome = request.session.get("nome")
    tipo = request.session.get("tipo_usuario")
    usuario_id = request.session.get("usuario_id")
    
    # Se for Admin, lista todas as reservas.
    if tipo == TipoUsuario.ADMINISTRADOR.value:
        reservas_exibidas = session.exec(
            select(Reserva).order_by(Reserva.data.desc())
        ).all()
    # Caso contrário, lista apenas as reservas do usuário logado.
    else:
        reservas_exibidas = session.exec(
            select(Reserva).where(Reserva.usuario_id == usuario_id).order_by(Reserva.data.desc())
        ).all()
    
    # Busca todas as salas para exibição no formulário
    salas = session.exec(select(Sala)).all() 
    
    # Retorna o template 'reservas.html'
    return templates.TemplateResponse(
        "reservas.html", 
        {
            "request": request, 
            "nome": nome, 
            "tipo_usuario": tipo,
            "todas_as_reservas": reservas_exibidas, 
            "salas_disponiveis": salas,
        }
    )


# Endpoints da API

@app.post("/api/v1/cadastro")
def cadastrar_usuario(dados: CadastroInput, request: Request, session: Session = Depends(get_session)):
    # Verifica se o e-mail já existe
    existente = session.exec(select(Usuario).where(Usuario.email == dados.email)).first()
    if existente:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail já cadastrado.")

    # Valida o tipo de usuário
    try:
        tipo_usuario = TipoUsuario(dados.tipo)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de usuário inválido.")

    # Cria o hash da senha
    senha_hash = hashlib.sha256(dados.senha.encode()).hexdigest()
    # Cria e salva o novo usuário
    usuario = Usuario(nome=dados.nome, email=dados.email, tipo=tipo_usuario, senha_hash=senha_hash)
    session.add(usuario)
    session.commit()
    session.refresh(usuario)

    # Inicia a sessão do usuário
    request.session["usuario_id"] = usuario.id
    request.session["nome"] = usuario.nome
    request.session["tipo_usuario"] = usuario.tipo.value

    return JSONResponse({"mensagem": f"Cadastro realizado com sucesso, {usuario.nome}!", "redirect": "/dashboard"})


@app.post("/api/v1/login")
def login(dados: LoginInput, request: Request, session: Session = Depends(get_session)):
    # Busca o usuário pelo email
    usuario = session.exec(select(Usuario).where(Usuario.email == dados.email)).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail não encontrado.")

    # Compara o hash da senha fornecida com o hash salvo
    senha_hash = hashlib.sha256(dados.senha.encode()).hexdigest()
    if usuario.senha_hash != senha_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha incorreta.")

    # Preenche a sessão após o login bem-sucedido
    request.session["usuario_id"] = usuario.id
    request.session["nome"] = usuario.nome
    request.session["tipo_usuario"] = usuario.tipo.value

    return {"mensagem": f"Login bem-sucedido! Bem-vindo(a), {usuario.nome}."}


@app.get("/logout", summary="Encerrar sessão do usuário")
def logout(request: Request):
    # Limpa todos os dados da sessão
    request.session.clear()
    # Redireciona para a página inicial
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.post(
    "/api/v1/salas",
    summary="Cadastrar nova Sala",
    response_model=SalaBase,
    status_code=status.HTTP_201_CREATED,
    # Protege o endpoint com a dependência de Admin
    dependencies=[Depends(verificar_admin)]
)
def criar_sala(
    sala_input: SalaBase,
    session: Session = Depends(get_session)
):
    """Endpoint para cadastrar uma nova sala. Requer privilégio de Administrador."""
    
    # Verifica se a sala já existe pelo nome
    existente = session.exec(select(Sala).where(Sala.nome == sala_input.nome)).first()
    if existente:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Sala com o nome '{sala_input.nome}' já cadastrada.")

    # Cria e salva a nova sala
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
    
    # Busca a sala pelo ID
    sala = session.get(Sala, sala_id)
    if not sala:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala não encontrada.")

    # Atualiza os campos fornecidos
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
    
    # Busca a sala
    sala = session.get(Sala, sala_id)
    if not sala:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala não encontrada.")
    
    # Verifica se existem reservas ativas (PENDENTES ou APROVADAS)
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

    # Exclui a sala
    session.delete(sala)
    session.commit()
    
    return

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
    """Endpoint para solicitar uma nova reserva. Requer que o usuário esteja logado."""
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")

    usuario_id = request.session["usuario_id"]

    # Verifica se a sala existe
    sala = session.get(Sala, dados.sala_id)
    if not sala:
        raise HTTPException(status_code=404, detail="Sala não encontrada.")

    # Cria a reserva com status PENDENTE
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
    """Endpoint para editar uma reserva própria. Requer autenticação e muda o status para PENDENTE após edição."""
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")

    usuario_id = request.session["usuario_id"]

    # Busca a reserva
    reserva = session.get(Reserva, reserva_id)
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva não encontrada.")

    # Verifica se o usuário é o dono da reserva
    if reserva.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar esta reserva.")

    # Atualiza os campos e redefine o status para PENDENTE
    update_data = dados.model_dump(exclude_unset=True)
    for campo, valor in update_data.items():
        setattr(reserva, campo, valor)

    reserva.status = StatusReserva.PENDENTE

    session.add(reserva)
    session.commit()
    session.refresh(reserva)

    return {"mensagem": "Reserva atualizada e reenviada para análise.", "reserva": reserva, "status": reserva.status.value}


@app.put(
    "/api/v1/reservas/{reserva_id}/cancelar",
    summary="Solicitar cancelamento de reserva pelo usuário"
)
def solicitar_cancelamento_reserva(
    reserva_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    """Endpoint para cancelar uma reserva própria, alterando o status para CANCELADA."""
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")

    usuario_id = request.session["usuario_id"]
    
    # Busca a reserva
    reserva = session.get(Reserva, reserva_id)
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva não encontrada.")

    # Verifica se é o dono e se já não está cancelada
    if reserva.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="Você não pode cancelar esta reserva.")

    if reserva.status == StatusReserva.CANCELADA:
         raise HTTPException(status_code=400, detail="Reserva já está cancelada.")

    # Altera o status para CANCELADA
    reserva.status = StatusReserva.CANCELADA

    session.add(reserva)
    session.commit()
    session.refresh(reserva)

    return {"mensagem": "Reserva cancelada com sucesso.", "status": reserva.status.value}


@app.get(
    "/api/v1/minhas_reservas",
    summary="Listar todas as reservas do usuário logado"
)
def listar_minhas_reservas(
    request: Request,
    session: Session = Depends(get_session)
):
    """Endpoint que lista as reservas associadas ao ID do usuário na sessão."""
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")

    usuario_id = request.session["usuario_id"]

    # Busca reservas pelo ID do usuário
    reservas = session.exec(
        select(Reserva).where(Reserva.usuario_id == usuario_id)
    ).all()

    return reservas

@app.get(
    "/api/v1/admin/reservas",
    summary="Listar todas as reservas (ADMIN)",
    dependencies=[Depends(verificar_admin)]
)
def listar_reservas_admin_api(session: Session = Depends(get_session)):
    """Endpoint para listar todas as reservas do sistema. Requer privilégio de Administrador."""
    reservas = session.exec(select(Reserva)).all()
    return reservas


@app.put(
    "/api/v1/reservas/{reserva_id}/status",
    summary="Mudar o status da reserva (ADMIN)",
    dependencies=[Depends(verificar_admin)]
)
def mudar_status_reserva(
    reserva_id: int,
    status_input: dict, 
    session: Session = Depends(get_session)
):
    """Endpoint para que o Administrador altere o status (Aprovada/Rejeitada/Cancelada) de uma reserva."""
    # Busca a reserva
    reserva = session.get(Reserva, reserva_id)
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva não encontrada.")

    # Extrai e valida o novo status
    novo_status_str = status_input.get("status")
    if not novo_status_str:
        raise HTTPException(status_code=400, detail="Status não fornecido.")

    try:
        novo_status = StatusReserva(novo_status_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Status inválido.")

    # Atualiza e salva o status
    reserva.status = novo_status

    session.add(reserva)
    session.commit()
    session.refresh(reserva)

    return {"mensagem": f"Status alterado para {novo_status_str} com sucesso!", "status": reserva.status.value}