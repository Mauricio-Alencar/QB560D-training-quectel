# MediaPipe: sete gestos no HTP 2.51

Esta demo usa três DLCs w8a8 do Qualcomm AI Hub: detector de palma, 21 landmarks e classificador de gestos. As redes executam no HTP da QB560D-EU; o host prepara/recorta imagens e interpreta as saídas. O pacote v0.65.0 foi validado com QAIRT/QNN 2.51.40.260930230134, no runtime persistente `/opt/qairt-isolated/2.51.40.260930`.

## Preparação

Use o workspace completo e uma caixa preparada conforme [provision_target/README.txt](../../provision_target/README.txt). No PowerShell, na raiz `training_v2`:

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
