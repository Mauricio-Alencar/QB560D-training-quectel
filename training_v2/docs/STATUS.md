# Prontidão atual do treinamento — 02/11/2026

**Revalidação após reorganização concluída:** [relatório e evidências](VALIDACAO_POS_REORGANIZACAO.md). A candidata extraída, com venv próprio, passou em `apply/verify`, suíte local e cinco demos HTP. WLAN/SSH/SCP, Docker, 11 controles CPU/GPU/HTP, execução local HTP, benchmark e novo fluxo AI Hub passaram. A sessão celular e o tráfego passaram, mas `71/d` reportou `-4`: o retorno da API permanece como ressalva explícita. Os 48 hashes protegidos ficaram iguais. Captura UVC, detecção CPU e preview da webcam no HDMI passaram em 02/11. O HDMI foi recuperado após restart gráfico e reconexão física; funcionamento após nova energização ainda precisa de teste. O congelamento aguarda o OK dos slides.

BSP revalidado: **QDPA_Ubuntu20.04.003.51.303 V01**, Ubuntu 20.04.3, kernel 5.4.219-perf build 02/04/2026. Login root autenticado por ADB, uid=0. O laboratório atual usa `/opt/qb560d-training-payload`; NumPy/Pillow e os runtimes adicionais ficam em árvores privadas. [Relatório e reprodução](TARGET_RESULTS.md), [resumo verificável](../evidence/CURRENT_FIRMWARE.json).

**Estado:** as demos locais de aplicação, systemd, cinco modelos CPU, GPU, HTP, WLAN e as extensões QAIRT/gestos passaram no firmware atual. O fluxo celular manual agora está documentado: ativação71/d enviada pelo proprietário, consultas RIL e HTTP vinculado à RMNET verificados. O ensaio iperf3 passou com três pares UL/DL e controle de falha. A confirmação NR/SA/NSA e o ciclo de desativação/reconexão não foram validados; não são requisitos para avançar nesta fila. A webcam USB capturou JPEG e executou detecção CPU; preview ao vivo no HDMI foi confirmado pelo operador. A avaliação visual da detecção e o HDMI após nova energização permanecem pendentes. O fluxo AI Hub e a contingência de referência foram concluídos. O treinamento completo ainda precisa de ensaio cronometrado.

## Situação por demo

**HTP 2.51:** as cinco demos base foram migradas e aprovadas na caixa, além das duas extensões já validadas. [Procedimento](../htp251/README.md), [galeria](../htp251/results/index.html) e [evidência](../htp251/evidence/20261101T195905Z-ffc9e/summary.json). O fluxo original mantém pré/pós-processamento e NMS SSD no host. O novo [fluxo inteiramente no target](VISION_CONTROLS.md) passou os 11 controles com preparo, inferência HTP e pós-processamento locais; usa referências CPU já gravadas, sem inferência CPU/GPU nova. [Evidência local](../evidence/vision-controls/target-shell/summary.json). Essas rodadas cobrem imagens de referência, sem homologar a câmera. O cold boot foi aprovado em rodada independente posterior. AI Hub e desempenho celular foram concluídos em ensaios independentes posteriores.

**Tempos comparativos medidos:** [CPU/GPU TFLite BSP versus HTP QNN 2.51](../htp251/BENCHMARK.md), 45 sessões aprovadas, 3×50 inferências por backend/modelo após 10 aquecimentos. Runtimes preservados; 48 arquivos/entradas iguais no snapshot ampliado. GPU tem partição OpenCL confirmada, com NMS SSD residual na CPU. O slide “CPU/GPU vs HTP 2.51 latency” reúne a comparação; os slides de cada demo trazem o README e os tempos correspondentes.

| ID | Estado atual | Evidência/limite | Próximo passo |
|---|---|---|---|
| D1-00/01 inventário e acesso | Validado | Novo login root, BSP e kernel registrados | Repetir por caixa do evento |
| D1-02 boot/diagnóstico | Cold boot físico aprovado, uma rodada | Root 13,94 s; persistência e modelo CPU passaram;14 falhas BSP já conhecidas, sem novas unidades | [Tempos, escopo e diagnóstico](BOOT_WLAN.md); repetir por caixa |
| D1-03 Ubuntu/logs | Validado | Evento único de logger encontrado em journald | Ensaio do apresentador |
| D1-07 WLAN | Autoconnect pós-cold-boot aprovado | Conectou sem wlan up em 29,02 s; DHCP/DNS/HTTPS200; NTP inicialmente não e depois sim | Repetir no AP e nas caixas do evento |
| D1-08 SSH/SCP | Login e download validados | Chave conferida via ADB; SSH root uid=0 e SCP do identificador do firmware pela WLAN | Aplicar o [guia SSH](SSH.md); webcam USB-A e preview no HDMI passaram via SSH; ensaiar HDMI após energização, conforme [guia câmera/HDMI](CAMERA_HDMI.md) |
| D1-04 RIL manual | Referência disponível e consultas validadas | SIM pronto, TIM,70 registrado/RAT19,73 ativo;71/d executado pelo proprietário | Repetir ativação em cada caixa; confirmar NR se exigido |
| D1-05 caminho celular | HTTP vinculado validado | rmnet_data0, HTTPS200 e RX/TX; ping-I indisponível | Ensaiar repetição e separar DNS sistêmico |
| D1-06 iperf3 | Ensaio técnico aprovado | Três pares TCP de 10 s/1 fluxo pela RMNET; mediana UL 9,957 / DL 8,178 Mb/s; falha local preservada | Reconfirmar disponibilidade do servidor no evento; [resultados](../evidence/iperf-public/20261101T195153557423Z-measure/RESULTADOS.txt) |
| D2-00 contratos/runtime | Validado | Cinco contratos e hashes, Pillow privado reutilizado | Conferir em cada caixa |
| D2-01 app Python/C | Validado | Compilação C; três ciclos HTTP200/200/404 e parada | Ensaio com projeção |
| D2-02 systemd/update/rollback | Validado | Três ciclos 1.0.0→1.0.1→1.0.0; serviço parado/desabilitado ao final | Ensaio com projeção |
| D2-03 Docker | Validado na tarefa anterior | [Pacote separado](../demos/docker/README.md): instalação inicial/repetição offline e 61 verificações | Ensaio do apresentador |
| D2-04 AI Hub | Fluxo e contingência de referência aprovados | Compile/inference/profile, mesmo TFLite CPU/GPU local e pacote offline testados; replay 106 s pronto | Ensaio didático final de 50 min, item 7 |
| D2-05 classificação | CPU/GPU e HTP 2.51 validados | Military uniform no top-1; três inferências HTP e perfil positivo | [11 controles públicos revisados](VISION_CONTROLS.md); manter limites visuais |
| D2-06 detecção | CPU/GPU e HTP 2.51 validados | IoU de pessoa 0,9975; duas caixas de tie sobrepostas também na CPU | Pessoa/sem pessoa testados; [referências selecionadas](VISION_CONTROLS.md) |
| D2-07 pose | CPU/GPU e HTP 2.51 validados | Sete pontos no retrato parcial; deslocamento mediano normalizado 0,0107 | Corpo inteiro e oclusão testados; CPU/GPU 17 e HTP 15 pontos na pessoa em pé |
| D2-08 gesto recortado | CPU/GPU e HTP 2.51 validados | open_hand e 21 landmarks; regra geométrica no host | Punho fechado e sem mão passaram; scores/presença não equivalentes |
| D2-09 segmentação | CPU/GPU e HTP 2.51 validados | Máscara de pessoa, IoU 0,9763 contra CPU | Pessoa/sem pessoa e bordas revisadas; dedos/pés e yoga mantêm erros visuais |
| D2-10 câmera opcional | Captura UVC, detecção CPU e preview HDMI executados | Webcam 1224:2a25 em video0; CPU mediana 35,613 ms; zero detecções, sem revisão semântica da foto | [Reprodução e recuperação HDMI](CAMERA_HDMI.md); verificar HDMI após energização |
| D2-11/12 comparação legada MobileNet V1 | SNPE 2.26 / GPU validados, 3 sessões/backend | HTP1,109 ms / CPU DLC6,701 ms, 34 DSP/zero CPU; OpenCL confirmado | Manter separada dos perfis QAIRT 2.51 |
| Extensão MobileNet V2/QAIRT2.51 | Validada na referência | CPU/HTP Samoyed, cinco saídas por backend; scores diferentes | Manter metodologia separada da V1 |
| Extensão sete gestos HTP | Validada 7/7 | 21 execuções de grafo com ciclos HTP positivos | Usar HTP; não promover o resultado CPU anterior |

## Verificação específica de 5G, 01/11/2026

Resultado: **LTE/LTE_CA observado; NR5G não confirmado nesta sessão**. Foram quatro consultas RIL 70 e cinco QENG, incluindo três durante tráfego pela RMNET. RIL 70 retornou registro 1 / RAT 19; QENG mostrou LTE/FDD, banda 7. C5GREG retornou 0,0, sem registro 5GS, o que isoladamente não exclui NSA. QNWINFO,QENDC,QCAINFO e a consulta QNWPREFCFG mode_pref retornaram ERROR neste BSP/caminho.

Dois downloads limitados de 2 MiB passaram com HTTP 200 e origem celular. Serviram para consultar o rádio em atividade, sem medir throughput. RIL 75 retornou 11, que o enum AOSP denomina LTE_ONLY; a correspondência específica do BSP precisa ser confirmada antes de atribuir causa ou mudar configuração. Sessão e configuração foram preservadas. Veja [passos e interpretação](CELLULAR_RIL.md#5a-focused-check-is-this-session-actually-using-5g), [evidência](../evidence/ril/20261101-5g-verification/summary.json) e [respostas](../evidence/ril/20261101-5g-verification/queries.txt). O ensaio posterior de iperf3 passou. A confirmação NR positiva e o ciclo de reconexão permanecem não testados, fora da fila atual por decisão do proprietário.

## Encaixe na agenda

Navegação no PPTX atual: sumário do Dia 1 no slide 4, do Dia 2 no slide 40 e das cinco demos no slide 91. Cada tema informa início/fim com links internos. O [mapa numerado completo](MAPA_SLIDES.txt) preserva os mesmos horários da agenda; os slides 96–97 mostram a execução HTP local, e 111–115 são referência de preparação.

Os horários e IDs permanecem em [AGENDA.md](AGENDA.md), [DAY1.md](DAY1.md) e [DAY2.md](DAY2.md): **300 minutos por dia**, incluindo intervalo. No Dia 1, os50min de D1-04 incluem o bring-up manual e debug RIL. D1-05 mantém50min para Linux/rotas/tráfego. D1-06 passou usando servidor público autorizado; sua disponibilidade/carga deve ser reconferida no evento. WLAN não substitui a aceitação do caminho celular.

No Dia 2, aplicação/systemd/Docker ocupam os primeiros 120 minutos. O bloco 02:10–02:50 reúne contratos e a comparação MobileNet V1 CPU/GPU/HTP. O AI Hub mantém 50 minutos, com compile/inference/profile e artefato CPU/GPU aprovados, além de pacote offline e vídeo de referência. As cinco demos mantêm 8/10/10/12/10 minutos dentro dos 50 minutos seguintes, agora com o caminho HTP 2.51 e a galeria ao lado da referência CPU. A extensão de sete gestos pode substituir/aprofundar a demonstração de gesto conforme decisão do apresentador; ela não cria tempo adicional na agenda. Câmera permanece opcional no bloco final.

## Material atualizado e preparação restante

- Runners ADB usam o login root e descobrem o cliente portátil. `--transport-id` resolve seriais repetidos. O caminho persistente é compartilhado, com alternativa explícita `/tmp`.
- `host/rehearse_local.py` repete os testes locais. O pacote inclui o subconjunto offline SNPE2.26, licença/lock e decoder Windows para o profile HTP.
- O guia WLAN cobre a recriação pós-reflash e a correção restrita a wlan0. Credenciais permanecem fora do material.
- Os guias de câmera distinguem os nós de codec e a tentativa QMMF com tempo limite; em 02/11 a webcam USB produziu JPEG validado e o preview no HDMI funcionou. A detecção CPU executou sem objetos; revisão semântica ainda pendente. [Resultados e reprodução](CAMERA_HDMI.md).
- A apresentação principal foi atualizada com os caminhos de /opt, login ADB e resultados desta revalidação. Os slides atuais, incluindo os acréscimos manuais e o slide WLAN, mantêm sua ordem, imagens e template. O arquivo atual continua como fonte de verdade; a geração inicial não deve sobrescrevê-lo.
- `provision_target/README.md` prepara uma caixa recém-gravada. Se os fontes forem atualizados, repita `prepare --offline` e gere um novo plano antes de um futuro `apply`; planos e manifests antigos estão vinculados aos hashes anteriores.
- Cold boot e reconexão WLAN passaram em uma rodada física. A webcam USB e o preview HDMI passaram em 02/11; ainda faltam revisão semântica da foto, ensaio HDMI após energização, aceitação por caixa e ensaio didático cronometrado. Os 11 controles públicos de visão passaram; há limites visuais documentados em VISION_CONTROLS.md. O ensaio iperf3 já passou; NR e repetição de ativação/reconexão ficam como limites não homologados, fora da fila atual por decisão do proprietário. O [guia RIL](CELLULAR_RIL.md) cobre o fluxo manual e todas as opções do menu com seu estado de teste.

A aprovação cobre as referências descritas e o firmware medido; cada caixa do treinamento deve passar pelo mesmo inventário e ensaio local.

## Pendências para treinamentos futuros

O fluxo completo do AI Hub com uma MobileNet V2 real, da compilação ao deploy e teste no HTP com QAIRT 2.51, foi reservado para um **treinamento futuro**, preservando os runtimes atuais e prevendo guia/slides com comandos, imagens e resultados. Este item não integra a agenda nem a aceitação do treinamento atual; não foi iniciado.
