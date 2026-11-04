# Preparação reproduzível da QB560D a partir do host

Perfil medido em 01/11/2026: Ubuntu 20.04.3, AArch64, Python 3.8, glibc 2.31.

## Estado desta entrega

O apply foi concluído em 01/11/2026 no novo firmware, com o resultado
INSTALL_AND_VALIDATION_PASSED. A caixa continuou com a data de junho de 2024.
Os pacotes estão nas árvores isoladas em /opt, e os hashes das bibliotecas
originais do firmware foram preservados. Na apresentação atual, localize os títulos Host prerequisites e
Target installation from the host para preparar host e caixa antes das atividades.

O verify separado também terminou com exit 0 e sete gestos corretos.
Os resultados de referência distribuídos estão em [TARGET_RESULTS.md](../docs/TARGET_RESULTS.md)
e [VALIDACAO_POS_REORGANIZACAO.md](../docs/VALIDACAO_POS_REORGANIZACAO.md). Inventários, planos e relatórios
internos de preparação de outra caixa não acompanham o pacote.
Após inspect/prepare/plan, o plan.json gerado localmente descreve o que
instalar; installation_executed=false indica que gerar o plano não instala.
O resultado de apply/verify fica nas novas evidências geradas para sua caixa.
Os testes de câmera, rede celular e WLAN continuam fora desta validação.

## Arquivos para revisão


```text
SOFTWARE_PLANEJADO.json      cada software, versão, origem e destino
bundle-manifest.json         arquivos do host e hashes para a instalação
sources.lock.json            downloads novos, versões e hashes fixados
provision.py               entrada única: inspect/prepare/plan/apply/verify/run
setup_host.ps1             prepara Python/venv/pacotes no Windows, sem ADB
adb_session.py             login ADB e transporte com status remoto
target_install.py          instalação privada de ferramentas e wheels
test_provision.py          testes locais dos bloqueios e do modo plano
```


## Arquivos gerados localmente


```text
plan.json                   plano vinculado ao inventário e ao bundle
LATEST.json                  caminho do inventário mais recente
evidence/                   logs e JSON da coleta autenticada
```

Esses arquivos são específicos da caixa inspecionada e não vêm preenchidos.

## 1. O QUE JÁ VEM NO NOVO FIRMWARE

Ubuntu 20.04.3 LTS (focal), kernel 5.4.219-perf, glibc 2.31, Python 3.8.10,
NumPy 1.17.4 global, TFLite C API 2.8.4, GCC/G++ 9.4.0, Make 4.2.1,
systemd/journald 245, curl 7.68.0, ip/ping, GStreamer 1.16.3 e v4l2-ctl.
Há bibliotecas OpenCL/Adreno, FastRPC e SNPE do BSP.

SNPE confirmado pela API da biblioteca:

```sh
/usr/lib/libSNPE.so
  2.21.0.240401120655_85612
/usr/lib/aarch64-linux-gnu/snpe-2.12/lib/aarch64_Linux/libSNPE.so
  2.12.0.230626174329_59328
```


Esses componentes SNPE não comprovam a instalação de um SDK QAIRT completo.
Não encontramos libQnn*, qnn-net-run ou a instalação isolada QAIRT 2.51.
Docker/Buildx/containerd/runc também não estão instalados.

## 2. O QUE O SCRIPT ACRESCENTARÁ, SE APPLY FOR EXECUTADO


### A. /opt/qb560d-workshop


```sh
 iperf3 3.22: fonte oficial ESnet baixado no host, compilado na caixa com
 GCC/Make já existentes. --disable-shared --enable-static --without-openssl.
 Não usa autenticação OpenSSL do iperf. O perfil não é um servidor público.
 ss 5.5.0: somente o executável ss e copyright extraídos do pacote ARM64
 iproute2_5.5.0-1ubuntu1. Não substitui o ip do BSP nem instala o .deb com dpkg.
 As bibliotecas compartilhadas necessárias ao ss foram localizadas no firmware.
 Wrappers de comandos em bin/ e env.sh para selecionar os caminhos da aula.
 Fontes, arquivos de download, intermediários e logs permanecem nesta árvore.
```


### B. /opt/qb560d-training-payload


```text
 Código do treinamento, cinco modelos TFLite, fotos, configuração de exemplo.
 NumPy 1.24.4 e Pillow 10.4.0 para CPython 3.8/AArch64, em .python-deps.
 Os wheels são extraídos em um diretório privado e usados por PYTHONPATH.
 O NumPy 1.17.4 global e o Python do firmware permanecem instalados.
 O runtime TFLite C API 2.8.4 do BSP será reutilizado.
 Não instala o serviço da aplicação de telemetria nesta etapa de dependências.
```


### C. /opt/qb560d-docker-demo


```text
 Docker Engine/CLI 29.9.2, containerd 2.4.2, runc 1.5.2 e Buildx v0.38.1.
 O arquivo estático oficial inclui docker, dockerd, containerd, ctr,
 containerd-shim-runc-v2, runc, docker-init e docker-proxy.
 Imagem offline qb560d-telemetry:1.0.0, Linux ARM64, com Python próprio.
 A imagem dispensa download de registry na caixa.
 Unit exclusiva: /etc/systemd/system/qb560d-docker-demo.service.
 Daemon com socket Unix e dados privados. Serviço iniciado para os testes,
 sem habilitação automática no boot. Redes host/none, sem bridge/NAT.
 O container de teste é parado ao concluir a verificação.
```


### D. /opt/qairt-isolated/2.51.40.260930


```text
 QAIRT/QNN/SNPE build 2.51.40.260930230134, ARM64 Ubuntu, com HTP v68.
 Executores qnn-net-run, snpe-net-run, qnn-platform-validator e
 qnn-profile-viewer. Bibliotecas CPU/HTP/System, loader DLC, stubs e skeletons.
 A lista exata dos 24 componentes SDK está no lock em runtimes/qairt_2_51.
 MobileNet V2 w8a8 e tensor de teste.
 MediaPipe Hand Gesture: palm_detector, hand_landmark_detector e
 canned_gesture_classifier, metadados e sete fotos selecionadas.
 A seleção de bibliotecas ocorre por processo, sem substituir /usr/lib.
 O roteiro de gestos usa HTP: o pacote w8a8 anterior teve 7/7 no HTP e 0/7
 na CPU. apply repetirá as sete fotos no novo firmware antes de aceitar o caso.
```


Não serão instalados no target: pip/venv, Git, CMake, Docker Compose,
PyTorch, TensorFlow Python, ONNX Runtime ou OpenCV Python, pois os fluxos
atuais não exigem esses pacotes. Os conversores de modelos também ficam fora
desta preparação: os DLCs e modelos já estão prontos.

## 3. REQUISITOS DO COMPUTADOR HOST

Windows x64, PowerShell, driver USB/ADB funcional, Android platform-tools e
Python 3.12 x64 com pip/venv. O launcher py é opcional; o roteiro abaixo não o
utiliza. Não precisa de Docker Desktop, WSL, SDK Yocto ou cross compiler.
Os passos de inspeção/plano usam Python stdlib. A preparação e as validações
de IA também usam as versões fixadas em runtimes/qairt_2_51/requirements-host.txt:
NumPy 2.3.5 e Pillow 12.3.0, no host, diferentes dos wheels ARM64 do target.

Abra PowerShell na raiz training_v2:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ./provision_target/setup_host.ps1 -InstallPython
$py = (Resolve-Path './provision_target/.venv/Scripts/python.exe').Path
& $py --version
```


O helper procura um Python 3.12 x64 válido no ambiente do projeto, PATH,
registro e diretórios usuais. Ignora os aliases WindowsApps que abrem a Store.
Se não encontrar Python, -InstallPython instala-o para o usuário via winget.
Depois cria provision_target/.venv, instala os pacotes fixados e valida as
versões. Aguarde HOST_READY antes de continuar. Não se conecta ao target.
ExecutionPolicy Bypass vale somente para esse processo PowerShell.

Se o Python estiver em outro diretório, informe o executável completo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ./provision_target/setup_host.ps1 -PythonExe 'C:/caminho/Python312/python.exe'
```


Se winget não estiver disponível, instale Python 3.12 x64 pelo instalador
completo oficial (com pip e venv), e execute o comando com -PythonExe acima:

```text
https://www.python.org/downloads/windows/
```

Não use o pacote embeddable. O erro "py não é reconhecido" indica que o
launcher não está acessível; não comprova se o interpretador está instalado.

Para somente verificar a localização/versão, sem instalar nem criar venv:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ./provision_target/setup_host.ps1 -CheckOnly
```


Confira também a conexão USB antes de iniciar o inventário. Na árvore completa, use o ADB portátil incluído, independentemente do caminho de extração:

```powershell
$adb = (Resolve-Path ./tools/platform-tools/adb.exe).Path
& $adb devices -l
```


Nos comandos inspect/apply/verify/run abaixo, acrescente --adb $adb.
Por exemplo: & $py provision_target/provision.py inspect --adb $adb
O parâmetro explícito evita depender do caminho legado C:/platform-tools.

Conecte uma caixa por vez. O script redescobre o transport ID. A unidade atual
usa serial "?", por isso esse valor não é um identificador único entre caixas.
Se outra unidade tiver serial real, --serial SERIAL permite selecioná-la.
Use --adb CAMINHO para selecionar um cliente diferente do incluído em tools/platform-tools.

## 4. INVENTÁRIO, SEM INSTALAR NADA


```powershell
& $py provision_target/provision.py inspect
```


O novo firmware exige login Linux no ADB. O usuário padrão é root e a senha
é solicitada de forma oculta no terminal. Não passa por argumento, arquivo
de configuração ou log. A sessão é encerrada ao terminar o comando.

Resultado: `evidence/<UTC>-inspect/inventory.json`, logs e `LATEST.json`.
O inventário consulta versões, arquivos, bibliotecas, ferramentas e filesystem.
Ele não instala pacotes, não altera rede e não executa inferência.

## 5. PREPARAÇÃO NO HOST, SEM ESCREVER NA CAIXA


```powershell
& $py provision_target/provision.py prepare
```


Usa os scripts e locks dos módulos runtimes/qairt_2_51 e demos/docker, verifica os
modelos TFLite e obtém os novos downloads de sources.lock.json.
A imagem Docker offline deve acompanhar demos/docker/offline/images/.
Todos os arquivos selecionados são registrados em bundle-manifest.json.
Com os caches presentes, a opção abaixo funciona sem Internet:

```powershell
& $py provision_target/provision.py prepare --offline
```


Não regenere hashes para contornar uma divergência. Atualização de versão
requer revisão dos locks e nova validação. Uma nova preparação muda o hash
do bundle e exige gerar/revisar novamente o plano.

## 6. GERAR E REVISAR O PLANO


```powershell
& $py provision_target/provision.py plan
```


Sem argumentos, a ação padrão também é plan. Não chama ADB nem instala nada.
Confira status READY_TO_REVIEW, blockers vazio e bundle_prepared true.
Revise os destinos, versões e hashes. O plano contém a impressão do firmware
medido e recusa outra ABI/BSP ou fontes alteradas na aplicação.

## 7. APLICAÇÃO FUTURA, SOMENTE QUANDO FOR EXECUTAR A INSTALAÇÃO


```powershell
& $py provision_target/provision.py apply
```


Esta é a única ação que instala. Ela pede a senha, coleta outro inventário,
compara o firmware com o plano, verifica os hashes do host, exige espaço livre,
cria diretórios identificados em /opt, transfere por ADB e instala por etapas.
Arquivos de payload existentes com conteúdo diferente são recusados.

O relógio desatualizado da caixa não exige conexão WLAN nem bloqueia o build.
O script não ajusta a data do sistema, RTC ou NTP. Quando os fontes do iperf3
têm datas futuras em relação à caixa, normaliza somente os timestamps da cópia
de compilação em /opt/qb560d-workshop/build/iperf-3.22, preservando a ordem
relativa das datas e o conteúdo dos arquivos. O tarball e seu hash não mudam.
Os horários dos diretórios de evidência são sempre gerados pelo host em UTC.

O target não precisa baixar da Internet. Apenas o host faz os downloads.
Não há apt update/upgrade/install, reparo de dpkg, escrita de firmware,
mudança de APN, configuração WLAN, alteração de rotas ou reboot automático.
O dpkg --audit desta imagem lista muitos arquivos de controle/lista ausentes.
Esse diagnóstico permanece documentado e não é corrigido implicitamente.

## 8. TESTES E RESULTADO ESPERADO APÓS APPLY


```text
Imports NumPy/Pillow privados e contratos dos cinco modelos TFLite.
Versão do iperf3, presença de --bind-dev e teste de um segundo só em loopback.
ss -V e consulta local de sockets.
Docker info, docker load e ciclo HTTP do container offline, seguido de stop.
MobileNet V2 em CPU/HTP e sete fotos de gestos no HTP, com perfis.
Hashes das bibliotecas do firmware antes/depois, sem alteração.
```


O sucesso final é INSTALL_AND_VALIDATION_PASSED. Se uma etapa falhar, o comando
retorna erro e mantém evidências. Não reporta homologação nem faz fallback CPU
para esconder uma falha HTP. Instalações parciais devem ser revisadas nos logs.
Não há remoção automática ampla ou tentativa de reparar o BSP.
Os casos de gestos usam diretórios curtos g01-<id> a g07-<id>, para caber no
limite de caminhos do Windows mesmo nesta raiz OneDrive. gestures.json e cada
result.json identificam a imagem e o gesto; cada execução recebe um id novo.

Para repetir somente a validação, após instalar:

```powershell
& $py provision_target/provision.py verify
```


Se apply foi interrompido antes de criar /opt/qb560d-workshop/env.sh, verify
informa "Installation incomplete" e os arquivos ausentes. verify não conclui
a instalação. Após atualizar os scripts, refaça o bundle/plano e retome:

```powershell
& $py provision_target/provision.py prepare --offline
& $py provision_target/provision.py plan
& $py provision_target/provision.py apply
```

Confira READY_TO_REVIEW e blockers vazio antes de executar apply. O modo
--offline pressupõe que todos os pacotes já estejam no cache do host.

Câmera, vídeo em tempo real, sessão celular, APN, WLAN e servidor externo de
iperf exigem configuração/ensaio próprios. O teste de loopback não mede 5G.
As bibliotecas de GPU/HTP presentes não comprovam captura ou inferência funcional
no firmware novo antes desses testes. Este pacote prepara as dependências.

## 9. UTILIZAÇÃO DOS PATHS

Em um adb shell autenticado, execute:

```sh
. /opt/qb560d-workshop/env.sh
docker version
qnn-net-run --version
iperf3 --version
ss -lnt
cd /opt/qb560d-training-payload
sh target/ai.sh classification --image media/grace_hopper.jpg
```


env.sh altera somente o ambiente da sessão. Cada wrapper de IA seleciona as
bibliotecas QAIRT 2.51 por processo; o wrapper Docker seleciona seu socket.
Não se escreve em .bashrc ou no PATH global. Após reboot, os arquivos persistem
em /opt, mas o daemon Docker precisa ser iniciado para uso:

```text
systemctl start qb560d-docker-demo.service
```


Os helpers antigos que supõem um shell ADB já autenticado não atendem ao login
novo. Para um comando a partir do host, use a entrada autenticada:

```powershell
& $py provision_target/provision.py run --command 'uname -a'
```


## 10. FONTES DOS PACOTES

QAIRT e modelos: [guia do runtime](../runtimes/qairt_2_51/readme.me) e [versions.lock.json](../runtimes/qairt_2_51/versions.lock.json).
Docker e imagem offline: [guia Docker](../demos/docker/README.md) e os locks em `../demos/docker/offline/`.
NumPy/Pillow: PyPI, wheels CPython 3.8/AArch64, versões e hashes fixados.
iperf3: https://downloads.es.net/pub/iperf/iperf-3.22.tar.gz
SHA256 do fornecedor: https://downloads.es.net/pub/iperf/iperf-3.22.tar.gz.sha256
ESnet recomenda os tarballs oficiais e a verificação de SHA256:
https://software.es.net/iperf/obtaining.html
ss: https://ports.ubuntu.com/ubuntu-ports/pool/main/i/iproute2/iproute2_5.5.0-1ubuntu1_arm64.deb
Docker estático (perfil de laboratório, atualização manual):
https://docs.docker.com/engine/install/binaries/
Lista atual de Ubuntu suportados pelo instalador de pacotes Docker:
https://docs.docker.com/engine/install/ubuntu/

Os hashes novos estão em sources.lock.json. As bibliotecas e modelos dos
pacotes existentes mantêm os locks já revisados. Licenças e créditos acompanham
os respectivos pacotes, wheels, fontes e materiais de treinamento.

## Revalidação das demos em 01/11/2026

Os fontes e guias do treinamento foram atualizados para o payload persistente.
Inventário/logs, HTTP/C, systemd, cinco demos CPU, GPU, HTP e WLAN passaram.
Os sete gestos HTP e MobileNet V2 também passaram. Relatório completo:
[resultados e reprodução](../docs/TARGET_RESULTS.md). O subconjunto SNPE2.26 para a comparação
V1 acompanha offline/snpe226 e é enviado por stage_snpe_runtime.py.
Após mudar os fontes, execute prepare --offline e gere novo plan antes de apply.
Nesta revalidação, celular e iperf3 ficaram adiados pelo proprietário.

## Cinco demos adicionais no HTP QAIRT 2.51

Depois deste provisionamento, os cinco modelos base também podem ser rodados
no HTP por um fluxo independente e isolado, sem substituir os runtimes atuais:

```powershell
& $py host/htp251_workshop.py deploy --adb $adb
& $py host/htp251_workshop.py test-all --adb $adb
Invoke-Item htp251/results/index.html
```

Defina $adb com o caminho do cliente incluído, conforme o preparo do host.
Os novos arquivos ficam em /opt/qb560d-ai-htp251. O resultado confirmado foi
PASS_ALL_MIGRATED_HTP_DEMOS, com imagens anotadas e perfis reais do acelerador.
Guia completo: [HTP 2.51](../htp251/README.md). Pré/pós-processamento e NMS
ficam no host; a CNN executa no HTP. Os modelos TFLite/CPU e SNPE 2.26 seguem
disponíveis nos caminhos anteriores.

## Onze controles HTP diretamente no shell da caixa

Depois do preparo acima, o pacote pronto também permite executar todo o
pipeline localmente (preparo/decode/desenho na CPU da caixa; CNN no HTP).
No PowerShell, na raiz training_v2, com $py definido como acima:

```powershell
& $py host/deploy_htp_target.py
```

O helper instala offline/htp-controls-target.tar.gz, verifica
SHA-256 e pede a senha root sem guardá-la. Runtime QAIRT e NumPy/Pillow vêm
do provisionamento; não estão dentro desse TAR.
No shell Linux da caixa:

```sh
cd /opt/qb560d-ai-htp251/htp-controls
sh run.sh check
sh run.sh run-all
```

Para um caso: sh run.sh run closed-fist
Resultado: PASS_TARGET_HTP_CONTROLS, 11 casos aprovados. Este modo usa
referências CPU já gravadas; não executa outra inferência CPU/GPU.
Guia e comandos dos 11 casos: [controles de visão](../docs/VISION_CONTROLS.md).
