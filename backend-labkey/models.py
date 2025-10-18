from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

# Usuário 
class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    email: str
    senha: str  
    tipo: str = "comum"

# Chave
class Chave(SQLModel, table=True):
    __tablename__ = "chaves"
    id: Optional[int] = Field(default=None, primary_key=True)
    laboratorio: str
    descricao: str
    status: str

# Reserva
class Reserva(SQLModel, table=True):
    __tablename__ = "reservas"
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuarios.id")
    chave_id: int = Field(foreign_key="chaves.id")
    inicio: datetime
    fim: datetime
    status: str = "ativa"
