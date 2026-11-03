# D2-03 — Docker na QB560D-EU: instalação, aplicação e deploy offline

Homologação em **01/11/2026, America/Sao_Paulo**. Evidências usam UTC. Pasta canônica desta demo no host: `demos/docker/`. Os fontes, runtime Docker, imagem offline, evidências e guia ficam aqui. A apresentação e as ferramentas ADB são compartilhadas pelo treinamento.

## 1. O que a demo faz

A demo empacota uma aplicação HTTP Python em uma imagem **Linux ARM64**, constrói essa imagem na própria QB560D, executa o container e comprova que a mesma aplicação pode ser implantada a partir de um arquivo offline.

| Endpoint | Resposta esperada |
|---|---|
| `GET /health` | HTTP 200 e `{"status":"ok"}` |
| `GET /telemetry` | HTTP 200; versão da aplicação, arquitetura, uptime do sistema e uptime do processo |
| `GET /missing` | HTTP 404, propositalmente |

A aplicação usa apenas a biblioteca padrão do Python. O container tem seu próprio userspace Python/Debian e compartilha o kernel da caixa. `system_uptime_s` vem de `/proc/uptime`; `process_uptime_s` mede o processo da aplicação. A execução usa CPU. Acesso a câmera/GPU/HTP em containers é outro ensaio.

## 2. Ambiente homologado e escolha da instalação

| Item | Valor medido |
|---|---|
| Plataforma | QB560D-EU, QCM6490, AArch64 |
| Ubuntu/kernel | 20.04.3 LTS / 5.4.219-perf |
| glibc | 2.31, medida com `getconf GNU_LIBC_VERSION` |
| Docker Engine/CLI | 29.9.2, Linux ARM64 |
| Buildx | v0.38.1 |
| containerd / runc | v2.4.2 / 1.5.2 |
| Storage driver | overlay2 sobre ext4 |
| Cgroups | v1, driver cgroupfs |
| Segurança observada | AppArmor disponível, seccomp builtin; container sem root e sem capabilities |
| Rede para preparação | WLAN; HTTPS ao repositório Docker passou |
| Raiz exclusiva no target | `/opt/qb560d-docker-demo` |
| Socket exclusivo | `unix:///run/qb560d-docker-demo/docker.sock` |
| Serviço | `qb560d-docker-demo.service`, iniciado sob demanda, autostart desabilitado |

O preflight encontrou o banco `dpkg` com diversos arquivos de controle/lista ausentes. A versão Ubuntu 20.04 também não aparece na lista atual de Ubuntu suportados pelo instalador de pacotes Docker. Para este laboratório usamos **binários estáticos oficiais** em uma árvore própria, sem instalar/reparar pacotes Ubuntu ou substituir o BSP.

O daemon usa `bridge=none`, `iptables=false`, `ip6tables=false`, `ip-forward=false` e socket Unix privado. A aplicação usa rede `host` durante a apresentação e `none` no teste offline. Bridge/NAT/port publishing não foram homologados. A instalação estática requer atualização manual; esta homologação funcional em uma unidade não substitui qualificação de produção.

## 3. Organização no host

```text
demos/docker/
  README.md                  este guia
  app/                       Dockerfile e aplicação Python
  config/                    daemon, unit systemd e digest da base
  host/                      login ADB, deploy offline, staging e coleta
  ../../tools/platform-tools/ cliente ADB compartilhado, DLLs e NOTICE
  tests/                     testes locais do protocolo de login
  deploy-offline.ps1         entrada PowerShell portátil
  GUIA_ALUNO_OFFLINE.md       passo a passo do aluno
  target/                    instalação, build, deploy e homologação
  offline/
    runtime/                 Docker e Buildx ARM64 oficiais
    runtime.lock.json        URLs, versões e hashes
    images/                  imagem exportada .tar.gz
    image.lock.json          ID da imagem, base, tamanhos e hashes
    image.sha256             checksum do arquivo deployável
  evidence/                  logs, recibos, resultados e ponteiro LATEST.json
  ../../slides/              apresentação única do treinamento
  .build/                    intermediários privados de preparação
```

A partir da revisão 1.1, o pacote também inclui login ADB e entrada portátil de deploy para o aluno.

O pacote do Docker é independente do caminho AI em `/tmp/qb560d-training`. Os dois daemons/configurações não compartilham socket com uma eventual instalação Docker do sistema. Use o wrapper `target/docker.sh` para selecionar o daemon homologado.

### 3.1. O que há dentro do pacote offline completo

O ZIP principal extrai a árvore `aibox_training/training_v2`. Esta demo fica em `demos/docker`; ferramentas e transporte ADB são compartilhados em `tools` e `host`. A imagem `.tar.gz` acompanha o pacote.

A distribuição preserva os caminhos das evidências selecionadas. O manifest principal registra os hashes; os registros históricos completos continuam no workspace do instrutor.

| Caminho/arquivo | Conteúdo | Onde é usado |
|---|---|---|
| `app/telemetry.py` | Código Python dos endpoints `/health`, `/telemetry` e tratamento de rota desconhecida | Copiado para `/app/telemetry.py` na imagem; executado no container |
| `app/Dockerfile` | Receita da imagem: base Python, COPY, usuário, porta, healthcheck e comando de partida | Build na caixa; não é necessário reconstruir para usar a imagem offline pronta |
| `offline/runtime/docker-29.9.2.tgz` | Executáveis ARM64 do Docker, containerd e runc | Instalação do motor de containers na caixa |
| `offline/runtime/buildx-v0.38.1.linux-arm64` | Plugin de build ARM64 | Construção de novas imagens, quando necessária |
| `offline/images/qb560d-telemetry-1.0.0-arm64.tar.gz` | Imagem pronta com o userspace Python/Debian e a aplicação HTTP, em 44,86 MiB | `docker load`; depois `docker run --pull never` |
| `host/fetch_runtime.py`, `stage.py`, `adb_control.py`, `collect.py`, `package.py` | Download/cache, envio ADB, execução remota, coleta e empacotamento | Executados no computador de preparação |
| `target/install.sh`, `docker.sh`, `build.sh`, `demo.sh` | Instalação, seleção do socket privado, build e operação do container | Executados no Ubuntu da caixa |
| `target/rehearse.py`, `check_http.py`, `preflight.sh` | Homologação integrada, verificação HTTP e inspeção do BSP | Executados na caixa; produzem logs e resultados |
| `config/daemon.json`, `qb560d-docker-demo.service`, `base-image.txt` | Socket/storage/rede do daemon, unit systemd e digest da base | Configuram o runtime do laboratório |
| `offline/runtime.lock.json`, `image.lock.json` | Versões, URLs/hashes dos binários e identidade da imagem homologada | Conferência de integridade/proveniência |
| `offline/runtime.sha256`, `image.sha256`, `MANIFEST.json` | Checksums e inventário de arquivos do pacote | Verificação dos artefatos antes da instalação/deploy |
| `evidence/`, `README.md`, apresentação principal | Logs reais e guia; slides centralizados na apresentação principal | Consulta e apresentação no host; não fazem parte da aplicação dentro da imagem |

O Docker Engine roda **na caixa**, fora do container da aplicação. O container usa o Python da imagem e o kernel do target. O ZIP também leva ferramentas de build e documentação que não são colocadas dentro da imagem da aplicação.

### 3.2. Como a demo se comporta

| Etapa | Comportamento observável |
|---|---|
| `stage` / `install` | O host envia os recursos; o instalador verifica os binários e inicia o daemon privado. Ainda não há aplicação em execução. |
| `demo.sh load` | Confere checksum, carrega a imagem do arquivo local, valida Linux/ARM64 e o ID esperado. Carregar uma imagem não inicia um container. |
| `demo.sh run` | Cria o container, inicia a API na porta 8081 e aguarda o healthcheck. Usa `--pull never`: imagem ausente gera erro, sem download automático. |
| `demo.sh check` | Consulta `/health` e `/telemetry` (200), confere arquitetura/versão e solicita `/missing` (404 esperado). |
| Durante a execução | A telemetria mostra versão, arquitetura e uptimes. O uptime do processo cresce enquanto a aplicação vive; o uptime do sistema acompanha o kernel da caixa. |
| `demo.sh logs` | Exibe os registros de requisições HTTP e erros da aplicação. Colete o que precisar antes de remover o container. |
| `demo.sh stop` | Para e remove apenas o container identificado como pertencente à demo. A imagem carregada e a instalação Docker permanecem disponíveis. |
| Nova execução | Um novo processo/container é criado e seu uptime recomeça. Os arquivos do tmpfs `/tmp` da execução anterior não permanecem. |

A execução normal usa a rede `host`: os testes locais consultam `127.0.0.1:8081` na caixa. O ensaio offline separado usa `--network none` e consulta HTTP por `docker exec` dentro do container; a WLAN ficou conectada. A aplicação está pronta quando o estado é `healthy` e os endpoints atendem ao contrato. Sem autostart, carregar a imagem ou reiniciar a caixa não equivale a iniciar automaticamente a aplicação.

## 4. Preparar o host e transferir para qualquer caixa do treinamento

Comece pelo [guia do aluno para deploy offline](GUIA_ALUNO_OFFLINE.md). Extraia **todo** o ZIP e abra um terminal na pasta `demos/docker` que contém este README, `host`, `offline` e `deploy-offline.ps1`. Ao usar a árvore completa do treinamento, a pasta equivalente é `demos/docker`.

Não há caminho `C:/Users/...` para copiar ou editar. Os scripts resolvem seus arquivos a partir do próprio local em disco, inclusive quando a pasta tem espaços ou acentos. O ADB Windows e suas DLLs/NOTICE estão em `../../tools/platform-tools`. É necessário ter Python 3 no host e o driver USB da caixa instalado.

Confira o conteúdo local, sem conectar ou modificar a caixa:

```powershell
python .\host\deploy_offline.py --validate-only
```

Depois conecte uma única caixa por USB e execute:

```powershell
python .\host\deploy_offline.py --unit-label Caixa-01
```

Esse comando único verifica os hashes locais, seleciona a caixa, faz o login Linux como **root**, verifica uid=0 e a plataforma, envia os arquivos, instala/inicia o Docker privado, carrega a imagem e testa HTTP. **Não faz downloads, apt, build ou pull de registry.** A senha do firmware deve ser digitada no prompt; ela não aparece na tela nem é gravada em scripts, argumentos ou evidências. O valor é fornecido pelo instrutor.

A entrada PowerShell equivalente localiza o Python e o pacote por `$PSScriptRoot`, funcionando também quando chamada de outra pasta:

```powershell
.\deploy-offline.ps1 -UnitLabel Caixa-01
```

Se a política de execução do PowerShell bloquear o `.ps1`, use o comando Python acima; não é necessário alterar uma política global. Para só validar e remover o container ao terminar, acrescente `--stop-after-test` no Python ou `-StopAfterTest` no PowerShell.

Com mais de uma caixa conectada, liste os transports e selecione explicitamente:

```powershell
..\..\tools\platform-tools\adb.exe devices -l
python .\host\deploy_offline.py --transport-id 2 --unit-label Caixa-02
```

O serial `?` pode se repetir entre caixas. O script recusa uma seleção ambígua e não muda silenciosamente para outra unidade. Use `--serial` quando houver um serial único. Em outro sistema operacional, ou para usar outro cliente, informe `--adb` com o executável compatível ou configure `QB560D_ADB` no processo.

O login ocorre dentro do `adb shell`: primeiro o cliente encontra o dispositivo USB, depois o helper responde aos prompts `login:` e `Password:` e só executa comandos após comprovar uid=0. Um login manual em outro terminal não autentica automaticamente as próximas instâncias de `adb shell`. O deploy completo mantém uma sessão autenticada; helpers manuais separados pedem a senha novamente.

`stage.py` também continua disponível para preparação avançada. Ele verifica os artefatos antes de transferir, só aceita a pasta target identificada pelo marcador `.owner` e envia `app`, `target`, `config` e `offline`. Não envia slides ou credenciais.

## 5. Instalar e iniciar o Docker

```powershell
python .\host\adb_control.py run --label install-engine --timeout 120 --command "sh /opt/qb560d-docker-demo/target/install.sh"
```

As instruções deste item são a alternativa manual ao deploy completo. O instalador verifica os hashes, extrai os binários em `runtime/docker`, instala Buildx em `client/cli-plugins`, valida `config/daemon.json` e instala a unit **exclusiva** `/etc/systemd/system/qb560d-docker-demo.service`. Uma unit existente com conteúdo diferente é recusada. Não há habilitação automática no boot.

No shell da caixa, os comandos equivalentes são:

```sh
cd /opt/qb560d-docker-demo
sh target/install.sh
sh target/docker.sh version
sh target/docker.sh info
sh target/docker.sh buildx version
```

Após reboot, os arquivos em `/opt` persistem, mas o socket em `/run` é recriado somente quando o serviço inicia:

```sh
systemctl start qb560d-docker-demo.service
```

Um cold boot desta instalação ainda não foi ensaiado; o restart do serviço e a persistência da imagem após esse restart passaram.

## 6. Fazer deploy com a imagem offline já homologada

Para o aluno, o fluxo recomendado é o comando único do item 4 e o [guia offline](GUIA_ALUNO_OFFLINE.md). Ele cobre uma caixa nova, sem Docker e sem imagem, usando somente os arquivos extraídos e o USB. Ao concluir sem `--stop-after-test`, a aplicação fica executando para observação.

Na operação manual avançada, os helpers abaixo fazem login root antes dos comandos; cada nova execução do Python abre sua própria sessão autenticada:

```powershell
python .\host\adb_control.py run --label offline-load --timeout 180 --command "sh /opt/qb560d-docker-demo/target/demo.sh load"
python .\host\adb_control.py run --label demo-run --command "sh /opt/qb560d-docker-demo/target/demo.sh run"
python .\host\adb_control.py run --label demo-check --command "sh /opt/qb560d-docker-demo/target/demo.sh check"
python .\host\adb_control.py run --label demo-logs --command "sh /opt/qb560d-docker-demo/target/demo.sh logs"
```

Esse fluxo manual pressupõe que os arquivos foram enviados e o daemon foi instalado/iniciado. O comando único evita esquecer essas etapas.

`load` verifica SHA-256 do arquivo, executa `docker load`, confere Linux/ARM64 e compara o ID carregado com `offline/image.lock.json`. `run` usa `--pull never`: a ausência da imagem gera erro, sem download. Ao repetir o deploy completo, um container em execução só é reutilizado se pertencer à demo e usar o ID da imagem homologada; um container conflitante é recusado.

Se preferir um shell manual na caixa:

```powershell
..\..\tools\platform-tools\adb.exe shell
```

Responda ao login com `root` e digite a senha quando solicitada. Então, no Ubuntu da caixa:

```sh
cd /opt/qb560d-docker-demo
systemctl start qb560d-docker-demo.service
sh target/demo.sh load
sh target/demo.sh run
sh target/demo.sh check
sh target/demo.sh logs
```

O caminho `/opt/qb560d-docker-demo` é **do target**, fixado pelo pacote e igual em cada caixa; não é um caminho do computador do instrutor.

O comando efetivo de execução da aplicação é:

```sh
sh target/docker.sh run -d --pull never --name qb560d-docker-demo \
  --network host --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 128m qb560d-telemetry:1.0.0
```

O Dockerfile define usuário `65534:65534`, aplicação na porta 8081 e healthcheck HTTP. A raiz é somente leitura; `/tmp` é um tmpfs de 16 MiB. Limites reais observados dentro do container: **134217728 bytes (128 MiB)** de memória e **64 PIDs**.

A rede host compartilha a pilha de rede da caixa. A aplicação escuta em `0.0.0.0:8081`, podendo ser acessada pela WLAN conforme regras da rede. Ela é uma API de laboratório sem autenticação. O fluxo testado verifica os endpoints em `127.0.0.1:8081` no target; acesso por navegador de outro computador não integra o critério já homologado.

```sh
curl --fail http://127.0.0.1:8081/health
curl --fail http://127.0.0.1:8081/telemetry
curl -o /dev/null -s -w '%{http_code}\n' http://127.0.0.1:8081/missing
```

O último comando deve mostrar **404**. Para terminar, removendo apenas o container reconhecido da demo:

```sh
sh target/demo.sh stop
```

## 7. Construir a imagem na própria caixa

O build online foi realizado na homologação. O pacote já contém a exportação pronta; não é necessário reconstruí-la para o deploy offline.

Em uma preparação nova, sem o arquivo exportado existente, execute:

```powershell
python .\host\adb_control.py run --label build-image --timeout 600 --command "sh /opt/qb560d-docker-demo/target/build.sh"
```

O script lê o digest fixado em `config/base-image.txt`, baixa a base oficial Python para Linux/ARM64, faz build nativo com Buildx e exporta a imagem. Os comandos centrais são:

```sh
cd /opt/qb560d-docker-demo
BASE_IMAGE=$(cat config/base-image.txt)
sh target/docker.sh pull --platform linux/arm64 "$BASE_IMAGE"
sh target/docker.sh buildx build --platform linux/arm64 --network none \
  --build-arg "BASE_IMAGE=$BASE_IMAGE" --load -t qb560d-telemetry:1.0.0 app
sh target/docker.sh image inspect qb560d-telemetry:1.0.0 --format '{{.Os}}/{{.Architecture}}'
```

A saída da inspeção deve ser `linux/arm64`. `--network none` no build restringe as etapas do build; o pull da base ainda usa Internet. O Dockerfile faz COPY e configuração, sem instalar pacotes por RUN.

Para exportar uma imagem nova, escolha um nome de arquivo novo e guarde seu hash:

```sh
sh target/docker.sh image save -o offline/images/qb560d-telemetry-1.0.0-arm64.tar qb560d-telemetry:1.0.0
gzip -n offline/images/qb560d-telemetry-1.0.0-arm64.tar
sha256sum offline/images/qb560d-telemetry-1.0.0-arm64.tar.gz
```

O script `build.sh` recusa sobrescrever a exportação já existente. `docker save/load` transporta a imagem com suas camadas e configuração; não confundir com `docker export/import`, que tem outro propósito.

## 8. Coletar o arquivo offline e as evidências no host

```powershell
python .\host\collect.py
```

O coletor copia os resultados do target, traz a imagem se ainda não existir no host, verifica seu hash e gera/atualiza os locks e `evidence/LATEST.json`. A imagem pronta para distribuição fica em:

`offline/images/qb560d-telemetry-1.0.0-arm64.tar.gz`

| Artefato homologado | Valor |
|---|---|
| Tag | `qb560d-telemetry:1.0.0` |
| ID | `sha256:e0654346d8e08cd3657544ec36d91fc50344b5ace226386d5b3fb4ac4d330021` |
| Tamanho lógico da imagem | 155045534 bytes, aproximadamente 147,86 MiB |
| Arquivo comprimido | 47037664 bytes, aproximadamente 44,86 MiB |
| SHA-256 do arquivo | `cd0c23929d9b698a1e824d1f735cad94112c9eeef6e9e1b60648e13ccc638550` |
| Base fixada | `python@sha256:94a8fee35252d06ab75856f15f12c7bae67b10e8a6da93c7fded82b2610926cd` |

## 9. Testes realizados e resultados

Resultado principal: **PASS_THREE_SESSIONS_AND_OFFLINE_DEPLOY**. O ensaio integrado registrou **61 verificações de comandos**, além das asserções de conteúdo/estado no script. A aplicação também foi executada pelos helpers finais do guia.

| Teste | Resultado observado |
|---|---|
| Instalação, versões e daemon | Docker 29.9.2 + Buildx v0.38.1 disponíveis; overlay2/ext4, cgroup v1 |
| Arquitetura | Imagem `linux/arm64`; aplicação reporta `aarch64` |
| Três ciclos independentes | Criar, aguardar healthy, testar HTTP, consultar logs, parar e remover: passaram |
| Contrato HTTP | `/health` 200, `/telemetry` 200 e versão 1.0.0, `/missing` 404 |
| Identidade/processo | UID 65534 dentro do container; processo sem root |
| Filesystem | Tentativa de escrita na raiz, mesmo via exec como UID 0, falhou com EROFS; escrita em `/tmp` passou |
| Recursos | Memória 128 MiB e limite de 64 PIDs confirmados dentro do container |
| Segurança | Capabilities removidas, no-new-privileges, AppArmor/seccomp disponíveis; detalhe nos logs de `/proc/self/status` |
| Parada | Endpoint ficou indisponível depois de parar a aplicação |
| Mudança e rollback de configuração | `APP_VERSION=1.0.0 → 1.0.1 → 1.0.0` passou, usando a mesma imagem |
| Imagem ausente | Depois de remover a tag, execução com `--pull never` foi recusada |
| Recuperação offline | Arquivo .tar.gz carregado; ID da imagem idêntico ao anterior |
| Execução sem rede | Container `--network none` ficou healthy e respondeu HTTP consultado internamente por `docker exec` |
| Persistência do daemon | Restart do serviço passou; imagem manteve o mesmo ID |
| Rotas | Saída de `ip -4 route show` igual antes/depois do ensaio integrado |
| Limpeza | Containers da homologação removidos; imagem e runtime preservados |

A WLAN permaneceu conectada durante os testes. A prova offline usa carregamento local, `--pull never` e isolamento `--network none`; não incluiu desligar fisicamente o Wi-Fi.

A mudança de `APP_VERSION` validou recriação/configuração do container. Ela não substitui um teste de atualização de binário ou migração de dados entre duas imagens diferentes.

Para repetir a homologação completa, pare a demo manual antes:

```sh
cd /opt/qb560d-docker-demo
sh target/demo.sh stop
python3 target/rehearse.py
```

Cada repetição cria uma pasta de evidência nova. Falhas são preservadas. Depois, rode `python .\host\collect.py` no host para coletar.

## 10. Adaptar para outra aplicação ou versão

1. Coloque código e arquivos de build em uma subpasta própria da nova demo. Defina os endpoints, porta, arquivos persistentes e variáveis de ambiente.
2. Adapte `app/Dockerfile`: base compatível, COPY, dependências fixadas, usuário, healthcheck e CMD. Atualize versão/label quando publicar outra versão.
3. Construa uma tag nova no target: por exemplo `qb560d-minha-app:1.0.1`, usando `--platform linux/arm64 --load`. Para dependências por RUN, prepare a rede de build necessária e valide esse fluxo separadamente.
4. Teste a imagem nova, endpoints, recursos e recuperação antes de substituir a versão em uso. Preserve a tag/arquivo da versão anterior.
5. Salve a nova imagem com `image save`, registre ID e SHA-256 e transporte o arquivo por ADB. No destino, faça `load`, confira a arquitetura e recrie o container com a tag nova.
6. Para rollback, pare/remova apenas o container da aplicação e recrie-o com a tag anterior e sua configuração compatível. Dados em volume exigem estratégia própria de backup/migração.

Evite depender de tags mutáveis sem registrar digest/ID. O exemplo atual usa filesystem raiz somente leitura e nenhum volume persistente de dados de aplicação. Docker Compose, bridge/NAT, bancos de dados e aceleradores em container ainda exigem exercícios próprios.

## 11. Diagnóstico e operação

```sh
systemctl status qb560d-docker-demo.service --no-pager
journalctl -u qb560d-docker-demo.service -n 80 --no-pager
sh /opt/qb560d-docker-demo/target/docker.sh info
sh /opt/qb560d-docker-demo/target/docker.sh ps -a
df -h /opt
```

- Socket indisponível: confira este serviço e este socket; o comando `docker` de outra instalação pode apontar para outro daemon.
- Nome de container já existe: inspecione-o; `demo.sh stop` só remove o container identificado como pertencente à demo.
- Imagem ausente: use `demo.sh load`; a execução não faz pull automático.
- Health falha: consulte logs, porta 8081 e `/health`. Portas ocupadas precisam ser resolvidas antes de executar o laboratório.
- Espaço/execução: a instalação usa `/opt`; `/data` foi observado com `noexec` nesta imagem.
- O daemon avisou que o BSP não oferece quota/período CFS de CPU nem throttling de bloco I/O. Não usar esses controles como requisito da demo. Memória e PIDs foram testados.
- Cgroup v1 e instalação estática permanecem limites desta combinação. Para produção, definir suporte/atualização com o time de BSP e a política Docker da organização.

Estado deixado após a homologação: daemon disponível sob demanda/ativo, autostart desabilitado e nenhum container da demo executando. Para parar somente o daemon do laboratório:

```sh
systemctl stop qb560d-docker-demo.service
```

## 12. Material de apresentação e agenda

Esta é a demo **D2-03**, bloco **01:20–02:00 do Dia 2**. Sugestão para 40 min: 5 min conceitos/aplicação, 10 min Dockerfile e build já preparado, 10 min deploy e endpoints, 10 min offline/isolamento e 5 min diagnóstico/perguntas.

A apresentação de aula é o [PPTX principal](../../slides/QB560D_EU_Training.pptx). Para acompanhar a prática, use o [guia offline](GUIA_ALUNO_OFFLINE.md).

## 13. Fontes e evidências

- [Binários oficiais e método de instalação Docker](https://docs.docker.com/engine/install/binaries/).
- [Versões Ubuntu atualmente suportadas pelo instalador Docker](https://docs.docker.com/engine/install/ubuntu/).
- [Distribuição oficial Linux aarch64](https://download.docker.com/linux/static/stable/aarch64/).
- [Buildx oficial](https://github.com/docker/buildx/releases/tag/v0.38.1).
- [Lock do runtime](offline/runtime.lock.json) e [lock da imagem](offline/image.lock.json).
- [Ponteiro para o resultado integrado](evidence/LATEST.json); os logs de preflight, instalação, build, ensaio e limites estão em `evidence/`.

A evidência certifica o comportamento descrito nesta unidade/BSP. Ela não mede throughput de rede, latência de AI, uptime de longa duração ou funcionamento de todos os recursos Docker.

## 14. Revalidação com o firmware que exige login

Em 01/11/2026 foi conectado o target com login Linux obrigatório. Observado: Ubuntu 20.04.3, kernel `5.4.219-perf`, build `Thu Apr 2 23:17:04 UTC 2026`, glibc 2.31, usuário root. O build string é diferente do ensaio inicial; a nova combinação foi testada diretamente, em vez de presumir compatibilidade só pelo nome do firmware.

A caixa estava **sem a árvore Docker instalada e sem IPv4 na WLAN**. O pacote foi copiado para uma pasta de aluno com espaços e caractere Unicode e chamado pelo PowerShell a partir de outra pasta. Passaram o primeiro deploy offline, o login por prompt, uid=0, instalação, load e HTTP 200/404; também foi ensaiada a repetição na mesma instalação. A homologação integrada de três ciclos voltou a passar com 61 verificações de comandos.

O relógio do target indicava 2024 nesse ensaio; recibos usam UTC do host. Isso não impediu o fluxo local. Exercícios posteriores que usem HTTPS precisam conferir relógio e rede separadamente. O preflight padrão não tenta acessar Internet.

Além da homologação física, os testes locais cobrem senha incorreta, recusa de usuário sem root, seleção explícita quando serial `?` se repete, retorno remoto não zero, timeout, caminhos/comandos Unicode e redação de saída que por acaso contenha a senha. Não foram feitas tentativas de senha incorreta na caixa real.

Evidências adicionais: [CLASSROOM_VALIDATION.json](evidence/CLASSROOM_VALIDATION.json) e o resultado integrado apontado por [LATEST.json](evidence/LATEST.json). Cada aluno deve passar pelo preflight e pelos testes na própria caixa: ter o mesmo firmware não substitui validar cabo, driver, armazenamento, autenticação e execução dessa unidade.
