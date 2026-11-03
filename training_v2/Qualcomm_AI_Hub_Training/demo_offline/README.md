# Contingencia offline: artefato AI Hub na QB560D-EU

Este pacote preserva o modelo, os tensores, os executores e as evidencias do fluxo aprovado. A parte local funciona sem Internet e sem token AI Hub. Compile e profile hospedados requerem o servico online; seus resultados salvos acompanham este pacote.

Pre-requisito: caixa ja preparada pelo treinamento, BSP QDPA_Ubuntu20.04.003.51.303 V01, Python3.8, NumPy privado em /opt/qb560d-training-payload/.python-deps, TFLite C API2.8.4 e OpenCL do BSP. O pacote nao instala firmware, drivers, Python, NumPy ou SDK Qualcomm. Os helpers ADB e o cliente Windows acompanham o treinamento principal em host/ e tools/.

## Repetir na caixa ja usada neste ensaio

Depois do login root em adb shell:

```sh
cd /opt/qb560d-training-payload
sh target/ai.sh tensor --model models/aihub_tiny_6a569f3f9ea3.tflite --input models/workbench_input.npy --expected models/workbench_expected.npy --backend cpu --output evidence/aihub-offline-cpu.json
sh target/ai.sh tensor --model models/aihub_tiny_6a569f3f9ea3.tflite --input models/workbench_input.npy --expected models/workbench_expected.npy --backend gpu --output evidence/aihub-offline-gpu.json
```

Verifique PASS, hash do modelo, saidas e o log OpenCL. Um erro precisa continuar identificado como erro.

## Restaurar os arquivos a partir do host

Na raiz training_v2, com esta pasta extraida em Qualcomm_AI_Hub_Training/demo_offline:

```powershell
$hostPy = (Resolve-Path 'provision_target/.venv/Scripts/python.exe').Path
Copy-Item 'Qualcomm_AI_Hub_Training/demo_offline/models/*' 'models/'
Copy-Item 'Qualcomm_AI_Hub_Training/demo_offline/ai/*' 'ai/'
& $hostPy host/adb_lab.py push
```

O helper pede a senha Linux root. Em seguida use os comandos locais acima ou o helper adb_lab.py run ai tensor. A configuracao/token AI Hub nao e enviada para a caixa.

Se a pasta inteira deste pacote for transferida para uma pasta propria na caixa, rode `sh run_target.sh cpu` e `sh run_target.sh gpu` de dentro dela. O PYTHONPATH reutiliza o NumPy privado do treinamento.

## Conteudo e resultado de referencia

- models/: TFLite de1992bytes, entrada float32 NCHW[1,3,32,32] e referencia[1,4].
- ai/: wrapper da C API do BSP e executor do tensor.
- source/: ONNX original, para recompilar quando houver servico online.
- evidence/: IDs/links, profile, saida hospedada e resultados/logs CPU/GPU reais.
- MANIFEST.json: SHA256 de cada arquivo, para conferir integridade.

CPU local: PASS, mediana0.0848305ms, erro maximo1.49e-08.
GPU local: PASS, mediana0.2543065ms, erro maximo2.98e-08, OpenCL e kernel delegado confirmados.
Hub: PASS numerico, erro maximo4.00543e-05, quatro entradas GPU no profile. Estimativa217us e mediana das100 amostras694.5us sao medidas distintas do kit hospedado.

O exemplo sintetico e pequeno. Nesta sessao, a GPU local levou cerca de3vezes o tempo da CPU. O objetivo e reproduzir conversao, deploy e validacao, sem prometer aceleracao para este grafo ou acuracia em imagens. As medicoes usam um unico input e uma sessao por backend.
