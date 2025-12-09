from sqlmodel import Session, select
from main import engine  # seu arquivo principal onde o engine está
from models.models import Usuario

with Session(engine) as session:
    usuarios = session.exec(select(Usuario)).all()  # pega todos os usuários
    if not usuarios:
        print("Nenhum usuário encontrado no banco.")
    else:
        print("=== Usuários cadastrados ===")
        for u in usuarios:
            print(f"ID: {u.id}, Nome: {u.nome}, E-mail: {u.email}, Tipo: {u.tipo.value}")
