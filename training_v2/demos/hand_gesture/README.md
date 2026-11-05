# MediaPipe: sete gestos no HTP 2.51

Esta demo usa três DLCs w8a8 do Qualcomm AI Hub: detector de palma, 21 landmarks e classificador de gestos. As redes executam no HTP da QB560D-EU; o host prepara/recorta imagens e interpreta as saídas. O pacote v0.65.0 foi validado com QAIRT/QNN 2.51.40.260930230134, no runtime persistente `/opt/qairt-isolated/2.51.40.260930`.

## Origem dos modelos desta demo

| Demo/modelo | Origem e tratamento | Download / artefato |
|---|---|---|
| Detector de palma, landmarks e classificador de gestos | **Três DLCs prontos do catálogo Qualcomm AI Hub**, w8a8 v0.65.0; não convertidos por nós. | [ZIP com os três DLCs](https://qaihub-public-assets.s3.us-west-2.amazonaws.com/qai-hub-models/models/mediapipe_hand_gesture/releases/v0.65.0/mediapipe_hand_gesture-qnn_dlc-w8a8.zip) · [Página oficial do modelo](https://huggingface.co/qualcomm/MediaPipe-Hand-Gesture-Recognition) |

O pacote fornece `palm_detector.dlc`, `hand_landmark_detector.dlc` e `canned_gesture_classifier.dlc`. Sete são os gestos reconhecidos, não a quantidade de modelos. O preparo de imagens, recortes e montagem de features é feito pela aplicação; não houve treinamento nem conversão local desses DLCs. As URLs e SHA-256 estão em [assets.lock.json](assets.lock.json). A demo de **mão recortada / Hand Landmark Lite**, pertencente às cinco demos HTP, usa outro fluxo: TFLite Google/MediaPipe convertido por nós. Consulte o [mapa das origens](../../README.md#origem-dos-modelos-e-das-demos).

## Preparação

Use o workspace completo e uma caixa preparada conforme [provision_target/README.md](../../provision_target/README.md). No PowerShell, na raiz `training_v2`:

```powershell
$py = (Resolve-Path './provision_target/.venv/Scripts/python.exe').Path
$adb = (Resolve-Path './tools/platform-tools/adb.exe').Path
& $adb devices -l
```

São necessários Python 3.12, NumPy/Pillow, ADB e driver USB. O primeiro download precisa de Internet no host; não há conversão, treinamento, TensorFlow ou PyTorch para rodar os DLCs prontos. O login Linux pede a senha root sem salvá-la. Havendo múltiplas caixas, selecione `--transport-id ID`.

## Download, deploy e teste

```powershell
& $py demos/hand_gesture/download_gesture.py
& $py demos/hand_gesture/gesture_demo.py deploy --adb $adb
& $py demos/hand_gesture/gesture_demo.py run --adb $adb --backend htp --image demos/hand_gesture/assets/images/thumbs_up.jpg
& $py demos/hand_gesture/gesture_demo.py test-all --adb $adb --backend htp
```

O deploy usa `/opt/qairt-isolated/2.51.40.260930/demos/hand_gesture`, verifica os arquivos existentes e preserva as bibliotecas do BSP. No teste completo, espere **7/7**: `Closed_Fist`, `Open_Palm`, `Pointing_Up`, `Thumb_Down`, `Thumb_Up`, `Victory` e `ILoveYou`. Abra `prediction.png` nas pastas de evidência indicadas pelo terminal; `result.json` e os perfis de cada rede acompanham a imagem. A rodada aprovada no firmware atual está em `evidence/fw-20261101/summary.json`.

## Outra imagem

```powershell
& $py demos/hand_gesture/gesture_demo.py run --adb $adb --backend htp --image C:/fotos/meu_gesto.jpg
```

Use uma mão frontal, bem iluminada, com pulso/dedos visíveis e espaço ao redor. `No_hand` indica que a detecção/presença não passou do limiar; `None` indica um gesto não reconhecido. Confira a imagem antes de aceitar uma foto nova. A validação cobre fotos estáticas, não vídeo ou acurácia de dataset.

O caminho homologado é HTP. O controle anterior QNN CPU divergiu nos sete rótulos e não serve como referência de qualidade nem comparação de velocidade desta pipeline. Não converta a soma dos três tempos de rede em FPS do aplicativo: recortes, transferências e inicialização são etapas adicionais.

O [guia detalhado](../../runtimes/qairt_2_51/GUIA_WORKSHOP_HAND_GESTURE.txt) preserva as fontes/licenças das fotos, URLs fixados, hashes, limiares e solução de problemas. A [galeria local](../../htp251/results/index.html) reúne as sete imagens anotadas e as cinco demos adicionais. A comparação CPU/GPU/HTP medida com metodologia uniforme aplica-se às cinco demos em [htp251/README.md](../../htp251/README.md), não a este fluxo de três redes.
