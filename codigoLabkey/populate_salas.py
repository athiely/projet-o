# populate_salas.py
from sqlmodel import Session, create_engine, select
from models.models import Sala, SQLModel 

engine = create_engine("sqlite:///labkey.db", connect_args={"check_same_thread": False})
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    # Verifica se as salas já existem para evitar duplicação
    if not session.exec(select(Sala).where(Sala.nome == "Lab 1")).first():
        sala1 = Sala(nome="Lab 1", capacidade=20, recursos="Projetor", localizacao="Bloco A")
        session.add(sala1)
        print("Sala 'Lab 1' adicionada.")
    
    if not session.exec(select(Sala).where(Sala.nome == "Lab 2")).first():
        sala2 = Sala(nome="Lab 2", capacidade=15, recursos="Computadores", localizacao="Bloco B")
        session.add(sala2)
        print("Sala 'Lab 2' adicionada.")
        
    session.commit()

print("Verificação e inserção de salas de teste concluída.")