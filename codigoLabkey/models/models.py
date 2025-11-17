from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import date, time
import enum

# ======================================================
# ENUMS
# ======================================================

class TipoUsuario(str, enum.Enum):
    """Define os tipos de usuários (RF015)."""
    COMUM = "COMUM"
    ADMINISTRADOR = "ADMINISTRADOR"


class StatusReserva(str, enum.Enum):
    """Define os status possíveis da reserva."""
    PENDENTE = "Pendente"
    APROVADA = "Aprovada"     # mais natural que “Confirmada”
    CANCELADA = "Cancelada"


# ======================================================
# MODELOS BASE
# ======================================================

class UsuarioBase(SQLModel):
    """Campos base para Usuário, excluindo IDs e hash."""
    nome: str = Field(index=True, description="Nome completo do usuário")
    email: str = Field(unique=True, description="E-mail único para login")
    tipo: TipoUsuario = Field(default=TipoUsuario.COMUM, description="Tipo de usuário")


class CadastroInput(SQLModel):
    """Modelo para receber dados do formulário de cadastro."""
    nome: str
    email: str
    senha: str
    tipo: str  # vem do front como string simples ("Comum" ou "Administrador")


class LoginInput(SQLModel):
    """Modelo para receber dados do formulário de login."""
    email: str
    senha: str


class SalaBase(SQLModel):
    """Campos base para o modelo de Sala."""
    nome: str = Field(unique=True, index=True, description="Nome identificador da sala")
    descricao: Optional[str] = Field(default=None, description="Descrição da sala")
    capacidade: int = Field(description="Capacidade máxima de pessoas")
    localizacao: Optional[str] = Field(default=None, description="Localização física da sala")
    recursos: Optional[str] = Field(default=None, description="Equipamentos ou recursos disponíveis")


class ReservaBase(SQLModel):
    """Campos base para o modelo de Reserva."""
    data: date = Field(description="Data da reserva")
    hora_inicio: time = Field(description="Hora de início")
    hora_fim: time = Field(description="Hora de término")
    status: StatusReserva = Field(default=StatusReserva.PENDENTE, description="Status atual da reserva")


# ======================================================
# MODELOS DE TABELA (SQLModel)
# ======================================================

class Usuario(UsuarioBase, table=True):
    """Tabela de Usuários."""
    id: Optional[int] = Field(default=None, primary_key=True)
    senha_hash: str = Field(description="Hash da senha do usuário (não armazenar texto puro)")

    # Relação: Um usuário pode ter várias reservas
    reservas: List["Reserva"] = Relationship(back_populates="usuario")


class Sala(SalaBase, table=True):
    """Tabela de Salas."""
    id: Optional[int] = Field(default=None, primary_key=True)

    # Relação: Uma sala pode ter várias reservas
    reservas: List["Reserva"] = Relationship(back_populates="sala")


class Reserva(ReservaBase, table=True):
    """Tabela de Reservas."""
    id: Optional[int] = Field(default=None, primary_key=True)

    usuario_id: int = Field(foreign_key="usuario.id")
    sala_id: int = Field(foreign_key="sala.id")

    # Relações bidirecionais
    usuario: Optional[Usuario] = Relationship(back_populates="reservas")
    sala: Optional[Sala] = Relationship(back_populates="reservas")

# --- MODELOS COMPLEMENTARES PARA INPUT / UPDATE ---

class SalaUpdate(SQLModel):
    """Modelo para atualizar informações da sala."""
    nome: Optional[str] = None
    capacidade: Optional[int] = None
    recursos: Optional[str] = None


class ReservaInput(SQLModel):
    """Modelo para criar uma nova reserva."""
    data: date
    hora_inicio: time
    hora_fim: time
    sala_id: int


class ReservaUpdate(SQLModel):
    """Modelo para atualizar uma reserva existente."""
    data: Optional[date] = None
    hora_inicio: Optional[time] = None
    hora_fim: Optional[time] = None
    status: Optional[StatusReserva] = None
