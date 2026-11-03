# Resultados atuais na QB560D-EU — 01/11/2026

**Após a reorganização das pastas:** [validação completa e correções](VALIDACAO_POS_REORGANIZACAO.md). A extração independente passou em `apply/verify` (82 comandos), suite local e cinco demos HTP. Novo AI Hub online e deploy CPU/GPU passaram; WLAN/SSH/SCP e tráfego celular também. O retorno `-4` de `71/d` permanece registrado como falha da API, apesar da call ativa e do tráfego aprovado. Os 48 hashes protegidos mantiveram-se iguais. Entrega sem congelamento, aguardando revisão dos slides.

Revalidação real na caixa com login Linux **root**, BSP **QDPA_Ubuntu20.04.003.51.303 V01**, Ubuntu 20.04.3, kernel 5.4.219-perf build **02/04/2026**, Python 3.8.10, glibc 2.31 e TFLite C API 2.8.4. O helper confirmou uid=0 antes dos comandos e transferências. As senhas não integram os arquivos distribuídos. Datas de evidência usam UTC do host.

O caminho atual é `/opt/qb560d-training-payload`, com NumPy 1.24.4/Pillow 10.4.0 privados preparados por `provision_target`. A ausência desses pacotes no Python global não indica falta no ambiente da demo. Os hashes das bibliotecas originais do BSP permaneceram iguais. [Resumo por demo](../evidence/CURRENT_FIRMWARE.json).

## Resultado por bloco

**Migração adicional para QAIRT/QNN 2.51:** as cinco demos base passaram no HTP, com três inferências por rede e ciclos positivos nos perfis. Detecção: IoU de pessoa 0,9975; pose: deslocamento normalizado 0,0107; mão: open_hand; segmentação: IoU de pessoa 0,9763; classificação: military uniform. [Guia e limites](../htp251/README.md), [imagens reais](../htp251/results/index.html) e [resumo da rodada](../htp251/evidence/20261101T195905Z-ffc9e/summary.json). Quarenta arquivos dos runtimes/modelos existentes mantiveram os hashes. Os resultados CPU/GPU/SNPE 2.26 abaixo continuam como referência independente.

| Demo | Resultado no firmware atual | Escopo e evidência |
|---|---|---|
| D1-01 inventário/login | Passou | OS, BSP, kernel, root e ferramentas coletados por ADB |
| D1-02 diagnóstico de boot | Cold boot físico passou, uma rodada | Novo boot_id, shell root 13,94 s, /opt/modelos persistentes e smoke CPU PASS. Startup systemd 76,464 s; mesmas 14 falhas BSP no estado estabilizado |
| D1-03 Ubuntu/logs | Passou | Evento único de logger localizado em journald |
| D1-07 WLAN | Passou inclusive após cold boot | Autoconnect29,02 s sem ativação manual; DHCP/DNS/HTTPS200. NTP não na captura inicial e sim no follow-up; perfil e rotas DNS persistiram |
| D1-04 RIL manual | Ativação do proprietário e consultas conferidas | 71/d no log enviado;4/21/20/29/37/38/70/73/75 e6 AT na caixa; NR/reconexão pendentes |
| D1-05 celular | HTTPS vinculado passou | rmnet_data0,HTTP200,IP de origem celular e contadores RX/TX; ICMP vinculado indisponível |
| D1-06 iperf3 | Passou, três pares UL/DL | Servidor público autorizado 103.230.142.1:5201; 10 s/1 fluxo; mediana UL 9,957 / DL 8,178 Mb/s; controle de falha aprovado |
| D2-00 contratos/runtime | Passou | Hashes, tensores dos cinco modelos e dependências privadas conferidos |
| D2-01 HTTP/Python/C | Passou, três ciclos HTTP | HTTP 200/200/404, endpoint indisponível após encerrar; GCC com warnings como erros |
| D2-02 systemd/update/rollback | Passou, três ciclos | 1.0.0 → 1.0.1 → 1.0.0; serviço restaurado, parado e sem autostart |
| D2-03 Docker | Revalidação anterior mantida | Pacote independente já passou instalação inicial/repetição offline; não repetido nesta tarefa |
| D2-05…09 cinco demos CPU | Passaram, três sessões por modelo | 20 invokes após 3 warmups; resultados de referência e imagens anotadas revisados |
| D2-05…09 cinco demos QAIRT 2.51 HTP | Passaram, três inferências por modelo | Perfil de acelerador positivo em todas; imagens/JSON comparados aos TFLite CPU; dados novos em /opt/qb560d-ai-htp251 |
| D2-11 HTP | Passou, três sessões | Mesmo DLC no CPU-fixed/HTP; profile separado com 34 entradas DSP e zero CPU |
| D2-12 GPU | Passou, três sessões | OpenCL confirmado no log; top-1 igual; sem fallback CPU silencioso |
| Extensão MobileNet V2/QAIRT 2.51 | Passou | Cinco inferências por backend; Samoyed top-1 em CPU/HTP; scores diferentes, sem alegar equivalência numérica |
| Extensão sete gestos HTP | Passou 7/7 | 21 execuções de grafo com ciclos HTP positivos; transformações/ROI no host |
| D2-04 AI Hub | Hosted, CPU/GPU local e contingência passaram | Mesmo TFLite de 1992 bytes; CPU 0,0848 ms / GPU 0,2543 ms; OpenCL confirmado; pacote offline CPU/GPU testado; replay 106 s disponível |
| D2-10 câmera | UVC + CPU e preview HDMI executados em 02/11 | Webcam USB em `/dev/video0`; JPEG validado; SSD MobileNet V1 CPU 35,613 ms, sem detecções. HDMI recuperado após restart gráfico e reconexão; preview confirmado visualmente. [Reprodução e limites](CAMERA_HDMI.md) |

## Inspeção RIL manual e caminho celular

Guia: [CELLULAR_RIL.md](CELLULAR_RIL.md). Evidência: [resumo RIL](../evidence/ril/20261101-manual/summary.json) e [menu instalado](../evidence/ril/20261101-manual/menu.txt). A ativação **71/d** foi executada pelo proprietário no log fornecido. A inspeção posterior consultou4/21/20/29/37/38/70/73/75 e seis comandos AT, sem recriar ou derrubar a sessão.

- Executável `/usr/bin/qlril-api-test`, biblioteca202411060822, mesmo BSP. SIM slot1, presente, USIM ready, TIM72402.70 retornou registrado1/RAT19; o log do proprietário mostrava RAT14.73 confirmou call0/up, rmnet_data0,100.65.195.62/30 e MTU1500.
- Opção6: AT/CPIN/CEREG/COPS/CSQ/QENG responderam OK. CPIN READY, CEREG0,1, COPS TIM TIM/7, CSQ23,99. QENG informou LTE/FDD/banda7 nesta captura. Não há comprovação de NR/SA/NSA.
- HTTPS manual com `--noproxy '*' --interface rmnet_data0`: **HTTP200**, origem100.65.195.62,0,306503s, RX+6023/TX+1801bytes. O probe atualizado também passou, HTTP200 em1,106281s e RX+5903/TX+1681bytes. Esses tempos são requisições individuais, sem significado de benchmark de throughput.
- `network.sh` agora identifica que o ping BusyBox não possui-I. Retorna HTTP_PASS_ICMP_NOT_TESTED quando só o HTTP passa. Configuração sem CELL_IF e endpoint fechado retornaram1, preservando a falha. DNS continua pelo resolver sistêmico.
- RIL reportou gateway100.65.195.61, enquanto o kernel mostrou default via100.65.195.62, métrica500. Ambos ficaram registrados como observados; nenhuma correção de rota foi aplicada.

O guia inclui o catálogo completo, distingue opções consultadas das apenas listadas e explica efeitos de DNS/rotas, PIN/PUK, reset e desconexão. O ensaio posterior iperf3 passou em três pares UL/DL e controle de falha. Nova ativação em cada caixa,74/reconexão e confirmação NR não foram homologadas; D1-04/05 foram retirados da fila atual pelo proprietário. O inventário e a aceitação por caixa continuam no preparo do evento. O menu é operado pelo aluno, sem script de bring-up.

## Verificação específica de 5G, 01/11/2026

Resultado: **LTE/LTE_CA observado; NR5G não confirmado nesta sessão**. Foram quatro consultas RIL 70 e cinco QENG, incluindo três durante tráfego pela RMNET. RIL 70 retornou registro 1 / RAT 19; QENG mostrou LTE/FDD, banda 7. C5GREG retornou 0,0, sem registro 5GS, o que isoladamente não exclui NSA. QNWINFO,QENDC,QCAINFO e a consulta QNWPREFCFG mode_pref retornaram ERROR neste BSP/caminho.

Dois downloads limitados de 2 MiB passaram com HTTP 200 e origem celular. Serviram para consultar o rádio em atividade, sem medir throughput. RIL 75 retornou 11, que o enum AOSP denomina LTE_ONLY; a correspondência específica do BSP precisa ser confirmada antes de atribuir causa ou mudar configuração. Sessão e configuração foram preservadas. Veja [passos e interpretação](CELLULAR_RIL.md#5a-focused-check-is-this-session-actually-using-5g), [evidência](../evidence/ril/20261101-5g-verification/summary.json) e [respostas](../evidence/ril/20261101-5g-verification/queries.txt). O ensaio posterior de iperf3 passou. A confirmação NR positiva e o ciclo de reconexão permanecem não testados, fora da fila atual por decisão do proprietário.

## Medições de inferência e referência visual

**Comparação atual com HTP 2.51:** [relatório completo](../htp251/BENCHMARK.md), 3 sessões/backend/modelo, 50 inferências após 10 aquecimentos; 45 sessões passaram. Medianas CPU/GPU/HTP em ms: MobileNet V1 **26,496 / 10,149 / 1,500**; SSD **35,668 / 23,559 / 3,936**; PoseNet **137,924 / 15,710 / 2,201**; mão **55,952 / 7,742 / 1,782**; DeepLabV3 **179,767 / 21,419 / 4,609**. CPU/GPU são TFLite BSP 2.8.4, com partição OpenCL confirmada; HTP é QNN 2.51 com profiling client e perfil de potência default. SSD conserva NMS na CPU no TFLite, fora do grafo medido no QNN/HTP. São latências dos caminhos disponíveis, sem equivalência de precisão/escopo ou alegação de FPS. O snapshot ampliado manteve 48 arquivos/entradas iguais.

Comparação MobileNet V1 de 01/11: TFLite CPU **25,994 ms**, GPU **9,786 ms**, SNPE CPU fixed point **6,701 ms**, HTP **1,109 ms**. Mesma política do ensaio anterior: três sessões por backend, 50 invokes após 10 warmups. No mesmo DLC, CPU/HTP = **6,04×**. [Resumo e diferenças numéricas](../evidence/htp-dsp/20261101T173204Z/summary.json). O runner GPU separado também passou: CPU 25,383 ms / GPU 9,820 ms. Essas rodadas são distintas; não misturar seus tempos.

Nas cinco demos CPU, a referência retornou `military uniform`, pessoa detectada, sete pontos visíveis no retrato de corpo parcial, `open_hand` no recorte e pessoa/fundo na segmentação. As 15 saídas passaram nas verificações de referência e as cinco imagens da última rodada foram inspecionadas. As duas caixas sobrepostas de `tie` na detecção continuam uma limitação visível do modelo. Acurácia em dataset permanece fora deste ensaio. Depois, 11 controles públicos de corpo inteiro, oclusão, punho/sem mão e pessoa/sem pessoa passaram nos três backends; [guia e limites visuais](VISION_CONTROLS.md).

- [28 verificações do núcleo local](../evidence/regression/20261101T173038495190Z/summary.json).
- [Conferência das 15 saídas CPU](../evidence/regression/20261101T173038495190Z/reference-correctness.json), JSON/NPZ e prévias na mesma pasta.
- [GPU](../evidence/acceleration/20261101T173429Z/summary.json) e [HTP](../evidence/htp-dsp/20261101T173204Z/summary.json).
- [WLAN](../evidence/wlan/20261101T173943Z/summary.json) e [testes de câmera](../evidence/current-firmware-wlan-camera.json).
- [MobileNet V2](../runtimes/qairt_2_51/evidence/fw-20261101-v2/test-run.json), [sete gestos](../demos/hand_gesture/evidence/fw-20261101/summary.json) e integridade do sistema nas respectivas pastas.
- [Estado final/hashes do BSP](../evidence/current-firmware-final-state.json).

## Reproduzir no host

Use a árvore completa do treinamento ou extraia os ZIPs v2 e Docker lado a lado. Para uma caixa recém-gravada, prepare primeiro as dependências conforme `provision_target/README.txt`. Dentro de `training_v2`, execute:

```powershell
python host/adb_lab.py inventory
python host/adb_lab.py push
python host/rehearse_local.py --repeat 3 --unit-label Caixa-01
python host/stage_snpe_runtime.py --check-only
python host/stage_snpe_runtime.py
python host/run_htp_comparison.py
python host/run_acceleration.py
python host/adb_lab.py run wlan status
python host/adb_lab.py run wlan check
```

Os helpers solicitam a senha Linux por processo; com várias caixas use o `--transport-id` atual. O comando de ensaio não testa celular/iperf3, cold boot, câmera ou jobs hospedados. Falhas reais mantêm retorno não zero. A comparação HTP usa o subconjunto offline e o decoder incluídos, sem SDK/conversor no target. As bibliotecas globais não foram substituídas.

Para os sete gestos, na raiz completa do treinamento: `python demos/hand_gesture/gesture_demo.py test-all --backend htp`. O ADB é descoberto automaticamente, o novo login foi validado e os arquivos longos do Windows usam cópia local compatível.

## Ajustes realizados

Os runners agora compartilham o caminho persistente e aceitam a alternativa explícita `--remote /tmp/qb560d-training`. O Pillow pode ser preparado novamente com verificação dos arquivos existentes. O subconjunto SNPE 2.26 foi incluído no ZIP com lock/licença. Os scripts da extensão de gestos/profiles usam o ADB descoberto e aceitam transport ID. A câmera diferencia codecs de sensores, testa a entrada QMMF explicitamente e limita a captura a 15 segundos.

A WLAN foi recriada após reflash, guardando a credencial somente no perfil privado do target. O helper `wlan_owner.py` adicionou apenas `wlan0` à exclusão existente do dhcpcd, com backup, preservando as demais interfaces. O relógio, inicialmente em 2024, sincronizou automaticamente por NTP após a conexão.

Os dados a seguir preservam o ensaio anterior para rastreabilidade; caminhos e medições históricos não substituem o procedimento atual acima.

# Histórico do ensaio de 31/10/2026

Coleta e ensaio via `C:/platform-tools/adb.exe`. O dispositivo apresenta ADB legado com apenas PTY e serial `?`. O wrapper agora seleciona o transport ID, envia comandos sem depender de EOF no PTY, reconhece o marcador de retorno remoto e grava timeout/exit status.

## Plataforma observada

| Item | Resultado |
|---|---|
| OS/kernel | Ubuntu 20.04.3 LTS / 5.4.219-perf / AArch64 |
| Python | 3.8.10 |
| Runtime | `/usr/lib/libtensorflowlite_c.so`, versão 2.8.4 |
| glibc | 2.31 confirmada em 01/11 com getconf; indicação anterior 2.29 vinha do runtime Python |
| Ferramentas presentes | GCC, systemd/journald/logger, curl, GStreamer, v4l2-ctl |
| Ferramentas ausentes no inventário inicial | Docker, iperf3, qnn-net-run, pip; Docker foi posteriormente instalado em diretório privado |
| Python AI inicial | NumPy presente; Pillow e bindings TFLite ausentes |
| Preparação isolada | Pillow 10.4.0 ARM64 em `/tmp/qb560d-training/.python-deps` |
| Bibliotecas do sistema | Reutilizadas; SNPE 2.26 adicional somente em pasta privada temporária, sem substituir pacotes ou bibliotecas globais |

O adaptador `ai/c_api_backend.py` chama a API C do TFLite existente. O padrão continua sendo CPU; `--backend gpu` solicita explicitamente o delegate GPU do BSP. O wrapper Python organiza os tensores e copia buffers NumPy. A tentativa `--backend dsp` falhou antes da inferência; a rota SNPE 2.26 executou efetivamente no HTP, com profile DSP detalhado.

## Comparação MobileNet CPU/GPU

Três sessões alternadas por backend, 50 inferências medidas após dez aquecimentos por sessão, duas threads para a CPU. Mesmo arquivo TFLite, imagem de entrada e biblioteca C 2.8.4:

| Backend | Mediana das medianas | Faixa das medianas |
|---|---:|---:|
| CPU | 25,41 ms | 23,28–25,43 ms |
| GPU/OpenCL | 9,67 ms | 9,66–9,67 ms |

Ganho: **2,63×**, redução de latência de **61,94%**, somente em `invoke`. Top-1 igual em todas as comparações; maior diferença absoluta entre probabilidades: **0,00390625 (1/256)**. O log confirma OpenCL e um kernel delegado GPU. A cobertura por operador não é exposta pela C API utilizada; uma partição GPU foi confirmada.

Evidências: `evidence/acceleration/20261031T230843Z/summary.json`, seis logs, resultados numéricos NPZ e imagens. Repetição a partir de training_v2: `& $py host/run_acceleration.py --adb $adb`, com as variáveis definidas no preparo do host. [Guia e materiais do AI Hub](../Qualcomm_AI_Hub_Training/README.md).

O BSP também contém SNPE 2.12 e stub/skel HTP v68; não foi localizado um DLC de exemplo ou `qnn-net-run`. Presença de bibliotecas não é evidência de inferência HTP. O fluxo do Workbench está atualizado para o cliente `qai-hub 0.57.0`, mas nenhum job autenticado foi enviado sem configuração de conta.

## HTP/DSP e WLAN

- Mesma MobileNet TFLite tentada em DSP: delegate indisponível, `Failed to fetch Hexagon NN version`; script terminou com erro e não executou em CPU como substituto.
- SNPE 2.12.0.230626 passou no probe unsigned PD, mas não executou o DLC novo. O runtime público 2.26 Ubuntu gcc9.4, isolado em `/tmp/qb560d-training/runtime/qairt226-ubuntu`, executou a MobileNet convertida em DLC INT8. Três sessões de 50 inferências após dez aquecimentos: CPU fixed point **6,748 ms**, HTP **1,130 ms**, ganho **5,97×** com o mesmo DLC. Novo ensaio TFLite CPU/GPU: 25,565/10,324 ms. O profile separado confirmou **34 entradas DSP e zero CPU**. Top-1 igual; maior diferença de probabilidade HTP versus CPU do mesmo DLC: **4/256**; versus TFLite CPU: 6/256. Sem validação de acurácia em dataset. [Evidência](../evidence/htp-dsp/20261101T021205Z/summary.json).
- WLAN `Mauricio_WIFI5G`: perfil `qb560d-training-wlan`, IPv4 DHCP observado `192.168.0.11/24`, gateway `192.168.0.1`, autoconnect, rota métrica 600.
- Foi desativado IPv6 apenas no perfil WLAN após erro DHCPv6. `wlan0` foi excluída do dhcpcd para eliminar a disputa com NetworkManager, preservando a exclusão bridge0 e demais configurações. Backup em `/etc/dhcpcd.conf.qb560d-training-20261101T010211Z.bak`.
- DNS, HTTP 204 e HTTPS 200 passaram pela WLAN; NTP sincronizou automaticamente. O perfil privado foi salvo com modo 600 e não foi copiado para o pacote.

Procedimentos e limites: [HTP_DSP.md](HTP_DSP.md) e [WLAN.md](WLAN.md). Logs curados em `evidence/htp-dsp` e `evidence/wlan`.

## AI: três execuções por demo

Cada execução: três warmups, 20 chamadas medidas a `invoke`, duas threads, entrada local. As faixas abaixo abrangem as medianas das três execuções, em milissegundos. Não incluem decode, pré-processamento, anotação ou ADB.

| Demo | Faixa de mediana CPU | Resultado de referência |
|---|---:|---|
| Classificação | 26,4–27,0 ms | Military uniform no top-1 |
| Detecção | 35,4–36,0 ms | Pessoa detectada; outras detecções exigem inspeção |
| Pose | 128,0–128,2 ms | Sete pontos visíveis no retrato de corpo parcial |
| Gesto | 54,0–54,1 ms | Mão aberta no recorte fornecido |
| Segmentação | 166,3–166,9 ms | DeepLabV3: pessoa e fundo presentes na amostra |

JSONs e imagens: `evidence/target-ai`. Recibos das 15 execuções: `evidence/target-ai-summary.json`. Todos terminaram com retorno remoto zero. Isso não substitui os controles negativos, cenas do evento ou teste de precisão em dataset.

O primeiro modelo de segmentação, MediaPipe selfie segmentation, exigia `Convolution2DTransposeBias`, ausente no runtime da caixa. A versão ativa usa DeepLabV3 com operações compatíveis e 21 classes Pascal VOC.

## Aplicação e sistema

- Compilação C diretamente no target: passou com `-Wall -Wextra -Werror`.
- Evento de logger localizado em journald: passou.
- Aplicação HTTP como systemd: health/telemetry passaram.
- Atualização 1.0.0 para 1.0.1 e rollback para 1.0.0: passaram.
- Estado final: serviço de treinamento restaurado, parado e sem habilitação automática no boot. Os arquivos da demo ficam em `/opt/qb560d-training/telemetry.py` e `/etc/systemd/system/qb560d-training.service`.

## Pendências observadas

1. Docker resolvido em 01/11: engine 29.9.2 e imagem ARM64 offline homologados em [demos/docker](../demos/docker/README.md). Três ciclos e 61 verificações de comandos passaram; rede host/none. O ensaio iperf3 posterior também passou: três pares UL/DL por RMNET, mediana 9,957/8,178 Mb/s e controle de falha, conforme `evidence/iperf-public/20261101T195153557423Z-measure/RESULTADOS.txt`.
2. No inventário inicial, as interfaces `rmnet_data*` estavam sem sessão/IP. Atualização: o proprietário forneceu71/d e a inspeção posterior confirmou a sessão ativa. O guia CELLULAR_RIL.md substitui a pendência de documentação. A inspeção preservou a sessão existente; reconexão e NR continuam sem comprovação.
3. Resolvido: o relógio inicialmente marcava junho de 2024. Após conectar WLAN, NTP sincronizou e HTTPS passou. Os recibos anteriores continuam usando UTC do computador e não foram reescritos.
4. O inventário inicial tinha dez unidades em falha; a revalidação seguinte tinha 11. A inspeção mais recente registrou 14 e examinou unidade, status e journal de cada uma. [Causas, impacto e ensaio de boot/WLAN](BOOT_WLAN.md). Os números anteriores são históricos; nenhuma unidade foi mascarada ou desabilitada para limpar o diagnóstico.
5. `/data` apareceu com `noexec`. Evitar instalar ali extensões Python ou executáveis; a pasta temporária usada no ensaio funcionou. Escolher armazenamento persistente com permissões apropriadas para o evento.
6. Atualização de 02/11: captura UVC e detecção CPU executadas, com zero detecções ainda sem avaliação visual da foto. O preview ao vivo no HDMI passou após restart gráfico e reconexão física; HDMI após energização ainda precisa de ensaio. [Guia e evidências](CAMERA_HDMI.md). O primeiro fluxo autenticado AI Hub, o deploy CPU/GPU e a contingência foram aprovados em 01/11, conforme Qualcomm_AI_Hub_Training/PASSO_A_PASSO_AIHUB.md. HTP passou na imagem de referência, sem medir acurácia em dataset. A demo de câmera é captura seguida de inferência; não é um aplicativo de vídeo contínuo.

Os logs brutos de inventário permanecem no projeto local para revisão. O pacote de distribuição seleciona os resultados de AI e relatórios resumidos, para evitar levar automaticamente dados de interfaces/processos a todos os participantes.
