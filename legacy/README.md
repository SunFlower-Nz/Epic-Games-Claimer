# 📦 Arquivos Antigos / Descontinuados

Esta pasta contém arquivos da versão anterior do projeto que foram substituídos durante a refatoração para a v2.0.0.

## Arquivos Descontinuados

| Arquivo | Motivo | Substituído Por |
|---------|--------|-----------------|
| `epic_games_claimer.py` | Monolítico (~1.2k linhas) | `src/` (modular) |
| `epic_games_claimer_backup.py` | Backup antigo | Não necessário |
| `epic_games_logger.py` | Logger simples | `src/logger.py` (aprimorado) |
| `get_cookies.py` | Script solto na raiz | `scripts/get_cookies.py` |
| `run.bat` / `run.sh` | Scripts na raiz | `scripts/run.bat` / `scripts/run.sh` |
| `install.bat` / `install.sh` | Instalação manual | Use pip install -r requirements.txt |
| `*.har` | Arquivos de debug/teste | Não necessários |

## Nova Estrutura (v2.0.0)

```
Epic-Games-Claimer/
├── main.py                    # CLI principal (entrada)
├── src/                       # Código modular
│   ├── config.py             # Configuração
│   ├── logger.py             # Logs aprimorados
│   ├── session_store.py      # Persistência
│   ├── api.py                # Cliente HTTP
│   ├── claimer.py            # Orquestração
│   └── scheduler.py          # Scheduler interno
├── scripts/                   # Scripts auxiliares
│   ├── get_cookies.py        # Extração de token
│   └── run*.bat/sh           # Scripts de execução
└── _old/                     # Este diretório
```

## Se Você Precisar Voltar

Se algo não funcionar na nova versão, você pode comparar com os arquivos antigos:

```bash
# Ver diferenças
git diff src/api.py _old/epic_games_claimer.py
```

Mas recomendamos usar a nova estrutura, que é mais limpa e mantível.

## Limpeza

Se você tiver certeza que não precisa mais desses arquivos, pode deletar toda a pasta `_old/`:

```bash
rm -r _old/        # Linux/macOS
rmdir /s _old/     # Windows
```

Ou simplesmente ignorar - eles não são usados de forma alguma.
