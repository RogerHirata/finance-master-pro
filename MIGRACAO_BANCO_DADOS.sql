-- =====================================================
-- MIGRAÇÕES DO BANCO DE DADOS PARA MULTI-USUÁRIO
-- =====================================================
-- Este script adiciona as tabelas e colunas necessárias
-- para o sistema de autenticação e isolamento de dados por usuário

-- 1. CRIAR TABELA DE USUÁRIOS (se não existir)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Usuarios')
BEGIN
    CREATE TABLE Usuarios (
        id INT PRIMARY KEY IDENTITY(1,1),
        email NVARCHAR(255) UNIQUE NOT NULL,
        senha_hash NVARCHAR(MAX) NOT NULL,
        nome NVARCHAR(255) NOT NULL,
        data_criacao DATETIME DEFAULT GETDATE(),
        ativo BIT DEFAULT 1
    );
    
    -- Criar índice para email
    CREATE INDEX idx_usuarios_email ON Usuarios(email);
    
    PRINT 'Tabela Usuarios criada com sucesso!';
END
ELSE
BEGIN
    PRINT 'Tabela Usuarios já existe.';
END

-- 2. ADICIONAR COLUNA usuario_id À TABELA Transacoes (se não existir)
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Transacoes' AND COLUMN_NAME = 'usuario_id')
BEGIN
    ALTER TABLE Transacoes ADD usuario_id INT;
    
    -- Criar referência para a tabela Usuarios
    ALTER TABLE Transacoes 
    ADD CONSTRAINT FK_Transacoes_Usuarios 
    FOREIGN KEY (usuario_id) REFERENCES Usuarios(id) ON DELETE CASCADE;
    
    -- Criar índice para usuario_id para melhorar performance
    CREATE INDEX idx_transacoes_usuario_id ON Transacoes(usuario_id);
    
    PRINT 'Coluna usuario_id adicionada à tabela Transacoes com sucesso!';
END
ELSE
BEGIN
    PRINT 'Coluna usuario_id já existe na tabela Transacoes.';
END

-- 3. VERIFICAÇÃO FINAL
SELECT 'Tabela Usuarios:' AS Info;
SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'Usuarios'
ORDER BY ORDINAL_POSITION;

SELECT 'Tabela Transacoes (colunas relevantes):' AS Info;
SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'Transacoes' 
AND COLUMN_NAME IN ('id', 'usuario_id', 'descricao', 'valor', 'tipo', 'categoria_id', 'data_transacao')
ORDER BY ORDINAL_POSITION;

PRINT 'Migrações concluídas com sucesso!';
