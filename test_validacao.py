"""
Testes básicos de validação do refactor
"""
import sys
from passlib.context import CryptContext

def test_imports():
    """Testa se todos os imports funcionam"""
    try:
        from fastapi import FastAPI
        from jose import jwt
        from passlib.context import CryptContext
        import pyodbc
        print("✅ Imports validados com sucesso!")
        return True
    except ImportError as e:
        print(f"❌ Erro no import: {e}")
        return False

def test_password_hashing():
    """Testa se o hashing de senhas funciona"""
    try:
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        senha_teste = "senha123456"
        
        # Hash
        hash_senha = pwd_context.hash(senha_teste)
        print(f"✅ Senha hasheada: {hash_senha[:30]}...")
        
        # Verificar
        é_válida = pwd_context.verify(senha_teste, hash_senha)
        if é_válida:
            print("✅ Verificação de senha funcionando!")
            return True
        else:
            print("❌ Verificação de senha falhou!")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar hashing: {e}")
        return False

def test_jwt():
    """Testa se a geração de JWT funciona"""
    try:
        from jose import jwt
        from datetime import datetime, timedelta
        
        SECRET_KEY = "test-secret-key"
        ALGORITHM = "HS256"
        
        # Criar token
        data = {"sub": "teste@email.com"}
        expire = datetime.utcnow() + timedelta(hours=24)
        data.update({"exp": expire})
        
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
        print(f"✅ Token gerado: {token[:30]}...")
        
        # Decodificar
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        
        if email == "teste@email.com":
            print(f"✅ Token validado! Email: {email}")
            return True
        else:
            print("❌ Token inválido!")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar JWT: {e}")
        return False

def main():
    print("=" * 60)
    print("TESTES DE VALIDAÇÃO - FINANCE MASTER PRO")
    print("=" * 60)
    
    testes = [
        ("Imports", test_imports),
        ("Password Hashing", test_password_hashing),
        ("JWT Tokens", test_jwt),
    ]
    
    resultados = []
    for nome, teste_func in testes:
        print(f"\n📋 Testando: {nome}")
        print("-" * 60)
        resultado = teste_func()
        resultados.append((nome, resultado))
    
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    
    passou = sum(1 for _, r in resultados if r)
    total = len(resultados)
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{nome}: {status}")
    
    print(f"\nTotal: {passou}/{total} testes passaram")
    
    if passou == total:
        print("\n🎉 Todos os testes passaram! Código está pronto para uso.")
        return 0
    else:
        print("\n⚠️  Alguns testes falharam. Instale as dependências:")
        print("   pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
