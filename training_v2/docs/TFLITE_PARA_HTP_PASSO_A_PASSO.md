# Do TFLite original à execução no HTP: roteiro do instrutor

Este capítulo abre as etapas implementadas em `host/inspect_htp251_sources.py`, `host/export_htp251_models.py`, `host/convert_htp251_models.py` e `host/htp251_workshop.py`. O primeiro exercício usa MobileNet V1 para classificação; o segundo reconstrói o SSD MobileNet V1 e explica suas particularidades. Ambos partem dos modelos Google/TensorFlow, e não de DLCs prontos baixados do AI Hub.

```text
TFLite original → ONNX validado → DLC float → DLC quantizado
                                              ↓
                                 execução e validação no HTP
```

Todos os comandos PowerShell começam em `training_v2`. Os comandos identificados como **Linux da caixa** são digitados depois do login root no `adb shell`. A conversão ocorre no Windows; a inferência HTP ocorre na QB560D-EU/QCM6490, HTP v68, Ubuntu 20.04.3, QAIRT 2.51.40.260930. O pré/pós-processamento deste roteiro ocorre na CPU. Não é necessário iniciar nenhum job hospedado no AI Hub.

Neste roteiro, **HTP é o caminho de execução no acelerador Hexagon/NPU**: a aplicação seleciona `libQnnHtp.so` para executar a rede. DLC é o formato do modelo; a escolha do backend determina onde ele executa. O exemplo não implica que o mesmo DLC quantizado foi homologado em CPU e GPU. A comparação disponível entre os três caminhos está na seção 15.

Use uma cópia completa do treinamento em um caminho curto, como `C:\QB560D\aibox_training\training_v2`. O target precisa estar provisionado conforme [README principal](../README.md). Cada execução abaixo cria um candidato novo, sem substituir os modelos, manifests ou evidências homologados. As ferramentas de conversão e seus ambientes são preparação do instrutor; o ZIP dos alunos fornece os DLCs prontos e os inputs de runtime, mas não distribui os ambientes `.venv` nem todo o SDK de conversão.

## 1. Ambientes e pasta de trabalho

Instale Python **3.8 x64 completo**, com pip/venv, e Python **3.12 x64**. O launcher `py` abaixo precisa reconhecer ambas as instalações; se não estiver disponível, substitua `py -3.8`/`py -3.12` pelo executável completo da instalação correspondente. O Python 3.8 portátil da estação original não acompanha a distribuição.

```powershell
py -3.8 --version
py -3.12 --version
py -3.8 -m venv .build/manual-export-py38
py -3.12 -m venv .build/manual-qairt-py312
$exporter = (Resolve-Path .build/manual-export-py38/Scripts/python.exe).Path
$converter = (Resolve-Path .build/manual-qairt-py312/Scripts/python.exe).Path
$py = (Resolve-Path provision_target/.venv/Scripts/python.exe).Path

& $exporter -m pip install -r host/requirements-snpe-conversion.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha nas dependências de exportação' }
& $converter -m pip install -r host/requirements-qairt251-conversion.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha nas dependências QAIRT' }
```

O primeiro ambiente fixa TensorFlow 2.13.0, tf2onnx 1.16.1, ONNX 1.14.1 e ONNX Runtime 1.16.3. O segundo fixa as dependências do conversor QAIRT Windows/Python 3.12. Não misture os dois conjuntos de versões.

```powershell
$training = (Get-Location).Path
$lab = Join-Path $training ('.build/manual-htp-' + [guid]::NewGuid().ToString('N').Substring(0,10))
New-Item -ItemType Directory -Path $lab | Out-Null
$env:MANUAL_TRAINING = $training
$env:MANUAL_LAB = $lab
Write-Output "Candidato desta sessão: $lab"
```

Mantenha este PowerShell aberto: os blocos seguintes usam essas variáveis. Para reconstruir outra vez, gere uma nova `$lab`.

## 2. Baixar os TFLites originais e conferir os hashes

| Caso | URL oficial do arquivo de origem | Membro dentro do arquivo | SHA-256 do TFLite extraído |
|---|---|---|---|
| Classificação | [MobileNet V1 quantizado, Google](https://storage.googleapis.com/download.tensorflow.org/models/mobilenet_v1_2018_08_02/mobilenet_v1_1.0_224_quant.tgz) | `mobilenet_v1_1.0_224_quant.tflite` | `ecc3a67c47c5a609ec35f6a58a7d97532834e43df4cb7d3f1204a8164b7d20dd` |
| SSD | [COCO SSD MobileNet V1 quantizado, Google](https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip) | `detect.tflite` | `e4b118e5e4531945de2e659742c7c590f7536f8d0ed26d135abcfe83b4779d13` |

Os hashes são dos **TFLites**, não dos arquivos TGZ/ZIP que os contêm. Estão congelados em `models/models.lock.json`. O bloco lê somente os membros esperados, valida os hashes e guarda cópias na pasta de trabalho.

```powershell
@'
import hashlib, io, os, tarfile, urllib.request, zipfile
from pathlib import Path
lab = Path(os.environ['MANUAL_LAB'])
items = [
 ('classification', 'https://storage.googleapis.com/download.tensorflow.org/models/mobilenet_v1_2018_08_02/mobilenet_v1_1.0_224_quant.tgz', 'mobilenet_v1_1.0_224_quant.tflite', 'ecc3a67c47c5a609ec35f6a58a7d97532834e43df4cb7d3f1204a8164b7d20dd'),
 ('detection', 'https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip', 'detect.tflite', 'e4b118e5e4531945de2e659742c7c590f7536f8d0ed26d135abcfe83b4779d13')]
for task, url, member, expected in items:
    folder = lab/task
    folder.mkdir(exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    (folder/('source.zip' if url.endswith('.zip') else 'source.tgz')).write_bytes(data)
    if url.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            blob = archive.read(member)
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            rows = [m for m in archive.getmembers() if m.name in (member, './'+member)]
            assert len(rows) == 1 and rows[0].isfile()
            blob = archive.extractfile(rows[0]).read()
    digest = hashlib.sha256(blob).hexdigest()
    assert digest == expected, (task, digest, 'Origem mudou; não atualizar o lock para ocultar a diferença')
    (folder/'source.tflite').write_bytes(blob)
    print(task, 'SOURCE_HASH_OK', len(blob), digest)
'@ | Set-Content -Encoding UTF8 (Join-Path $lab download.py)
& $exporter (Join-Path $lab download.py)
if ($LASTEXITCODE -ne 0) { throw 'Download/hash recusado' }
```

Sem Internet, use o bloco alternativo abaixo em lugar do download. Essa cópia substitui apenas a obtenção dos TFLites; a inspeção, exportação e demais etapas são iguais. O SDK de conversão e os ambientes Python precisam já estar preparados para uma sessão totalmente offline.

```powershell
New-Item -ItemType Directory -Force (Join-Path $lab classification), (Join-Path $lab detection) | Out-Null
Copy-Item models/mobilenet_v1.tflite (Join-Path $lab classification/source.tflite)
Copy-Item models/ssd_mobilenet_v1.tflite (Join-Path $lab detection/source.tflite)
if ((Get-FileHash (Join-Path $lab classification/source.tflite) -Algorithm SHA256).Hash.ToLower() -ne 'ecc3a67c47c5a609ec35f6a58a7d97532834e43df4cb7d3f1204a8164b7d20dd') { throw 'Hash MobileNet divergente' }
if ((Get-FileHash (Join-Path $lab detection/source.tflite) -Algorithm SHA256).Hash.ToLower() -ne 'e4b118e5e4531945de2e659742c7c590f7536f8d0ed26d135abcfe83b4779d13') { throw 'Hash SSD divergente' }
```

## 3. Abrir o contrato do TFLite

```powershell
@'
import hashlib, json, os
from pathlib import Path
import numpy as np
import tensorflow as tf
from tensorflow.lite.python import schema_py_generated as schema
from flatbuffers import flexbuffers
lab = Path(os.environ['MANUAL_LAB'])
def detail(d):
    return dict(name=d['name'], shape=d['shape'].tolist(), dtype=str(d['dtype']),
                quantization=list(d['quantization']))
for task in ('classification', 'detection'):
    folder = lab/task
    source = folder/'source.tflite'
    interpreter = tf.lite.Interpreter(model_path=str(source), experimental_preserve_all_tensors=True)
    interpreter.allocate_tensors()
    inputs = interpreter.get_input_details()
    outputs = interpreter.get_output_details()
    contract = dict(task=task, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    input=detail(inputs[0]), outputs=[detail(d) for d in outputs])
    if task == 'detection':
        op = next(o for o in interpreter._get_ops_details() if 'Detection_PostProcess' in o['op_name'])
        details = {d['index']:d for d in interpreter.get_tensor_details()}
        contract['outputs'] = [detail(details[int(i)]) for i in op['inputs'][:2]]
        anchors = interpreter.get_tensor(int(op['inputs'][2]))
        scale, zero = details[int(op['inputs'][2])]['quantization']
        anchors = (anchors.astype(np.float32)-zero)*scale if scale else anchors.astype(np.float32)
        np.save(folder/'anchors.npy', anchors)
        model = schema.Model.GetRootAsModel(source.read_bytes(), 0)
        graph = model.Subgraphs(0)
        for i in range(graph.OperatorsLength()):
            operator = graph.Operators(i)
            code = model.OperatorCodes(operator.OpcodeIndex())
            if code.CustomCode() and b'Detection_PostProcess' in code.CustomCode():
                contract['nms_options'] = flexbuffers.Loads(bytes(operator.CustomOptionsAsNumpy()))
    (folder/'contract.json').write_text(json.dumps(contract, indent=2), encoding='utf-8')
    print(json.dumps(contract, indent=2))
'@ | Set-Content -Encoding UTF8 (Join-Path $lab inspect.py)
& $exporter (Join-Path $lab inspect.py)
if ($LASTEXITCODE -ne 0) { throw 'Inspeção falhou' }
```

Explique o contrato antes de converter:

| Campo | Classificação | SSD |
|---|---|---|
| Entrada TFLite | `input`, uint8, `[1,224,224,3]` | `normalized_input_image_tensor`, uint8, `[1,300,300,3]` |
| Quantização de entrada | escala `1/128`, zero-point `128` | escala `1/128`, zero-point `128` |
| Entrada real enviada ao DLC neste fluxo | float32 `(pixel - 128)/128` | float32 com pixels `0…255`; normalização fica no grafo exportado |
| Saídas exportadas | 1001 scores | `Squeeze`: `[1,1917,4]`; `convert_scores`: `[1,1917,91]` |

NHWC significa lote, altura, largura e canais. A entrada TFLite uint8 recebe os pixels sem normalização manual. A fórmula `real = (quantizado - zero_point) × escala` produz a entrada float da classificação. Usar essa mesma fórmula no input externo do SSD deste roteiro normalizaria duas vezes. Guarde `contract.json`, `anchors.npy` e as opções de NMS junto do candidato.

## 4. Comando explícito: TFLite → ONNX

```powershell
# A API abaixo é a mesma chamada da classificação no exportador homologado.
& $exporter -c 'import os,tf2onnx; from pathlib import Path; p=Path(os.environ["MANUAL_LAB"])/"classification"; tf2onnx.convert.from_tflite(str(p/"source.tflite"), output_names=["MobilenetV1/Predictions/Reshape_1"], opset=13, output_path=str(p/"export.onnx"))'
if ($LASTEXITCODE -ne 0) { throw 'Exportação MobileNet falhou' }

& $exporter -m tf2onnx.convert --tflite (Join-Path $lab detection/source.tflite) --outputs 'Squeeze,convert_scores' --opset 13 --dequantize --output (Join-Path $lab detection/export.onnx)
if ($LASTEXITCODE -ne 0) { throw 'Exportação SSD falhou' }
```

`output_names` na API e `--outputs` na CLI selecionam os tensores identificados na inspeção. A classificação usa a chamada Python `from_tflite` do script homologado; o SSD usa a CLI do mesmo pacote. Não trate chamadas com opções/defaults distintos como numericamente equivalentes sem repetir a comparação da seção 5. No SSD, a CNN termina antes do operador customizado de detecção do TFLite: caixas finais não são uma saída direta desse ONNX. A opção `--dequantize` faz parte da exportação do SSD; a limpeza abaixo ainda é necessária para reproduzir a política usada no treinamento.

### 4.1 Ajustes explícitos do ONNX, incluindo o caso SSD

Este bloco abre a transformação que o exportador automatiza. No SSD, materializa pesos dequantizados com `(peso - zero_point) × escala`, substitui Q/DQ de ativações por Identity e deixa a calibração nova calcular os encodings. Na classificação, preserva Q/DQ e corrige somente o eixo ausente em casos escalares de tensores 1D.

```powershell
@'
import json, os
from pathlib import Path
import numpy as np
import onnx
from onnx import numpy_helper
lab = Path(os.environ['MANUAL_LAB'])
for task in ('classification', 'detection'):
    folder = lab/task
    model = onnx.load(str(folder/'export.onnx'))
    removed = []
    if task == 'detection':
        constants = {t.name:t for t in model.graph.initializer}
        nodes = []
        for node in model.graph.node:
            if node.op_type == 'DequantizeLinear' and node.input[0] in constants:
                value = numpy_helper.to_array(constants[node.input[0]]).astype(np.float32)
                scale = numpy_helper.to_array(constants[node.input[1]])
                zero = numpy_helper.to_array(constants[node.input[2]]) if len(node.input)>2 else 0
                if np.asarray(scale).size>1:
                    axis = next((a.i for a in node.attribute if a.name=='axis'), 1)
                    shape = [1]*value.ndim; shape[axis] = scale.size
                    scale = scale.reshape(shape); zero = np.asarray(zero).reshape(shape)
                model.graph.initializer.append(numpy_helper.from_array(((value-zero)*scale).astype(np.float32), node.output[0]))
                removed.append(node.name)
            elif node.op_type in ('QuantizeLinear', 'DequantizeLinear'):
                nodes.append(onnx.helper.make_node('Identity', [node.input[0]], list(node.output), name=node.name+'_float'))
                removed.append(node.name)
            else:
                nodes.append(node)
        del model.graph.node[:]; model.graph.node.extend(nodes)
        del model.graph.value_info[:]
        for tensor in list(model.graph.input)+list(model.graph.output):
            tensor.type.tensor_type.elem_type = onnx.TensorProto.FLOAT
    tensors = {t.name:t for t in model.graph.initializer}
    axes = []
    for node in model.graph.node:
        if (node.op_type=='DequantizeLinear' and node.input[0] in tensors and node.input[1] in tensors
            and len(tensors[node.input[0]].dims)==1 and numpy_helper.to_array(tensors[node.input[1]]).size==1
            and not any(a.name=='axis' for a in node.attribute)):
            node.attribute.append(onnx.helper.make_attribute('axis', 0)); axes.append(node.name)
    onnx.checker.check_model(model)
    onnx.save(onnx.shape_inference.infer_shapes(model), str(folder/'model.onnx'))
    (folder/'onnx-adjustments.json').write_text(json.dumps(dict(removed_quantizers=removed, axis_metadata_changes=axes), indent=2))
    print(task, 'ONNX_STRUCTURAL_CHECK_OK')
'@ | Set-Content -Encoding UTF8 (Join-Path $lab adjust_onnx.py)
& $exporter (Join-Path $lab adjust_onnx.py)
if ($LASTEXITCODE -ne 0) { throw 'ONNX estruturalmente inválido' }
```

O checker valida a estrutura do grafo. A próxima etapa verifica valores, pois um ONNX estruturalmente válido pode calcular resultados diferentes.

## 5. Gerar inputs de calibração e comparar TFLite × ONNX

Usamos cinco imagens disponíveis no treinamento: Grace Hopper, mãos, polegar para baixo, polegar para cima e vitória. São controles didáticos pequenos. Para implantação real, selecione uma calibração representativa do domínio e avalie um conjunto de teste separado. Este roteiro registra os arquivos efetivamente utilizados; um conjunto diferente pode produzir outro DLC e outro hash.

```powershell
@'
import hashlib, json, os
from pathlib import Path
import numpy as np
import onnxruntime as ort
import tensorflow as tf
from PIL import Image, ImageOps
root = Path(os.environ['MANUAL_TRAINING']); lab = Path(os.environ['MANUAL_LAB'])
samples = [root/'media/grace_hopper.jpg', root/'media/right_hands.jpg']
samples += [root/'demos/hand_gesture/assets/images'/name for name in ('thumbs_down.jpg','thumbs_up.jpg','victory.jpg')]
for task, size in [('classification',(224,224)), ('detection',(300,300))]:
    folder = lab/task; cal = folder/'calibration'; cal.mkdir(exist_ok=False)
    contract = json.loads((folder/'contract.json').read_text())
    interpreter = tf.lite.Interpreter(model_path=str(folder/'source.tflite'), experimental_preserve_all_tensors=(task=='detection'))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    details = {d['name']:d for d in interpreter.get_tensor_details()}
    session = ort.InferenceSession(str(folder/'model.onnx'), providers=['CPUExecutionProvider'])
    scale, zero = input_detail['quantization']; records = []; paths = []
    for i, path in enumerate(samples):
        image = ImageOps.exif_transpose(Image.open(path)).convert('RGB').resize(size, Image.Resampling.BILINEAR)
        native = np.asarray(image, dtype=np.uint8)[None]
        real = (native.astype(np.float32)-zero)*scale
        tensor = native.astype(np.float32) if task=='detection' else real
        raw = cal/('%02d.raw'%i); tensor.astype('<f4').tofile(raw)
        paths.append('calibration/'+raw.name)
        if i==0:
            image.save(folder/'input.png'); tensor.astype('<f4').tofile(folder/'input.raw')
        errors = []
        if i<2:
            interpreter.set_tensor(input_detail['index'], native); interpreter.invoke()
            actual = session.run(None, {session.get_inputs()[0].name:tensor if task=='detection' else native})
            for spec, value in zip(contract['outputs'], actual):
                expected = interpreter.get_tensor(details[spec['name']]['index'])
                if task=='detection':
                    out_scale, out_zero = spec['quantization']
                    expected = (expected.astype(np.float32)-out_zero)*out_scale
                diff = np.abs(expected.astype(np.float64)-value.astype(np.float64))
                limit = (2.0 if spec['name']=='Squeeze' else 0.10) if task=='detection' else 4.0
                assert np.isfinite(value).all() and diff.max()<=limit, (task,spec['name'],float(diff.max()),limit)
                if task=='classification' and i==0: assert np.argmax(expected)==np.argmax(value)
                errors.append(dict(output=spec['name'], max_abs_error=float(diff.max()), mean_abs_error=float(diff.mean()), limit=limit))
        records.append(dict(image=path.relative_to(root).as_posix(), image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(), comparisons=errors))
    (cal/'input_list.txt').write_text('\n'.join(paths)+'\n', encoding='utf-8')
    (folder/'onnx-validation.json').write_text(json.dumps(dict(status='ONNX_EXPORT_VALIDATED', records=records), indent=2))
    print(task, 'ONNX_EXPORT_VALIDATED', len(paths), 'calibration samples')
'@ | Set-Content -Encoding UTF8 (Join-Path $lab validate_onnx.py)
& $exporter (Join-Path $lab validate_onnx.py)
if ($LASTEXITCODE -ne 0) { throw 'Não avançar: comparação TFLite/ONNX falhou' }
```

Explique os limites: classificação compara scores quantizados, com tolerância máxima de 4 unidades uint8, e exige o mesmo top-1 na primeira imagem; SSD compara os tensores anteriores ao NMS depois de dequantizar a referência, com limites de 2,0 para caixas codificadas e 0,10 para scores. São os critérios do exportador atual, não métricas de acurácia. `onnx-validation.json` registra os erros observados. A validação semântica final acontece depois no HTP.

Na comparação, `experimental_preserve_all_tensors` fica habilitado somente para SSD, pois precisamos ler seus tensores internos. Aplicá-lo também à classificação muda a configuração de delegates do TFLite. Na validação deste capítulo, essa configuração diferente produziu desvio de 6 unidades uint8; reproduzir a configuração do exportador homologado fez as duas referências de classificação coincidirem exatamente. O limite não foi aumentado para fazer o teste passar.

## 6. Disponibilizar o SDK e abrir o lançador Windows

```powershell
& $py host/fetch_qairt251_converter.py
if ($LASTEXITCODE -ne 0) { throw 'SDK de conversão incompleto' }
$sdk = (Resolve-Path .build/sdk251-host/qairt/2.51.40.260930).Path
$env:QAIRT_SDK_ROOT = $sdk
$env:QNN_SDK_ROOT = $sdk
$env:SNPE_ROOT = $sdk
$env:PYTHONPATH = Join-Path $sdk 'lib/python'
$env:PATH = (Join-Path $sdk 'lib/x86_64-windows-msvc') + ';' + (Split-Path $converter) + ';' + $env:PATH
$env:QAIRT_TMP_DIR = Join-Path $lab 'qairt-temp'
New-Item -ItemType Directory -Path $env:QAIRT_TMP_DIR | Out-Null
$env:TEMP = $env:QAIRT_TMP_DIR
$env:TMP = $env:QAIRT_TMP_DIR

# Somente carrega as DLLs do SDK e entrega os argumentos à ferramenta escolhida.
$launch = 'import os,runpy,sys; from pathlib import Path; root=Path(os.environ["QAIRT_SDK_ROOT"]); dll=os.add_dll_directory(str(root/"lib/x86_64-windows-msvc")); entry=root/"bin/x86_64-windows-msvc"/sys.argv[1]; sys.argv=[str(entry)]+sys.argv[2:]; runpy.run_path(str(entry),run_name="__main__")'
& $converter -X utf8 -c $launch qairt-converter --help
if ($LASTEXITCODE -ne 0) { throw 'Conversor/DLLs não carregaram' }
& $converter -X utf8 -c $launch qairt-quantizer --help
if ($LASTEXITCODE -ne 0) { throw 'Quantizador não carregou' }
```

O downloader obtém o subconjunto do [SDK público 2.51.40.260930](https://softwarecenter.qualcomm.com/api/download/software/sdks/Qualcomm_AI_Runtime_Community/All/2.51.40.260930/v2.51.40.260930.zip), verifica CRC dos membros e registra SHA-256 em `.build/sdk251-host/receipt.json`. O lançador mostrado inteiro acima corresponde ao preparo de DLLs de `host/qairt251_entry.py`; ele não exporta, calibra ou converte modelos. As chamadas abaixo expõem todos os argumentos das ferramentas Qualcomm. As variáveis alteram apenas este PowerShell; feche-o ao terminar.

## 7. Classificação: ONNX validado → DLC float → DLC quantizado

```powershell
$cls = Join-Path $lab classification
& $converter -X utf8 -c $launch qairt-converter -i (Join-Path $cls model.onnx) -o (Join-Path $cls model.float.dlc) --source_model_input_layout input NHWC --source_model_input_datatype input float32 --onnx_skip_simplification --onnx_disable_defer_loading > (Join-Path $cls conversion.log) 2>&1
if ($LASTEXITCODE -ne 0) { throw "Verificar $cls/conversion.log" }

Push-Location $cls
try {
    & $converter -X utf8 -c $launch qairt-quantizer --input_dlc (Join-Path $cls model.float.dlc) --input_list (Join-Path $cls calibration/input_list.txt) --output_dlc (Join-Path $cls model.w8a16.dlc) --weights_bitwidth 8 --act_bitwidth 16 --bias_bitwidth 32 > (Join-Path $cls quantization.log) 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Verificar $cls/quantization.log" }
} finally { Pop-Location }

& $converter -X utf8 -c $launch qairt-dlc-info -i (Join-Path $cls model.w8a16.dlc) --save (Join-Path $cls model-info.csv) > (Join-Path $cls model-info.txt) 2>&1
if ($LASTEXITCODE -ne 0) { throw 'Inspeção do DLC falhou' }
Get-FileHash (Join-Path $cls model.onnx), (Join-Path $cls model.float.dlc), (Join-Path $cls model.w8a16.dlc) -Algorithm SHA256
Select-String -Path (Join-Path $cls model-info.csv) -Pattern 'uFxp_8|uFxp_16|bitwidth'
```

`-i/-o` definem os arquivos de entrada/saída. `NHWC` mantém o layout esperado; `float32` estabelece a interface de entrada real do DLC. As flags ONNX preservam o caminho de conversão usado no treinamento. O quantizador lê os tensores float32 da lista, solicita pesos de 8 bits, ativações de 16 bits e bias de 32 bits. A lista contém nomes relativos `calibration/00.raw`, evitando espaços no parser de inputs; `Push-Location` executa o quantizador na pasta do caso e `finally` retorna a `training_v2`.

**“DLC float” aqui é o arquivo intermediário gerado antes da chamada explícita ao quantizador.** Como o ONNX de classificação mantém Q/DQ de origem, esse nome não garante que todo tensor interno seja float. Da mesma forma, `model.w8a16.dlc` e `--act_bitwidth 16` expressam uma solicitação: os encodings já existentes podem permanecer em 8 bits. No artefato homologado da classificação, `model-info.csv` mostra `uFxp_8` na entrada e em ativações. Registre a precisão efetiva observada no seu candidato. Esse ponto explica por que filename e flags, sozinhos, não comprovam a precisão de execução.

## 8. Estudo do SSD: converter e recalibrar a CNN

```powershell
$ssd = Join-Path $lab detection
& $converter -X utf8 -c $launch qairt-converter -i (Join-Path $ssd model.onnx) -o (Join-Path $ssd model.float.dlc) --source_model_input_layout normalized_input_image_tensor NHWC --source_model_input_datatype normalized_input_image_tensor float32 --onnx_skip_simplification --onnx_disable_defer_loading --source_model_output_layout Squeeze NFC --desired_output_layout Squeeze NFC --source_model_output_layout convert_scores NFC --desired_output_layout convert_scores NFC > (Join-Path $ssd conversion.log) 2>&1
if ($LASTEXITCODE -ne 0) { throw "Verificar $ssd/conversion.log" }

Push-Location $ssd
try {
    & $converter -X utf8 -c $launch qairt-quantizer --input_dlc (Join-Path $ssd model.float.dlc) --input_list (Join-Path $ssd calibration/input_list.txt) --output_dlc (Join-Path $ssd model.w8a16.dlc) --weights_bitwidth 8 --act_bitwidth 16 --bias_bitwidth 32 > (Join-Path $ssd quantization.log) 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Verificar $ssd/quantization.log" }
} finally { Pop-Location }

& $converter -X utf8 -c $launch qairt-dlc-info -i (Join-Path $ssd model.w8a16.dlc) --save (Join-Path $ssd model-info.csv) > (Join-Path $ssd model-info.txt) 2>&1
if ($LASTEXITCODE -ne 0) { throw 'Inspeção SSD falhou' }
Get-FileHash (Join-Path $ssd model.onnx), (Join-Path $ssd model.float.dlc), (Join-Path $ssd model.w8a16.dlc) -Algorithm SHA256
Select-String -Path (Join-Path $ssd model-info.csv) -Pattern 'uFxp_8|uFxp_16|bitwidth'
```

`NFC` informa o layout das saídas de três dimensões. Elas representam 1917 caixas codificadas e 91 scores por anchor, incluindo background. O HTP executa a CNN; a CPU precisa decodificar caixas com os anchors, aplicar os limiares e fazer NMS. Não compare diretamente essas saídas com as dez caixas finais do operador customizado TFLite.

O caminho que preservava os encodings antigos do SSD executou, mas produziu caixas extras. Por isso a etapa 4.1 remove esses quantizadores e a etapa 8 recalibra o grafo. O fluxo homologado está em `htp251/models/detection_requant/`; os candidatos deste roteiro ficam em `$lab/detection/`. Os pesos/tarefas de origem são mantidos, mas a quantização muda e requer nova aceitação.

## 9. Preparar os arquivos de transferência de um caso

Execute esta seção primeiro com classificação. Depois repita da seção 9 em diante com `$task = 'detection'`, criando outro `$remoteRun`.

```powershell
$task = 'classification'   # Na segunda passagem: 'detection'
$case = Join-Path $lab $task
$contract = Get-Content (Join-Path $case contract.json) -Raw | ConvertFrom-Json
$remoteRun = '/opt/qb560d-ai-htp251/runs/manual-' + [guid]::NewGuid().ToString('N').Substring(0,14)
$inputLine = $contract.input.name + ':=' + $remoteRun + '/input.raw'
[System.IO.File]::WriteAllText((Join-Path $case input_list.txt), $inputLine + "`n", [System.Text.Encoding]::ASCII)
$checksums = @('model.w8a16.dlc','input.raw','input.png') | ForEach-Object {
    $file = $_
    $remoteName = if ($file -eq 'model.w8a16.dlc') { 'model.dlc' } else { $file }
    (Get-FileHash (Join-Path $case $file) -Algorithm SHA256).Hash.ToLower() + '  ' + $remoteName
}
[System.IO.File]::WriteAllText((Join-Path $case transfer.sha256), ($checksums -join "`n") + "`n", [System.Text.Encoding]::ASCII)
$adb = (Resolve-Path tools/platform-tools/adb.exe).Path
& $adb devices -l
```

Conecte uma única caixa. Na listagem, anote o `transport_id`. Nos exemplos, substitua `ID_DA_LISTAGEM` pelo número observado; o serial `?` não identifica uma unidade de forma única.

```powershell
$adbSelection = @('-t', 'ID_DA_LISTAGEM')
```

O PowerShell de conversão permanece como **Terminal B**, com `$lab`, `$case` e `$remoteRun`. Abra outro PowerShell em `training_v2`, que será o **Terminal A**, e execute:

```powershell
$adb = (Resolve-Path tools/platform-tools/adb.exe).Path
& $adb -t ID_DA_LISTAGEM shell
```

**Terminal A, Linux da caixa:** faça login root com a senha fornecida pelo instrutor e mantenha a sessão aberta durante os transfers do Terminal B. Na preparação inicial, confira/crie somente o diretório identificado do treinamento:

```sh
python3 - <<'PY'
import json
from pathlib import Path
p = Path('/opt/qb560d-ai-htp251')
assert p.resolve() == p
owner = {'package':'qb560d-ai-htp251-v1'}
if p.exists():
    assert json.loads((p/'.owner.json').read_text()) == owner, 'Diretório de outro proprietário'
else:
    p.mkdir()
    (p/'.owner.json').write_text(json.dumps(owner))
(p/'runs').mkdir(exist_ok=True)
assert Path('/opt/qairt-isolated/2.51.40.260930/bin/qnn-net-run').is_file(), 'Provisionar QAIRT primeiro'
print('OWNED_MANUAL_WORKSPACE_READY')
PY
```

**Terminal B, PowerShell:** use as variáveis da sessão de conversão. O comando abaixo imprime exatamente a atribuição que deve ser copiada para o Terminal A.

```powershell
Write-Output "run='$remoteRun'"
```

**Terminal A, Linux da caixa:** cole a linha `run='…'` impressa acima; depois:

```sh
mkdir "$run"
```

**Terminal B, PowerShell:**

```powershell
& $adb @adbSelection push (Join-Path $case model.w8a16.dlc) "$remoteRun/model.dlc"
if ($LASTEXITCODE -ne 0) { throw 'Transferência DLC falhou' }
foreach ($file in @('input.raw','input.png','input_list.txt','transfer.sha256')) {
    & $adb @adbSelection push (Join-Path $case $file) "$remoteRun/$file"
    if ($LASTEXITCODE -ne 0) { throw "Transferência falhou: $file" }
}
Write-Output "task='$task'"
Write-Output "expected_source_sha='$($contract.source_sha256)'"
```

O input de inferência é a mesma primeira imagem usada na validação ONNX, redimensionada e gravada como PNG, com tensor float32 little-endian em `input.raw`. A lista usa `nome_da_entrada:=caminho_absoluto_do_raw`. O runtime converte o input float para a codificação interna do grafo; não acrescente `--use_native_input_files` a esse comando.

## 10. Referência CPU e comando HTP sem o runner do workshop

**Terminal A, Linux da caixa:** cole também as linhas `task='…'` e `expected_source_sha='…'` impressas no Terminal B.

```sh
cd "$run"
set -e
sha256sum -c transfer.sha256
# Pare se qualquer hash falhar.
if [ "$task" = classification ]; then source_model=mobilenet_v1.tflite; else source_model=ssd_mobilenet_v1.tflite; fi
printf '%s  %s\n' "$expected_source_sha" "/opt/qb560d-training-payload/models/$source_model" | sha256sum -c -
# Pare se a referência da caixa não for o mesmo TFLite.

sh /opt/qb560d-training-payload/target/ai.sh "$task" \
  --image "$run/input.png" --output "$run/reference" \
  --runs 1 --warmup 0 --vendor-c-api
# Exigir exit code 0 antes de continuar.

runtime=/opt/qairt-isolated/2.51.40.260930
export LD_LIBRARY_PATH="$runtime/lib:/usr/lib:/lib/aarch64-linux-gnu:/usr/lib/aarch64-linux-gnu"
export ADSP_LIBRARY_PATH="$runtime/dsp;/usr/lib/rfsa/adsp;/dsp;/usr/lib"
"$runtime/bin/qnn-net-run" --version

timeout 180s "$runtime/bin/qnn-net-run" \
  --model "$runtime/lib/libQnnModelDlc.so" \
  --dlc_path "$run/model.dlc" \
  --backend "$runtime/lib/libQnnHtp.so" \
  --input_list "$run/input_list.txt" \
  --output_dir "$run/htp" \
  --profiling_level detailed --log_level info \
  --num_inferences 3 --keep_num_outputs 3
# Exigir exit code 0; erro de grafo/runtime não autoriza declarar sucesso CPU.

"$runtime/bin/qnn-profile-viewer" \
  --input_log "$run/htp/qnn-profiling-data_0.log" \
  --output "$run/htp/profile.csv"
ls "$run/htp/Result_0"
```

`libQnnModelDlc.so` carrega o DLC; `libQnnHtp.so` seleciona o backend HTP. Os arquivos `.raw` em `Result_0` são as saídas, não os pesos do modelo. A referência TFLite CPU é uma execução separada e explícita. O comando não pede fallback CPU para uma falha do HTP.

**Terminal B, PowerShell:** o destino abaixo deve ser novo. O ADB coloca o conteúdo do diretório remoto diretamente nele quando o destino ainda não existe.

```powershell
$target = Join-Path $case ('target-' + [guid]::NewGuid().ToString('N').Substring(0,8))
& $adb @adbSelection pull $remoteRun $target
if ($LASTEXITCODE -ne 0) { throw 'Coleta falhou' }
$env:MANUAL_TASK = $task
$env:MANUAL_TARGET = $target
```

## 11. Interpretar as saídas, comparar e provar HTP

O bloco abaixo abre também o pós-processamento: lê os tensores float32 do QNN, exige perfil positivo e compara resultados. Para classificação, mostra os três maiores scores e exige o mesmo top-1 da CPU. Para SSD, calcula centros/tamanhos com os anchors e escalas de `contract.json`, remove background, ordena scores, aplica NMS e exige pessoa com IoU ≥ 0,70, limitando caixas extras. São as operações de `detection_decode`/`semantic` de `host/htp251_workshop.py`, expostas aqui para a aula. Nenhuma função do runner é chamada neste bloco.

```powershell
@'
import csv, hashlib, json, os, re
from pathlib import Path
import numpy as np
root = Path(os.environ['MANUAL_TRAINING']); task = os.environ['MANUAL_TASK']
folder = Path(os.environ['MANUAL_LAB'])/task; target = Path(os.environ['MANUAL_TARGET'])
contract = json.loads((folder/'contract.json').read_text())
assert hashlib.sha256((target/'model.dlc').read_bytes()).hexdigest() == hashlib.sha256((folder/'model.w8a16.dlc').read_bytes()).hexdigest()
lines = (target/'htp/profile.csv').read_text(encoding='utf-8-sig').splitlines()
start = next(i for i,line in enumerate(lines) if line.startswith('Msg Timestamp,'))
rows = [{k.strip():v.strip() for k,v in row.items()} for row in csv.DictReader(lines[start:])]
profile = dict(accelerator_events=sum(r.get('Message')=='EXECUTE' and 'qnn accelerator' in r.get('Event Identifier','').lower() and float(r.get('Time') or 0)>0 for r in rows), positive_cycle_events=sum(r.get('Unit of Measurement')=='CYCLES' and float(r.get('Time') or 0)>0 for r in rows))
assert profile['accelerator_events']>0 and profile['positive_cycle_events']>0, 'Sem prova de execução HTP'
files = list((target/'htp/Result_0').rglob('*.raw')); outputs = []; used = set()
for spec in contract['outputs']:
    safe = re.sub(r'[^A-Za-z0-9_.-]', '_', spec['name']); count = int(np.prod(spec['shape']))
    matches = [p for p in files if p not in used and p.stat().st_size==count*4 and p.stem in (spec['name'],safe,spec['name'].replace('/','_').replace(':','_'))]
    if not matches: matches = [p for p in files if p not in used and p.stat().st_size==count*4]
    assert len(matches)==1, ('Tensor ausente ou ambíguo', spec['name'])
    used.add(matches[0]); value = np.fromfile(matches[0], dtype='<f4').reshape(spec['shape'])
    assert np.isfinite(value).all(); outputs.append(value)
reference_dir = target/'reference'/task
jsons = list(reference_dir.glob('*.json')); arrays = list(reference_dir.glob('*.npz'))
assert len(jsons)==len(arrays)==1
reference = json.loads(jsons[0].read_text())
assert reference['model_sha256']==contract['source_sha256']
def iou(a,b):
    y0=max(a[0],b[0]); x0=max(a[1],b[1]); y1=min(a[2],b[2]); x1=min(a[3],b[3])
    intersection=max(0,y1-y0)*max(0,x1-x0)
    area=lambda box:max(0,box[2]-box[0])*max(0,box[3]-box[1])
    return float(intersection/max(area(a)+area(b)-intersection,1e-12))
if task=='classification':
    labels=(root/'models/imagenet_labels.txt').read_text(encoding='utf-8').splitlines()
    scores=outputs[0].reshape(-1); top=np.argsort(scores)[-3:][::-1]
    result=dict(top3=[dict(class_id=int(i),label=labels[i],score=float(scores[i])) for i in top])
    comparison=dict(passed=int(top[0])==reference['top3'][0]['class_id'],criterion='Mesmo top-1 da referência TFLite CPU')
else:
    anchors=np.load(folder/'anchors.npy'); options=contract['nms_options']
    enc=outputs[0].reshape(-1,4); scores=outputs[1].reshape(len(enc),-1)[:,1:]
    classes=np.argmax(scores,axis=1); best=np.max(scores,axis=1)
    cy=enc[:,0]/options['y_scale']*anchors[:,2]+anchors[:,0]
    cx=enc[:,1]/options['x_scale']*anchors[:,3]+anchors[:,1]
    height=np.exp(np.clip(enc[:,2]/options['h_scale'],-50,50))*anchors[:,2]
    width=np.exp(np.clip(enc[:,3]/options['w_scale'],-50,50))*anchors[:,3]
    boxes=np.stack([cy-height/2,cx-width/2,cy+height/2,cx+width/2],axis=1)
    selected=[]
    for index in np.argsort(best,kind='stable')[::-1]:
        if best[index]<options['nms_score_threshold']: break
        if any(iou(boxes[index],boxes[other])>options['nms_iou_threshold'] for other in selected): continue
        selected.append(int(index))
        if len(selected)>=options['max_detections']: break
    labels=(root/'models/coco_labels.txt').read_text(encoding='utf-8').splitlines()
    detections=[dict(class_id=int(classes[i]),label=labels[int(classes[i])+1],score=float(best[i]),box_yxyx=np.clip(boxes[i],0,1).tolist()) for i in selected if best[i]>=0.5]
    result=dict(detections=detections)
    actual=[d for d in detections if d['label']=='person']
    expected=[d for d in reference['detections'] if d['label']=='person']
    overlap=max([iou(a['box_yxyx'],b['box_yxyx']) for a in actual for b in expected] or [0])
    comparison=dict(passed=bool(actual and expected and overlap>=0.7 and len(actual)<=len(expected)+1 and len(detections)<=len(reference['detections'])+2),person_box_iou=overlap,criterion='Pessoa com IoU >=0.70 e limite de caixas extras')
report = dict(task=task, source_sha256=contract['source_sha256'], dlc_sha256=hashlib.sha256((folder/'model.w8a16.dlc').read_bytes()).hexdigest(), profile=profile, result=result, comparison=comparison, passed=bool(comparison['passed']), scope='Referência didática; não é acurácia de dataset nem benchmark de latência')
(folder/'acceptance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
assert report['passed'], 'HTP executou, mas o resultado precisa de revisão'
'@ | Set-Content -Encoding UTF8 (Join-Path $lab accept.py)
& $py (Join-Path $lab accept.py)
if ($LASTEXITCODE -ne 0) { throw 'Candidato não aceito; inspecionar logs e saídas' }
```

Os resultados homologados anteriores estão na [galeria HTP](../htp251/results/index.html): classificação `military uniform`, SSD com pessoa/gravata e IoU de pessoa aproximadamente 0,9975. Esses números são referências históricas; o novo candidato precisa produzir o seu próprio `acceptance.json`. Não copie o hash de um DLC antigo para identificar uma conversão nova. Uma execução com perfis detalhados mede também overhead; não use seus tempos como benchmark comparativo.

## 12. O que mostrar durante a aula e o que guardar

| Passagem | Comando principal | Arquivos/prova para abrir |
|---|---|---|
| Origem → TFLite | download e leitura do membro esperado | `source.tflite`, URL e SHA-256 |
| Contrato | inspeção TensorFlow | `contract.json`; SSD: `anchors.npy` e opções NMS |
| TFLite → ONNX | `python -m tf2onnx.convert` + ajustes abertos | `export.onnx`, `model.onnx`, `onnx-adjustments.json` |
| ONNX validado | TFLite Interpreter × ONNX Runtime | `onnx-validation.json`, erros, `calibration/*.raw`, lista e hashes das imagens |
| ONNX → DLC intermediário | `qairt-converter` | `model.float.dlc`, `conversion.log` |
| Calibração/quantização | `qairt-quantizer` | `model.w8a16.dlc`, `quantization.log` |
| Precisão efetiva | `qairt-dlc-info` | `model-info.csv`, tipos/encodings por tensor |
| Transferência | `adb push`, `sha256sum -c` | `transfer.sha256`, nomes e hashes do candidato |
| Inferência | `qnn-net-run` + backend HTP | `.raw`, log de execução, referência CPU independente |
| Aceitação | profile viewer + comparação | `profile.csv`, `acceptance.json`, eventos/ciclos positivos, top-1 ou IoU |

Explique as falhas que motivaram o fluxo atual:

- **TFLite direto no conversor Windows:** o subconjunto público usado exigia TVM que não estava disponível. A exportação intermediária ONNX tornou o processo reproduzível com as ferramentas selecionadas.
- **Eixo de DequantizeLinear:** alguns tensores 1D com escala escalar precisaram de `axis=0` explícito; o ajuste fica registrado.
- **SSD executando com caixas incorretas:** os encodings antigos mantidos na primeira tentativa geraram detecções extras. A solução foi reconstruir a CNN em float, recalibrar e validar novamente.
- **Input correto em um modelo e errado em outro:** classificação usa a entrada real normalizada; o SSD deste fluxo recebe pixels float 0–255 porque a normalização está no grafo.
- **Nome w8a16 sem precisão efetiva correspondente:** Q/DQ preservado pode manter encodings de 8 bits. Inspecione o DLC.
- **DLC roda na CPU QNN, ou falha nela:** QNN CPU não substitui a referência TFLite CPU. Houve falhas de preparação de modelos w8a16 nesse backend no ensaio original; o critério principal continua sendo execução HTP com comparação TFLite.
- **DLLs/caminhos longos no Windows:** use caminhos curtos, ambientes separados e o carregamento explícito de DLLs. Os temporários pertencem somente à pasta da sessão.
- **Checksum no Linux procurando um nome com `\r`:** os arquivos enviados à caixa precisam de LF. Por isso o PowerShell usa `WriteAllText` com uma quebra LF explícita para lista e checksums; não substitua por um gravador que insira CRLF.

## 13. Relação com as automações existentes

Depois de explicar as etapas manuais, mostre onde elas aparecem nos scripts:

| Etapas deste capítulo | Implementação do treinamento |
|---|---|
| Download/hash e origem | `ai/fetch_models.py`, `ai/profiles.json`, `models/models.lock.json` |
| Inspeção, anchors, NMS | `host/inspect_htp251_sources.py` |
| Exportação, ajustes, calibração, comparação ONNX | `host/export_htp251_models.py` |
| SDK, DLLs e temporários | `host/fetch_qairt251_converter.py`, `host/qairt251_entry.py` |
| Converter, quantizer, DLC info e manifesto | `host/convert_htp251_models.py`, `htp251/models.json` |
| Deploy, TFLite CPU, QNN/HTP, perfil, pós-processamento e comparação | `host/htp251_workshop.py` |

O caminho automatizado é apresentado no [README HTP](../htp251/README.md#conversão-reproduzível-somente-para-preparação). Ele escreve os manifests de autoria em `htp251/`; use-o em uma cópia de preparação quando estiver reconstruindo candidatos. O roteiro manual deste capítulo escreve em `$lab` e executa candidatos em um diretório de run novo, sem publicar um novo modelo automaticamente.

Referências: [documentação pública do SDK QAIRT](https://docs.qualcomm.com/bundle/publicresource/topics/80-63442-10/general_overview.html), [exemplo Qualcomm/AIMET de conversão e quantização para execução no target](https://qualcomm.github.io/aimet-pages/releases/2.26.0/tutorials/on_target_inference.html), locks e logs QAIRT 2.51 deste treinamento. A autoridade para os argumentos desta versão é o `--help` do SDK 2.51 fixado, junto dos comandos registrados em `htp251/models.json`; outras versões do SDK podem expor interfaces diferentes.

## 14. Validação deste roteiro em 04/11/2026

Os blocos Python foram extraídos deste documento e executados com os TFLites locais, conferidos pelos hashes oficiais da seção 2. Foram gerados ONNX, inputs de calibração, DLCs intermediários e DLCs quantizados novos. Os comandos Qualcomm foram executados nos ambientes de preparação já existentes. A nova classificação e o novo SSD foram enviados a diretórios de execução novos na caixa e comparados com referências TFLite CPU novas; o validador da seção 11 foi executado sem importar funções do runner.

Resultado: classificação com o mesmo top-1 CPU (`military uniform`), três eventos HTP e 99 eventos de ciclos positivos; SSD com IoU de pessoa **0,9973126**, três eventos HTP e 153 eventos de ciclos positivos. A conferência de 48 arquivos dos runtimes/modelos existentes não encontrou alterações. Os 19 blocos PowerShell passaram na análise sintática. A criação de ambientes e o download externo não foram repetidos neste ensaio; foram usados os ambientes e as cópias offline já disponíveis.

O [recibo de validação](../evidence/demo-regression/20261105T003157Z/release/MANUAL_CONVERSION.json) registra hashes dos candidatos, comparações e perfis. O diretório da estação pode usar data UTC de 05/11, correspondente à noite de 04/11 em São Paulo. Esse resultado aprova os casos didáticos descritos, sem estabelecer acurácia em dataset ou homologar outra versão de SDK/BSP.

## 15. CPU, GPU e NPU/HTP: o que já foi medido

A rodada de **01/11/2026**, anterior aos candidatos manuais deste capítulo, aprovou 45 sessões: três por modelo/backend, com 10 aquecimentos e 50 inferências medidas em cada sessão. Tempos em ms, mediana das três medianas:

| Modelo | CPU: TFLite 2.8.4, duas threads | GPU: TFLite 2.8.4/OpenCL | NPU/HTP: DLC/QNN 2.51 |
|---|---:|---:|---:|
| MobileNet V1 / classificação | 26,496 | 10,149 | 1,500 |
| SSD MobileNet V1 / detecção | 35,668 | 23,559 | 3,936 |
| PoseNet / pose | 137,924 | 15,710 | 2,201 |
| Hand Landmark Lite / mão recortada | 55,952 | 7,742 | 1,782 |
| DeepLabV3 / segmentação | 179,767 | 21,419 | 4,609 |

CPU/GPU usam os TFLites originais; HTP usa os DLCs convertidos e quantizados homologados. Portanto, o comparativo abrange os caminhos disponíveis da demo, com runtimes e precisões diferentes. Não é uma comparação do mesmo binário DLC nos três backends. A GPU foi confirmada por logs OpenCL; operadores residuais podem executar na CPU. O backend QNN GPU 2.51 não faz parte desta instalação.

A medida cobre a chamada de inferência, sem download, carga/compilação, pré-processamento, ADB ou desenho. **No SSD, o invoke TFLite inclui NMS; a medida HTP termina em caixas/scores e exclui NMS na CPU.** Esses tempos não são FPS de câmera nem latência ponta a ponta. Os perfis detalhados da seção 14 comprovam execução dos candidatos novos; eles não substituem uma rodada de benchmark desses candidatos.

Para repetir o benchmark dos **artefatos homologados** a partir de `training_v2`:

```powershell
$py = (Resolve-Path provision_target/.venv/Scripts/python.exe).Path
$adb = (Resolve-Path tools/platform-tools/adb.exe).Path
& $py host/benchmark_htp251.py --adb $adb --sessions 3 --warmup 10 --runs 50
if ($LASTEXITCODE -ne 0) { throw 'Benchmark incompleto; revisar os logs' }
```

Acrescente `--task classification` ou `--task detection` para um caso. Esse runner seleciona os modelos registrados em `htp251/models.json`; ele não troca automaticamente para os candidatos de `$lab`. Para medir um candidato novo, faça essa seleção explicitamente em uma cópia de preparação, registrando os hashes e as mesmas condições de entrada, warmup, runs e perfil; não atribua ao candidato os números históricos da tabela.

Consulte [metodologia e reprodução do benchmark](../htp251/BENCHMARK.md), [amostras, p95 e critérios](../htp251/results/timing-summary.json) e a [explicação da Qualcomm sobre QNN/HTP e Hexagon NPU](https://www.qualcomm.com/developer/blog/2026/10/how-ai-models-reach-hexagon-npu-qairt-fastrpc-hexagon-explained).
