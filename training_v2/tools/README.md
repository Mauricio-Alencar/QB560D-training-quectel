# Ferramentas do computador

O cliente ADB compartilhado está em `platform-tools/adb.exe`. Os hashes e a origem estão em `platform-tools.lock.json`; o NOTICE acompanha os binários.

Partindo de `training_v2`:

```powershell
$adb = (Resolve-Path tools/platform-tools/adb.exe).Path
& $adb devices -l
```

Os instaladores de driver, PuTTY e QPST originais permanecem nesta pasta para preparação do instrutor. O pacote principal seleciona o ADB, o driver Quectel e os pacotes oficiais de [Python 3.12 portátil](python312/README.md) para o host e [Python 3.8 portátil](python38/README.md), opcional para reconstrução dos modelos. QPST e procedimentos de gravação de firmware são materiais separados da aula operacional.
