# Treinamento técnico QB560D-EU

## Download para os alunos

- [Baixar o treinamento completo v0.12.1 (ZIP)](https://github.com/Mauricio-Alencar/QB560D-training-quectel/releases/download/v0.12.1/QB560D_EU_Training_0.12.1_20261103.zip)
- [Baixar o SHA-256](https://github.com/Mauricio-Alencar/QB560D-training-quectel/releases/download/v0.12.1/QB560D_EU_Training_0.12.1_20261103.zip.sha256)
- [Notas da release v0.12.1](https://github.com/Mauricio-Alencar/QB560D-training-quectel/releases/tag/v0.12.1)

Extraia o pacote em uma pasta curta, como `C:\QB560D`, e abra `training_v2/README.md`. O ZIP inclui as dependências offline selecionadas para a aula.

A revisão 0.12.2 dos fontes corrige o provisionamento Docker e o layout do QAIRT no Windows. Os links acima ainda identificam a release publicada 0.12.1, anterior a essas correções. O pacote revisado é gerado por `training_v2/host/build_release.py`. Consulte o [diagnóstico de download e extração](training_v2/docs/DOWNLOAD_DIAGNOSTICS.md) antes de usar uma cópia extraída em Downloads/OneDrive.

Para conferir o download no PowerShell, execute o comando abaixo e compare o resultado com o arquivo `.sha256`:

```powershell
Get-FileHash .\QB560D_EU_Training_0.12.1_20261103.zip -Algorithm SHA256
```

Comece pelo [guia único do treinamento](training_v2/README.md). Os comandos do host partem da pasta `training_v2`.

- [Apresentação principal](training_v2/slides/QB560D_EU_Training.pptx)
- [Preparação do computador e da caixa](training_v2/provision_target/README.md)
- [Agenda e navegação](training_v2/docs/AGENDA.md)
- [Módulo Qualcomm AI Hub](training_v2/Qualcomm_AI_Hub_Training/README.md)
- [Apresentações complementares Qualcomm AI Hub](training_v2/Qualcomm_AI_Hub_Training/apresentacoes/)

O único PPTX usado na aula é a apresentação principal indicada acima. O conteúdo de Yocto é conceitual, sem execução de builds ou labs.

Os pacotes dos alunos incluem os guias, as demos e as dependências offline selecionadas. Firmware, fontes de autoria, backups, pendências internas e inventários/planos locais de preparação ficam fora da distribuição.

O código autoral usa a [licença MIT](LICENSE). Slides, guias, READMEs e demais materiais didáticos autorais usam a [CC BY-NC-SA 4.0](LICENSE-CONTENT). Copyright © 2026 José Maurício Alencar Filho. Consulte o [alcance das licenças e as exceções de terceiros](LICENSING.md).
