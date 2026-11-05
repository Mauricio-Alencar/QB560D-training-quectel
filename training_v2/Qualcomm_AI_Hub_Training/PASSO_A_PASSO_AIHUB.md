# Primeiro laboratório AI Hub Workbench

Estado em 1 de novembro de 2026: conta/API autenticadas, compile e inference/profile aprovados. O TFLite exportado também passou na CPU da QB560D-EU com runtime 2.8.4. A GPU local passou com OpenCL confirmado. O pacote offline e um vídeo de 106 segundos, com replay dos logs reais, estão disponíveis abaixo. O ambiente do computador usa Python 3.12 e as versões de `requirements.txt`.

Entregas: [pacote offline](demo_offline/README.md), [vídeo de contingência](contingencia/AIHub_QB560D_Contingencia_Replay.mp4) e [comparação completa](evidence/tiny-gpu-20261101-171619/deployment-comparison.json).

Primeira execução acompanhada: [compile j5q1v4l7g](https://workbench.aihub.qualcomm.com/jobs/j5q1v4l7g/) e [inference/profile j56mwo8vp](https://workbench.aihub.qualcomm.com/jobs/j56mwo8vp/) concluídos com sucesso. Os resultados e a revisão estão em `evidence/tiny-gpu-20261101-171619/`, incluindo [hosted-review.json](evidence/tiny-gpu-20261101-171619/hosted-review.json).

### Resultado hospedado conferido

| Saída | Referência NumPy | GPU hospedada | Diferença absoluta |
|---|---:|---:|---:|
| 0 | 0,09336850 | 0,09338379 | 0,00001529 |
| 1 | 0,18468535 | 0,18469238 | 0,00000703 |
| 2 | 0,32469758 | 0,32470703 | 0,00000945 |
| 3 | 0,09120750 | 0,09124756 | 0,00004005 |

Todas as saídas passaram em `allclose(atol=1e-4, rtol=1e-3)`. O profile lista quatro operações em GPU (TRANSPOSE, CONV_2D, MEAN e RESHAPE) e nenhuma entrada de CPU. Isso descreve o grafo listado, sem afirmar que todo o programa evita CPU.

O campo `estimated_inference_time` é 217 µs (0,217 ms). A mediana das 100 amostras salvas é 694,5 µs (0,6945 ms), com faixa de 217–4895 µs. A estimativa reportada não é a mediana dessas amostras. São medidas do kit hospedado, e não da QB560D-EU. A [documentação de profiling](https://workbench.aihub.qualcomm.com/docs/hub/jobs.html) define os tempos em microssegundos.

O artefato tem 1992 bytes e SHA-256 `6a569f3f9ea3b0891281f7122e76ba568ce0d2307a437ecbf7810c69bcd150fc`. A primeira execução CPU na caixa passou com o mesmo hash, erro máximo de 1,49e-08, 10 aquecimentos/50 invokes, mediana de 0,0848305 ms e p95 de 0,0870753 ms. Esses tempos locais cobrem somente invoke. Não calcular ganho de hardware dividindo a estimativa hospedada pela mediana local.

### Resultado local e contingência

| Backend na QB560D-EU | Resultado | Erro absoluto máximo | Mediana invoke | p95 invoke |
|---|---|---:|---:|---:|
| CPU | PASS | 1,49e-08 | 0,0848305 ms | 0,0870753 ms |
| GPU OpenCL | PASS | 2,98e-08 | 0,2543065 ms | 0,4496499 ms |

Mesmo arquivo TFLite, entrada e referência, runtime 2.8.4, 10 aquecimentos e 50 invokes por backend. OpenCL e um kernel GPU delegado aparecem no log local. A mediana GPU foi aproximadamente 3 vezes a da CPU neste grafo pequeno. Isso não contradiz o funcionamento do delegate nem demonstra um ganho geral de GPU. O objetivo deste exercício é conversão, execução e validação numérica.

O pacote também foi testado de forma independente na pasta `/opt/qb560d-training-payload/aihub-offline-demo`, com seis hashes conferidos e CPU/GPU aprovados. O runner Linux usa quebras de linha LF. Veja [teste do pacote](evidence/tiny-gpu-20261101-171619/offline-validation.json). Ele reutiliza o BSP e o NumPy privado já preparados na caixa.

Controle negativo de configuração: em um processo filho com `QAIHUB_CLIENT_INI` apontando para um arquivo inexistente, `account.py devices` retornou 2 e `ACCOUNT_NOT_CONFIGURED`, sem enviar job nem alterar a configuração real. A falha foi preservada em [negative-config.json](evidence/tiny-gpu-20261101-171619/negative-config.json).

Orçamento didático proposto: 5 min contrato/modelo, 5 min conta/dispositivo, 15 min jobs e fila, 10 min deploy CPU/GPU, 10 min comparação, 5 min contingência, total 50 min. O ensaio didático completo cronometrado continua no item 7 da checklist temporária.

## 1. Entrar no portal

Abra https://workbench.aihub.qualcomm.com/ e entre com sua Qualcomm ID. Na tela inicial, a linha **Configure your API token** permite copiar o token pelo ícone à direita. A alternativa documentada é **Account > Settings > API Token**. Selecione a organização pretendida antes de copiar: o token pertence à organização ativa.

## 2. Configurar o cliente no computador

Abra PowerShell na pasta `aibox_training/training_v2` do pacote extraído. O laboratório desta estação já foi preparado em uma pasta curta para evitar o limite de caminhos do Windows/OneDrive.

Prepare primeiro o host portátil pelo README principal. Crie o ambiente do cliente dentro desta cópia do treinamento; o download dos pacotes AI Hub requer Internet:

```powershell
$py = (Resolve-Path provision_target/.venv/Scripts/python.exe).Path
& $py -m venv .build/aihub-client
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o ambiente do cliente AI Hub' }
$hubPy = (Resolve-Path .build/aihub-client/Scripts/python.exe).Path
& $hubPy -m pip install -r Qualcomm_AI_Hub_Training/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha nas dependências do cliente AI Hub' }
& $hubPy Qualcomm_AI_Hub_Training/host/account.py check
& $hubPy Qualcomm_AI_Hub_Training/host/account.py configure
```

O comando `configure` pede o token com entrada oculta. Cole-o diretamente no terminal e pressione Enter. Se o ícone do portal copiar o comando inteiro `qai-hub configure --api_token ...`, o helper também aceita essa linha e extrai o token, sem executar o comando colado. Ele valida o acesso consultando dispositivos e grava a configuração padrão do SDK no perfil do usuário, fora da pasta de treinamento. Não imprime o token. Se houver uma configuração anterior, o helper a preserva. O esperado é `ACCOUNT_READY` e uma quantidade de dispositivos.

O comando oficial `qai-hub configure --api_token ...` existe. Neste laboratório usamos o helper para evitar o token no histórico e na saída do terminal durante a gravação. O cliente0.57.0 imprime o conteúdo da configuração ao executar seu comando configure.

Em uma nova extração, repita o preparo acima; crie a venv no destino em vez de copiar a venv de outra estação. Se já configurou o cliente, reutilize `.build/aihub-client/Scripts/python.exe` nesta cópia.

## 3. Escolher um dispositivo hospedado

```powershell
& $hubPy Qualcomm_AI_Hub_Training/host/account.py devices --contains 6490
```

Se nenhum dispositivo corresponder, liste todos sem `--contains`. Use o nome exato retornado. Registre o dispositivo e o sistema operacional do job. A QB560D-EU conectada por ADB não se torna automaticamente um dispositivo hospedado pelo AI Hub. As medições hospedadas e as locais ficam separadas.

## 4. Entender a referência do primeiro exercício

Usaremos os arquivos já preparados:

- `models/workbench_demo.onnx`: Conv3×3 com quatro filtros, ReLU, média espacial e Flatten.
- `models/workbench_input.npy`: entrada sintética float32, NCHW `[1,3,32,32]`.
- `models/workbench_expected.npy`: referência NumPy, saída `[1,4]`.

Valores aproximados esperados: `[0.0933685, 0.1846853, 0.3246976, 0.0912075]`. São características numéricas de um modelo determinístico, sem classes de objetos. O objetivo inicial é validar o fluxo completo com uma referência pequena e controlada. A MobileNet será uma extensão visual depois.

## Origem do modelo do laboratório

| Demo/modelo | Origem e tratamento | Download / artefato |
|---|---|---|
| Tiny / `aihub_tiny_6a569f3f9ea3.tflite` | **Sintético, sem treinamento, criado por nós** em ONNX. Compilado no AI Hub Workbench e baixado como TFLite; executado localmente em CPU/GPU. | [ONNX de entrada](../models/workbench_demo.onnx) · [TFLite gerado](demo_offline/models/aihub_tiny_6a569f3f9ea3.tflite) · [Job de compilação](https://workbench.aihub.qualcomm.com/jobs/j5q1v4l7g/) |

Esse exercício ensina envio, compilação, inferência/profile e deploy; o modelo não vem do catálogo pré-treinado e seus quatro valores de saída não são classes semânticas. IDs, opções e hashes estão em [jobs.json](demo_offline/evidence/jobs.json). Os links de jobs podem exigir login/acesso à conta AI Hub; o TFLite preservado no pacote permite repetir a parte local offline. As duas demos do catálogo com DLCs prontos são MobileNet V2 e MediaPipe sete gestos, conforme o [mapa geral](../README.md#origem-dos-modelos-e-das-demos).

## 5. Executar compile, inference e profile

Na mesma sessão PowerShell, use o nome confirmado pela consulta desta conta. Em outra data/conta, repita a etapa3 antes de escolher:

```powershell
$device = 'Dragonwing RB3 Gen 2 Vision Kit'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$run = "Qualcomm_AI_Hub_Training/evidence/$stamp-tiny-gpu"
& $hubPy ai/workbench.py `
  --model models/workbench_demo.onnx `
  --device $device --runtime tflite --compute-unit gpu `
  --input models/workbench_input.npy `
  --expected models/workbench_expected.npy `
  --output $run
```

O programa envia o compile, salva ID/link, espera o resultado e envia inferência com `profile=True`, usando a entrada conhecida. Isso produz inferência e dados de profiling no cliente fixado. A fila pode demorar. Abra os links de `jobs.json` no portal para acompanhar. Uma falha permanece como falha, com os IDs preservados para investigação. Use outro diretório para uma nova tentativa.

Aceitação hospedada: compile e inferência com profile concluídos, saída próxima da referência (`atol=1e-4`, `rtol=1e-3`) e backend conferido no profile. Não inferir execução em GPU apenas pelo parâmetro solicitado.

## 6. Conferir os resultados

O diretório `$run` deve conter:

| Arquivo | Conteúdo |
|---|---|
| `jobs.json` | Dispositivo, opções, IDs/links, hashes e comparação numérica |
| `model.tflite` | Artefato gerado pelo compile |
| `hosted_outputs.npz` | Saída da inferência hospedada |
| `profile.json` | Dados de profiling do dispositivo hospedado |
| `scope.txt` | Local de execução e limites da comparação |

Compare a saída completa, além dos quatro valores exibidos. Confira quais unidades executaram os operadores e se houve fallback. O modelo é pequeno e não é uma promessa de ganho de desempenho em GPU.

## 7. Executar o artefato na AI Box

Com o job aprovado, mantendo `$run` e `$hubPy` na sessão:

```powershell
$hubPy = (Resolve-Path .build/aihub-client/Scripts/python.exe).Path
$run = 'Qualcomm_AI_Hub_Training/evidence/tiny-gpu-20261101-171619'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$artifact = Join-Path $run 'model.tflite'
$modelHash = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.Substring(0,12).ToLowerInvariant()
$modelName = "aihub_tiny_$modelHash.tflite"
Copy-Item -LiteralPath $artifact -Destination (Join-Path 'models' $modelName)
& $hubPy host/adb_lab.py push
& $hubPy host/adb_lab.py run ai tensor `
  --model "models/$modelName" `
  --input models/workbench_input.npy --expected models/workbench_expected.npy `
  --backend cpu --output "evidence/aihub-$stamp-cpu.json"
```

Confira `result: PASS`, o hash do artefato e as saídas. Se a CPU falhar, preserve o erro e investigue antes de continuar. Após aprovar a CPU, execute:

```powershell
& $hubPy host/adb_lab.py run ai tensor `
  --model "models/$modelName" `
  --input models/workbench_input.npy --expected models/workbench_expected.npy `
  --backend gpu --output "evidence/aihub-$stamp-gpu.json"
& $hubPy host/adb_lab.py pull
```

Os helpers descobrem o ADB portátil e pedem o login root da caixa. Use `--transport-id` antes da ação se houver várias caixas. O diretório padrão é `/opt/qb560d-training-payload`. A configuração/token AI Hub fica somente no computador.

O TFLite 2.8.4 do BSP pode não aceitar um operador gerado por um compilador moderno. Essa etapa verifica a compatibilidade real. Se falhar, preserve o erro e investigue o artefato/runtime. Não altere as bibliotecas originais do BSP para ocultar uma incompatibilidade. A comparação deve apresentar separadamente referência NumPy, inferência hospedada e CPU/GPU locais, com os hashes do mesmo artefato.

## 8. Preparar a contingência gravada

O [vídeo de 106 segundos](contingencia/AIHub_QB560D_Contingencia_Replay.mp4) está pronto: 1280x720, H.264, sem áudio, com legendas em português. Ele apresenta o contrato, os jobs reais, a saída hospedada, os logs CPU/GPU, a comparação e a repetição offline. É replay identificado de resultados salvos, sem nova submissão ou captura de autenticação. [Roteiro, hashes e fonte imutável](contingencia/recording.json).

Roteiro para apresentação ou futura gravação de tela ao vivo:

1. Explicar o modelo, a entrada e os quatro valores de referência.
2. Mostrar o comando de compile e o job no portal.
3. Mostrar a inferência, a comparação numérica e o profile. A gravação pode encurtar a espera da fila, identificando o corte.
4. Fazer o deploy do mesmo artefato e mostrar os resultados locais na caixa.
5. Mostrar os arquivos salvos e explicar a diferença entre o dispositivo hospedado e a QB560D-EU.

O vídeo deve omitir a configuração da credencial. Junto dele, manter artefato, entrada/referência, hashes, resultados e um roteiro para reprodução offline da parte local. O vídeo disponível usa os dados aprovados deste ensaio e está incluído no ZIP offline. A demonstração ao vivo, a gravação de uma execução real e o pacote offline serão identificados separadamente.

Referências: [instalação e autenticação oficiais](https://workbench.aihub.qualcomm.com/docs/hub/install.html), [organizações e tokens](https://workbench.aihub.qualcomm.com/docs/hub/collab_orgs.html), [compile e inferência com profile](https://workbench.aihub.qualcomm.com/docs/hub/compile_examples.html) e [guia amplo do projeto](GUIA_DEPLOY_AIBOX.md).
