# 🚀 QUICK START — Epic Games Claimer

## ⚡ Instalação Rápida

```bash
# 1. Clone e entre na pasta
git clone https://github.com/SunFlower-Nz/Epic-Games-Claimer.git
cd Epic-Games-Claimer

# 2. Crie ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 3. Instale dependências
pip install -r requirements.txt

# 4. Instale o Playwright
playwright install chromium

# 5. Faça login no Chrome (store.epicgames.com)

# 6. Feche o Chrome e execute!
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

### Opção 1: Automática via Chrome (Recomendado)
```bash
# 1. Faça login em store.epicgames.com no Chrome
# 2. Feche o Chrome
# 3. Execute:
python main.py
# O claimer extrairá seus cookies automaticamente via CDP
```

### Opção 2: Token Manual
```bash
# 1. Abra store.epicgames.com no navegador
# 2. F12 → Application → Cookies → EPIC_EG1
# 3. Copie o valor (começa com eg1~...)
python scripts/get_cookies.py
# Cole o token
```

### Opção 3: .env
```env
EPIC_EG1=eg1~seu_token_aqui
```

## 📁 Estrutura

```
src/          ← Código principal
scripts/      ← Helpers
data/         ← session.json salvo aqui (não versionado)
logs/         ← Logs por data (logs/YYYY/MM/DD.txt)
docs/         ← Documentação técnica
```

## ⚙️ Configuração

Copie `.env.example` para `.env` e personalize:

```env
# Horário do agendamento
SCHEDULE_HOUR=12
SCHEDULE_MINUTE=0

# Localização
COUNTRY=BR
LOCALE=pt-BR

# Perfil do Chrome (padrão: Default)
CHROME_PROFILE=Default

# Timeout de requisições (segundos)
TIMEOUT=30
```

## 🐛 Troubleshooting

### "Chrome não conecta via CDP"
```bash
# Feche todas as instâncias do Chrome antes de executar
taskkill /IM chrome.exe /F    # Windows
killall chrome                 # Linux/macOS
```

### "Token expirado"
```bash
# Faça login novamente no Chrome e reexecute
python main.py
```

### "CAPTCHA apareceu"
Resolva manualmente na janela do Chrome (o claimer aguarda até 5 min).

## 🎯 Casos de Uso

### Verificar e resgatar agora
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
```powershell
schtasks /create /tn "Epic Games Claimer" /tr "python main.py" /sc daily /st 12:00
```

### Agendar no Linux/macOS
```bash
crontab -e
# Adicione:
0 12 * * * cd /path/Epic-Games-Claimer && .venv/bin/python main.py
```

## ✅ Checklist Inicial

- [ ] Repositório clonado
- [ ] Ambiente virtual criado e ativado
- [ ] `pip install -r requirements.txt` executado
- [ ] `playwright install chromium` executado
- [ ] Login feito no Chrome (store.epicgames.com)
- [ ] `python main.py` testado com sucesso

## 📚 Mais Informações

- [README.md](README.md) — Guia completo
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Estrutura técnica
- [CHANGELOG.md](CHANGELOG.md) — Histórico de mudanças
- [.env.example](.env.example) — Todas as variáveis disponíveis
