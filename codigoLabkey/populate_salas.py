# populate_salas.py
from sqlmodel import Session, create_engine
from models.models import Sala, SQLModel   # <-- note o ".models" extra

engine = create_engine("sqlite:///labkey.db", connect_args={"check_same_thread": False})
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    sala1 = Sala(nome="Lab 1", capacidade=20, recursos="Projetor")
    sala2 = Sala(nome="Lab 2", capacidade=15, recursos="Computadores")
    session.add_all([sala1, sala2])
    session.commit()

print("Salas de teste inseridas com sucesso!")
