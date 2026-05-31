# Guia de Implementação - Finance Master Pro Refatorado

## 📌 Passo 1: Preparar Dependências

### 1.1 Instalar pacotes Python

```bash
cd c:\Users\ROGER\Desktop\financeiroAcad
pip install -r requirements.txt
```

Dependências principais instaladas:
- ✅ fastapi, uvicorn (framework web)
- ✅ pyodbc (conexão SQL Server)
- ✅ **passlib, bcrypt** (hashing de senhas)
- ✅ **python-jose[cryptography]** (tokens JWT)

### 1.2 Verificar instalação

```bash
python test_validacao.py
```

Esperado: "Todos os testes passaram! Código está pronto para uso."

---

## 📌 Passo 2: Preparar Banco de Dados

### 2.1 Executar migrations SQL

1. Abra **SQL Server Management Studio**
2. Conecte ao servidor: `DESKTOP-JBCNUT6\SQL_ROGER`
3. Abra o arquivo: `MIGRACAO_BANCO_DADOS.sql`
4. Clique **Execute** (F5)

**Resultado esperado:**
```
Tabela Usuarios criada com sucesso!
Coluna usuario_id adicionada à tabela Transacoes com sucesso!
Migrações concluídas com sucesso!
```

### 2.2 Verificar estrutura

```sql
-- Verificar Usuarios
SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'Usuarios'

-- Verificar Transacoes com usuario_id
SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'Transacoes' 
AND COLUMN_NAME IN ('id', 'usuario_id', 'descricao', 'valor')
```

---

## 📌 Passo 3: Configurar Aplicação

### 3.1 Verificar STRING DE CONEXÃO

Em `main.py`, linha ~28:

```python
CONN_STR = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=DESKTOP-JBCNUT6\\SQL_ROGER;"  # ✅ Verifique este valor
    "Database=ControleFinanceiro;"         # ✅ Verifique este valor
    "Trusted_Connection=yes;"
)
```

### 3.2 Configurar SECRET_KEY (Recomendado em produção)

Gere uma SECRET_KEY segura:

```python
import secrets
secret_key = secrets.token_urlsafe(32)
print(secret_key)
```

Depois, em `main.py`, linha ~18:

```python
SECRET_KEY = "seu-secret-key-super-seguro-aqui"  # MUDE ISTO!
```

---

## 📌 Passo 4: Iniciar Aplicação

### 4.1 Rodar servidor de desenvolvimento

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Esperado na console:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### 4.2 Acessar aplicação

```
http://localhost:8000/login
```

---

## 📌 Passo 5: Primeiro Uso

### 5.1 Criar Primeira Conta

1. Acesse `http://localhost:8000/cadastro`
2. Preencha:
   - **Nome:** Seu Nome
   - **Email:** seu@email.com
   - **Senha:** Mínimo 6 caracteres

3. Clique "Criar Conta"

**Resultado:** Redirecionado para login com mensagem de sucesso

### 5.2 Fazer Login

1. Email: seu@email.com
2. Senha: (a que cadastrou)
3. Clique "Entrar"

**Resultado:** Acessa dashboard financeiro

---

## 📌 Passo 6: Testar Funcionalidades

### 6.1 Adicionar Transação

1. Preencha o formulário à direita:
   - **Data:** Data de hoje
   - **Descrição:** "Teste de Transação"
   - **Valor:** 100.00
   - **Tipo:** Receita
   - **Categoria:** (escolha qualquer uma)

2. Clique "Salvar Registro"

**Resultado:** Transação aparece na tabela

### 6.2 Editar Transação

1. Na tabela, clique no ícone de edição (lápis)
2. Modifique os dados
3. Clique "Salvar Registro"

**Resultado:** Dados atualizados

### 6.3 Deletar Transação

1. Na tabela, clique no ícone de lixeira
2. Confirme a exclusão
3. Clique "OK"

**Resultado:** Transação removida

### 6.4 Filtrar por Período

1. Use os calendários "De" e "Até"
2. Clique "Filtrar Período"

**Resultado:** Dashboard atualiza com dados do período

### 6.5 Logout

1. Clique no botão "Logout" (vermelho, topo direito)

**Resultado:** Redirecionado para /login

---

## 📌 Passo 7: Testar Isolamento de Dados

### 7.1 Criar Segunda Conta

1. Clique "Logout"
2. Vá para `/cadastro`
3. Cadastre: `outro@email.com`

### 7.2 Adicionar Transação no Segundo Usuário

1. Faça login com `outro@email.com`
2. Adicione uma transação diferente: "Segunda Conta - R$ 200"

### 7.3 Verificar Isolamento

1. Logout do segundo usuário
2. Login com primeira conta (`seu@email.com`)
3. ✅ Verificar: Vê apenas sua transação (R$ 100)
4. NÃO vê a transação da segunda conta (R$ 200)

---

## 📌 Passo 8: Testar Segurança

### 8.1 Tentar Acessar sem Token

1. Limpe os cookies do navegador
2. Vá para `http://localhost:8000/`

**Resultado Esperado:** Redireciona para `/login`

### 8.2 Tentar Usar Token Expirado

Tokens expiram após **24 horas**:
1. Espere 24 horas (ou altere o código para 1 minuto no teste)
2. Tente atualizar a página

**Resultado Esperado:** Redireciona para `/login`

### 8.3 Tentar Acessar Dados de Outro Usuário

Tecnicamente seguro (frontend não permite, backend valida):
- Mesmo se alguém modificar a URL `/web/deletar/1` de outro usuário
- Backend verifica propriedade: `SELECT usuario_id FROM Transacoes WHERE id = ?`
- Se `usuario_id != usuario_logado`, rejeita ✅

---

## 📌 Passo 9: Monitorar Logs

### 9.1 Console de Desenvolvimento

Verifique a console onde rodou `uvicorn`:

```
INFO:     127.0.0.1:12345 "POST /web/login HTTP/1.1" 303 See Other
INFO:     127.0.0.1:12346 "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:12347 "POST /web/salvar HTTP/1.1" 303 See Other
```

### 9.2 Adicionar Logging (Opcional)

Em `main.py`, adicione no início:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Depois, em cada rota:
logger.info(f"Login do usuário: {email}")
logger.error(f"Erro ao deletar transação: {id}")
```

---

## 📌 Passo 10: Deploy (Produção)

### 10.1 Mudar para Modo Produção

```bash
# Em desenvolvimento
uvicorn main:app --reload

# Em produção (use Gunicorn)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

### 10.2 HTTPS em Produção

Em produção, SEMPRE use HTTPS:
- Use Let's Encrypt (certbot)
- Configure reverse proxy (nginx)
- Mude `SECRET_KEY` para ambiente variável

### 10.3 Backup do Banco

```sql
-- Backup automático do BD
BACKUP DATABASE [ControleFinanceiro] 
TO DISK = 'C:\Backups\ControleFinanceiro.bak'
WITH FORMAT, MEDIANAME = 'Monthly Backup'
```

---

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| `ModuleNotFoundError: No module named 'fastapi'` | `pip install -r requirements.txt` |
| `Connection refused` ao conectar BD | Verifique SQL Server está rodando |
| `Email já cadastrado` | Use outro email ou recupere senha |
| `Token expirado` | Faça logout e login novamente |
| `404 Not Found` em `/` | Certifique-se que está em `http://localhost:8000/` |
| Senha rejeitada no login | Verifique capitalização e espaços |

---

## 📊 Checklist de Implementação

- [ ] Passo 1: Dependências instaladas
- [ ] Passo 2: Banco de dados migrado
- [ ] Passo 3: STRING de conexão configurada
- [ ] Passo 4: Servidor iniciado
- [ ] Passo 5: Primeira conta criada
- [ ] Passo 6: Funcionalidades testadas
- [ ] Passo 7: Isolamento de dados verificado
- [ ] Passo 8: Segurança testada
- [ ] Passo 9: Logs monitorados
- [ ] Passo 10: Pronto para produção ✅

---

## 📞 Referências

- FastAPI: https://fastapi.tiangolo.com/
- Passlib: https://passlib.readthedocs.io/
- Python-JOSE: https://python-jose.readthedocs.io/
- pyodbc: https://pyodbc.github.io/

---

**Status: ✅ Pronto para Uso**

Qualquer dúvida, revise o código em `main.py` ou consulte a documentação oficial dos pacotes.
