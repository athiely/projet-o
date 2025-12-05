from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import date, time
import enum

class TipoUsuario(str, enum.Enum):
    COMUM = "COMUM"
    ADMINISTRADOR = "ADMINISTRADOR"


class StatusReserva(str, enum.Enum):
    PENDENTE = "Pendente"
    APROVADA = "Aprovada"
    CANCELADA = "Cancelada"


class UsuarioBase(SQLModel):
    nome: str = Field(index=True, description="Nome completo do usuário")
    email: str = Field(unique=True, description="E-mail único para login")
    tipo: TipoUsuario = Field(default=TipoUsuario.COMUM, description="Tipo de usuário")


class SalaBase(SQLModel):
    nome: str = Field(unique=True, index=True, description="Nome identificador da sala")
    descricao: Optional[str] = Field(default=None, description="Descrição da sala")
    capacidade: int = Field(description="Capacidade máxima de pessoas")
    localizacao: Optional[str] = Field(default=None, description="Localização física da sala") # Opcional
    recursos: Optional[str] = Field(default=None, description="Equipamentos ou recursos disponíveis") # Opcional


class ReservaBase(SQLModel):
    data: date = Field(description="Data da reserva")
    hora_inicio: time = Field(description="Hora de início")
    hora_fim: time = Field(description="Hora de término")
    status: StatusReserva = Field(default=StatusReserva.PENDENTE, description="Status atual da reserva")


class CadastroInput(SQLModel):
    nome: str
    email: str
    senha: str
    tipo: str


class LoginInput(SQLModel):
    email: str
    senha: str


class ReservaInput(SQLModel):
    data: date
    hora_inicio: time
    hora_fim: time
    sala_id: int


class SalaUpdate(SQLModel):
    nome: Optional[str] = None
    capacidade: Optional[int] = None
    localizacao: Optional[str] = None
    descricao: Optional[str] = None
    recursos: Optional[str] = None


class ReservaUpdate(SQLModel):
    data: Optional[date] = None
    hora_inicio: Optional[time] = None
    hora_fim: Optional[time] = None
    status: Optional[StatusReserva] = None


class Usuario(UsuarioBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    senha_hash: str

    reservas: List["Reserva"] = Relationship(back_populates="usuario")


class Sala(SalaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    reservas: List["Reserva"] = Relationship(back_populates="sala")


class Reserva(ReservaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    usuario_id: int = Field(foreign_key="usuario.id")
    sala_id: int = Field(foreign_key="sala.id")

    usuario: Optional[Usuario] = Relationship(back_populates="reservas")
    sala: Optional[Sala] = Relationship(back_populates="reservas")