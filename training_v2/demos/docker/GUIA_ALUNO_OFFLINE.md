# Deploy offline da demo Docker — guia do aluno

Este roteiro instala o runtime e a imagem já pronta em uma QB560D-EU com o firmware do treinamento. **Não precisa de Internet na caixa, apt, registry ou build.** A comunicação de preparação usa USB/ADB.

## Antes de começar

- Windows x64 com Python 3 instalado e o driver USB da caixa funcionando. Os testes do host usaram Python 3.12; os scripts usam biblioteca padrão e sintaxe compatível com Python 3.8+.
- Uma caixa ligada, um cabo de dados USB e pelo menos **2 GiB livres em `/opt`** no target.
- Usuário Linux **root** e senha do firmware fornecida pelo instrutor. O programa solicita a senha sem eco; não a coloque em um comando ou arquivo.
- O ZIP completo extraído. Não execute os arquivos de dentro da janela do ZIP.

## 1. Abrir a pasta certa

Extraia o pacote completo do treinamento e abra `aibox_training/training_v2/demos/docker`. Nela devem aparecer `README.md`, `GUIA_ALUNO_OFFLINE.md`, `deploy-offline.ps1`, `host`, `target` e `offline`. O ADB compartilhado fica em `../../tools/platform-tools`.

No Explorador de Arquivos, abra um terminal nessa pasta. Por exemplo, clique na barra de endereço, digite `powershell` e pressione Enter. Confirme:

```powershell
Test-Path .\host\deploy_offline.py
```

O resultado precisa ser `True`. Se recebeu a árvore completa do treinamento, entre em `demos/docker`; ela contém os mesmos arquivos. Não copie o caminho do computador do instrutor. Os scripts também funcionam com espaços ou acentos no caminho.

## 2. Conectar e identificar a caixa

Conecte uma única caixa por USB:

```powershell
..\..\tools\platform-tools\adb.exe devices -l
```

A caixa deve aparecer com estado `device`. O serial `?` é esperado neste firmware. Se não aparecer, confira cabo/driver/energia antes de prosseguir. O estado USB `device` não substitui o login Linux, que será feito pelo próximo comando.

## 3. Conferir os arquivos offline

```powershell
python .\host\deploy_offline.py --validate-only
```

Esperado: `PASS_LOCAL_OFFLINE_CACHE`. Essa verificação não acessa o target nem faz downloads. Se faltar arquivo ou houver divergência de hash, extraia novamente o pacote completo.

## 4. Fazer o deploy completo

Troque somente a etiqueta da caixa, se necessário:

```powershell
python .\host\deploy_offline.py --unit-label Caixa-01
```

Quando surgir `Senha Linux da caixa para root:`, digite a senha do firmware e pressione Enter. Nada será exibido enquanto digita. O helper responde aos prompts do target e exige uid=0 antes dos comandos e transferências.

O programa executa, nesta ordem:

1. Confere os hashes do runtime e da imagem local.
2. Seleciona a caixa, faz login root e verifica a plataforma/espaço/ferramentas.
3. Envia os recursos para a pasta própria `/opt/qb560d-docker-demo`.
4. Instala e inicia o daemon Docker privado.
5. Carrega o `.tar.gz` local e confere arquitetura e ID da imagem.
6. Cria a aplicação, aguarda `healthy` e verifica HTTP 200/404.
7. Coleta os resultados no host e deixa o container executando para observação.

Também é possível usar a entrada PowerShell:

```powershell
.\deploy-offline.ps1 -UnitLabel Caixa-01
```

Ela usa a própria localização para achar os arquivos, mesmo se for chamada de outra pasta. Se o PowerShell bloquear a execução de `.ps1`, use o comando Python equivalente; não é preciso alterar a política global do computador.

## 5. Conferir o resultado

O relatório final deve mostrar:

```text
PASS_AUTHENTICATED_OFFLINE_CLASSROOM_DEPLOY
/health:    HTTP 200, status ok
/telemetry: HTTP 200, version 1.0.0, machine aarch64
/missing:   HTTP 404 esperado
```

O log identifica a caixa e a autenticação, sem guardar a senha. O recibo fica em `evidence/deployment-<UTC>.json`; a coleta fica em `evidence/collected/`. Os tempos de registro usam o computador, pois uma caixa recém-preparada pode estar com relógio antigo.

O pacote completo preserva os caminhos das evidências selecionadas. `evidence/LATEST.json` aponta para o resumo integrado; `training_v2/RELEASE.json` registra os hashes dos arquivos distribuídos.

A aplicação HTTP responde na porta 8081 da caixa. O teste é local no target e não exige IP WLAN no computador ou na caixa.

## 6. Consultar a aplicação e os logs

```powershell
python .\host\adb_control.py run --label observar-demo --command "sh /opt/qb560d-docker-demo/target/demo.sh check && sh /opt/qb560d-docker-demo/target/demo.sh logs"
```

Um helper iniciado em um novo processo faz seu próprio login e pode pedir a senha novamente. Fazer login manual em outra janela não autentica esse processo.

## 7. Parar e remover o container da demo

```powershell
python .\host\adb_control.py run --label parar-demo --command "sh /opt/qb560d-docker-demo/target/demo.sh stop"
```

A imagem e o runtime permanecem instalados para outra execução. Para fazer deploy, testar e já remover o container ao final:

```powershell
python .\host\deploy_offline.py --unit-label Caixa-01 --stop-after-test
```

Repetir o comando completo na mesma caixa é permitido. O helper só reutiliza um container ativo reconhecido como pertencente à demo e usando a imagem homologada; conflitos são recusados para inspeção.

## Mais de uma caixa no mesmo computador

Prefira uma caixa por aluno/computador. Se houver várias, o serial `?` pode se repetir; use o `transport_id` listado pelo ADB:

```powershell
python .\host\deploy_offline.py --transport-id 2 --unit-label Caixa-02
python .\host\adb_control.py --transport-id 2 run --label checar-caixa-02 --command "id -u"
```

Não reutilize um transport ID depois de desconectar/reconectar sem conferir a lista. Uma seleção ambígua falha, e uma desconexão não faz o helper escolher silenciosamente outra caixa.

## Problemas comuns

| Situação | Ação |
|---|---|
| `Test-Path` retorna `False` | Abra `training_v2/demos/docker`, com `host` e `offline`, e repita. |
| `python` não encontrado | Instale/prepare o Python do host antes da aula ou use a entrada `.ps1` se o launcher `py` estiver disponível. |
| ADB não lista a caixa | Confira cabo de dados, energia e driver USB. O cliente Windows está no pacote. |
| Login recusado | Confira a senha com o instrutor. O script não repete tentativas automaticamente. |
| Seleção ambígua | Desconecte as outras caixas ou informe `--transport-id`. |
| Hash/arquivo ausente | Reextraia o ZIP completo. Não tente compensar fazendo pull de registry. |
| Pasta/unit/container conflitante | Pare e peça inspeção ao instrutor; o script não sobrescreve uma instalação não reconhecida. |
| Docker não inicia ou HTTP falha | Consulte `evidence` e o guia completo. Registre a falha para essa caixa. |
| Caixa reiniciou | O serviço não tem autostart. Execute novamente o deploy completo para iniciar e conferir a demo. Cold boot não fazia parte do ensaio anterior. |

O guia completo, o Dockerfile, as limitações de rede/recursos e as evidências estão no [README](README.md). Outras caixas devem passar pelos mesmos testes, mesmo tendo o mesmo firmware.
