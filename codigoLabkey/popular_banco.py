from sqlmodel import SQLModel, Session, select
from main import engine
from models.models import Usuario, TipoUsuario, Sala, Reserva, StatusReserva
from datetime import date, time
import hashlib

# ==============================
# Criar tabelas
# ==============================
SQLModel.metadata.create_all(engine)
print("Tabelas criadas ou já existentes.")

# ==============================
# Popula Usuários
# ==============================
with Session(engine) as session:
    usuarios = [
        Usuario(
            nome="Administrador Geral",
            email="admin@sistema.com",
            tipo=TipoUsuario.ADMINISTRADOR,
            senha_hash=hashlib.sha256("admin123".encode()).hexdigest()
        ),
        Usuario(
            nome="João Silva",
            email="joao.silva@email.com",
            tipo=TipoUsuario.COMUM,
            senha_hash=hashlib.sha256("joao123".encode()).hexdigest()
        ),
        Usuario(
            nome="Maria Oliveira",
            email="maria.oliveira@email.com",
            tipo=TipoUsuario.COMUM,
            senha_hash=hashlib.sha256("maria123".encode()).hexdigest()
        ),
        Usuario(
            nome="Pedro Almeida",
            email="pedro.almeida@email.com",
            tipo=TipoUsuario.COMUM,
            senha_hash=hashlib.sha256("pedro123".encode()).hexdigest()
        ),
        Usuario(
            nome="Ana Beatriz",
            email="ana.beatriz@email.com",
            tipo=TipoUsuario.COMUM,
            senha_hash=hashlib.sha256("ana123".encode()).hexdigest()
        ),
    ]

    adicionados = 0
    for u in usuarios:
        # Adiciona somente se o e-mail ainda não estiver no banco
        if not session.exec(select(Usuario).where(Usuario.email == u.email)).first():
            session.add(u)
            adicionados += 1

    session.commit()
    print(f"{adicionados} usuário(s) adicionados ao banco.")

# ==============================
# Popula Salas
# ==============================
with Session(engine) as session:
    salas = [
        Sala(nome="Sala Alfa", descricao="Sala pequena", capacidade=8, localizacao="Bloco A", recursos="TV, Ar"),
        Sala(nome="Sala Beta", descricao="Sala média", capacidade=15, localizacao="Bloco A", recursos="Projetor"),
        Sala(nome="Sala Gama", descricao="Sala para reuniões", capacidade=12, localizacao="Bloco B", recursos="Mesa ampla"),
        Sala(nome="Sala Delta", descricao="Espaço multiuso", capacidade=25, localizacao="Bloco B", recursos="Som e TV"),
        Sala(nome="Sala Sigma", descricao="Sala compacta", capacidade=6, localizacao="Bloco C", recursos="Ar"),
        Sala(nome="Sala Ômega", descricao="Sala grande", capacidade=30, localizacao="Bloco C", recursos="Projetor, Ar"),
        Sala(nome="Sala Polo", descricao="Ambiente para estudos", capacidade=20, localizacao="Bloco D", recursos="Computadores"),
        Sala(nome="Sala Atlas", descricao="Sala executiva", capacidade=10, localizacao="Bloco D", recursos="TV"),
        Sala(nome="Sala Orion", descricao="Sala de apresentações", capacidade=40, localizacao="Bloco E", recursos="Som, Projetor"),
        Sala(nome="Sala Kronos", descricao="Sala premium", capacidade=18, localizacao="Bloco E", recursos="Ar, TV, Projetor"),
    ]

    adicionadas = 0
    for s in salas:
        if not session.exec(select(Sala).where(Sala.nome == s.nome)).first():
            session.add(s)
            adicionadas += 1

    session.commit()
    print(f"{adicionadas} sala(s) adicionada(s) ao banco.")

# ==============================
# Popula Reservas
# ==============================
with Session(engine) as session:
    usuarios = session.exec(select(Usuario)).all()
    salas = session.exec(select(Sala)).all()

    reservas = [
        Reserva(data=date(2025,1,10), hora_inicio=time(9,0), hora_fim=time(10,0), status=StatusReserva.PENDENTE, usuario_id=usuarios[0].id, sala_id=salas[0].id),
        Reserva(data=date(2025,1,12), hora_inicio=time(14,0), hora_fim=time(15,0), status=StatusReserva.APROVADA, usuario_id=usuarios[1].id, sala_id=salas[1].id),
        Reserva(data=date(2025,1,14), hora_inicio=time(8,0), hora_fim=time(9,0), status=StatusReserva.REJEITADA, usuario_id=usuarios[2].id, sala_id=salas[2].id),
        Reserva(data=date(2025,1,15), hora_inicio=time(10,0), hora_fim=time(11,0), status=StatusReserva.CANCELADA, usuario_id=usuarios[0].id, sala_id=salas[3].id),
        Reserva(data=date(2025,1,20), hora_inicio=time(9,0), hora_fim=time(11,0), status=StatusReserva.PENDENTE, usuario_id=usuarios[1].id, sala_id=salas[4].id),
        Reserva(data=date(2025,1,22), hora_inicio=time(15,0), hora_fim=time(16,0), status=StatusReserva.APROVADA, usuario_id=usuarios[2].id, sala_id=salas[5].id),
        Reserva(data=date(2025,1,25), hora_inicio=time(13,0), hora_fim=time(15,0), status=StatusReserva.PENDENTE, usuario_id=usuarios[0].id, sala_id=salas[6].id),
        Reserva(data=date(2025,1,27), hora_inicio=time(7,0), hora_fim=time(8,0), status=StatusReserva.APROVADA, usuario_id=usuarios[1].id, sala_id=salas[7].id),
        Reserva(data=date(2025,1,28), hora_inicio=time(16,0), hora_fim=time(17,0), status=StatusReserva.REJEITADA, usuario_id=usuarios[2].id, sala_id=salas[8].id),
        Reserva(data=date(2025,1,30), hora_inicio=time(10,30), hora_fim=time(12,0), status=StatusReserva.PENDENTE, usuario_id=usuarios[0].id, sala_id=salas[9].id),
    ]

    adicionadas_reservas = 0
    for r in reservas:
        # Evita duplicar reservas exatamente iguais (mesma data, sala e usuário)
        if not session.exec(
            select(Reserva).where(
                (Reserva.data == r.data) &
                (Reserva.hora_inicio == r.hora_inicio) &
                (Reserva.hora_fim == r.hora_fim) &
                (Reserva.usuario_id == r.usuario_id) &
                (Reserva.sala_id == r.sala_id)
            )
        ).first():
            session.add(r)
            adicionadas_reservas += 1

    session.commit()
    print(f"{adicionadas_reservas} reserva(s) adicionada(s) ao banco.")

print("Banco de dados populado com sucesso!")
