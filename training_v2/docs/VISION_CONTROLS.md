# D2-05…09 — Referências e controles adicionais

Em 01/11/2026, as cinco demos e a entrega HTP 2.51 foram revisadas e receberam **11 casos adicionais em CPU, GPU e HTP**, todos com aprovação funcional nos critérios declarados. São 33 combinações de caso/backend. A [galeria offline](../vision_controls/index.html) contém entrada preparada e as três saídas reais, com JSON por caso.

As imagens públicas foram selecionadas para o treinamento a pedido do proprietário, que não tinha fotos específicas do evento. Elas complementam as referências originais, que continuam preservadas. Não ficam pendentes fotos particulares para executar esta versão da aula.

No PPTX principal, procure **“Vision controls: cases and inputs”**, **“Vision controls: deploy and reproduce”** e **“HTP from the host: all 11 vision cases”** (93–95), seguidos de **“HTP on target: setup and results”** (96) e **“HTP in the target shell: 11 cases”** (97). A numeração corresponde a esta revisão de 1/11/2026 e pode mudar com futuras edições manuais. Os slides pertencem ao bloco de visão já previsto na agenda.

## Resultado e seleção para apresentar

| Caso/imagem | Resultado observado | Uso e limite |
|---|---|---|
| burger.jpg / classificação | `cheeseburger`, score 0,99609375 nos três backends | Referência positiva simples; top-3 com scores empatados em zero não tem interpretação útil. |
| pose.jpg / detecção | Pessoa nos três backends; IoU HTP/CPU 0,9589 | Pessoa inteira localizada; comparação com CPU não é ground truth anotado. |
| cat.jpg / detecção | Nenhuma pessoa acima de 0,5 nos três backends | O SSD classificou o gato como `dog` em CPU/GPU/HTP (scores ~0,699/0,688/0,675). Passa somente o controle de ausência de pessoa; a classe do animal está errada e serve como limitação do modelo. |
| male_full_height_hands.jpg / pose | CPU/GPU: 17 pontos acima de 0,5; HTP: 15 | **Preferir esta imagem para corpo inteiro.** Um tornozelo HTP teve confiança 0,467 e ficou oculto no desenho; não prometer 17 pontos sempre. Deslocamento mediano HTP/CPU 0,01459. |
| pose.jpg / pose | CPU/GPU: 14 pontos; HTP: 12 | A imagem de yoga é útil para discutir confiança, mas não demonstra todos os membros com o limiar padrão. |
| pose_lower_body_occluded.png / pose | CPU/GPU: 13 pontos; HTP: 11; deslocamento mediano HTP/CPU 0,01150 | Controle **sintético**: retângulo cinza cobre a parte inferior da imagem original. Examinar pontos visíveis; palpites atrás da oclusão não são validação da anatomia escondida. |
| fist.jpg / mão, crop 52 42 310 300 | `closed_fist` nos três backends | Presença CPU/GPU 0,99697; HTP 0,99484. Mão alinhada e recorte quadrado; regra geométrica, não classificador geral de gestos. |
| burger.jpg / mão, crop 77 0 402 325 | `no_hand` nos três backends | Presença CPU/GPU ~0,00113 e HTP 0,35803, todas abaixo de 0,5. Scores não são numericamente equivalentes nem calibrados. |
| male_full_height_hands.jpg / segmentação | Máscara de pessoa; IoU HTP/CPU 0,9624 | **Preferir esta imagem para as bordas.** A inspeção mostrou imprecisão nos dedos, sapatos e contorno; não é uma máscara anotada de verdade. |
| pose.jpg / segmentação | IoU HTP/CPU 0,7500 | O modelo perde partes dos braços/pernas nessa cena. Mantido como exemplo de limitação, não como demonstração de máscara completa. |
| cat.jpg / segmentação | Fração `person` = 0 nos três backends | Gato/sofá/fundo são classes válidas. Ausência de pessoa não significa ausência de todo foreground. |

O limiar de desenho/gesto/detecção ficou em 0,5. Segmentação usa argmax de 21 classes VOC. A avaliação HTP exige perfil detalhado com eventos/ciclos de acelerador positivos; a GPU exige log OpenCL e partição de delegate. Isso confirma a partição GPU; operadores residuais, como o pós-processamento SSD, podem continuar na CPU. Nenhum backend fez retry silencioso de toda a inferência na CPU.

As rodadas originais CPU/GPU/HTP usaram três inferências HTP, uma referência CPU e três invokes GPU após um aquecimento por caso. Este ensaio é funcional e visual; os tempos comparativos continuam no [benchmark de 45 sessões](../htp251/BENCHMARK.md). Não usar estes poucos invokes como novo benchmark.

## Mapa completo dos 11 casos

São **11 casos sobre 6 entradas distintas**, com **33 resultados anotados** (CPU/GPU/HTP). Há sete arquivos de imagem em `media/controls`: cinco fotos, um controle sintético e uma cópia alternativa `tfjs_pose.jpg`, que não cria um caso independente. Cada caso também tem um PNG da entrada preparada na galeria.

| `--case` | Tarefa | Entrada em `media/controls` | Crop |
|---|---|---|---|
| `burger-classification` | classification | `burger.jpg` | — |
| `full-body-detection` | detection | `pose.jpg` | — |
| `no-person-detection` | detection | `cat.jpg` | — |
| `full-body-pose` | pose | `pose.jpg` | — |
| `standing-full-body-pose` | pose | `male_full_height_hands.jpg` | — |
| `occluded-pose` | pose | `pose_lower_body_occluded.png` | — |
| `closed-fist` | gesture | `fist.jpg` | `52 42 310 300` |
| `no-hand` | gesture | `burger.jpg` | `77 0 402 325` |
| `person-segmentation` | segmentation | `pose.jpg` | — |
| `standing-boundary-segmentation` | segmentation | `male_full_height_hands.jpg` | — |
| `no-person-segmentation` | segmentation | `cat.jpg` | — |

Use qualquer identificador da primeira coluna com o comando de um caso abaixo. O runner aplica o crop registrado; não é preciso editar o fonte.

## O que entra no deploy

- **Entradas:** `media/controls/`, incluindo fotos, oclusão sintética, `cases.json`, `sources.json` e duas licenças: 11 arquivos de recurso no total.
- **`adb_lab.py push`:** copia a árvore `media` junto com o payload para `/opt/qb560d-training-payload`.
- **Provisionamento:** `provision.py prepare` registra a árvore `media` no `bundle-manifest.json`; `apply` a envia ao mesmo payload. O provisionamento completo é para preparação da caixa.
- **Runner do host:** envia as entradas preparadas e os DLCs necessários às pastas de execução em `/opt/qb560d-ai-htp251`, independentemente da cópia persistente usada pelos comandos manuais.
- **Runner local:** o TAR pronto `offline/htp-controls-target.tar.gz` leva modelos, imagens, referências e código para `/opt/qb560d-ai-htp251/htp-controls`; depois dessa cópia, prepara e processa tudo na própria caixa.
- **Galeria:** `vision_controls/` acompanha o ZIP principal para abrir no host. As 33 imagens anotadas são resultados de referência; as entradas do algoritmo vêm de `media/controls`.

A pasta persistente de controles foi enviada à caixa em 01/11/2026. Os 11 arquivos coincidiram por SHA-256, e o comando manual de classificação usando `media/controls/burger.jpg` retornou `cheeseburger`, score 0,99609375. Antes desse envio, os ensaios já tinham usado cópias em pastas de execução; isso não significava que a pasta persistente existia.

Provas verificáveis: [manifest do deploy](../provision_target/bundle-manifest.json), [manifest da distribuição](../RELEASE.json), [auditoria dos seis inputs](../evidence/vision-controls/deploy-confirmation/package-audit.json), [confirmação na caixa](../evidence/vision-controls/deploy-confirmation/summary.json) e [hashes lidos do target](../evidence/vision-controls/deploy-confirmation/target-hashes.json).

## Reprodução

### HTP diretamente no shell da caixa — sem host na execução

**Disponível e testado nos 11 casos.** O pacote local faz decode da foto, crop, resize e normalização na CPU da caixa; executa a CNN no HTP com `libQnnHtp.so`; depois faz decode/NMS/regras de gesto, comparação e desenho também na caixa. Não chama ADB, PowerShell, AI Hub ou scripts do computador durante a demo. ADB, SSH ou console serial servem apenas para abrir o shell Linux.

O modo local compara a saída com **referências TFLite CPU já gravadas e incluídas no pacote**. Não executa outra inferência CPU/GPU. Os controles e limites visuais da tabela acima continuam valendo. O fluxo pelo host, documentado depois desta seção, continua disponível para comparação com CPU executada novamente.

#### 1. Preparação e cópia offline — uma vez por caixa

Na caixa atual, o pacote já está instalado e validado em `/opt/qb560d-ai-htp251/htp-controls`. Pode ir direto ao passo 2.

Para outra caixa, prepare primeiro o target conforme [provision_target/README.txt](../provision_target/README.txt). Mesmo firmware não garante que os recursos de treinamento já tenham sido copiados. São necessários:

- Python 3.8; NumPy 1.24.4 e Pillow 10.4.0 privados em `/opt/qb560d-training-payload/.python-deps`;
- QAIRT/QNN ARM64 e bibliotecas HTP v68 em `/opt/qairt-isolated/2.51.40.260930`;
- espaço para o pacote e novas saídas: a rodada validada de 11 casos gerou aproximadamente 84 MB de resultados brutos.

No **PowerShell do host**, na raiz `training_v2`, copie o pacote pronto:

```powershell
$py = (Resolve-Path './provision_target/.venv/Scripts/python.exe').Path
& $py host/deploy_htp_target.py
```

O helper pede a senha root sem salvá-la, confere SHA-256, extrai em uma pasta própria e roda `check`. Resultado esperado: `TARGET_BUNDLE_READY`. O helper reconhece uma instalação idêntica; ao atualizar uma instalação reconhecida, preserva a anterior e seus resultados em `htp-controls.previous-<hash>`. Diretórios de outra origem são recusados.

O arquivo pronto é `offline/htp-controls-target.tar.gz` (cerca de 9,14 MB), com seu `.sha256`. Ele contém 40 arquivos: cinco DLCs, imagens com crops declarados no manifest, scripts locais, labels, contratos/anchors SSD e referências CPU/máscaras já gravadas. `MANIFEST.json` registra os hashes dos outros 39 arquivos. **O runtime QAIRT e os módulos Python são pré-requisitos do preparo da caixa; não estão dentro desse TAR.** Não precisa rebuild, download ou conversor para usar a distribuição pronta. `host/build_htp_target_bundle.py` serve para manutenção do pacote, não para cada aula.

#### 2. Login e conferência — shell Linux da caixa

Abra o shell por ADB interativo (`adb shell` com login root), SSH ou console. Os comandos daqui até o fim da seção são **Linux da caixa**, não PowerShell:

```sh
cd /opt/qb560d-ai-htp251/htp-controls
sh run.sh check
sh run.sh list
```

`check` precisa retornar `TARGET_HTP_READY`, 11 casos e 39 arquivos verificados. Ele confere os arquivos e a versão QNN. A execução real ainda precisa passar pelo perfil do acelerador em cada caso. Na caixa validada: Python 3.8.10, NumPy 1.24.4, Pillow 10.4.0 e QNN 2.51.40.260930230134. O wrapper seleciona `.python-deps`, `LD_LIBRARY_PATH` e `ADSP_LIBRARY_PATH` por processo; não exige `pip` nem mudança global no sistema.

#### 3. Comandos HTP dos 11 casos — todos no target

Escolha um caso ou execute as linhas desejadas:

```sh
sh run.sh run burger-classification
sh run.sh run full-body-detection
sh run.sh run no-person-detection
sh run.sh run full-body-pose
sh run.sh run standing-full-body-pose
sh run.sh run occluded-pose
sh run.sh run closed-fist
sh run.sh run no-hand
sh run.sh run person-segmentation
sh run.sh run standing-boundary-segmentation
sh run.sh run no-person-segmentation
```

Para os 11 em uma única rodada:

```sh
sh run.sh run-all
```

Cada caso usa três inferências HTP e o crop registrado no manifest. O comando imprime `PASS` por caso e termina com **`PASS_TARGET_HTP_CONTROLS`**, seguido de `EVIDENCE` e do diretório absoluto. Uma falha retorna exit code diferente de zero; runtime ausente ou perfil sem eventos/ciclos positivos não gera retry CPU.

#### 4. Ler os resultados na própria caixa

Para escolher um nome de saída que ainda não exista:

```sh
sh run.sh run closed-fist --output /opt/qb560d-ai-htp251/htp-controls/runs/fist-aula-01
cat /opt/qb560d-ai-htp251/htp-controls/runs/fist-aula-01/summary.json
cat /opt/qb560d-ai-htp251/htp-controls/runs/fist-aula-01/closed-fist/result.json
```

Use outro nome para repetir; o runner recusa sobrescrever uma pasta de resultados. Sem `--output`, ele cria um nome com UTC e identificador aleatório em `runs/`.

Em cada `<EVIDENCE>/<case>/`:

| Arquivo | Conteúdo |
|---|---|
| `input.png`, `input.raw` | Imagem preparada e tensor; SHA do tensor igual ao input revisado |
| `prediction.png` | Resultado desenhado na CPU da própria caixa |
| `result.json` | Classes/pontos/máscara/gesto, `backend: htp`, `passed`, comparação com CPU salva e perfil |
| `command.json`, `inference.log` | Comando QNN com `libQnnHtp.so`, sem fallback, e log real |
| `qnn/profile.csv` | Perfil detalhado; eventos/ciclos positivos também aparecem no JSON |
| `qnn/Result_0/`, `outputs.npz` | Tensores brutos e saídas interpretadas |

O `summary.json` da rodada registra `fresh_cpu_inferences: 0`, `gpu_inferences: 0`, os casos e a integridade do runtime. O programa não precisa de conexão de rede depois do deploy. Se usar SSH, mantenha o shell aberto até terminar ou use `nohup` para continuar após sair:

```sh
nohup sh run.sh run-all > /tmp/htp-controls-console.log 2>&1 < /dev/null &
tail -f /tmp/htp-controls-console.log
```

`Ctrl+C` no `tail` encerra a visualização; a rodada iniciada com `nohup` continua. As imagens são arquivos PNG: um shell de texto exibe o JSON/log, e a visualização da imagem usa um viewer disponível ou uma cópia posterior. Essa cópia não participa da inferência.

#### 5. O que foi validado

Rodada real `20261101T234943Z-shell11`: **11/11 aprovados, 33 execuções HTP**, preparação e pós-processamento locais, eventos/ciclos de acelerador positivos. O tensor preparado no target coincidiu por SHA-256 com o input revisado em todos os casos. Nenhuma inferência CPU/GPU foi executada pelo modo local. Os 21 arquivos do runtime conferidos localmente e os 48 hashes de runtimes/modelos do inventário de proteção permaneceram iguais.

A sessão ADB que lançou `nohup` foi fechada; outra sessão apenas recolheu os resultados completos depois. O ensaio não removeu fisicamente USB nem alimentação. O comando individual `closed-fist` também passou. Um teste com caminho de runtime inexistente falhou com exit code 1 e sem fallback CPU. [Resumo verificável](../evidence/vision-controls/target-shell/summary.json), [preflight](../evidence/vision-controls/target-shell/preflight.log) e [controle negativo](../evidence/vision-controls/target-shell/missing-runtime-negative.log).

Estes são controles funcionais contra as referências já revisadas, não um novo benchmark. Para medir CPU e HTP novamente e comparar tempos, use a metodologia de [BENCHMARK.md](../htp251/BENCHMARK.md).

### HTP pelo host — comandos dos 11 casos

Execute no **PowerShell do host**, na raiz `training_v2`. A CNN roda no **HTP da caixa**, usando QAIRT/QNN 2.51 (`qnn-net-run` e `libQnnHtp.so`). O runner faz uma inferência CPU separada como referência de correção; `--backend htp` não executa a rodada GPU e não pede fallback CPU para o grafo HTP. Pré/pós-processamento e renderização HTP continuam no host.

Defina os caminhos uma vez:

```powershell
$py = (Resolve-Path './provision_target/.venv/Scripts/python.exe').Path
$htpDemo = 'host/validate_vision_controls.py'
```

Escolha o comando do caso desejado. Cada comando abaixo pede a senha root no seu próprio processo e gera imagem/JSON/perfil novos:

```powershell
& $py $htpDemo run --backend htp --case burger-classification
& $py $htpDemo run --backend htp --case full-body-detection
& $py $htpDemo run --backend htp --case no-person-detection
& $py $htpDemo run --backend htp --case full-body-pose
& $py $htpDemo run --backend htp --case standing-full-body-pose
& $py $htpDemo run --backend htp --case occluded-pose
& $py $htpDemo run --backend htp --case closed-fist
& $py $htpDemo run --backend htp --case no-hand
& $py $htpDemo run --backend htp --case person-segmentation
& $py $htpDemo run --backend htp --case standing-boundary-segmentation
& $py $htpDemo run --backend htp --case no-person-segmentation
```

Para executar **todos os 11 casos em HTP em um só processo**, use:

```powershell
& $py $htpDemo run --backend htp
```

Resultado esperado: `PASS_HTP_REFERENCE_CONTROLS`. Para cada caso, confira `htp/result.json`: `backend: htp`, `passed: true` e eventos/ciclos positivos no campo `profile`. O PNG está em `htp/prediction.png`; logs e CSV do acelerador ficam na mesma árvore. A referência CPU fica em `reference/<tarefa>/`; `gpu` no resumo é `null` nesse modo. O rodapé do comando informa a pasta exata da rodada.

**Validação real do seletor em 01/11/2026:** os 11 casos passaram com `--backend htp`, três inferências HTP por caso e eventos/ciclos positivos no perfil. Não houve rodada GPU. Os 48 hashes dos runtimes/modelos originais continuaram iguais. A [evidência resumida](../evidence/vision-controls/htp-command-validation.json) registra os 11 resultados e a regressão do modo padrão CPU/GPU/HTP com `burger-classification`. A rodada completa está no host de preparação em `evidence/vision-controls/20261101-explicit-htp/`.

### Comparação CPU/GPU/HTP

PowerShell na raiz `training_v2`, com a caixa preparada e uma conexão ADB disponível:

```powershell
$py = (Resolve-Path './provision_target/.venv/Scripts/python.exe').Path
& $py host/validate_vision_controls.py run --backend all
Invoke-Item vision_controls/index.html
```

O primeiro comando executa a suíte e cria uma nova pasta em `evidence/vision-controls`. A galeria distribuída preserva a rodada revisada; para publicar novas rodadas, revise seus resultados antes de substituir essa referência. A senha root é pedida e não é salva.

Para somente um caso:

```powershell
& $py host/validate_vision_controls.py run --case standing-full-body-pose
& $py host/validate_vision_controls.py run --case closed-fist
```

O runner usa os mesmos DLCs da entrega HTP, sem conversão/download/AI Hub durante a aula. Ele verifica hashes e envia entradas para uma pasta de execução em `/opt/qb560d-ai-htp251`. Pré-processamento, decode, NMS SSD, regra de gesto e renderização do caminho HTP ficam no host; a CNN roda na caixa. Os caminhos TFLite CPU/GPU também rodam na caixa.

### Comandos diretos CPU/GPU na caixa

Para usar os arquivos manualmente no target, envie antes o payload atualizado:

```powershell
& $py host/adb_lab.py push
```

Depois do login root, no shell da caixa:

```sh
cd /opt/qb560d-training-payload
sh target/ai.sh classification --image media/controls/burger.jpg
sh target/ai.sh pose --image media/controls/male_full_height_hands.jpg
sh target/ai.sh gesture --image media/controls/fist.jpg --crop 52 42 310 300
sh target/ai.sh gesture --image media/controls/burger.jpg --crop 77 0 402 325
sh target/ai.sh segmentation --image media/controls/male_full_height_hands.jpg
```

Esses comandos `target/ai.sh` usam a CPU padrão. Para a GPU, acrescente `--backend gpu`. Para HTP diretamente na caixa, use `sh run.sh run <case>` no pacote local, conforme a primeira seção de reprodução. O fluxo alternativo pelo host usa `run --backend htp --case ...`. Os modelos originais e as bibliotecas do firmware/runtime mantiveram os **48 hashes conferidos** nas rodadas de proteção.

### Onde encontrar os resultados do fluxo pelo host

O runner dos 11 casos imprime a pasta nova em `evidence/vision-controls/<rodada>/`. Dentro de cada Case ID, a saída HTP fica em `htp/prediction.png` e `htp/result.json`; CPU em `reference/<tarefa>/` e GPU em `gpu/gpu/<tarefa>/`. A galeria distribuída contém a referência revisada, e não é substituída automaticamente por cada nova execução.

Os comandos manuais no target gravam PNG, JSON e tensores em `/opt/qb560d-training-payload/evidence/ai/<tarefa>/`, salvo se você escolher outro `--output`. Para recolher essa árvore para o host, execute em PowerShell:

```powershell
& $py host/adb_lab.py pull
```

O helper informa a pasta criada em `evidence/<horário>-target/evidence/`. Compare o novo JSON e a imagem anotada com os critérios e a referência da galeria.

## Fontes, créditos e evidência

- Imagens MediaPipe: [inventário oficial de testdata](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/testdata/vision/BUILD), downloads em `https://storage.googleapis.com/mediapipe-assets/`.
- A referência `tfjs_pose.jpg` também veio do [testdata oficial TensorFlow.js](https://github.com/tensorflow/tfjs-models/blob/master/pose-detection/test_data/pose.jpg); é uma cópia de origem alternativa, não outro caso independente.
- URLs exatas, SHA-256, dimensões e derivação do controle ocluído: `media/controls/sources.json`. Licenças/créditos acompanham `media/controls/LICENSE-MEDIAPIPE.txt` e `LICENSE-TFJS.txt`.
- Rodadas reais: `evidence/vision-controls/20261101-reference-controls/summary.json` e `20261101-standing-controls/summary.json`, com perfis, imagens e tensores completos no host de preparação.
- Distribuição resumida: `vision_controls/summary.json`, galeria e JSON por caso. Não é medição de acurácia em dataset, vídeo contínuo nem homologação da câmera USB.
