# Qualcomm AI Hub — materiais e laboratório para a AI Box

Revisão: 31/10/2026. Plataforma local: QB560D-EU / QCM6490 / Ubuntu 20.04.3 / TFLite C API 2.8.4.

Para o primeiro uso do portal e da API, comece pelo [passo a passo acompanhado](PASSO_A_PASSO_AIHUB.md). A conta já foi autenticada e a API retornou 77 dispositivos. O exercício seleciona Dragonwing RB3 Gen 2 Vision Kit, QCS6490/v68/Linux. Compile/inference/profile e deploy do mesmo TFLite em CPU/GPU passaram. O [vídeo](contingencia/AIHub_QB560D_Contingencia_Replay.mp4) e o [pacote offline](demo_offline/README.md) preservam os resultados reais e a repetição local. O vídeo é um replay identificado dos logs, com 106 segundos e sem áudio.

O [guia de uso e deploy](GUIA_DEPLOY_AIBOX.md) reúne o contexto anterior. Ele contém o exercício já executado de classificação em CPU/GPU e um exercício pequeno de compilação, validação e deploy pelo AI Hub.

O guia também inclui [configuração WLAN](../docs/WLAN.md) e o [laboratório HTP/DSP](../docs/HTP_DSP.md): MobileNet convertida em DLC INT8, CPU 6,748 ms e HTP 1,130 ms, com profile DSP confirmado e diferenças numéricas documentadas.

## Origem do modelo do laboratório

| Demo/modelo | Origem e tratamento | Download / artefato |
|---|---|---|
| Tiny / `aihub_tiny_6a569f3f9ea3.tflite` | **Sintético, sem treinamento, criado por nós** em ONNX. Compilado no AI Hub Workbench e baixado como TFLite; executado localmente em CPU/GPU. | [ONNX de entrada](../models/workbench_demo.onnx) · [TFLite gerado](demo_offline/models/aihub_tiny_6a569f3f9ea3.tflite) · [Job de compilação](https://workbench.aihub.qualcomm.com/jobs/j5q1v4l7g/) |

Esse exercício ensina envio, compilação, inferência/profile e deploy; o modelo não vem do catálogo pré-treinado e seus quatro valores de saída não são classes semânticas. IDs, opções e hashes estão em [jobs.json](demo_offline/evidence/jobs.json). Os links de jobs podem exigir login/acesso à conta AI Hub; o TFLite preservado no pacote permite repetir a parte local offline. As duas demos do catálogo com DLCs prontos são MobileNet V2 e MediaPipe sete gestos, conforme o [mapa geral](../README.md#origem-dos-modelos-e-das-demos).

## Apresentações baixadas

Os arquivos são os PDFs originais, sem alterações. São apresentações em formato PDF; os arquivos-fonte PPTX dessas palestras não estavam disponíveis nos links públicos consultados.

| Arquivo | Páginas | Origem e uso |
|---|---:|---|
| [Introduction to Edge AI](apresentacoes/01_Introduction_to_Edge_AI_CVPR2025.pdf) | 11 | Tutorial CVPR 2025, Elizabete Munzlinger. Introdução ao processamento local. |
| [Model Deployment for Edge AI](apresentacoes/02_Model_Deployment_for_Edge_AI_CVPR2025.pdf) | 97 | Tutorial CVPR 2025, Fabricio Batista Narcizo e coautores. Conversão, runtimes e deploy. |
| [Accelerating Edge AI with Qualcomm AI Hub](apresentacoes/03_Accelerating_Edge_AI_with_Qualcomm_AI_Hub_CVPR2025.pdf) | 29 | Tutorial CVPR 2025, Shan Ahmed Shaffi. Fluxo de compile, profile e inferência no AI Hub. |
| [How Qualcomm Is Powering AI-driven Multimedia at the Edge](apresentacoes/04_Qualcomm_AI_driven_Multimedia_Embedded_Vision_Summit_2025.pdf) | 21 | Apresentação da Qualcomm Technologies por Ning Bi, Embedded Vision Summit 2025. Contexto complementar sobre aceleração e ecossistema. |

Os três materiais do CVPR foram publicados pelos autores/organizadores do tutorial. Eles não são apostilas oficiais da Qualcomm Academy. O quarto material é uma apresentação de um palestrante da Qualcomm publicada pelo organizador do evento. As origens, autores, tamanhos e hashes SHA-256 estão em [materiais.lock.json](materiais.lock.json).

Fonte do tutorial e vídeo completo: [Edge AI in Action — CVPR 2025](https://www.fabricionarcizo.com/cvpr2025-edge-ai-in-action/).
Fonte da apresentação Qualcomm: [Embedded Vision Summit](https://www.edge-ai-vision.com/2025/06/how-qualcomm-is-powering-ai-driven-multimedia-at-the-edge-a-presentation-from-qualcomm/).

## Treinamentos oficiais em vídeo

| Recurso | Como usar |
|---|---|
| [Qualcomm Academy — AI Hub Training](https://academy.qualcomm.com/course-catalog/AI-Hub-Training) | Sequência oficial: API token, primeiro job, dispositivo, runtime, compute unit, validação de precisão e integração em app. |
| [Introduction to Qualcomm AI Hub](https://academy.qualcomm.com/course-catalog/Introduction-to-Qualcomm-AI-Hub) | Webinar introdutório de uma hora. |
| [Documentação atual do Workbench](https://workbench.aihub.qualcomm.com/docs/) | Referência para os comandos atuais. |

Os vídeos ficam nos portais dos autores; foram registrados como links, sem cópia de conteúdo que exija login. Atalhos do Windows estão em `links/`.

## Sequência sugerida para o treinamento

1. Conceitos de edge AI: primeiro PDF, 10–15 minutos.
2. Compile, profile e inferência: terceiro PDF e vídeos oficiais, 20–30 minutos.
3. Comparação real de CPU/GPU na QB560D: exercício A do guia, 15 minutos.
4. Modelo mínimo no Workbench e deploy local: exercício B, 20–30 minutos, mais a fila dos jobs.

O cliente `qai-hub 0.57.0` foi instalado em uma pasta isolada no computador para conferir as APIs usadas pelo guia. Na preparação original não havia configuração de conta. Atualização de01/11: acesso Web e autenticação API validados, com77 dispositivos retornados. O passo a passo acompanhado registra a continuação. As execuções locais de MobileNet em GPU e HTP foram concluídas e possuem evidências. O caminho HTP usa componentes públicos SNPE 2.26 em pasta privada; não depende do Workbench.

Os slides do nosso treinamento continuam no arquivo [QB560D_EU_Training.pptx](../slides/QB560D_EU_Training.pptx), que preserva o modelo oficial Quectel. Os PDFs desta pasta são referências externas e não foram inseridos automaticamente nesse PPTX.
