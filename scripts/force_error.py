from src.logger import Logger

l = Logger()
try:
    raise RuntimeError('erro de teste forçado')
except Exception as e:
    l.error('Teste de log de erro forçado', exc=e)
