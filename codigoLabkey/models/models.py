from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import date, time
import enum

# ======================================================
# ENUMS
# ======================================================

class TipoUsuario(str, enum.Enum):
    """Define os tipos de usuários (RF015)."""
    COMUM = "Comum"
    ADMINISTRADOR = "Administrador"


class StatusReserva(str, enum.Enum):
    """Define os status possíveis da reserva."""
    PENDENTE = "Pendente"
    APROVADA = "Aprovada"
    CANCELADA = "Cancelada"


# ======================================================
# MODELOS BASE
# ======================================================

class UsuarioBase(SQLModel):
    """Campos base para Usuário, excluindo IDs e hash."""
    use_nome: str = Field(index=True, description="Nome completo do usuário")
    use_email: str = Field(unique=True, description="E-mail único para login")
    use_tipo: TipoUsuario = Field(default=TipoUsuario.COMUM, description="Tipo de usuário")


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
    sal_nome: str = Field(unique=True, index=True, description="Nome identificador da sala")
    sal_descricao: Optional[str] = Field(default=None, description="Descrição da sala")
    sal_capacidade: int = Field(description="Capacidade máxima de pessoas")
    sal_localizacao: Optional[str] = Field(default=None, description="Localização física da sala")
    sal_recursos: Optional[str] = Field(default=None, description="Equipamentos ou recursos disponíveis")


class ReservaBase(SQLModel):
    """Campos base para o modelo de Reserva."""
    res_data: date = Field(description="Data da reserva")
    res_hora_inicio: time = Field(description="Hora de início")
    res_hora_fim: time = Field(description="Hora de término")
    res_status: StatusReserva = Field(default=StatusReserva.PENDENTE, description="Status atual da reserva")


# ======================================================
# MODELOS DE TABELA (SQLModel)
# ======================================================

class Usuario(UsuarioBase, table=True):
    """Tabela de Usuários."""
    use_id: Optional[int] = Field(default=None, primary_key=True)
    use_senha_hash: str = Field(description="Hash da senha do usuário (não armazenar texto puro)")

    # Relação: Um usuário pode ter várias reservas
    reservas: List["Reserva"] = Relationship(back_populates="usuario")


class Sala(SalaBase, table=True):
    """Tabela de Salas."""
    sal_id: Optional[int] = Field(default=None, primary_key=True)

    # Relação: Uma sala pode ter várias reservas
    reservas: List["Reserva"] = Relationship(back_populates="sala")


class Reserva(ReservaBase, table=True):
    """Tabela de Reservas."""
    res_id: Optional[int] = Field(default=None, primary_key=True)

    res_usuario_id: int = Field(foreign_key="usuario.use_id")
    res_sala_id: int = Field(foreign_key="sala.sal_id")

    # Relações bidirecionais
    usuario: Optional[Usuario] = Relationship(back_populates="reservas")
    sala: Optional[Sala] = Relationship(back_populates="reservas")

# --- MODELOS COMPLEMENTARES PARA INPUT / UPDATE ---

class SalaUpdate(SQLModel):
    """Modelo para atualizar informações da sala."""
    sal_nome: Optional[str] = None
    sal_capacidade: Optional[int] = None
    sal_recursos: Optional[str] = None


class ReservaInput(SQLModel):
    """Modelo para criar uma nova reserva."""
    res_data: date
    res_hora_inicio: time
    res_hora_fim: time
    res_sala_id: int


class ReservaUpdate(SQLModel):
    """Modelo para atualizar uma reserva existente."""
    res_data: Optional[date] = None
    res_hora_inicio: Optional[time] = None
    res_hora_fim: Optional[time] = None
    res_status: Optional[StatusReserva] = None
