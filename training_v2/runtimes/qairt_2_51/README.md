# QAIRT 2.51 e demos no ambiente persistente

Use este índice a partir da raiz `training_v2`. O preparo do host e da caixa está em [provision_target/README.md](../../provision_target/README.md). O runtime validado fica em `/opt/qairt-isolated/2.51.40.260930`, com bibliotecas selecionadas por processo.

## Origem do modelo desta demo

| Demo/modelo | Origem e tratamento | Download / artefato |
|---|---|---|
| MobileNet V2 | **Pronto do catálogo Qualcomm AI Hub**, QNN DLC w8a8 v0.65.0; não convertido por nós. | [ZIP do DLC pronto](https://qaihub-public-assets.s3.us-west-2.amazonaws.com/qai-hub-models/models/mobilenet_v2/releases/v0.65.0/mobilenet_v2-qnn_dlc-w8a8.zip) · [Página oficial do modelo](https://huggingface.co/qualcomm/MobileNet-v2) |

Este pacote contém um DLC pré-exportado. Fizemos download, preparo do input, deploy e validação CPU/HTP. A MobileNet **V1** das cinco demos de comparação é outro modelo, convertido por nós a partir do TFLite Google. Veja o [mapa de todas as origens](../../README.md#origem-dos-modelos-e-das-demos). A URL, o tamanho e o hash do ZIP estão em [assets/sources.lock.json](assets/sources.lock.json); os hashes dos componentes ensaiados estão em [versions.lock.json](versions.lock.json).

- **MobileNet V2 e instalação do runtime:** [guia completo original](readme.me), com download, paths, testes CPU/HTP e evidências. A validação no firmware atual está em `evidence/fw-20261101-v2/results.json`.
- **MediaPipe com sete gestos:** [README completo da demo](../../demos/hand_gesture/README.md), com download, deploy, execução por foto e sete testes.
- **Cinco demos migradas, imagens reais e comparação CPU/GPU/HTP 2.51:** [guia do hands-on](../../htp251/README.md).

O material usa o Python 3.12 já preparado em `provision_target/.venv/Scripts/python.exe`; o launcher Windows `py` não é necessário para executar essas demos. Não misture bibliotecas de versões diferentes nem substitua os runtimes anteriores.
