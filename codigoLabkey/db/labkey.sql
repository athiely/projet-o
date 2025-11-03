-- TABELA USUARIO (RF001)
-- Armazena os dados dos usuários, incluindo o hash da senha (RNF002).
CREATE TABLE usuario (
    -- Chave Primária, gerenciada pelo SQLite (auto-incremento)
    id INTEGER PRIMARY KEY NOT NULL,
    
    nome VARCHAR NOT NULL,
    
    -- E-mail deve ser único para garantir que cada usuário tenha uma conta
    email VARCHAR NOT NULL UNIQUE,
    
    -- O campo 'tipo' armazena o valor do Enum (Aluno, Professor, etc.)
    tipo VARCHAR NOT NULL,
    
    -- Armazena o hash seguro da senha (RNF002: passlib/bcrypt)
    senha_hash VARCHAR NOT NULL
);

-- TABELA SALA (RF004)
-- Armazena informações sobre as salas/laboratórios disponíveis para reserva.
CREATE TABLE sala (
    -- Chave Primária
    id INTEGER PRIMARY KEY NOT NULL,
    
    -- Nome da sala deve ser único
    nome VARCHAR NOT NULL UNIQUE,

    descricao varchar not null,
    
    capacidade INTEGER NOT NULL,
    
    recursos VARCHAR NOT NULL
);

-- TABELA RESERVA (RF008)
-- Tabela de relacionamento que liga um usuário a uma sala em um período específico.
CREATE TABLE reserva (
    -- Chave Primária
    id INTEGER PRIMARY KEY NOT NULL,
    
    -- Chave Estrangeira: Referencia o usuário que fez a reserva
    usuario_id INTEGER NOT NULL,
    
    -- Chave Estrangeira: Referencia a sala reservada
    sala_id INTEGER NOT NULL,
    
    -- Data da reserva (Usamos TEXT para armazenar o formato YYYY-MM-DD no SQLite)
    data DATE NOT NULL,
    
    -- Hora de início (Usamos TEXT para armazenar o formato HH:MM:SS)
    hora_inicio TIME NOT NULL,
    
    -- Hora de fim
    hora_fim TIME NOT NULL,
    
    -- Status da reserva (Pendente por padrão)
    status VARCHAR NOT NULL DEFAULT 'Pendente',
    
    -- Definição das chaves estrangeiras (Constraints)
    FOREIGN KEY(usuario_id) REFERENCES usuario (id),
    FOREIGN KEY(sala_id) REFERENCES sala (id)
);