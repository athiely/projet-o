from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

# Usuário 
class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    matricula_identificacao: str = Field(unique=True, index=True)
    senha: str 
    tipo: str = Field(default="Aluno") 

# Sala 
class Sala(SQLModel, table=True):
    __tablename__ = "salas"
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(unique=True, index=True)
    capacidade: int 
    recursos: str 

# Reserva 
class Reserva(SQLModel, table=True):
    __tablename__ = "reservas"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuarios.id")
    sala_id: int = Field(foreign_key="salas.id")
    inicio: datetime = Field(index=True)
    fim: datetime = Field(index=True)
    status: str = Field(default="Pendente", index=True)
    periodicidade: Optional[str] = Field(default=None) 


# Notificação 
class Notificacao(SQLModel, table=True):
    __tablename__ = "notificacoes"
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuarios.id")
    reserva_id: Optional[int] = Field(default=None, foreign_key="reservas.id")
    mensagem: str
    data_envio: datetime = Field(default_factory=datetime.utcnow)
    lida: bool = Field(default=False)

# Log Auditoria
class LogAuditoria(SQLModel, table=True):  
    __tablename__ = "logs_auditoria"
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: Optional[int] = Field(default=None, foreign_key="usuarios.id")
    acao: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    detalhes: Optional[str] = Field(default=None)


