# 🔐 NOTAS DE SEGURANÇA - Finance Master Pro

## ⚠️ IMPORTANTE: Antes de Colocar em Produção

Este documento lista TODOS os pontos de segurança que devem ser revisados antes de fazer deploy.

---

## 1. SECRET_KEY - CRÍTICO 🔴

### Situação Atual
```python
SECRET_KEY = "your-secret-key-change-this-in-production"
```

### ⚠️ RISCO
- A chave é fraca e conhecida
- Tokens JWT podem ser falsificados
- **NÃO use em produção!**

### ✅ Solução
Gere uma chave segura:

```python
import secrets
chave_secreta = secrets.token_urlsafe(32)
print(chave_secreta)
# Resultado: algo como "xK7qL9m2oP5wR8sT1uV4xY9aB2cD5eF8"
```

Depois, salve em `.env`:
```
SECRET_KEY=xK7qL9m2oP5wR8sT1uV4xY9aB2cD5eF8
```

---

## 2. HTTPS/SSL - CRÍTICO 🔴

### Situação Atual
- Aplicação roda em HTTP (localhost:8000)

### ⚠️ RISCO
- Sem HTTPS, tokens são transmitidos em texto plano
- Mensagens de senha podem ser interceptadas
- Man-in-the-middle attack

### ✅ Solução em Produção

**Opção 1: Let's Encrypt (Grátis)**
```bash
# Instalar certbot
pip install certbot certbot-nginx

# Gerar certificado
certbot certonly --standalone -d seu-dominio.com

# Usar no nginx (reverse proxy)
```

**Opção 2: Cloud Provider**
- AWS: Certificate Manager (grátis)
- Azure: App Service (HTTPS automático)
- Heroku: SSL automático

---

## 3. Cookies - SEGURANÇA 🟡

### Situação Atual
```python
response.set_cookie(key="token", value=access_token, 
                   httponly=True, max_age=86400)
```

### ✅ Boas Práticas Adicionar

```python
response.set_cookie(
    key="token",
    value=access_token,
    httponly=True,
    secure=True,        # ✅ HTTPS only
    samesite="strict",  # ✅ CSRF protection
    max_age=86400,
    path="/"
)
```

---

## 4. Rate Limiting - SEGURANÇA 🟡

### ⚠️ RISCO
- Nenhuma proteção contra força bruta
- Múltiplas tentativas de login não são limitadas

### ✅ Implementar Proteção

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/web/login")
@limiter.limit("5/minute")  # Máx 5 tentativas por minuto
def login(email: str = Form(...), senha: str = Form(...)):
    # ... resto do código
```

---

## 5. CORS - SEGURANÇA 🟡

### ⚠️ RISCO
- Sem CORS configurado, aplicações JavaScript de origem diferente podem acessar a API

### ✅ Implementar CORS

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://seu-dominio.com"],  # Específico
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

## 6. SQL Injection - ✅ JÁ PROTEGIDO

### Situação
```sql
cursor.execute("SELECT * FROM Usuarios WHERE email = ?", email)
```

✅ **Está seguro!** Usa parameterized queries (prepared statements)

---

## 7. XSS (Cross-Site Scripting) - ✅ JÁ PROTEGIDO

### Situação
- Cookies têm `httponly=True`
- JavaScript não pode acessar tokens

✅ **Está seguro!**

---

## 8. CSRF (Cross-Site Request Forgery) - ✅ PARCIALMENTE

### Situação Atual
- Cookies têm `samesite` (necessário configurar)

### ✅ Melhorar

```python
response.set_cookie(
    ...
    samesite="strict",  # Protege contra CSRF
    ...
)
```

---

## 9. Validação de Entrada - ⚠️ MELHORAR

### Situação Atual
```python
@app.post("/web/cadastro")
def cadastro(nome: str, email: str, senha: str):
    if len(senha) < 6:  # ✅ Mínimo
        ...
```

### ✅ Adicionar Validações

```python
import re
from pydantic import EmailStr, validator

class UsuarioRegistro(BaseModel):
    email: EmailStr  # Valida formato de email
    senha: str
    nome: str
    
    @validator('senha')
    def senha_forte(cls, v):
        if len(v) < 8:
            raise ValueError('Senha deve ter ≥8 caracteres')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Senha deve ter letra maiúscula')
        if not re.search(r'[0-9]', v):
            raise ValueError('Senha deve ter número')
        return v
    
    @validator('nome')
    def nome_valido(cls, v):
        if len(v) < 3:
            raise ValueError('Nome deve ter ≥3 caracteres')
        return v
```

---

## 10. Logs e Auditoria - 🟡 ADICIONAR

### ⚠️ RISCO
- Nenhum log de autenticação
- Impossível detectar ataques

### ✅ Implementar Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security.log'),  # Arquivo
        logging.StreamHandler()                # Console
    ]
)
logger = logging.getLogger(__name__)

# Usar em rotas:
logger.info(f"✅ Login bem-sucedido: {email}")
logger.warning(f"⚠️  Falha de login: {email}")
logger.error(f"❌ Erro ao deletar transação: {id}")
```

---

## 11. Senhas no Banco de Dados - ✅ SEGURO

### Situação
```python
senha_hash = hash_password(senha)  # Bcrypt
cursor.execute("INSERT INTO Usuarios (senha_hash) VALUES (?)", senha_hash)
```

✅ **Seguro!** Senhas nunca são armazenadas em texto plano

---

## 12. Tokens Expirados - ✅ SEGURO

### Situação
```python
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24 horas
```

✅ **Seguro!** Tokens expiram automaticamente

---

## 13. Recuperação de Senha - 🔴 NÃO IMPLEMENTADO

### ⚠️ RISCO
- Usuário não consegue recuperar senha esquecida

### ✅ Implementar

```python
from datetime import datetime, timedelta

@app.post("/recuperar-senha")
def recuperar_senha(email: str = Form(...)):
    # 1. Verificar se email existe
    # 2. Gerar token de recuperação (JWT com exp. curta)
    # 3. Enviar por email (SMTP)
    # 4. Redirecionar para form de reset
```

---

## 14. Backups - 🟡 CONFIGURAR

### ⚠️ RISCO
- Sem backups, perda de dados é possível

### ✅ Automatizar Backups

```sql
-- Script agendado no SQL Server
BACKUP DATABASE [ControleFinanceiro] 
TO DISK = 'C:\Backups\ControleFinanceiro_$(DATE).bak'
WITH FORMAT, COMPRESSION
```

---

## 15. Variáveis de Ambiente - 🟡 CONFIGURAR

### Situação Atual
```python
CONN_STR = "Driver=... Server=DESKTOP-JBCNUT6..."
```

### ✅ Usar .env

```python
import os
from dotenv import load_dotenv

load_dotenv()

DB_SERVER = os.getenv("DB_SERVER")
DB_DATABASE = os.getenv("DB_DATABASE")
SECRET_KEY = os.getenv("SECRET_KEY")
```

Arquivo `.env`:
```
DB_SERVER=seu-servidor
DB_DATABASE=seu-database
SECRET_KEY=sua-chave-secreta
```

---

## 16. Dependências Atualizadas - 🟡 VERIFICAR

### Comando para verificar vulnerabilidades

```bash
pip install safety
safety check
```

---

## 📋 Checklist Pré-Produção

- [ ] SECRET_KEY alterada (não é padrão)
- [ ] HTTPS/SSL configurado
- [ ] Cookies com secure=True e samesite="strict"
- [ ] Rate limiting em /login
- [ ] CORS configurado para seu domínio
- [ ] Validação forte de senhas
- [ ] Logs de auditoria funcionando
- [ ] Backups automatizados
- [ ] Variáveis de ambiente .env
- [ ] Dependências atualizadas (safety check)
- [ ] Senhas em .env (não em código)
- [ ] Database password em variável
- [ ] WAF (Web Application Firewall) configurado
- [ ] Monitora logs em tempo real
- [ ] Plano de recuperação de desastres

---

## 🚨 Checklist de Resposta a Incidentes

Se seu sistema for comprometido:

1. **Imediato (Minutos)**
   - [ ] Desativar app
   - [ ] Ativar WAF
   - [ ] Revisar logs

2. **Curto Prazo (Horas)**
   - [ ] Revogar todos os tokens
   - [ ] Forçar reset de senhas
   - [ ] Contatar usuários
   - [ ] Backup de evidências

3. **Médio Prazo (Dias)**
   - [ ] Análise forense
   - [ ] Patch de segurança
   - [ ] Atualizar documentação
   - [ ] Comunicado de segurança

---

## 📞 Recursos de Segurança

### Testes de Segurança
- **OWASP ZAP**: https://www.zaproxy.org/
- **Burp Suite**: https://portswigger.net/burp
- **npm audit**: para JavaScript

### Padrões e Guidelines
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **NIST Cybersecurity**: https://www.nist.gov/
- **CWE/SANS**: https://cwe.mitre.org/

### Certificações
- **Security+**: CompTIA
- **OSCP**: Offensive Security
- **CEH**: Certified Ethical Hacker

---

## 🎓 Resumo Resumo

| Risco | Status | Ação |
|-------|--------|------|
| Secret Key fraca | 🔴 Crítico | MUDAR antes de produção |
| Sem HTTPS | 🔴 Crítico | Adicionar SSL/TLS |
| Sem rate limiting | 🟡 Alto | Implementar limiter |
| Sem logs | 🟡 Alto | Adicionar auditoria |
| CORS aberto | 🟡 Médio | Configurar domínios |
| Sem backup | 🟡 Médio | Automatizar backups |
| SQL Injection | ✅ Seguro | Já usa prepared statements |
| XSS | ✅ Seguro | httponly=True já ativa |

---

**Lembre-se:** Segurança é um processo contínuo, não um destino!

🔒 **Mantenha a aplicação atualizada e monitore logs regularmente.**
