# Download e extração no Windows

Extraia o treinamento completo em uma pasta curta, como `C:\QB560D`. Abra `training_v2` somente depois de a extração terminar sem erros. Não execute scripts dentro da janela do ZIP e crie o ambiente Python no destino.

## O que foi conferido em 04/11/2026

O ZIP local correspondente à release publicada 0.12.1 e um arquivo gerado por `git archive` da revisão `d49698e` contêm os três arquivos Docker completos. Tamanhos e SHA-256 conferem com os locks:

| Arquivo | Bytes |
|---|---:|
| `demos/docker/offline/runtime/docker-29.9.2.tgz` | 77.953.959 |
| `demos/docker/offline/runtime/buildx-v0.38.1.linux-arm64` | 63.766.690 |
| `demos/docker/offline/images/qb560d-telemetry-1.0.0-arm64.tar.gz` | 47.037.664 |

O repositório não configura Git LFS para esses arquivos. A hipótese de ponteiros LFS não explica essas duas cópias verificadas. O GitHub gera os arquivos de código-fonte usando `git archive`, conforme a [documentação do GitHub](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives). O ZIP de código-fonte e o pacote preparado em Releases são distribuições diferentes; os hashes publicados em Releases correspondem ao asset de mesmo nome.

A extração comum da release em uma subpasta longa do workspace falhou com `FileNotFoundError` em um log Docker, antes de concluir a árvore. Nesse destino, 1.118 entradas alcançariam pelo menos 260 caracteres. No destino `C:\QB560D`, a maior extensão de caminho dessa release é 188 caracteres. Uma falha de extração pode, portanto, parecer um download incompleto. Isso foi reproduzido localmente; sem analisar o ZIP e o erro de cada aluno, não é possível atribuir todos os relatos à mesma causa.

Também foi confirmado um erro independente no primeiro provisionamento: `install-docker.log` mostrava `evidence/docker-info.txt: No such file or directory`. O daemon chegava a iniciar, mas o redirecionamento da verificação falhava porque a pasta ainda não existia. A revisão 0.12.2 faz o próprio instalador criar essa pasta. Uma caixa que já possuía `evidence/` mascarava o problema, independentemente de ter sido usada uma cópia clonada ou extraída.

## Conferir a cópia recebida

Para o pacote completo de uma release, compare `Get-FileHash -Algorithm SHA256` com o arquivo `.zip.sha256` de mesmo nome. Depois da extração e do preparo do Python, a partir de `training_v2`:

```powershell
$py = (Resolve-Path provision_target/.venv/Scripts/python.exe).Path
& $py demos/docker/host/deploy_offline.py --validate-only
& $py host/validate_release.py
```

O primeiro comando deve informar `PASS_LOCAL_OFFLINE_CACHE`. Ele verifica os tamanhos e hashes antes de acessar a caixa. Os diagnósticos de arquivo ausente, arquivo truncado, checksum incorreto e ponteiro LFS têm mensagens distintas. Não altere locks para fazer uma cópia danificada passar.

Se a cópia falhar, extraia novamente o pacote completo em uma pasta curta e confira de novo. A revisão 0.12.2 dos fontes também corrige o estágio QAIRT pelo Windows. Depois de atualizar os scripts, regenere `prepare --offline` e `plan` antes de aplicar o provisionamento. Os links para 0.12.1 no README identificam a release anterior; o novo pacote local precisa ser publicado para atualizar esses links.
