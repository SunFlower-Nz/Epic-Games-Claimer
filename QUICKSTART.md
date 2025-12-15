# 🚀 QUICK START - Epic Games Claimer v2.0

## ⚡ 30 Segundos

```bash
# 1. Clone e entre na pasta
git clone https://github.com/SunFlower-Nz/Epic-Games-Claimer.git
cd Epic-Games-Claimer

# 2. Crie ambiente virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
# ou
source .venv/bin/activate  # Linux/macOS

# 3. Instale dependências
pip install -r requirements.txt

# 4. Configure (copie e edite se necessário)
cp .env.example .env

# 5. Execute!
python main.py
```

## 📋 Comandos Principais

| Comando | O que faz |
|---------|-----------|
| `python main.py` | Resgate jogos UMA VEZ |
| `python main.py --schedule` | Loop contínuo (12:00 diariamente) |
| `python main.py --check` | Só lista jogos sem resgatar |
| `python main.py --status` | Mostra próxima execução |
| `python scripts/get_cookies.py` | Gera session.json do navegador |

## 🔑 Autenticação

### Opção 1: Automática (Recomendado)
```bash
python main.py
# Navegador abrirá automaticamente, faça login
```

### Opção 2: Token do Navegador
```bash
# 1. Abra store.epicgames.com no navegador
# 2. F12 → Application → Cookies → EPIC_EG1
# 3. Copie o valor (começa com eg1~...)
python scripts/get_cookies.py
# Cole o token
```

### Opção 3: .env (Se souber o token)
```bash
# Edit .env
EPIC_EG1=eg1~seu_token_aqui
```

## 📁 Estrutura Importante

```
src/          ← Código principal (não edite se novo)
scripts/      ← Helpers
data/         ← Seu session.json salvo aqui
logs/         ← Logs por data (logs/2025/12/15.txt)
legacy/       ← Scripts de debug e arquivos antigos (pode ignorar)
```

## 🔍 Ver Logs

```bash
# Último log (hoje)
cat logs/2025/12/15.txt  # Linux/macOS
type logs\2025\12\15.txt  # Windows

# Ou abra em editor
```

## ⚙️ Configuração

Edite `.env` para personalizar:

```env
# Horário do agendamento
SCHEDULE_HOUR=12
SCHEDULE_MINUTE=0

# Sua localização
COUNTRY=BR
LOCALE=pt-BR

# Perfil do Chrome para extração de cookies (padrão: 'Profile negao')
# Se não encontrado, usa 'Default'
CHROME_PROFILE=Profile negao

# Timeout de requisições (segundos)
TIMEOUT=30
```

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'src'"
```bash
# Certifique-se de estar na pasta raiz do projeto
cd path/to/Epic-Games-Claimer
python main.py
```

### "Token expirado"
```bash
# Gere novo token
python scripts/get_cookies.py
```

### "Não consegue conectar"
```bash
# Aumente timeout no .env
TIMEOUT=60
```

## 🎯 Casos de Uso

### Verificar agora
```bash
python main.py
```

### Deixar rodando 24/7
```bash
python main.py --schedule
# Roda para sempre, verifica às 12:00
# Feche com Ctrl+C
```

### Agendar no Windows
```bash
# Abra Task Scheduler e crie tarefa:
# Programa: python
# Argumentos: main.py --schedule
# Iniciar em: C:\path\to\Epic-Games-Claimer
```

### Agendar no Linux/macOS
```bash
crontab -e
# Adicione:
0 12 * * * cd /path/Epic-Games-Claimer && python main.py
```

## 📚 Mais Informações

- `README.md` - Guia completo
- `docs/ARCHITECTURE.md` - Estrutura técnica
- `CHANGELOG.md` - Histórico de mudanças
- `.env.example` - Todas as variáveis disponíveis

## ✅ Checklist Inicial

- [ ] Clonado o repositório
- [ ] Ambiente virtual criado e ativado
- [ ] `pip install -r requirements.txt` executado
- [ ] `.env` configurado (ou deixado padrão)
- [ ] `python main.py` testado com sucesso
- [ ] Logs aparecem em `logs/`

## 🚀 Próximos Passos

1. **Primeira execução**: `python main.py` (testa autenticação)
2. **Modo agendado**: `python main.py --schedule` (deixa rodando)
3. **Verificar logs**: Abra `logs/2025/12/15.txt`
4. **Personalizar**: Edite `.env` se necessário

---

**Need help?** Cheque a [documentação completa](README.md)
