# QAIRT 2.51 e demos no ambiente persistente

Use este índice a partir da raiz `training_v2`. O preparo do host e da caixa está em [provision_target/README.md](../../provision_target/README.md). O runtime validado fica em `/opt/qairt-isolated/2.51.40.260930`, com bibliotecas selecionadas por processo.

- **MobileNet V2 e instalação do runtime:** [guia completo original](readme.me), com download, paths, testes CPU/HTP e evidências. A validação no firmware atual está em `evidence/fw-20261101-v2/results.json`.
- **MediaPipe com sete gestos:** [README completo da demo](../../demos/hand_gesture/README.md), com download, deploy, execução por foto e sete testes.
- **Cinco demos migradas, imagens reais e comparação CPU/GPU/HTP 2.51:** [guia do hands-on](../../htp251/README.md).

O material usa o Python 3.12 já preparado em `provision_target/.venv/Scripts/python.exe`; o launcher Windows `py` não é necessário para executar essas demos. Não misture bibliotecas de versões diferentes nem substitua os runtimes anteriores.
