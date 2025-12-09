from typing import Optional, List
# Importa Field, SQLModel e Relationship, essenciais para definir modelos e mapeamento de banco de dados
from sqlmodel import Field, SQLModel, Relationship
from datetime import date, time
import enum

# Definições de Enums (Tipos Enumerados)

class TipoUsuario(str, enum.Enum):
    """
    Define os possíveis níveis de acesso do usuário.
    """
    COMUM = "COMUM"
    ADMINISTRADOR = "ADMINISTRADOR"


class StatusReserva(str, enum.Enum):
    """
    Define os possíveis estados de uma reserva no sistema.
    """
    PENDENTE = "Pendente"
    APROVADA = "Aprovada"
    REJEITADA = "Rejeitada"
    CANCELADA = "Cancelada"


# Schemas Base (Modelos de Dados Sem Relações/ID de Tabela)

class UsuarioBase(SQLModel):
    """
    Schema base para dados de Usuário, usado em criações e visualizações.
    """
    nome: str = Field(index=True, description="Nome completo do usuário")
    email: str = Field(unique=True, description="E-mail único para login")
    tipo: TipoUsuario = Field(default=TipoUsuario.COMUM, description="Tipo de usuário")


class SalaBase(SQLModel):
    """
    Schema base para dados de Sala.
    """
    nome: str = Field(unique=True, index=True, description="Nome identificador da sala")
    descricao: Optional[str] = Field(default=None, description="Descrição da sala")
    capacidade: int = Field(description="Capacidade máxima de pessoas")
    localizacao: Optional[str] = Field(default=None, description="Localização física da sala") # Opcional
    recursos: Optional[str] = Field(default=None, description="Equipamentos ou recursos disponíveis") # Opcional


class ReservaBase(SQLModel):
    """
    Schema base para dados de Reserva.
    """
    data: date = Field(description="Data da reserva")
    hora_inicio: time = Field(description="Hora de início")
    hora_fim: time = Field(description="Hora de término")
    status: StatusReserva = Field(default=StatusReserva.PENDENTE, description="Status atual da reserva")


# Schemas de Input (Usados para receber dados de formulários/APIs)

class CadastroInput(SQLModel):
    """
    Modelo de input para o endpoint de cadastro de novo usuário.
    """
    nome: str
    email: str
    senha: str
    tipo: str # Recebe a string do TipoUsuario

# Não requer bloco de string, pois é direto

class LoginInput(SQLModel):
    """
    Modelo de input para o endpoint de login.
    """
    email: str
    senha: str

# Não requer bloco de string, pois é direto

class ReservaInput(SQLModel):
    """
    Modelo de input para o endpoint de solicitação de reserva.
    Inclui o ID da sala.
    """
    data: date
    hora_inicio: time
    hora_fim: time
    sala_id: int


class SalaUpdate(SQLModel):
    """
    Modelo de input para atualização parcial de dados da Sala.
    Todos os campos são opcionais.
    """
    nome: Optional[str] = None
    capacidade: Optional[int] = None
    localizacao: Optional[str] = None
    descricao: Optional[str] = None
    recursos: Optional[str] = None


class ReservaUpdate(SQLModel):
    """
    Modelo de input para atualização parcial de dados da Reserva pelo usuário.
    Todos os campos são opcionais.
    """
    data: Optional[date] = None
    hora_inicio: Optional[time] = None
    hora_fim: Optional[time] = None
    status: Optional[StatusReserva] = None # Embora o usuário não deva alterar o status, a estrutura permite


# Modelos de Tabela (Mapeamento ORM)

class Usuario(UsuarioBase, table=True):
    """
    Modelo de Tabela para Usuários.
    Herdando de UsuarioBase e adicionando o ID e o hash da senha.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    senha_hash: str # Campo para armazenar o hash da senha

    # Define o relacionamento com a tabela Reserva (Um Usuário tem muitas Reservas)
    reservas: List["Reserva"] = Relationship(back_populates="usuario")


class Sala(SalaBase, table=True):
    """
    Modelo de Tabela para Salas.
    Herdando de SalaBase e adicionando o ID.
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # Define o relacionamento com a tabela Reserva (Uma Sala tem muitas Reservas)
    reservas: List["Reserva"] = Relationship(back_populates="sala")


class Reserva(ReservaBase, table=True):
    """
    Modelo de Tabela para Reservas.
    Herdando de ReservaBase e definindo chaves estrangeiras para Usuário e Sala.
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # Chave estrangeira ligando à tabela Usuario
    usuario_id: int = Field(foreign_key="usuario.id")
    # Chave estrangeira ligando à tabela Sala
    sala_id: int = Field(foreign_key="sala.id")

    # Define o relacionamento de volta para a tabela Usuario (Muitas Reservas têm um Usuário)
    usuario: Optional[Usuario] = Relationship(back_populates="reservas")
    # Define o relacionamento de volta para a tabela Sala (Muitas Reservas têm uma Sala)
    sala: Optional[Sala] = Relationship(back_populates="reservas")