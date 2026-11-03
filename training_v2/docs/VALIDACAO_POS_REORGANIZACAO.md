# Validação após a reorganização das pastas

Rodada iniciada em 01/11/2026, horário de São Paulo; recibos de 02/11/2026 UTC. Caixa QB560D-EU/QCM6490, BSP QDPA_Ubuntu20.04.003.51.303 V01, kernel 5.4.219-perf. Os comandos do host partem de `training_v2`; os diretórios instalados em `/opt` continuam os mesmos.

**Validação concluída com ressalva RIL; entrega sem congelamento.** O congelamento depende do OK do proprietário para os slides. A sessão celular funciona, mas o retorno da API de ativação exige a ressalva descrita abaixo. A câmera permanece opcional e sem captura homologada.

## Resultado dos exercícios

| Fluxo | Resultado observado nesta rodada |
|---|---|
| Estrutura e caminhos | PASS: 96 arquivos Python, nove entrypoints CLI e quatro PDFs AI Hub. A extração testada tinha 108 slides; durante a finalização o PPTX recebeu uma edição independente para 115 slides. Os links e os textos de caminhos da versão corrente também passaram; sua aprovação visual continua pendente. |
| Extração e host novo | SHA-256 do ZIP conferido. Extração independente e `.venv` criada do zero com NumPy 2.3.5/Pillow 12.3.0 dos wheels offline; `HOST_READY`. Validação de caminhos passou usando o Python da extração. |
| Provisionamento | `inspect`, `prepare --offline`, `plan`, `apply` e `verify` passaram também na candidata extraída corrigida, com seu próprio Python e lançados de outro diretório. `verify`: 82 comandos, MobileNet CPU/HTP e 7/7 gestos. A suíte local e as cinco demos HTP também passaram a partir dessa extração. |
| Aplicação e systemd | Três ciclos de HTTP, compilação C, atualização e rollback passaram. O evento de diagnóstico passou após a correção de transporte para journald. |
| Docker | Deploy offline e HTTP passaram. Ensaio de três ciclos, update/rollback, falta de imagem, reload offline e rede `none`: 61 checks, PASS após a correção de diretório do checksum. |
| Cinco demos HTP 2.51 | Classificação, detecção, pose, mão recortada e segmentação: PASS, perfil do acelerador e comparação com a referência CPU. |
| Controles de visão | 11 casos em CPU/GPU/HTP, 33 combinações aprovadas. Outros 11 casos passaram com preparo, inferência HTP e pós-processamento inteiramente na caixa. |
| Comparação legada | SNPE 2.26: 12 sessões aprovadas; profile com 34 entradas DSP e zero CPU. Runtime preservado. |
| Benchmark QAIRT 2.51 | 45 sessões aprovadas: três sessões de 50 inferências por modelo/backend, depois de dez aquecimentos. |
| Qualcomm AI Hub online | Novo compile `jp44344lp` e inference/profile `j5mk8kkqp`: PASS no Dragonwing RB3 Gen 2 Vision Kit hospedado, com erro máximo 4,00543e-05. |
| Artefato AI Hub na caixa | Mesmo TFLite baixado, CPU e GPU OpenCL: PASS. Erros máximos 1,49e-08 e 2,98e-08. Kit offline independente também passou nos dois backends; seis arquivos conferidos no target. |
| WLAN | `status`, `check`, `down/up`, rádio off/on e recuperação: PASS, DNS e HTTPS 200. Perfil salvo manteve o mesmo hash. Coexistência com a sessão RMNET passou. |
| Celular | RIL mostrou SIM pronto e registro LTE. Sessão confirmada por `73`, HTTPS vinculado à RMNET e três pares iperf3 passaram. A API `71/d` reportou erro `-4`; não classificar seu retorno como aprovado. |
| SSH/SCP | Chave pública obtida por ADB e verificação estrita: login root, identidade da caixa, payload em `/opt` e download de `/etc/build_version` passaram. |
| Testes locais | 23 testes de host e 14 de provisionamento: PASS, incluindo quatro regressões de caminhos Windows acima de 260 caracteres. |
| Integridade | 48 arquivos de runtimes/modelos conferidos antes e depois: mesmos hashes, nenhuma adição ou alteração nesse conjunto protegido. |

## Correções realizadas e revalidadas

1. `ai/workbench.py`: configura stdout/stderr em UTF-8 para os símbolos de progresso do SDK, incluindo saída redirecionada. O primeiro compile foi registrado, mas a espera local falhou na codificação cp1252; a nova execução completou compile, inference/profile, download e teste local.
2. `target/diagnostics.sh`: envia o evento diretamente a journald com `systemd-cat` quando disponível. Nesta imagem, `/dev/log` é um socket separado de `/run/systemd/journal/dev-log`; `logger` retornar zero não comprova recebimento no journal. A checagem continua exigindo o marcador real e informa o transporte utilizado.
3. `demos/docker/target/rehearse.py`: executa comandos com `cwd` no diretório da demo. O checksum contém caminhos relativos; o ensaio passou novamente lançado a partir de `/`.
4. Transporte, logs e análise em caminhos longos: `host/provision_session.py` passa a reutilizar a cópia temporária curta de `host/adb_transport.py`. O analisador MobileNet e o runner de gestos normalizam os caminhos Windows estendidos. As falhas de cópia, leitura de tensores e gravação de profiling foram reproduzidas numa extração mais profunda e corrigidas; os quatro testes de regressão passaram. Um gesto completo de três redes também passou com o caminho de log de 278 caracteres, seguido de `apply/verify` completos.
5. Guias HTP/AI Hub: corrigidas instruções antigas que apresentavam `/tmp` como instalação principal. O subconjunto SNPE 2.26 e o decoder ficam em `offline/snpe226`; a instalação atual usa `/opt/qb560d-training-payload/runtime/qairt226-ubuntu`.

As três versões anteriores dos scripts enviados à caixa foram preservadas nas respectivas pastas de evidência privadas do target. Nenhuma biblioteca global de runtime foi substituída.

## Ressalvas que continuam explícitas

- **RIL:** `71/d` imprimiu `QLRIL_SetupDataCall failed with return:-4`. O `73` seguinte mostrou call 0 ativa e o tráfego passou. Não foi inferida a causa do código, nem repetido setup sobre uma call ativa. APN, preferência de rádio e teardown não foram alterados para ocultar o retorno. O fluxo de dados está aprovado; o retorno da API não está.
- **Rádio:** LTE foi observado, sem confirmação de NR/SA/NSA. A aceitação atual não exige forçar NR.
- **Perfil Wi-Fi:** a rodada reutilizou o perfil já autorizado; não recriou o perfil nem exportou a senha. O cadastro de SSID/senha em outra unidade continua interativo pelo `nmcli --ask`.
- **Câmera:** o probe terminou com `CONFIG_REQUIRED`, exit 78, por ausência do nó de captura padrão. Não há JPEG novo homologado. Retirada física da USB-C, enumeração USB-A e comparação HDMI continuam fora desta rodada.
- **Boot e evento:** esta rodada não executou novo corte físico de alimentação nem substitui a aceitação de cada caixa ou o ensaio didático dos dois dias.
- **Pacote:** o ZIP em `dist` permanece preservado como revisão anterior às correções desta rodada. Uma candidata extraída recebe as correções para a verificação final; gerar o ZIP definitivo somente depois do OK dos slides, mantendo a ressalva RIL explícita.

## Resultados e evidências

- [Resumo publicável desta rodada](../evidence/reorganization-validation/20261102/release/summary.json).
- [Rede, RIL e iperf3](../evidence/reorganization-validation/20261102/release/network.json).
- [AI Hub online, deploy CPU/GPU e kit offline](../evidence/reorganization-validation/20261102/release/aihub.json).
- [Benchmark de 45 sessões](../evidence/reorganization-validation/20261102/release/benchmark.json).
- [Integridade dos runtimes/modelos](../evidence/reorganization-validation/20261102/release/integrity.json).
- [Galeria das cinco demos HTP](../htp251/results/index.html), com saídas reais da caixa.

Os recibos completos registram falhas iniciais e as repetições aprovadas, em `training_v2/evidence/reorganization-validation/20261102` no computador de preparação. A distribuição seleciona somente os resumos da subpasta `release`, sem os logs brutos de rede/RIL. Os caminhos de execução continuam isolados em `/opt/qb560d-training-payload`, `/opt/qb560d-docker-demo`, `/opt/qb560d-ai-htp251` e `/opt/qairt-isolated/2.51.40.260930`.
