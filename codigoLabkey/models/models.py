from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import date, time
import enum

# --- ENUMS (Restrições de Dados) ---

class TipoUsuario(str, enum.Enum):
    """Define os tipos de usuários (RF015)."""
    ALUNO = "Aluno"
    PROFESSOR = "Professor"
    FUNCIONARIO = "Funcionario"
    ADMINISTRADOR = "Administrador"

class StatusReserva(str, enum.Enum):
    """Define os status possíveis da reserva."""
    PENDENTE = "Pendente"
    CONFIRMADA = "Confirmada"
    CANCELADA = "Cancelada"

# --- MODELOS BASE (Pydantic/Input) ---

class UsuarioBase(SQLModel):
    """Campos base para Usuário, excluindo IDs e hash."""
    nome: str = Field(index=True)
    email: str = Field(unique=True)
    # RF001 (Simplificado): 'matricula_identificacao' removida.
    tipo: TipoUsuario = Field(default=TipoUsuario.ALUNO) 

class CadastroInput(UsuarioBase):
    """Modelo para RECEBER dados do formulário de Cadastro (inclui senha em texto simples)."""
    senha: str 

class LoginInput(SQLModel):
    """Modelo para RECEBER dados do formulário de Login."""
    email: str
    senha: str

class SalaBase(SQLModel):
    """Campos base para o modelo de Sala."""
    nome: str = Field(unique=True, index=True)
    capacidade: int 
    recursos: str 

class ReservaBase(SQLModel):
    """Campos base para o modelo de Reserva."""
    data: date
    hora_inicio: time
    hora_fim: time
    status: StatusReserva = Field(default=StatusReserva.PENDENTE)

# --- MODELOS DE TABELA (SQLModel) ---

class Usuario(UsuarioBase, table=True):
    """Tabela de Usuários (RF001)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    # RNF002: Armazena o hash da senha, não o texto simples.
    senha_hash: str 
    
    # Relações com Reserva
    reservas: List["Reserva"] = Relationship(back_populates="usuario")

class Sala(SalaBase, table=True):
    """Tabela de Salas (RF004)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relações com Reserva
    reservas: List["Reserva"] = Relationship(back_populates="sala")

class Reserva(ReservaBase, table=True):
    """Tabela de Reservas (RF008)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Chaves Estrangeiras (Foreign Keys)
    usuario_id: int = Field(foreign_key="usuario.id")
    sala_id: int = Field(foreign_key="sala.id")
    
    # Relações Bidirecionais
    usuario: Usuario = Relationship(back_populates="reservas")
    sala: Sala = Relationship(back_populates="reservas")