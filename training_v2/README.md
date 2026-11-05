# QB560D-EU: treinamento dos dias 1 e 2

Esta é a entrada única do treinamento. Abra PowerShell nesta pasta `training_v2`; os comandos abaixo usam essa base. Plataforma homologada: QB560D-EU/QCM6490, Ubuntu 20.04.3 e acesso root por ADB. O conteúdo de Yocto é conceitual, com comandos e recipes como referência, sem executar builds ou labs de Yocto.

No Windows, extraia o pacote em uma pasta curta, por exemplo `C:\QB560D`, para evitar o limite de caminhos de ferramentas e os nomes longos dos PDFs do fabricante. Crie o ambiente Python depois da extração; não copie uma `.venv` de outra pasta.

## Download desta versão

[Pacote completo v0.12.2](https://github.com/Mauricio-Alencar/QB560D-training-quectel/releases/download/v0.12.2/QB560D_EU_Training_0.12.2_20261104-release.zip) e [SHA-256](https://github.com/Mauricio-Alencar/QB560D-training-quectel/releases/download/v0.12.2/QB560D_EU_Training_0.12.2_20261104-release.zip.sha256). Os [detalhes da release](https://github.com/Mauricio-Alencar/QB560D-training-quectel/releases/tag/v0.12.2) identificam a versão publicada.

O pacote inclui as correções Docker/QAIRT da revisão 0.12.2 e foi validado em uma extração independente, com ambiente Python criado no destino e dependências offline. Para conferir uma cópia recebida e entender falhas de extração no Windows, consulte [download e extração](docs/DOWNLOAD_DIAGNOSTICS.md).

## 1. Preparar o computador

Windows x64, Python 3.12 x64, driver Quectel ADB e cabo USB de dados. O cliente ADB está em `tools/platform-tools`. Não é necessário Docker Desktop, WSL ou SDK Yocto para os labs locais.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File provision_target/setup_host.ps1 -InstallPython
$py = (Resolve-Path provision_target/.venv/Scripts/python.exe).Path
$adb = (Resolve-Path tools/platform-tools/adb.exe).Path
& $adb devices -l
```

O helper recria o ambiente local e instala NumPy/Pillow nas versões fixadas. Os wheels Windows acompanham `offline/host-wheels`; instalar o próprio Python pode exigir Internet. O ambiente do cliente AI Hub é separado, conforme o guia do módulo.

## 2. Preparar uma caixa nova

Leia o [procedimento de provisionamento](provision_target/README.md). Conecte uma caixa e execute:

```powershell
& $py provision_target/provision.py inspect --adb $adb
& $py provision_target/provision.py prepare --offline
& $py provision_target/provision.py plan
```

Revise `provision_target/plan.json`: o estado deve ser `READY_TO_REVIEW`, sem blockers. Para a instalação planejada e sua verificação:

```powershell
& $py provision_target/provision.py apply --adb $adb
& $py provision_target/provision.py verify --adb $adb
```

`prepare` e `plan` trabalham no host. `apply` instala na caixa e pede a senha root. A distribuição inclui os componentes fixados para preparação offline. Um plano salvo corresponde a um inventário específico; outra caixa exige nova inspeção e plano.

## 3. Acompanhar a aula

| Material | Entrada |
|---|---|
| Apresentação única | [PPTX principal](slides/QB560D_EU_Training.pptx) |
| Agenda, horários e navegação | [AGENDA](docs/AGENDA.md) e [mapa atual dos slides](docs/MAPA_SLIDES.txt) |
| Dia 1: plataforma, Linux e celular | [Roteiro do Dia 1](docs/DAY1.md) |
| Dia 2: aplicações, Docker e IA | [Roteiro do Dia 2](docs/DAY2.md) |
| WLAN e acesso SSH/SCP | [WLAN](docs/WLAN.md), [SSH](docs/SSH.md) |
| Webcam USB e HDMI | [Captura, inferência, preview e recuperação de sinal](docs/CAMERA_HDMI.md) |
| Bring-up celular manual | [RIL e RMNET](docs/CELLULAR_RIL.md) |
| Docker D2-03 | [Guia offline](demos/docker/GUIA_ALUNO_OFFLINE.md) |
| Qualcomm AI Hub D2-04 | [Passo a passo](Qualcomm_AI_Hub_Training/PASSO_A_PASSO_AIHUB.md) |
| Quatro PDFs complementares de AI Hub/edge AI | [Apresentações](Qualcomm_AI_Hub_Training/apresentacoes/) |
| Runtime QAIRT 2.51 e MobileNet V2 | [Guia do runtime](runtimes/qairt_2_51/README.md) |
| Sete gestos no HTP | [Guia de gestos](demos/hand_gesture/README.md) |
| Cinco demos HTP e comparação CPU/GPU/HTP | [HTP 2.51](htp251/README.md) |
| Conversão manual para o instrutor: TFLite → ONNX → DLC → HTP | [Classificação passo a passo e estudo do SSD](docs/TFLITE_PARA_HTP_PASSO_A_PASSO.md) |
| Onze controles de visão e execução local | [Guia de reprodução](docs/VISION_CONTROLS.md) |

O módulo AI Hub pertence ao Dia 2. Os PDFs e o replay são material complementar e contingência desse módulo.

## Origem dos modelos e das demos

| Demo/modelo | Origem e tratamento | Download / artefato |
|---|---|---|
| Classificação / MobileNet V2 | Pronto do catálogo Qualcomm AI Hub: **1 DLC w8a8**, release v0.65.0. | [Pacote QNN DLC pronto](https://qaihub-public-assets.s3.us-west-2.amazonaws.com/qai-hub-models/models/mobilenet_v2/releases/v0.65.0/mobilenet_v2-qnn_dlc-w8a8.zip) |
| MediaPipe / sete gestos | Pronto do catálogo Qualcomm AI Hub: **3 DLCs w8a8** (palma, landmarks e classificador), release v0.65.0. | [Pacote com os três DLCs](https://qaihub-public-assets.s3.us-west-2.amazonaws.com/qai-hub-models/models/mediapipe_hand_gesture/releases/v0.65.0/mediapipe_hand_gesture-qnn_dlc-w8a8.zip) |
| Classificação / MobileNet V1 | Pesos pré-treinados Google/MediaPipe; **DLC convertido e quantizado por nós no host**. | [TFLite de origem](https://storage.googleapis.com/download.tensorflow.org/models/mobilenet_v1_2018_08_02/mobilenet_v1_1.0_224_quant.tgz) |
| Detecção / SSD MobileNet V1 | Pesos pré-treinados Google/MediaPipe; **DLC convertido e quantizado por nós no host**. | [TFLite de origem](https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip) |
| Pose / PoseNet | Pesos pré-treinados Google/MediaPipe; **DLC convertido e quantizado por nós no host**. | [TFLite de origem](https://storage.googleapis.com/download.tensorflow.org/models/tflite/gpu/multi_person_mobilenet_v1_075_float.tflite) |
| Mão recortada / Hand Landmark Lite | Pesos pré-treinados Google/MediaPipe; **DLC convertido e quantizado por nós no host**. | [TFLite de origem](https://storage.googleapis.com/mediapipe-assets/hand_landmark_lite.tflite) |
| Segmentação / DeepLabV3 | Pesos pré-treinados Google/MediaPipe; **DLC convertido e quantizado por nós no host**. | [TFLite de origem](https://storage.googleapis.com/download.tensorflow.org/models/tflite/gpu/deeplabv3_257_mv_gpu.tflite) |
| AI Hub Workbench / exemplo tiny | Modelo **sintético, sem treinamento**, criado por nós em ONNX; compilado no serviço AI Hub e baixado como TFLite para CPU/GPU. | [ONNX autoral](models/workbench_demo.onnx) · [TFLite retornado pelo job](Qualcomm_AI_Hub_Training/demo_offline/models/aihub_tiny_6a569f3f9ea3.tflite) |

Os dois pacotes prontos do catálogo somam **quatro DLCs**, não sete modelos de gestos: sete são os gestos da demo, reconhecidos por uma pipeline de três redes. Os links Google/MediaPipe da tabela são downloads dos **TFLites de entrada**; os DLCs dessas cinco demos foram gerados por nós. A comparação CPU/GPU/HTP usa **MobileNet V1** e a **mão recortada**, fluxos diferentes de MobileNet V2 e da pipeline completa dos sete gestos.

As URLs e os hashes estão em [MobileNet V2: fontes](runtimes/qairt_2_51/assets/sources.lock.json), [sete gestos: assets.lock.json](demos/hand_gesture/assets.lock.json) e [TFLites: models.lock.json](models/models.lock.json). O [manifesto dos DLCs convertidos](htp251/models.json) registra arquivos, hashes e comandos. Para baixar os resultados já convertidos deste treinamento, use o ZIP completo da release no início deste README; para reconstruí-los, siga o [guia manual](docs/TFLITE_PARA_HTP_PASSO_A_PASSO.md). O [job do tiny](Qualcomm_AI_Hub_Training/demo_offline/evidence/jobs.json) documenta a compilação na nuvem.

## 4. Executar e coletar

Depois do provisionamento, os scripts principais usam `/opt/qb560d-training-payload`. `/data` tem `noexec` neste BSP. Os demais runtimes mantêm suas pastas privadas em `/opt`.

```powershell
& $py host/adb_lab.py inventory
& $py host/adb_lab.py push
& $py host/rehearse_local.py --repeat 3 --unit-label Caixa-01
& $py host/adb_lab.py pull
```

Esses comandos autenticam a sessão e gravam resultados novos em `evidence`. Não automatizam o bring-up do modem. Para USB-A, use o roteiro SSH e conclua os transfers ADB antes da troca de conexão. Logs e tempos de uma caixa não substituem a aceitação de cada unidade.

## 5. Resultados e limites

Consulte [resultados atuais](docs/TARGET_RESULTS.md), [status](docs/STATUS.md), [boot/WLAN](docs/BOOT_WLAN.md), [plano de testes](docs/TEST_PLAN.md) e [fontes/créditos](docs/SOURCES.md). Os caminhos CPU/GPU/HTP, Docker e AI Hub possuem evidências preservadas. Câmera, disponibilidade dos serviços hospedados e a aceitação por caixa têm os limites descritos nesses guias. O Yocto não tem homologação de build de imagem neste treinamento.

A [revalidação de 04/11/2026](docs/DEMO_REGRESSION_20261104.md) registra a execução das demos locais, as correções Docker/QAIRT, os controles adicionais e os limites de câmera/Wi-Fi/5G desta sessão.

A [validação após a reorganização](docs/VALIDACAO_POS_REORGANIZACAO.md) registra as novas execuções, as correções de scripts e a ressalva do retorno RIL `71/d`. O congelamento da entrega aguarda o OK dos slides.

## 6. Distribuição e licenças

```powershell
& $py host/validate_release.py
& $py host/build_release.py
```

O empacotador reúne o treinamento completo em um ZIP versionado. Inclui os quatro PDFs, os guias e as dependências offline fixadas; exclui fontes de slides, histórico, backups, ambientes virtuais, pendências internas, inventários/planos locais e firmware. O manifest `RELEASE.json` registra os arquivos e hashes da revisão. Gere um novo inventário e plano para a sua caixa conforme a seção 2.

O código autoral usa a [licença MIT](../LICENSE). Slides, guias, READMEs e demais materiais didáticos autorais usam a [CC BY-NC-SA 4.0](../LICENSE-CONTENT). Copyright © 2026 José Maurício Alencar Filho. Consulte o [alcance das licenças e as exceções de terceiros](../LICENSING.md); PDFs, modelos, SDKs e outros componentes de terceiros conservam seus próprios termos.
