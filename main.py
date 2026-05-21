from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import pyodbc
import json
from datetime import datetime, timedelta

app = FastAPI()

# CONFIGURAÇÃO DE CONEXÃO
CONN_STR = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=DESKTOP-JBCNUT6\\SQL_ROGER;"
    "Database=ControleFinanceiro;"
    "Trusted_Connection=yes;"
)

def get_db_connection():
    return pyodbc.connect(CONN_STR)

# --- ROTA DE EXCLUSÃO (Movida para cima para evitar conflito de leitura do FastAPI) ---
@app.get("/web/deletar/{id}")
def web_deletar(id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Executa a exclusão no banco de dados
    cursor.execute("DELETE FROM Transacoes WHERE id = ?", id)
    
    conn.commit()
    conn.close()
    
    # Redireciona limpando os filtros para atualizar os gráficos e o histórico
    return RedirectResponse(url="/", status_code=303)


@app.get("/", response_class=HTMLResponse)
def dashboard_executivo(
    edit_id: int = None, 
    data_inicio: str = None, 
    data_fim: str = None
):
    hoje = datetime.today()
    hoje_str = hoje.strftime('%Y-%m-%d')
    
    # Se não houver filtro na URL, define o período apenas para o DIA ATUAL
    if not data_inicio or data_inicio.strip() == "":
        data_inicio = hoje_str
    if not data_fim or data_fim.strip() == "":
        data_fim = hoje_str

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Resumo Financeiro Geral Filtrado pelo Dia/Período (Ignora a Categoria Poupança/Reserva)
    cursor.execute("""
        SELECT SUM(t.valor) 
        FROM Transacoes t
        JOIN Categorias c ON t.categoria_id = c.id
        WHERE t.tipo = 'Receita' 
          AND t.data_transacao BETWEEN ? AND ?
          AND LOWER(TRIM(c.nome)) <> 'poupança/reserva'
    """, data_inicio, data_fim)
    total_receitas = float(cursor.fetchone()[0] or 0.0)
    
    # Nova consulta: Receitas destinadas à Poupança no período
    cursor.execute("""
        SELECT SUM(t.valor) 
        FROM Transacoes t
        JOIN Categorias c ON t.categoria_id = c.id
        WHERE t.tipo = 'Receita' 
          AND t.data_transacao BETWEEN ? AND ?
          AND LOWER(TRIM(c.nome)) = 'poupança/reserva'
    """, data_inicio, data_fim)
    receitas_poupanca = float(cursor.fetchone()[0] or 0.0)
    
    cursor.execute("""
        SELECT SUM(t.valor) 
        FROM Transacoes t
        WHERE t.tipo = 'Despesa' 
          AND t.data_transacao BETWEEN ? AND ?
    """, data_inicio, data_fim)
    total_despesas = float(cursor.fetchone()[0] or 0.0)
    
    # O saldo agora subtrai as despesas E as transferências para poupança
    saldo = total_receitas - total_despesas - receitas_poupanca
    # 2. Saldo Total da Poupança (Acumulado Histórico - Soma Receita, Subtrai Despesa)
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
    """)
    total_poupanca = float(cursor.fetchone()[0] or 0.0)
    
    # 3. Dados Gráfico 1: Rosca (Gastos por Categoria no Período - Ignora Poupança para focar em despesas reais)
    cursor.execute("""
        SELECT c.nome, SUM(t.valor) 
        FROM Transacoes t 
        JOIN Categorias c ON t.categoria_id = c.id 
        WHERE t.tipo = 'Despesa' 
          AND t.data_transacao BETWEEN ? AND ?
          AND LOWER(TRIM(c.nome)) <> 'poupança/reserva'
        GROUP BY c.nome
    """, data_inicio, data_fim)
    resumo_gastos = cursor.fetchall()
    labels_rosca = [r[0] for r in resumo_gastos]
    values_rosca = [float(r[1]) for r in resumo_gastos]

    # 4. Dados Gráfico 2: Ranking Top 5 (Ignora Poupança)
    cursor.execute("""
        SELECT TOP 5 c.nome, SUM(t.valor) 
        FROM Transacoes t 
        JOIN Categorias c ON t.categoria_id = c.id 
        WHERE t.tipo = 'Despesa' 
          AND t.data_transacao BETWEEN ? AND ?
          AND LOWER(TRIM(c.nome)) <> 'poupança/reserva'
        GROUP BY c.nome 
        ORDER BY SUM(t.valor) DESC
    """, data_inicio, data_fim)
    ranking = cursor.fetchall()
    labels_rank = [r[0] for r in ranking]
    values_rank = [float(r[1]) for r in ranking]

    # 5. Histórico de Transações do Período (Mantém a exibição da Poupança na tabela para controle do histórico)
    cursor.execute("""
        SELECT t.id, t.descricao, t.valor, t.tipo, c.nome, CONVERT(VARCHAR, t.data_transacao, 103) 
        FROM Transacoes t 
        JOIN Categorias c ON t.categoria_id = c.id 
        WHERE t.data_transacao BETWEEN ? AND ?
        ORDER BY t.data_transacao DESC, t.id DESC
    """, data_inicio, data_fim)
    historico = cursor.fetchall()
    
    # Busca a lista de categorias ordenada alfabeticamente para o formulário
    cursor.execute("SELECT id, nome FROM Categorias ORDER BY nome")
    categorias_lista = cursor.fetchall()

    edit_item = None
    if edit_id:
        cursor.execute("SELECT id, descricao, valor, tipo, categoria_id, data_transacao FROM Transacoes WHERE id = ?", edit_id)
        edit_item = cursor.fetchone()

    conn.close()

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
            <span style="color: var(--text-muted); font-size: 0.85rem;"><i class="fas fa-circle" style="color: var(--success); font-size: 0.6rem;"></i> Banco de Dados Conectado</span>
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

@app.post("/web/salvar")
def web_salvar(
    id: str = Form(None), 
    descricao: str = Form(...), 
    valor: float = Form(...), 
    tipo: str = Form(...), 
    categoria_id: int = Form(...),
    data_transacao: str = Form(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    if id and id != "":
        cursor.execute("""
            UPDATE Transacoes 
            SET descricao=?, valor=?, tipo=?, categoria_id=?, data_transacao=? 
            WHERE id=?
        """, descricao, valor, tipo, categoria_id, data_transacao, id)
    else:
        cursor.execute("""
            INSERT INTO Transacoes (descricao, valor, tipo, categoria_id, data_transacao) 
            VALUES (?, ?, ?, ?, ?)
        """, descricao, valor, tipo, categoria_id, data_transacao)
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)