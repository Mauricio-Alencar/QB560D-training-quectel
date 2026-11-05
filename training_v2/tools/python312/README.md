# Python 3.12.10 portátil para Windows x64

Este diretório distribui o **pacote oficial CPython NuGet 3.12.10**, com biblioteca padrão, `venv` e `ensurepip`. Ele é extraído localmente em `.build/portable-python312` pelo [helper compartilhado](../../host/prepare_portable_python.ps1). Não executa instalador Windows, não registra Python e não altera PATH, launcher ou associações de arquivos.

Uso no treinamento: scripts do host, demos e ferramentas QAIRT 2.51. As venvs são criadas no computador do aluno, no destino onde o treinamento foi extraído; elas não acompanham Git/ZIP. Use uma pasta curta, como `C:\QB560D`, antes de criá-las.

- [Pacote original](python.3.12.10.nupkg), obtido da [distribuição oficial CPython no NuGet](https://www.nuget.org/packages/python/3.12.10).
- [URL, tamanho e SHA-256](python312.lock.json). O helper confere o pacote e cada arquivo extraído antes de reutilizar o runtime.
- [Licenças originais incluídas no pacote](LICENSE.txt), preservadas sem alteração.

O formato NuGet é [documentado pelo CPython](https://docs.python.org/3/using/windows.html#the-nuget-org-packages). Não é o pacote embeddable mínimo e não exige instalar NuGet ou .NET SDK: o helper usa o ZIP e os recursos do PowerShell já disponíveis no Windows.

Execute `powershell -NoProfile -ExecutionPolicy Bypass -File provision_target/setup_host.ps1` a partir de `training_v2`. Ele usa este runtime para criar `provision_target/.venv` e instala NumPy/Pillow com os wheels offline do treinamento.
