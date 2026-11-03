# Tempos comparativos: CPU, GPU e HTP 2.51

Medição real na QB560D-EU em 01/11/2026. **45 sessões aprovadas**, três por backend e por modelo. Cada sessão fez 10 aquecimentos descartados e 50 inferências medidas. A tabela apresenta a mediana das três medianas de sessão, em milissegundos. A ordem CPU/GPU/HTP foi alternada; a mesma imagem preparada foi usada por tarefa.

| Demo | CPU TFLite 2.8.4 | GPU TFLite 2.8.4 | HTP QNN 2.51 |
|---|---:|---:|---:|
| Classificação / MobileNet V1 | 26.496 | 10.149 | 1.500 |
| Detecção / SSD MobileNet V1 | 35.668 | 23.559 | 3.936 |
| Pose / PoseNet | 137.924 | 15.710 | 2.201 |
| Mão recortada / Hand Landmark Lite | 55.952 | 7.742 | 1.782 |
| Segmentação / DeepLabV3 | 179.767 | 21.419 | 4.609 |

## Como interpretar

CPU e GPU usam os TFLite originais no runtime 2.8.4 do BSP; CPU com duas threads, GPU com partição OpenCL confirmada em log. Operadores residuais podem executar na CPU. Não existe `libQnnGpu.so` 2.51 na instalação atual e não foi instalado outro runtime para esta comparação. Os números GPU não são QNN GPU 2.51.

HTP usa os DLCs convertidos/quantizados validados, `libQnnHtp.so` do QAIRT/QNN 2.51.40.260930, `--perf_profile default` e `--profiling_level client`. Selecionamos somente eventos `NETRUN / ROOT / EXECUTE`, em microssegundos convertidos para ms, descartando os dez primeiros. Os perfis detalhados de execução no acelerador estão na rodada funcional anterior, com os mesmos hashes de DLC. O profiling detalhado não foi usado como medição de latência.

O intervalo medido cobre `InterpreterInvoke` no TFLite e a chamada de execução do grafo no QNN. Não inclui carregar/compilar modelos, preparar imagem, renderizar ou transferir via ADB. **SSD tem uma diferença de escopo:** o TFLite inclui seu pós-processamento/NMS interno no invoke; o grafo QNN termina em caixas/scores e o NMS no host fica fora desses 3,936 ms. As precisões/encodings e pipelines diferem. Estes números comparam os caminhos disponíveis da demo; não isolam ganho puro do hardware e não equivalem a FPS de uma aplicação/câmera.

As 45 saídas passaram nos critérios semânticos contra o TFLite CPU da respectiva imagem (top-1, caixa de pessoa, pontos visíveis, gesto e máscara). O teste não mede acurácia de dataset. Não mudamos governors, serviços, PATH global ou bibliotecas; carga e temperaturas observadas ficam nos logs `conditions-*.log`. O snapshot ampliado conferiu **48 arquivos/entradas**, sem alteração.

## Reproduzir no host

PowerShell na raiz `training_v2`, após o preparo normal de host/target:

```powershell
$py = (Resolve-Path './provision_target/.venv/Scripts/python.exe').Path
$adb = (Resolve-Path './tools/platform-tools/adb.exe').Path
& $py host/benchmark_htp251.py --adb $adb --sessions 3 --warmup 10 --runs 50
```

Para uma tarefa apenas, acrescente `--task classification`, `detection`, `pose`, `gesture` ou `segmentation`. A senha root é pedida sem ser salva. Os dados remotos novos ficam em `/opt/qb560d-ai-htp251/runs/b...`, e os resultados completos no host ficam em `htp251/benchmarks/<rodada>/`.

## Evidência e exportação

- [Resumo completo com medianas, p95, amostras HTP e correção](results/timing-summary.json).
- [CSV para planilha](results/timing.csv).
- Rodada original: `benchmarks/20261101T203651Z-1117c/summary.json`.
- [Guia das demos e imagens reais](README.md).

Metodologia de profiling e overhead: [benchmarking oficial do QAIRT](https://docs.qualcomm.com/nav/home/benchmarking.html?product=924033590759186372) e [FAQ do Qualcomm AI Hub](https://dev.aihub.qualcomm.com/docs/hub/faq.html). As opções desta versão foram confirmadas pelo `qnn-net-run --help` instalado na caixa.
