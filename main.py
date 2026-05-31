from fastapi import FastAPI, HTTPException, Form, Request, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
import pyodbc
import json
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel

# ==================== CONFIGURAÇÕES DE SEGURANÇA ====================

SECRET_KEY = "your-secret-key-change-this-in-production"  # IMPORTANTE: TROCAR EM PRODUÇÃO
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24 horas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# ==================== CONFIGURAÇÃO DE CONEXÃO ====================

CONN_STR = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=DESKTOP-JBCNUT6\\SQL_ROGER;"
    "Database=ControleFinanceiro;"
    "Trusted_Connection=yes;"
)

# ==================== CONTEXT MANAGER PARA BD ====================

@contextmanager
def get_db_connection():
    """Context manager para garantir fechamento seguro da conexão"""
    conn = None
    try:
        conn = pyodbc.connect(CONN_STR)
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


# ==================== MODELOS PYDANTIC ====================

class UsuarioRegistro(BaseModel):
    email: str
    senha: str
    nome: str

class UsuarioLogin(BaseModel):
    email: str
    senha: str


# ==================== FUNÇÕES DE AUTENTICAÇÃO ====================

def hash_password(password: str) -> str:
    """Hash uma senha usando bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: Optional[str] = Cookie(None)) -> str:
    """Verifica o token JWT e retorna o email do usuário"""
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expirado ou inválido")

def get_usuario_id_by_email(email: str) -> int:
    """Obtém o ID do usuário pelo email"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Usuarios WHERE email = ?", email)
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        return result[0]

def usuario_existe(email: str) -> bool:
    """Verifica se um usuário já existe"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Usuarios WHERE email = ?", email)
        return cursor.fetchone() is not None


# ==================== ROTAS DE AUTENTICAÇÃO ====================

@app.get("/login", response_class=HTMLResponse)
def login_page(message: Optional[str] = None):
    """Página de login"""
    error_html = f'<div style="background: #ff3b3b; color: #fff; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; text-align: center;">{message}</div>' if message else ""
    
    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Finance Master Pro</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            
            body {{
                font-family: 'Inter', 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #0b0c10 0%, #1f2833 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                color: #fff;
            }}
            
            .auth-container {{
                background: #1f2833;
                padding: 2rem;
                border-radius: 0.8rem;
                border: 1px solid #2f3e46;
                width: 100%;
                max-width: 400px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            }}
            
            .auth-header {{
                text-align: center;
                margin-bottom: 2rem;
            }}
            
            .auth-header h1 {{
                color: #45f3ff;
                font-size: 1.8rem;
                margin-bottom: 0.5rem;
            }}
            
            .auth-header p {{
                color: #95a5a6;
                font-size: 0.9rem;
            }}
            
            .form-group {{
                margin-bottom: 1.5rem;
            }}
            
            .form-group label {{
                display: block;
                font-size: 0.85rem;
                font-weight: 600;
                text-transform: uppercase;
                color: #95a5a6;
                margin-bottom: 0.5rem;
            }}
            
            .form-group input {{
                width: 100%;
                padding: 0.75rem;
                background: #11161d;
                color: #fff;
                border: 1px solid #2f3e46;
                border-radius: 0.35rem;
                font-size: 0.95rem;
                transition: border-color 0.3s;
            }}
            
            .form-group input:focus {{
                outline: none;
                border-color: #45f3ff;
                box-shadow: 0 0 5px rgba(69, 243, 255, 0.3);
            }}
            
            .btn-login {{
                width: 100%;
                padding: 0.85rem;
                background: linear-gradient(135deg, #45f3ff 0%, #02f78e 100%);
                color: #000;
                border: none;
                border-radius: 0.35rem;
                font-weight: 700;
                font-size: 1rem;
                cursor: pointer;
                transition: transform 0.2s;
                margin-top: 1rem;
            }}
            
            .btn-login:hover {{
                transform: translateY(-2px);
            }}
            
            .auth-link {{
                text-align: center;
                margin-top: 1.5rem;
                font-size: 0.9rem;
            }}
            
            .auth-link a {{
                color: #45f3ff;
                text-decoration: none;
                font-weight: 600;
            }}
            
            .auth-link a:hover {{
                text-decoration: underline;
            }}
            
            .error-message {{
                background: #ff3b3b;
                color: #fff;
                padding: 1rem;
                border-radius: 0.5rem;
                margin-bottom: 1rem;
                text-align: center;
                font-size: 0.9rem;
            }}
        </style>
    </head>
    <body>
        <div class="auth-container">
            <div class="auth-header">
                <h1><i class="fas fa-wallet"></i> Finance Master Pro</h1>
                <p>Acesse sua conta</p>
            </div>
            
            {error_html}
            
            <form action="/web/login" method="POST">
                <div class="form-group">
                    <label for="email">E-mail</label>
                    <input type="email" id="email" name="email" placeholder="seu@email.com" required>
                </div>
                
                <div class="form-group">
                    <label for="senha">Senha</label>
                    <input type="password" id="senha" name="senha" placeholder="••••••••" required>
                </div>
                
                <button type="submit" class="btn-login">Entrar</button>
            </form>
            
            <div class="auth-link">
                Não tem conta? <a href="/cadastro">Crie uma agora</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/web/login")
def login(email: str = Form(...), senha: str = Form(...)):
    """Processa login do usuário"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, senha_hash FROM Usuarios WHERE email = ?", email)
        usuario = cursor.fetchone()
        
        if not usuario or not verify_password(senha, usuario[1]):
            return RedirectResponse(url="/login?message=Email ou senha inválidos", status_code=303)
        
        # Cria token JWT
        access_token = create_access_token(data={"sub": email})
        
        # Redireciona para dashboard com token no cookie
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="token", value=access_token, httponly=True, max_age=86400)
        return response


@app.get("/cadastro", response_class=HTMLResponse)
def cadastro_page(message: Optional[str] = None):
    """Página de cadastro"""
    error_html = f'<div class="error-message">{message}</div>' if message else ""
    
    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cadastro - Finance Master Pro</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            
            body {{
                font-family: 'Inter', 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #0b0c10 0%, #1f2833 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                color: #fff;
            }}
            
            .auth-container {{
                background: #1f2833;
                padding: 2rem;
                border-radius: 0.8rem;
                border: 1px solid #2f3e46;
                width: 100%;
                max-width: 400px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            }}
            
            .auth-header {{
                text-align: center;
                margin-bottom: 2rem;
            }}
            
            .auth-header h1 {{
                color: #45f3ff;
                font-size: 1.8rem;
                margin-bottom: 0.5rem;
            }}
            
            .auth-header p {{
                color: #95a5a6;
                font-size: 0.9rem;
            }}
            
            .form-group {{
                margin-bottom: 1.5rem;
            }}
            
            .form-group label {{
                display: block;
                font-size: 0.85rem;
                font-weight: 600;
                text-transform: uppercase;
                color: #95a5a6;
                margin-bottom: 0.5rem;
            }}
            
            .form-group input {{
                width: 100%;
                padding: 0.75rem;
                background: #11161d;
                color: #fff;
                border: 1px solid #2f3e46;
                border-radius: 0.35rem;
                font-size: 0.95rem;
                transition: border-color 0.3s;
            }}
            
            .form-group input:focus {{
                outline: none;
                border-color: #45f3ff;
                box-shadow: 0 0 5px rgba(69, 243, 255, 0.3);
            }}
            
            .btn-cadastro {{
                width: 100%;
                padding: 0.85rem;
                background: linear-gradient(135deg, #02f78e 0%, #45f3ff 100%);
                color: #000;
                border: none;
                border-radius: 0.35rem;
                font-weight: 700;
                font-size: 1rem;
                cursor: pointer;
                transition: transform 0.2s;
                margin-top: 1rem;
            }}
            
            .btn-cadastro:hover {{
                transform: translateY(-2px);
            }}
            
            .auth-link {{
                text-align: center;
                margin-top: 1.5rem;
                font-size: 0.9rem;
            }}
            
            .auth-link a {{
                color: #45f3ff;
                text-decoration: none;
                font-weight: 600;
            }}
            
            .auth-link a:hover {{
                text-decoration: underline;
            }}
            
            .error-message {{
                background: #ff3b3b;
                color: #fff;
                padding: 1rem;
                border-radius: 0.5rem;
                margin-bottom: 1rem;
                text-align: center;
                font-size: 0.9rem;
            }}
        </style>
    </head>
    <body>
        <div class="auth-container">
            <div class="auth-header">
                <h1><i class="fas fa-wallet"></i> Finance Master Pro</h1>
                <p>Crie sua conta</p>
            </div>
            
            {error_html}
            
            <form action="/web/cadastro" method="POST">
                <div class="form-group">
                    <label for="nome">Nome Completo</label>
                    <input type="text" id="nome" name="nome" placeholder="Seu nome" required>
                </div>
                
                <div class="form-group">
                    <label for="email">E-mail</label>
                    <input type="email" id="email" name="email" placeholder="seu@email.com" required>
                </div>
                
                <div class="form-group">
                    <label for="senha">Senha</label>
                    <input type="password" id="senha" name="senha" placeholder="••••••••" minlength="6" required>
                </div>
                
                <button type="submit" class="btn-cadastro">Criar Conta</button>
            </form>
            
            <div class="auth-link">
                Já tem conta? <a href="/login">Faça login</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/web/cadastro")
def cadastro(nome: str = Form(...), email: str = Form(...), senha: str = Form(...)):
    """Processa cadastro de novo usuário"""
    
    # Validações básicas
    if len(senha) < 6:
        return RedirectResponse(url="/cadastro?message=Senha deve ter pelo menos 6 caracteres", status_code=303)
    
    if usuario_existe(email):
        return RedirectResponse(url="/cadastro?message=Email já cadastrado", status_code=303)
    
    # Insere novo usuário
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            senha_hash = hash_password(senha)
            cursor.execute(
                "INSERT INTO Usuarios (email, senha_hash, nome) VALUES (?, ?, ?)",
                email, senha_hash, nome
            )
            conn.commit()
        
        return RedirectResponse(url="/login?message=Cadastro realizado com sucesso! Faça login", status_code=303)
    except Exception as e:
        return RedirectResponse(url="/cadastro?message=Erro ao criar conta. Tente novamente", status_code=303)

@app.get("/logout")
def logout():
    """Faz logout do usuário"""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="token")
    return response




# ==================== ROTAS PROTEGIDAS DO DASHBOARD ====================

@app.get("/", response_class=HTMLResponse)
def dashboard_executivo(
    edit_id: int = None, 
    data_inicio: str = None, 
    data_fim: str = None,
    token: Optional[str] = Cookie(None)
):
    """Dashboard principal - protegido por autenticação"""
    
    # Verifica autenticação
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        email = verify_token(token)
        usuario_id = get_usuario_id_by_email(email)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    hoje = datetime.today()
    hoje_str = hoje.strftime('%Y-%m-%d')
    
    if not data_inicio or data_inicio.strip() == "":
        data_inicio = hoje_str
    if not data_fim or data_fim.strip() == "":
        data_fim = hoje_str

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Resumo Financeiro Geral Filtrado pelo Dia/Período (Ignora Poupança) - APENAS DADOS DO USUÁRIO
        cursor.execute("""
            SELECT SUM(t.valor) 
            FROM Transacoes t
            JOIN Categorias c ON t.categoria_id = c.id
            WHERE t.tipo = 'Receita' 
              AND t.data_transacao BETWEEN ? AND ?
              AND LOWER(TRIM(c.nome)) <> 'poupança/reserva'
              AND t.usuario_id = ?
        """, data_inicio, data_fim, usuario_id)
        total_receitas = float(cursor.fetchone()[0] or 0.0)
        
        # Receitas destinadas à Poupança no período
        cursor.execute("""
            SELECT SUM(t.valor) 
            FROM Transacoes t
            JOIN Categorias c ON t.categoria_id = c.id
            WHERE t.tipo = 'Receita' 
              AND t.data_transacao BETWEEN ? AND ?
              AND LOWER(TRIM(c.nome)) = 'poupança/reserva'
              AND t.usuario_id = ?
        """, data_inicio, data_fim, usuario_id)
        receitas_poupanca = float(cursor.fetchone()[0] or 0.0)
        
        cursor.execute("""
            SELECT SUM(t.valor) 
            FROM Transacoes t
            WHERE t.tipo = 'Despesa' 
              AND t.data_transacao BETWEEN ? AND ?
              AND t.usuario_id = ?
        """, data_inicio, data_fim, usuario_id)
        total_despesas = float(cursor.fetchone()[0] or 0.0)
        
        saldo = total_receitas - total_despesas - receitas_poupanca
        
        # 2. Saldo Total da Poupança (Acumulado Histórico)
        cursor.execute("""
            SELECT SUM(
                CASE 
                    WHEN LOWER(TRIM(t.tipo)) = 'receita' THEN t.valor 
                    WHEN LOWER(TRIM(t.tipo)) = 'despesa' THEN -t.valor 
                    ELSE 0 
                END
            )
            FROM Transacoes t 
            JOIN Categorias c ON t.categoria_id = c.id 
            WHERE LOWER(TRIM(c.nome)) = 'poupança/reserva'
              AND t.usuario_id = ?
        """, usuario_id)
        total_poupanca = float(cursor.fetchone()[0] or 0.0)
        
        # 3. Dados Gráfico 1: Rosca (Gastos por Categoria - Ignora Poupança)
        cursor.execute("""
            SELECT c.nome, SUM(t.valor) 
            FROM Transacoes t 
            JOIN Categorias c ON t.categoria_id = c.id 
            WHERE t.tipo = 'Despesa' 
              AND t.data_transacao BETWEEN ? AND ?
              AND LOWER(TRIM(c.nome)) <> 'poupança/reserva'
              AND t.usuario_id = ?
            GROUP BY c.nome
        """, data_inicio, data_fim, usuario_id)
        resumo_gastos = cursor.fetchall()
        labels_rosca = [r[0] for r in resumo_gastos]
        values_rosca = [float(r[1]) for r in resumo_gastos]

        # 4. Dados Gráfico 2: Ranking Top 5
        cursor.execute("""
            SELECT TOP 5 c.nome, SUM(t.valor) 
            FROM Transacoes t 
            JOIN Categorias c ON t.categoria_id = c.id 
            WHERE t.tipo = 'Despesa' 
              AND t.data_transacao BETWEEN ? AND ?
              AND LOWER(TRIM(c.nome)) <> 'poupança/reserva'
              AND t.usuario_id = ?
            GROUP BY c.nome 
            ORDER BY SUM(t.valor) DESC
        """, data_inicio, data_fim, usuario_id)
        ranking = cursor.fetchall()
        labels_rank = [r[0] for r in ranking]
        values_rank = [float(r[1]) for r in ranking]

        # 5. Histórico de Transações do Período
        cursor.execute("""
            SELECT t.id, t.descricao, t.valor, t.tipo, c.nome, CONVERT(VARCHAR, t.data_transacao, 103) 
            FROM Transacoes t 
            JOIN Categorias c ON t.categoria_id = c.id 
            WHERE t.data_transacao BETWEEN ? AND ?
              AND t.usuario_id = ?
            ORDER BY t.data_transacao DESC, t.id DESC
        """, data_inicio, data_fim, usuario_id)
        historico = cursor.fetchall()
        
        # Busca lista de categorias
        cursor.execute("SELECT id, nome FROM Categorias ORDER BY nome")
        categorias_lista = cursor.fetchall()

        edit_item = None
        if edit_id:
            cursor.execute(
                "SELECT id, descricao, valor, tipo, categoria_id, data_transacao FROM Transacoes WHERE id = ? AND usuario_id = ?", 
                edit_id, usuario_id
            )
            edit_item = cursor.fetchone()

    data_padrao_form = edit_item[5].strftime('%Y-%m-%d') if edit_item else hoje_str

    # Geração das linhas da tabela dinamicamente para evitar conflito com chaves da f-string
    linhas_tabela = ""
    for t in historico:
        cor_tipo = "var(--success)" if t[3] == "Receita" else "var(--danger)"
        linhas_tabela += f"""
        <tr>
            <td>{t[5]}</td>
            <td>{t[1]}</td>
            <td>{t[4]}</td>
            <td style="color:{cor_tipo}">{t[3]}</td>
            <td>R$ {float(t[2]):,.2f}</td>
            <td class="action-icons">
                <a href="/?edit_id={t[0]}&data_inicio={data_inicio}&data_fim={data_fim}" class="icon-edit"><i class="fas fa-edit"></i></a>
                <a href="/web/deletar/{t[0]}" class="icon-del" onclick="return confirm('Excluir este lançamento?')"><i class="fas fa-trash"></i></a>
            </td>
        </tr>
        """

    # Geração das opções de categoria dinamicamente
    opcoes_categorias = "".join([
        f'<option value="{c[0]}" {"selected" if edit_item and edit_item[4]==c[0] else ""}>{c[1]}</option>' 
        for c in categorias_lista
    ])

    titulo_formulario = "Editar Lançamento" if edit_item else "Novo Lançamento"
    botao_cancelar = f'<a href="/" style="display:block; text-align:center; margin-top:0.8rem; font-size:0.8rem; color:var(--danger); text-decoration:none;">Cancelar Edição</a>' if edit_item else ""

    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Finance Master Pro - Dark Mode</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {{
                --bg-main: #0b0c10;
                --bg-card: #1f2833;
                --text-main: #c5a059;
                --text-muted: #95a5a6;
                --primary: #45f3ff;
                --success: #02f78e;
                --danger: #ff3b3b;
                --orange: #ff9f43;
                --border: #2f3e46;
            }}
            
            body {{
                font-family: 'Inter', 'Segoe UI', sans-serif;
                background-color: var(--bg-main);
                margin: 0;
                color: #fff;
            }}
            
            .navbar {{
                background: #11161d;
                padding: 1.2rem 2rem;
                border-bottom: 1px solid var(--border);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .navbar h2 {{ margin: 0; font-size: 1.4rem; color: var(--primary); }}
            
            .navbar-right {{
                display: flex;
                gap: 2rem;
                align-items: center;
            }}
            
            .user-info {{
                display: flex;
                align-items: center;
                gap: 0.8rem;
                font-size: 0.9rem;
                color: var(--text-muted);
            }}
            
            .logout-btn {{
                padding: 0.5rem 1rem;
                background: var(--danger);
                color: #fff;
                border: none;
                border-radius: 0.35rem;
                cursor: pointer;
                font-size: 0.85rem;
                text-decoration: none;
                display: inline-block;
            }}
            
            .logout-btn:hover {{
                background: #ff5252;
            }}

            .main-layout {{
                max-width: 1400px;
                margin: 1.5rem auto;
                padding: 0 1.5rem;
                display: flex;
                flex-direction: column;
                gap: 1.5rem;
            }}
            
            .filter-bar {{
                background: var(--bg-card);
                padding: 1rem;
                border-radius: 0.5rem;
                border: 1px solid var(--border);
            }}
            .filter-bar form {{ display: flex; gap: 20px; align-items: center; flex-wrap: wrap; }}
            .filter-group {{ display: flex; align-items: center; gap: 10px; }}
            .filter-group label {{ font-size: 0.85rem; font-weight: bold; color: var(--text-muted); }}
            input[type="date"], input[type="text"], input[type="number"], select {{
                background: #11161d;
                color: #fff;
                border: 1px solid var(--border);
                padding: .55rem;
                border-radius: .35rem;
                box-sizing: border-box;
            }}
            input[type="date"]::-webkit-calendar-picker-indicator {{ filter: invert(1); }}
            
            .btn-filter {{
                background: var(--primary);
                color: #000;
                border: none;
                padding: .55rem 1.5rem;
                border-radius: .35rem;
                cursor: pointer;
                font-weight: bold;
            }}
            
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 1.5rem;
            }}
            .metric-card {{
                background: var(--bg-card);
                border-radius: 0.5rem;
                padding: 1.2rem;
                border: 1px solid var(--border);
                position: relative;
                overflow: hidden;
            }}
            .metric-card::before {{
                content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
            }}
            .m-receita::before {{ background: var(--success); }}
            .m-despesa::before {{ background: var(--danger); }}
            .m-saldo::before {{ background: var(--primary); }}
            .m-poupanca::before {{ background: var(--orange); }}
            
            .m-label {{ font-size: .75rem; font-weight: bold; text-transform: uppercase; color: var(--text-muted); margin-bottom: .4rem; }}
            .m-value {{ font-size: 1.4rem; font-weight: bold; }}

            .dashboard-row {{
                display: grid;
                grid-template-columns: 1fr 1fr 350px;
                gap: 1.5rem;
            }}
            .content-box {{
                background: var(--bg-card);
                border-radius: 0.5rem;
                padding: 1.5rem;
                border: 1px solid var(--border);
            }}
            .content-box h4 {{ margin: 0 0 1.2rem 0; font-size: 1rem; color: var(--text-muted); display: flex; align-items: center; gap: 8px; }}
            .chart-container {{ position: relative; height: 230px; width: 100%; }}

            .form-group {{ margin-bottom: 1rem; }}
            .form-group label {{ font-size: .8rem; color: var(--text-muted); display: block; margin-bottom: .4rem; }}
            .btn-save {{
                background: var(--success);
                color: #000;
                border: none;
                padding: .75rem;
                width: 100%;
                border-radius: .35rem;
                cursor: pointer;
                font-weight: bold;
                font-size: 0.95rem;
                margin-top: 0.5rem;
            }}

            .table-box {{
                background: var(--bg-card);
                border-radius: 0.5rem;
                padding: 1.5rem;
                border: 1px solid var(--border);
            }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ font-size: .8rem; text-transform: uppercase; padding: 1rem; border-bottom: 2px solid var(--border); text-align: left; color: var(--text-muted); }}
            td {{ padding: 1rem; border-bottom: 1px solid var(--border); font-size: .9rem; color: #e0e6ed; }}
            tr:hover td {{ background: #242f3d; }}
            
            .action-icons {{ display: flex; gap: 15px; }}
            .icon-edit {{ color: var(--primary); }} .icon-del {{ color: var(--danger); }}
        </style>
    </head>
    <body>
        <div class="navbar">
            <h2><i class="fas fa-wallet"></i> Finance Master Pro</h2>
            <div class="navbar-right">
                <div class="user-info">
                    <i class="fas fa-user-circle"></i>
                    <span>{email}</span>
                </div>
                <a href="/logout" class="logout-btn">Logout</a>
            </div>
        </div>
        
        <div class="main-layout">
            <div class="filter-bar">
                <form action="/" method="GET">
                    <div class="filter-group">
                        <label><i class="fas fa-calendar-alt"></i> De:</label>
                        <input type="date" name="data_inicio" value="{data_inicio}">
                    </div>
                    <div class="filter-group">
                        <label>Até:</label>
                        <input type="date" name="data_fim" value="{data_fim}">
                    </div>
                    <button type="submit" class="btn-filter">Filtrar Período</button>
                    <a href="/" style="font-size: 0.85rem; color: var(--primary); text-decoration: none; margin-left: auto;">Limpar Filtros</a>
                </form>
            </div>

            <div class="metrics-grid">
                <div class="metric-card m-receita"><div class="m-label">Entradas (Período)</div><div class="m-value" style="color:var(--success)">R$ {total_receitas:,.2f}</div></div>
                <div class="metric-card m-despesa"><div class="m-label">Saídas (Período)</div><div class="m-value" style="color:var(--danger)">R$ {total_despesas:,.2f}</div></div>
                <div class="metric-card m-saldo"><div class="m-label">Balanço (Período)</div><div class="m-value" style="color:var(--primary)">R$ {saldo:,.2f}</div></div>
                <div class="metric-card m-poupanca"><div class="m-label">Saldo Atual Poupança</div><div class="m-value" style="color:var(--orange)">R$ {total_poupanca:,.2f}</div></div>
            </div>

            <div class="dashboard-row">
                <div class="content-box">
                    <h4><i class="fas fa-chart-pie"></i> Distribuição de Gastos</h4>
                    <div class="chart-container"><canvas id="chartRosca"></canvas></div>
                </div>

                <div class="content-box">
                    <h4><i class="fas fa-chart-bar"></i> Maiores Despesas</h4>
                    <div class="chart-container"><canvas id="chartRanking"></canvas></div>
                </div>

                <div class="content-box">
                    <h4><i class="fas fa-plus-circle"></i> {titulo_formulario}</h4>
                    <form action="/web/salvar" method="POST">
                        <input type="hidden" name="id" value="{edit_item[0] if edit_item else ""}">
                        
                        <div class="form-group">
                            <label>Data da Transação</label>
                            <input type="date" name="data_transacao" style="width:100%" value="{data_padrao_form}" required>
                        </div>
                        <div class="form-group">
                            <label>Descrição</label>
                            <input type="text" name="descricao" style="width:100%" value="{edit_item[1] if edit_item else ""}" placeholder="Ex: Mercado, Luz..." required>
                        </div>
                        <div class="form-group">
                            <label>Valor (R$)</label>
                            <input type="number" step="0.01" name="valor" style="width:100%" value="{float(edit_item[2]) if edit_item else ""}" required>
                        </div>
                        <div class="form-group">
                            <label>Tipo</label>
                            <select name="tipo" style="width:100%">
                                <option value="Receita" {"selected" if edit_item and edit_item[3]=='Receita' else ""}>Receita (Entrada)</option>
                                <option value="Despesa" {"selected" if edit_item and edit_item[3]=='Despesa' else ""}>Despesa (Saída)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Categoria</label>
                            <select name="categoria_id" style="width:100%">
                                {opcoes_categorias}
                            </select>
                        </div>
                        <button type="submit" class="btn-save">Salvar Registro</button>
                        {botao_cancelar}
                    </form>
                </div>
            </div>

            <div class="table-box">
                <h4><i class="fas fa-list"></i> Histórico de Movimentações do Período</h4>
                <table>
                    <thead><tr><th>Data</th><th>Descrição</th><th>Categoria</th><th>Tipo</th><th>Valor</th><th>Ações</th></tr></thead>
                    <tbody>
                        {linhas_tabela}
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            Chart.defaults.color = '#95a5a6';
            Chart.defaults.borderColor = '#2f3e46';

            new Chart(document.getElementById('chartRosca'), {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(labels_rosca)},
                    datasets: [{{ 
                        data: {json.dumps(values_rosca)}, 
                        backgroundColor: ['#45f3ff', '#02f78e', '#ff3b3b', '#ff9f43', '#a55eea', '#fed330', '#4b7bec'],
                        borderWidth: 0
                    }}]
                }},
                options: {{ maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ color: '#fff' }} }} }} }}
            }});

            new Chart(document.getElementById('chartRanking'), {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels_rank)},
                    datasets: [{{
                        label: 'R$',
                        data: {json.dumps(values_rank)},
                        backgroundColor: '#45f3ff',
                        borderRadius: 4
                    }}]
                }},
                options: {{ indexAxis: 'y', maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }} }}
            }});
        </script>
    </body>
    </html>
    """



@app.get("/web/deletar/{id}")
def web_deletar(id: int, token: Optional[str] = Cookie(None)):
    """Deleta uma transação (protegido por autenticação)"""
    
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        email = verify_token(token)
        usuario_id = get_usuario_id_by_email(email)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Verifica se a transação pertence ao usuário (SEGURANÇA)
        cursor.execute("SELECT usuario_id FROM Transacoes WHERE id = ?", id)
        resultado = cursor.fetchone()
        
        if not resultado or resultado[0] != usuario_id:
            return RedirectResponse(url="/", status_code=303)
        
        # Executa a exclusão
        cursor.execute("DELETE FROM Transacoes WHERE id = ?", id)
        conn.commit()
    
    return RedirectResponse(url="/", status_code=303)


@app.post("/web/salvar")
def web_salvar(
    id: str = Form(None), 
    descricao: str = Form(...), 
    valor: float = Form(...), 
    tipo: str = Form(...), 
    categoria_id: int = Form(...),
    data_transacao: str = Form(...),
    token: Optional[str] = Cookie(None)
):
    """Salva uma transação (protegido por autenticação)"""
    
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        email = verify_token(token)
        usuario_id = get_usuario_id_by_email(email)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if id and id != "":
            # ATUALIZAR: Verifica se pertence ao usuário (SEGURANÇA)
            cursor.execute("SELECT usuario_id FROM Transacoes WHERE id = ?", id)
            resultado = cursor.fetchone()
            
            if not resultado or resultado[0] != usuario_id:
                return RedirectResponse(url="/", status_code=303)
            
            cursor.execute("""
                UPDATE Transacoes 
                SET descricao=?, valor=?, tipo=?, categoria_id=?, data_transacao=? 
                WHERE id=?
            """, descricao, valor, tipo, categoria_id, data_transacao, id)
        else:
            # INSERTAR: Adiciona usuario_id automaticamente
            cursor.execute("""
                INSERT INTO Transacoes (descricao, valor, tipo, categoria_id, data_transacao, usuario_id) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, descricao, valor, tipo, categoria_id, data_transacao, usuario_id)
        
        conn.commit()
    
    return RedirectResponse(url="/", status_code=303)