# Cinco demos no HTP com QAIRT 2.51

As cinco demos originais foram migradas e executadas na QB560D-EU/QCM6490, no HTP v68, com **QNN 2.51.40.260930230134**. A rodada final de 01/11/2026 passou para classificação, detecção, pose, mão recortada e segmentação. Cada rede executou três inferências com perfil detalhado. Os modelos e runtimes anteriores continuam disponíveis.

Abra a [galeria de resultados reais](results/index.html). Ela mostra entrada preparada, referência TFLite CPU, saída HTP, JSON e perfil do acelerador. As imagens são produzidas a partir das saídas da caixa. O runner atualiza a galeria após cada teste aprovado.

Na apresentação atual, use os sumários clicáveis dos **slides 4** (Dia 1), **40** (Dia 2) e **91** (visão). O runner compartilhado está no **92**; os controles e os dois fluxos de execução nos **93–97**; classificação no **98**; detecção no **99**; pose no **100**; mão recortada no **101**; galeria de sete gestos nos **102–104**; segmentação no **105**; validação HTP no **106**. No bloco anterior de runtime, a comparação legada SNPE 2.26 está no **82**, a latência QAIRT 2.51 no **83** e a referência CPU no **84**. O material de preparação MediaPipe está nos **111–115**, sem novo bloco na agenda. Consulte o [mapa completo](../docs/MAPA_SLIDES.txt) após futuras inserções manuais.

## Execução inteiramente no target

O pacote offline `../offline/htp-controls-target.tar.gz` acrescenta um fluxo independente do host para os 11 controles das cinco demos. Após uma cópia inicial com `host/deploy_htp_target.py`, no shell Linux da caixa:

```sh
cd /opt/qb560d-ai-htp251/htp-controls
sh run.sh check
sh run.sh run closed-fist
sh run.sh run-all
```

A CPU da própria caixa prepara a imagem e interpreta/desenha as saídas; a CNN executa no HTP. A conferência usa as referências TFLite CPU já incluídas, sem inferência CPU/GPU nova. Os 11 casos passaram, com perfis positivos. [Passo a passo, todos os comandos e resultados](../docs/VISION_CONTROLS.md). As seções seguintes descrevem o fluxo anterior **pelo host**, que continua executando uma referência CPU nova.

## O que roda onde no fluxo pelo host

| Demo | Modelo | Execução nova |
|---|---|---|
| Classificação | MobileNet V1 | CNN no HTP; top-3 e desenho no host |
| Detecção | SSD MobileNet V1 | CNN até caixas/scores no HTP; decode de anchors e NMS no host |
| Pose | PoseNet | CNN no HTP; decoder de 17 pontos e desenho no host |
| Mão recortada | Hand Landmark Lite | CNN no HTP; regra geométrica de gesto e desenho no host |
| Segmentação | DeepLabV3 | CNN no HTP; argmax e sobreposição da máscara no host |

O runtime é o existente em `/opt/qairt-isolated/2.51.40.260930`. Os novos DLCs e execuções ficam em **`/opt/qb560d-ai-htp251`**, com marcador de propriedade e nomes de modelo vinculados ao SHA-256. O script seleciona as bibliotecas por processo. Ele não substitui os runtimes do BSP, o SNPE 2.26, o QAIRT 2.51 instalado ou os modelos TFLite.

Os dois outros fluxos do treinamento, MobileNet V2 e MediaPipe de sete gestos, já estavam validados no HTP/QNN 2.51 e continuam disponíveis. Assim, os sete casos de IA têm um caminho HTP 2.51 validado. A comparação legada da MobileNet V1 em SNPE 2.26 permanece como exercício separado.

## Hands-on pelo computador host

Use o pacote completo `aibox_training`, uma caixa por vez e o preparo de host/target do `provision_target/README.md`. São necessários Python 3.12 com NumPy/Pillow, ADB e os modelos/runtime do pacote. **O aluno não precisa instalar TensorFlow, ONNX ou conversores Qualcomm para executar os DLCs prontos.** A caixa não precisa acessar a Internet.

Abra PowerShell na raiz `training_v2`:

```powershell
$py = (Resolve-Path './provision_target/.venv/Scripts/python.exe').Path
$adb = (Resolve-Path './tools/platform-tools/adb.exe').Path
```

Para conferir os arquivos atuais sem instalar modelos:

```powershell
& $py host/htp251_workshop.py inspect --adb $adb
```

Para transferir os novos modelos para a pasta isolada:

```powershell
& $py host/htp251_workshop.py deploy --adb $adb
```

`deploy` verifica hashes e transfere os modelos; seu resultado é `MODELS_DEPLOYED_NOT_TESTED`. Ele não declara sucesso de inferência.

Execute as cinco demos e gere os resultados:

```powershell
& $py host/htp251_workshop.py test-all --adb $adb
```

Resultado esperado: **`PASS_ALL_MIGRATED_HTP_DEMOS`**. O script pede a senha Linux de root, sem guardá-la. Para cada demo, executa primeiro o TFLite original na CPU da caixa como referência e depois o DLC no HTP. Exige perfil de acelerador, saídas finitas e as verificações visuais/semânticas descritas abaixo. Não solicita fallback CPU no backend HTP.

Para executar uma demo por vez:

```powershell
& $py host/htp251_workshop.py run classification --adb $adb
& $py host/htp251_workshop.py run detection --adb $adb
& $py host/htp251_workshop.py run pose --adb $adb
& $py host/htp251_workshop.py run gesture --adb $adb
& $py host/htp251_workshop.py run segmentation --adb $adb
```

Abra a galeria no navegador:

```powershell
Invoke-Item htp251/results/index.html
```

Clique nas imagens para ampliá-las. As cópias estáveis ficam em `results/<demo>/htp.png`, `cpu-reference.png`, `input.png`, `result.json` e `profile.csv`. Os arquivos brutos, tensores e logs permanecem em `htp251/evidence/<execução>/`. O ZIP atualizado do treinamento inclui os cinco DLCs revisados, a galeria e a evidência da rodada aprovada; o runtime e o transporte ADB continuam no pacote completo de preparação.

## Outras imagens

```powershell
& $py host/htp251_workshop.py run detection --adb $adb --image C:/fotos/pessoa.jpg
& $py host/htp251_workshop.py run segmentation --adb $adb --image C:/fotos/pessoa.jpg
& $py host/htp251_workshop.py run gesture --adb $adb --image C:/fotos/mao.jpg --crop 100 50 400 350
```

O recorte da mão deve ser quadrado, estar dentro da foto e conter uma mão alinhada. O renderer mantém o redimensionamento dos modelos originais. Os critérios automáticos foram preparados para as referências do treinamento: a detecção procura uma pessoa, a segmentação compara a classe pessoa e a pose precisa de pontos visíveis. Uma foto de outro tipo pode executar corretamente e receber `QUALITY_CHECK_FAILED`; examine imagem, JSON e a referência CPU antes de aceitar uma nova cena.

## Resultados medidos

**Latência comparativa CPU/GPU/HTP 2.51:** houve uma rodada adicional com 45 sessões aprovadas, 3 por backend/modelo, 10 aquecimentos e 50 inferências medidas por sessão. [Tabela completa, condições e comando para reproduzir](BENCHMARK.md). CPU/GPU usam TFLite 2.8.4 do BSP; HTP usa QAIRT/QNN 2.51. Para o SSD, a medida HTP exclui NMS no host, enquanto o TFLite inclui o pós-processamento interno. Os tempos abaixo nos perfis da rodada funcional anterior não são usados como benchmark comparativo.

Evidência final: `evidence/20261101T195905Z-ffc9e/summary.json` e `runtime-integrity.json`.

| Demo | Resultado HTP na referência | Evidência de execução |
|---|---|---|
| Classificação | `military uniform`, top-1 igual à CPU; score 0,8711 | 3 eventos de execução, 99 eventos com ciclos positivos |
| Detecção | Pessoa e gravata; IoU da pessoa **0,9975** contra CPU | 3 eventos de execução, 153 eventos com ciclos positivos |
| Pose | Pontos de cabeça/ombros preservados; deslocamento mediano normalizado **0,0107** | 3 eventos de execução, 93 eventos com ciclos positivos |
| Mão recortada | `open_hand`, igual à CPU | 3 eventos de execução, 195 eventos com ciclos positivos |
| Segmentação | Máscara de pessoa; IoU **0,9763** contra CPU | 3 eventos de execução, 210 eventos com ciclos positivos |

A integridade conferiu 40 arquivos dos runtimes/modelos existentes, sem mudanças. Nas execuções futuras o snapshot também considera os modelos das extensões anteriores quando presentes. O SNPE 2.26 é opcional para este fluxo; sua ausência não bloqueia a execução das cinco demos 2.51.

Os testes locais têm oito casos, incluindo normalização da entrada, input SSD em pixels float, rejeição de recortes inválidos, buffers ambíguos/NaN e rejeição de caixas falsas duplicadas. Execute:

```powershell
& $py host/test_htp251_workshop.py
```

Não usamos esses scores ou IoUs como acurácia de dataset. Os perfis detalhados e três inferências comprovam execução e funcionamento nas amostras; não são um benchmark controlado de FPS/latência. A detecção conserva duas caixas de gravata sobrepostas, também presentes na referência CPU. A foto de pose é um retrato parcial e não valida o corpo inteiro.

## Conversão reproduzível, somente para preparação

Para ensinar cada etapa, use o [roteiro manual TFLite → ONNX validado → DLC → HTP](../docs/TFLITE_PARA_HTP_PASSO_A_PASSO.md). Ele abre os comandos de download/hash, exportação, ajustes ONNX, calibração, conversor/quantizador, transferência, execução e aceitação, com classificação acompanhada e estudo do SSD. Os candidatos ficam em uma pasta nova, preservando os modelos homologados.

Esta seção é para quem reconstrói os DLCs. Mantenha os dois ambientes Python separados. O Python 3.8/TensorFlow 2.13 usado na exportação segue `host/requirements-snpe-conversion.txt`. O SDK 2.51 usa outro ambiente Python 3.12, definido em `host/requirements-qairt251-conversion.txt`. Nada precisa ser instalado no Python global ou no target.

1. Prepare o Python 3.8 isolado, conforme `docs/HTP_DSP.md`, e confira os arquivos originais de `models/`.
2. Baixe o subconjunto oficial do SDK 2.51. O downloader usa HTTP Range, CRC do ZIP e registra SHA-256 dos membros em `.build/sdk251-host/receipt.json`.

```powershell
& $py host/fetch_qairt251_converter.py
& $py -m venv .build/qairt251-py312
$converter = (Resolve-Path '.build/qairt251-py312/Scripts/python.exe').Path
$site = '\\?\' + (Resolve-Path '.build/qairt251-py312/Lib/site-packages').Path
& $converter -m pip install --upgrade --target $site -r host/requirements-qairt251-conversion.txt
```

O prefixo de caminho longo evita o limite do Windows durante a instalação dos testes internos do ONNX nesta raiz OneDrive. O wrapper `qairt251_entry.py` configura PATH/DLLs/temporários somente no processo. As ferramentas originais do SDK permanecem sem alteração.

```powershell
$exporter = (Resolve-Path '.build/python38-host/python.exe').Path
& $exporter host/inspect_htp251_sources.py
& $exporter host/export_htp251_models.py
& $converter host/convert_htp251_models.py
& $py host/htp251_workshop.py test-all --adb $adb
```

Os contratos, hashes, calibração, logs e comandos estão em `source-contracts.json`, `export-results.json`, `models.json` e `models/<demo>/`. A classificação retém os encodings w8a8 de origem; pose/mão/segmentação e a detecção recalibrada usam ativações de 16 bits e pesos de 8 bits. `model-info.csv` registra os tipos efetivos de cada tensor.

A leitura direta de TFLite pelo conversor Windows do SDK exigiu TVM indisponível no subconjunto Windows público; usamos ONNX. A tentativa inicial do SSD que conservava os encodings antigos executou, mas gerou caixas extras. A versão final dequantiza a CNN, remove os quantizadores de ativação de origem e faz nova calibração w8a16, mantendo as mesmas tarefas/pesos de origem. O grafo inclui a normalização SSD: sua entrada é RGB em pixels float 0–255; os demais perfis usam os floats normalizados registrados. O runner segue o modo de entrada do manifesto.

O controle adicional QNN CPU não é a referência de aceitação: os três modelos w8a16 testados tiveram falha de preparação nesse backend e o SSD com encodings antigos mostrou diferenças incorretas. Esses resultados exploratórios estão preservados em `evidence/20261101T195126Z-4d2f4/`. Para diagnóstico explícito, use `--qnn-cpu-control`; a comparação principal permanece com os TFLite CPU originais e o HTP 2.51.

## Preservação e fontes

Os snapshots usam SHA-256 antes/depois. O deploy recusa diretório alheio e arquivos com conteúdo diferente; cada DLC novo recebe nome com hash. Todos os dados novos estão em `/opt/qb560d-ai-htp251`. Para voltar às demos anteriores, use seus comandos originais; nenhum PATH global, biblioteca, serviço, firmware, NTP ou configuração de rede foi substituído por esta migração.

Fontes: modelos e labels em `ai/profiles.json`, `models/models.lock.json` e `media/sources.json`; SDK público Qualcomm `2.51.40.260930`, URL registrada pelo downloader; referências de ferramentas no [manual QAIRT](https://docs.qualcomm.com/bundle/publicresource/topics/80-63442-10/general_overview.html). A galeria também mostra as evidências já existentes de MobileNet V2 e MediaPipe quando esses arquivos acompanham o workspace.
