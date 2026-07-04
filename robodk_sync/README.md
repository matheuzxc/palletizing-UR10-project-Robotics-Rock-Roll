# Sync RoboDK ↔ IDE

Sincroniza os **programas Python (macros)** da estação aberta no RoboDK com arquivos
`.py` editáveis na IDE, nos dois sentidos.

## Requisitos
- RoboDK **aberto** com a estação desejada em foco.
- Usar o Python embutido do RoboDK (já traz o pacote `robodk`):
  `C:/RoboDK/Python-Embedded/python.exe`

## Comandos

```powershell
# RoboDK -> IDE  (extrai os macros para programs/*.py)
& "C:/RoboDK/Python-Embedded/python.exe" sync_robodk.py pull

# IDE -> RoboDK  (reimporta os .py de volta na estação)
& "C:/RoboDK/Python-Embedded/python.exe" sync_robodk.py push

# ...e salva o arquivo .rdk depois de enviar
& "C:/RoboDK/Python-Embedded/python.exe" sync_robodk.py push --save

# Mostra o estado (o que está na estação x o que está em disco)
& "C:/RoboDK/Python-Embedded/python.exe" sync_robodk.py status
```

## Fluxo de trabalho
1. `pull` uma vez para trazer os macros da estação para `programs/`.
2. Edite os `.py` na IDE normalmente.
3. `push --save` para devolver as alterações ao RoboDK e gravar a estação.

## Como funciona
- **pull:** lê o código de cada item tipo *Python Program* (tipo 10) via API
  (`item.setParam("Code")`) e grava em `programs/<nome>.py`. O mapeamento
  nome-do-macro → arquivo fica em `programs/_manifest.json`.
- **push:** para cada `programs/*.py`, remove o macro de mesmo nome e reimporta o
  arquivo com `RDK.AddFile(...)`. As chamadas por nome (Program call) continuam válidas.

## Observações
- Só sincroniza **macros Python** (tipo 10). Programas de instruções (MoveJ, Program
  call, etc. — tipo 8) **não** são tocados: o "código" deles é gerado automaticamente
  e não deve ser reenviado.
- O erro "Cannot find module robolink" que a IDE mostra é só o linter usando o seu
  Python 3.10 (sem o pacote). O script roda certo com o Python embutido do RoboDK.
- Para editar direto do RoboDK na sua IDE: RoboDK → *Tools ▸ Options ▸ Other ▸
  Text editor* e aponte para o executável do VS Code.
