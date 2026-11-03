"""Build the post-provisioning offline fallback for the validated tiny AI Hub lab."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-dir',required=True)
    p.add_argument('--cpu-log',required=True)
    p.add_argument('--gpu-log',required=True)
    a=p.parse_args()
    root=Path(__file__).resolve().parents[2];folder=root/'Qualcomm_AI_Hub_Training';run=Path(a.run_dir).resolve()
    review=json.loads((run/'deployment-comparison.json').read_text(encoding='utf-8'))
    assert review['result']=='HOSTED_AND_TARGET_CPU_GPU_PASS','Complete the validated flow first'
    digest=review['artifact_sha256'];name='aihub_tiny_'+digest[:12]+'.tflite'
    dest=folder/'demo_offline';dest.mkdir(exist_ok=True)
    copies={run/'model.tflite':'models/'+name,
            root/'models/workbench_input.npy':'models/workbench_input.npy',
            root/'models/workbench_expected.npy':'models/workbench_expected.npy',
            root/'models/workbench_demo.onnx':'source/workbench_demo.onnx',
            root/'ai/run_tensor.py':'ai/run_tensor.py',
            root/'ai/c_api_backend.py':'ai/c_api_backend.py',
            Path(a.cpu_log):'evidence/local-cpu.log',Path(a.gpu_log):'evidence/local-gpu.log'}
    for file in ('jobs.json','profile.json','hosted_outputs.npz','hosted-review.json','target-cpu.json','target-gpu.json','deployment-comparison.json','offline-validation.json','negative-config.json','completion-observation.json'):
        copies[run/file]='evidence/'+file
    recording=folder/'contingencia/recording.json'
    if recording.is_file():
        for file in ('AIHub_QB560D_Contingencia_Replay.mp4','AIHub_QB560D_Contingencia_Replay.srt','recording.json','source-comparison.json','README.md'):
            copies[folder/'contingencia'/file]='contingencia/'+file
    for source,relative in copies.items():
        target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    runner='''#!/bin/sh
set -eu
cd "$(dirname -- "$0")"
backend=${1:-cpu}
case "$backend" in cpu|gpu) ;; *) echo 'Use cpu or gpu' >&2; exit 78;; esac
export PYTHONPATH="/opt/qb560d-training-payload/.python-deps${PYTHONPATH:+:$PYTHONPATH}"
exec python3 ai/run_tensor.py --model models/MODEL_NAME --input models/workbench_input.npy --expected models/workbench_expected.npy --backend "$backend" --output "results/$backend.json"
'''.replace('MODEL_NAME',name)
    (dest/'run_target.sh').write_text(runner,encoding='utf-8',newline='\n')
    readme='''# Contingencia offline: artefato AI Hub na QB560D-EU

Este pacote preserva o modelo, os tensores, os executores e as evidencias do fluxo aprovado. A parte local funciona sem Internet e sem token AI Hub. Compile e profile hospedados requerem o servico online; seus resultados salvos acompanham este pacote.

Pre-requisito: caixa ja preparada pelo treinamento, BSP QDPA_Ubuntu20.04.003.51.303 V01, Python3.8, NumPy privado em /opt/qb560d-training-payload/.python-deps, TFLite C API2.8.4 e OpenCL do BSP. O pacote nao instala firmware, drivers, Python, NumPy ou SDK Qualcomm. Os helpers ADB e o cliente Windows acompanham o treinamento principal em host/ e tools/.

## Repetir na caixa ja usada neste ensaio

Depois do login root em adb shell:

```sh
cd /opt/qb560d-training-payload
sh target/ai.sh tensor --model models/MODEL_NAME --input models/workbench_input.npy --expected models/workbench_expected.npy --backend cpu --output evidence/aihub-offline-cpu.json
sh target/ai.sh tensor --model models/MODEL_NAME --input models/workbench_input.npy --expected models/workbench_expected.npy --backend gpu --output evidence/aihub-offline-gpu.json
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
'''.replace('MODEL_NAME',name)
    (dest/'README.md').write_text(readme,encoding='utf-8')
    selected=[dest/relative for relative in copies.values()]+[dest/'README.md',dest/'run_target.sh']
    manifest={'revision':'1.1.0-tiny-aihub-with-replay','at_host_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
              'model_sha256':digest,'result':review['result'],'requires_prepared_box':True,
              'cloud_credentials_included':False,'files':{x.relative_to(dest).as_posix():hashlib.sha256(x.read_bytes()).hexdigest() for x in selected}}
    (dest/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    archive=root.parent/'dist/QB560D_AIHub_Demo_Offline.zip'
    archive.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for file in sorted(selected+[dest/'MANIFEST.json']):z.write(file,'QB560D_AIHub_Demo_Offline/'+file.relative_to(dest).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(selected)+1,'result':review['result']}))


if __name__=='__main__':
    main()
