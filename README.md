# Treinamento técnico QB560D-EU

## Download para os alunos

- [Baixar o treinamento completo v0.12.2 (ZIP)](https://github.com/Mauricio-Alencar/QB560D-training-quectel/releases/download/v0.12.2/QB560D_EU_Training_0.12.2_20261104-release.zip)
- [Baixar o SHA-256](https://github.com/Mauricio-Alencar/QB560D-training-quectel/releases/download/v0.12.2/QB560D_EU_Training_0.12.2_20261104-release.zip.sha256)
- [Notas da release v0.12.2](https://github.com/Mauricio-Alencar/QB560D-training-quectel/releases/tag/v0.12.2)

Extraia o pacote em uma pasta curta, como `C:\QB560D`, e abra `training_v2/README.md`. O ZIP inclui as dependências offline selecionadas para a aula.

Esta release corrige o provisionamento Docker e o layout do QAIRT no Windows. Consulte o [diagnóstico de download e extração](training_v2/docs/DOWNLOAD_DIAGNOSTICS.md) antes de usar uma cópia extraída em Downloads/OneDrive.

Para conferir o download no PowerShell, execute o comando abaixo e compare o resultado com o arquivo `.sha256`:

```powershell
Get-FileHash .\QB560D_EU_Training_0.12.2_20261104-release.zip -Algorithm SHA256
```

Comece pelo [guia único do treinamento](training_v2/README.md). Os comandos do host partem da pasta `training_v2`.

- [Apresentação principal](training_v2/slides/QB560D_EU_Training.pptx)
- [Preparação do computador e da caixa](training_v2/provision_target/README.md)
- [Agenda e navegação](training_v2/docs/AGENDA.md)
- [Módulo Qualcomm AI Hub](training_v2/Qualcomm_AI_Hub_Training/README.md)
- [Apresentações complementares Qualcomm AI Hub](training_v2/Qualcomm_AI_Hub_Training/apresentacoes/)

O único PPTX usado na aula é a apresentação principal indicada acima. O conteúdo de Yocto é conceitual, sem execução de builds ou labs.

Os pacotes dos alunos incluem os guias, as demos e as dependências offline selecionadas. Firmware, fontes de autoria, backups, pendências internas e inventários/planos locais de preparação ficam fora da distribuição.

## Origem dos modelos das demos

| Demo/modelo | Origem e tratamento | Download / artefato |
|---|---|---|
| Classificação / MobileNet V2 | Pronto do catálogo Qualcomm AI Hub: **1 DLC w8a8**, release v0.65.0. | [Pacote QNN DLC pronto](https://qaihub-public-assets.s3.us-west-2.amazonaws.com/qai-hub-models/models/mobilenet_v2/releases/v0.65.0/mobilenet_v2-qnn_dlc-w8a8.zip) |
| MediaPipe / sete gestos | Pronto do catálogo Qualcomm AI Hub: **3 DLCs w8a8** (palma, landmarks e classificador), release v0.65.0. | [Pacote com os três DLCs](https://qaihub-public-assets.s3.us-west-2.amazonaws.com/qai-hub-models/models/mediapipe_hand_gesture/releases/v0.65.0/mediapipe_hand_gesture-qnn_dlc-w8a8.zip) |
| Classificação / MobileNet V1 | Pesos pré-treinados Google/MediaPipe; **DLC convertido e quantizado por nós no host**. | [TFLite de origem](https://storage.googleapis.com/download.tensorflow.org/models/mobilenet_v1_2018_08_02/mobilenet_v1_1.0_224_quant.tgz) |
| Detecção / SSD MobileNet V1 | Pesos pré-treinados Google/MediaPipe; **DLC convertido e quantizado por nós no host**. | [TFLite de origem](https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip) |
| Pose / PoseNet | Pesos pré-treinados Google/MediaPipe; **DLC convertido e quantizado por nós no host**. | [TFLite de origem](https://storage.googleapis.com/download.tensorflow.org/models/tflite/gpu/multi_person_mobilenet_v1_075_float.tflite) |
| Mão recortada / Hand Landmark Lite | Pesos pré-treinados Google/MediaPipe; **DLC convertido e quantizado por nós no host**. | [TFLite de origem](https://storage.googleapis.com/mediapipe-assets/hand_landmark_lite.tflite) |
| Segmentação / DeepLabV3 | Pesos pré-treinados Google/MediaPipe; **DLC convertido e quantizado por nós no host**. | [TFLite de origem](https://storage.googleapis.com/download.tensorflow.org/models/tflite/gpu/deeplabv3_257_mv_gpu.tflite) |
| AI Hub Workbench / exemplo tiny | Modelo **sintético, sem treinamento**, criado por nós em ONNX; compilado no serviço AI Hub e baixado como TFLite para CPU/GPU. | [ONNX autoral](training_v2/models/workbench_demo.onnx) · [TFLite retornado pelo job](training_v2/Qualcomm_AI_Hub_Training/demo_offline/models/aihub_tiny_6a569f3f9ea3.tflite) |

Os dois pacotes prontos do catálogo somam **quatro DLCs**, não sete modelos de gestos: sete são os gestos da demo, reconhecidos por uma pipeline de três redes. Os links Google/MediaPipe da tabela são downloads dos **TFLites de entrada**; os DLCs dessas cinco demos foram gerados por nós. A comparação CPU/GPU/HTP usa **MobileNet V1** e a **mão recortada**, fluxos diferentes de MobileNet V2 e da pipeline completa dos sete gestos.

O [README principal do treinamento](training_v2/README.md#origem-dos-modelos-e-das-demos) reúne os locks, manifests e o guia de conversão. O ZIP completo acima contém os artefatos prontos para os alunos; os links de origem identificam de onde vieram os modelos.

O código autoral usa a [licença MIT](LICENSE). Slides, guias, READMEs e demais materiais didáticos autorais usam a [CC BY-NC-SA 4.0](LICENSE-CONTENT). Copyright © 2026 José Maurício Alencar Filho. Consulte o [alcance das licenças e as exceções de terceiros](LICENSING.md).
