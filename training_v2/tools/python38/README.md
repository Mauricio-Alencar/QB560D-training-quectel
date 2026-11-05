# Python 3.8 para reconstruir os modelos

Este diretório distribui o **instalador completo oficial Python 3.8.10 Windows x64**, necessário somente para o ambiente de exportação TFLite/ONNX do instrutor. O preparo normal e a execução das demos usam Python 3.12; os DLCs prontos dispensam instalar Python 3.8.

O instalador não é um ambiente virtual e não é a cópia embeddable/portátil usada na preparação histórica. Instale-o no computador e crie a venv localmente, conforme a [seção de ambientes do guia manual](../../docs/TFLITE_PARA_HTP_PASSO_A_PASSO.md#1-ambientes-e-pasta-de-trabalho). A pasta `.build` é criada pelos comandos no computador do aluno; não acompanha o Git/ZIP.

- [Instalador oficial](python-3.8.10-amd64.exe), obtido da [Python Software Foundation](https://www.python.org/downloads/release/python-3810/).
- [Origem, tamanho e SHA-256](python38.lock.json). A assinatura Authenticode da Python Software Foundation foi validada na preparação.
- [Licença original do CPython](LICENSE.txt), preservada sem alteração.

Python 3.8 é uma dependência legada para reproduzir esta conversão fixada com TensorFlow 2.13. Os pacotes Python da exportação e o SDK de conversão ainda exigem preparação/download no host; incluir o instalador não torna a reconstrução dos modelos integralmente offline. As dependências offline para executar os modelos prontos continuam no treinamento.
