# Guia de AI Hub e deploy direto na QB560D-EU

**Revalidação de 01/11/2026:** o firmware com login root passou novamente nos caminhos locais CPU/GPU/HTP e no WLAN. O payload padrão agora fica em `/opt/qb560d-training-payload`. Os helpers pedem a senha Linux e usam o ADB compartilhado em tools/platform-tools. O subconjunto SNPE 2.26 acompanha o ZIP em `offline/snpe226`. Atualização AI Hub: a conta entrou no portal e a API autenticada retornou 77 dispositivos. Siga PASSO_A_PASSO_AIHUB.md para a execução acompanhada dos jobs. A aprovação hospedada e o deploy do artefato gerado serão registrados por resultado. Veja [resultados atuais](../docs/TARGET_RESULTS.md).

Este laboratório usa o Ubuntu que já está instalado na caixa. O primeiro exercício reproduz uma classificação MobileNet V1 com CPU e GPU. O segundo mostra como levar um modelo ONNX mínimo ao Qualcomm AI Hub, baixar o TFLite resultante e validar sua execução local.

## Atualização: HTP executado

A MobileNet do treinamento também executou no **HTP v68** após conversão para DLC INT8. Com exatamente o mesmo DLC, medimos **CPU fixed point 6,748 ms e HTP 1,130 ms (5,97×)**, três sessões de 50 inferências. O profile confirmou 34 entradas DSP e zero CPU. A classe principal coincidiu, com diferença máxima de probabilidade de 4/256 entre CPU/HTP. [Procedimento e evidência completos](../docs/HTP_DSP.md).

## Comparação inicial CPU/GPU

| Execução | Mediana das medianas de sessão | Faixa das medianas de sessão |
|---|---:|---:|
| CPU, duas threads | 25,41 ms | 23,28–25,43 ms |
| GPU, delegate OpenCL do BSP | 9,67 ms | 9,66–9,67 ms |

Ganho observado: **2,63×**, com redução de **61,94%** na latência de inferência. Foram três sessões por backend, 50 inferências medidas e dez aquecimentos por sessão, alternando a ordem de CPU e GPU. Usamos o mesmo TFLite, a mesma imagem e a mesma biblioteca C 2.8.4. A medição cobre `InterpreterInvoke`; leitura da imagem, pré-processamento, cópia da saída e renderização ficam fora desse tempo. Portanto, ela não mede FPS de câmera nem consumo de energia.

Em todas as sessões, CPU e GPU retornaram a classe principal `military uniform`. A maior diferença absoluta entre probabilidades foi 0,00390625, equivalente a um nível da quantização uint8 da saída. Essa conferência valida a imagem de referência; outras cenas ainda precisam de revisão.

O log confirma `Initialized OpenCL-based API` e `Created 1 GPU delegate kernels`. Isso confirma uma partição executada pelo delegate GPU. A C API usada não expõe a contagem de operadores delegados; não afirmamos cobertura integral do grafo. Conversões nas fronteiras da partição podem usar CPU. O código não tenta recriar silenciosamente um interpretador CPU se a inicialização GPU falhar.

Evidência completa: [summary.json](../evidence/acceleration/20261031T230843Z/summary.json), logs das seis sessões, saídas numéricas NPZ e imagens anotadas no mesmo diretório. Na comparação original o relógio ainda indicava 2024; após conectar WLAN, o serviço NTP sincronizou. As sessões continuam identificadas por UTC do computador.

## A. Repetir o deploy de classificação já validado

No PowerShell do computador, entre na raiz `training_v2`. Os comandos abaixo usam `python` do seu ambiente, com NumPy disponível. Os helpers descobrem o ADB portátil do pacote Docker e fazem o login root da caixa.

```powershell
python host/adb_lab.py push
```

O envio copia os modelos, a imagem e os scripts para `/opt/qb560d-training-payload`. Prepare ou confira a dependência Pillow isolada:

```powershell
python host/adb_lab.py run ai prepare
```

Se `.python-deps` já existir, o comando verifica os membros do wheel fixado e reutiliza apenas conteúdo correspondente; diferenças são recusadas. A biblioteca TensorFlow Lite, OpenCL e os drivers continuam sendo os do BSP. O payload atual em `/opt` persiste. `/tmp` permanece uma alternativa transitória com `--remote` explícito; `/data` tem `noexec` nesta imagem.

Execute primeiro em CPU e depois em GPU:

```powershell
python host/adb_lab.py run ai classification --image media/grace_hopper.jpg --backend cpu --vendor-c-api --threads 2 --warmup 10 --runs 50 --output evidence/demo-cpu
python host/adb_lab.py run ai classification --image media/grace_hopper.jpg --backend gpu --vendor-c-api --threads 2 --warmup 10 --runs 50 --output evidence/demo-gpu
```

O wrapper escolhe a conexão ADB autorizada e trata corretamente o código de saída do `adbd` legado. Cada execução grava um log no computador e JSON/PNG/NPZ no target. Para coletar os arquivos:

```powershell
python host/adb_lab.py pull
```

Para repetir automaticamente as três sessões e gerar uma nova comparação:

```powershell
python host/run_acceleration.py
```

O programa exige a confirmação de OpenCL e de kernel delegado nos logs, confere hashes do modelo/imagem/runtime e compara a saída numérica completa. Ele grava os resultados em `evidence/acceleration/<UTC>/`, preservando sessões anteriores, e atualiza `LATEST.json`.

## B. Primeiro ciclo no Qualcomm AI Hub

Use o [passo a passo acompanhado](PASSO_A_PASSO_AIHUB.md), atualizado com a autenticação validada nesta estação. Ele substitui os exemplos antigos com caminho literal de ADB e destino temporário no target.

O ambiente isolado usa Python 3.12, qai-hub 0.57.0, ONNX 1.17.0 e NumPy 1.26.4 em uma pasta curta no perfil do usuário, para evitar o limite de caminhos do Windows/OneDrive. As dependências estão fixadas em requirements.txt. O helper host/account.py pede o token sem eco, valida a lista de dispositivos e guarda a configuração fora da pasta do treinamento. Ele também aceita o comando de configuração copiado do portal, extraindo o token sem executar o texto colado.

A API retornou 77 dispositivos e uma opção da família 6490: **Dragonwing RB3 Gen 2 Vision Kit**, QCS6490, Hexagon v68 e Linux Qualcomm 1.6. O nome exato para o comando é **Dragonwing RB3 Gen 2 Vision Kit**. Esse kit hospedado e seu sistema não são a QB560D-EU Ubuntu conectada por ADB.

O primeiro modelo é a referência determinística já preparada: Conv3×3 com quatro filtros, ReLU, média espacial e Flatten. A entrada é float32 NCHW[1,3,32,32], e a saída é[1,4], sem classes semânticas. A conferência local ONNX versus NumPy passou novamente em 01/11, com erro máximo2,98e-08.

O roteiro cobre escolha do dispositivo, compile, inferência com profile=True, comparação numérica, download e deploy do mesmo TFLite em CPU/GPU na caixa. Usa o caminho persistente /opt/qb560d-training-payload e helpers ADB autenticados. As latências hospedadas e locais permanecem separadas. O TFLite 2.8.4 do BSP precisa aceitar o artefato compilado; a etapa local verifica isso.

O primeiro fluxo foi aprovado: compile/inference/profile, comparação numérica e execução do mesmo TFLite em CPU/GPU na QB560D-EU. Um pacote offline testado e um vídeo de 106 segundos com replay dos logs reais estão disponíveis no passo a passo. O ensaio didático completo de 50 minutos permanece na consolidação final.

## C. Executar a mesma MobileNet no HTP/DSP

O caminho funcional usa **SNPE 2.26 Ubuntu gcc9.4**, obtido do SDK público Qualcomm e instalado em `/opt/qb560d-training-payload/runtime/qairt226-ubuntu`. O subconjunto necessário e o decoder de profile já acompanham o pacote completo em `offline/snpe226`; não é necessário baixar o SDK novamente para executar a demo. O DLC `mobilenet_v1_snpe_int8.dlc` foi convertido do TFLite original; os dois arquivos têm hashes e permanecem separados.

Após o envio/preparo do exercício A:

```powershell
& $py host/stage_snpe_runtime.py
& $py host/run_htp_comparison.py
```

Isso compara TFLite CPU/GPU e o mesmo DLC em CPU fixed point/HTP. O coletor verifica o profile, guarda as saídas completas e registra diferenças numéricas. Os resultados atuais são 25,565 ms / 10,324 ms / 6,748 ms / 1,130 ms, respectivamente. Tempos apenas de inferência; CPU SNPE usa sua política padrão de threads, TFLite CPU usa duas.

Para uma apresentação rápida somente em HTP:

```powershell
python host/adb_lab.py run ai snpe --model models/mobilenet_v1_snpe_int8.dlc --image media/grace_hopper.jpg --backend dsp --input-mode normalized --runs 50 --warmup 10 --profiling detailed --output evidence/htp-live-001
```

Escolha uma pasta de saída nova a cada execução. Para o controle CPU use `--backend cpu --cpu-fixed-point`. A entrada ITensor é float32 NHWC `(RGB - 128) / 128`, distinta dos bytes uint8 do TFLite. Não houve fallback CPU no HTP. Preparação da imagem continua na CPU.

Top-1 coincide na imagem fornecida, mas os scores diferem: máximo 4/256 HTP/CPU do DLC e 6/256 HTP/TFLite CPU. Isso valida o funcionamento da demo; acurácia em dataset permanece pendente. Não apresentar a razão TFLite CPU/HTP como ganho isolado de hardware, pois também muda o runtime e a quantização.

O [guia HTP/DSP](../docs/HTP_DSP.md) detalha hashes, profile, download/staging, reconstrução do DLC no computador e diagnóstico anterior. O delegate Hexagon do TFLite falhou; o SNPE 2.12 instalado apenas passou no probe. A inferência comprovada usa o conjunto 2.26 privado. O caminho atual em `/opt` é persistente; somente a alternativa explícita `--remote /tmp/qb560d-training` exige repetir o staging após reboot.

## D. Configuração e uso de WLAN

A caixa foi conectada ao SSID `Mauricio_WIFI5G` pela interface `wlan0`. O perfil persistente `qb560d-training-wlan` está com autoconnect, IPv4 automático e métrica 600. O endereço observado foi `192.168.0.11/24`, gateway `192.168.0.1`. DNS, HTTP e HTTPS passaram; o relógio sincronizou por NTP. O IP pode mudar conforme DHCP.

Houve conflito DHCPv6 e disputa entre `dhcpcd` e NetworkManager. Deixamos IPv6 desativado nesse perfil e acrescentamos somente `wlan0` à exclusão do dhcpcd, com backup, para que NetworkManager seja seu gerenciador. Ethernet, USB e a configuração celular não foram alterados.

Para conferir ou reativar a conexão salva:

```powershell
python host/adb_lab.py run wlan status
python host/adb_lab.py run wlan check
python host/adb_lab.py run wlan up
```

Em outra unidade, abra `adb shell`, confira os perfis existentes e crie este perfil somente se ainda não existir:

```sh
nmcli radio wifi on
nmcli connection add type wifi ifname wlan0 con-name qb560d-training-wlan ssid Mauricio_WIFI5G ipv4.method auto ipv4.route-metric 600 ipv6.method disabled wifi-sec.key-mgmt wpa-psk connection.autoconnect yes
nmcli --ask --wait 45 connection up qb560d-training-wlan ifname wlan0
```

Informe a senha no prompt interativo. Ela não é incluída no guia ou nos scripts. O [guia WLAN completo](../docs/WLAN.md) explica scan, reconexão, proteção da credencial, exclusão do dhcpcd, diagnóstico, NTP e coexistência com os testes celulares vinculados à RMNET.

## Diagnóstico rápido

| Sintoma | Verificação |
|---|---|
| `no device with transport id` | A caixa pode ter reconectado. Use `adb_lab.py`, que seleciona a conexão atual. |
| `PIL` ausente | Prepare o wheel isolado com `run ai prepare` no payload atual em `/opt/qb560d-training-payload`. |
| Falha ao carregar dependência em `/data` | Foi observado `noexec`; use o diretório de laboratório em `/tmp`. |
| Falha GPU | Procure logs OpenCL/driver e operadores incompatíveis. O script não muda para CPU automaticamente. |
| Falha de alocação TFLite após compile no Hub | Confira versões de operadores/custom ops e a versão local 2.8.4. Preserve o modelo e o log para selecionar conversão/runtime compatíveis. |
| Top-1 ou valores diferentes | Confira hashes, RGB, resize, layout e quantização; compare a saída completa antes de aceitar. |
| Job hospedado usa CPU | Confira o profile e a configuração de compute unit; a opção solicitada sozinha não comprova execução no acelerador. |

## Fontes para os comandos

- [Qualcomm Academy: AI Hub Training](https://academy.qualcomm.com/course-catalog/AI-Hub-Training).
- [Workbench: compile jobs](https://workbench.aihub.qualcomm.com/docs/hub/compile_examples.html), [API e opções](https://workbench.aihub.qualcomm.com/docs/hub/api.html), [CLI](https://workbench.aihub.qualcomm.com/docs/hub/cli.html) e [deploy](https://workbench.aihub.qualcomm.com/docs/hub/deployment.html).
- [Qualcomm: seleção de unidades de execução e fallback](https://workbench.aihub.qualcomm.com/docs/hub/faq.html).
- [TensorFlow: GPU delegate C API, série 2.8](https://github.com/tensorflow/tensorflow/blob/v2.8.0/tensorflow/lite/delegates/gpu/delegate.h). Este BSP exige opções explícitas obtidas de `TfLiteGpuDelegateOptionsV2Default`; sua implementação falhou ao receber opções nulas. O código atualizado já incorpora esse ajuste.

Os slides de 2025 ajudam a entender o fluxo. Para executar os comandos, prevalecem este guia, a versão fixada do cliente e a documentação atual consultada em 31/10/2026.
