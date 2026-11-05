# Revalidação das demos — 04/11/2026

Revisão 0.12.2, QB560D-EU/QCM6490, Ubuntu 20.04.3, kernel 5.4.219-perf. Foram executados novamente os fluxos locais, por ADB autenticado. Os diretórios usam UTC; por isso esta sessão aparece como `20261105T003157Z`, ainda em 04/11 no horário de São Paulo.

| Fluxo | Resultado desta sessão |
|---|---|
| Inventário, diagnósticos e compilação C | PASS |
| HTTP nativo e systemd, atualização/rollback | PASS, três ciclos |
| Cinco demos TFLite CPU | PASS, três repetições de cada demo |
| Docker por provisionamento e deploy independente | PASS, imagem offline e HTTP |
| Docker integrado | PASS, três sessões, load, restrições, atualização/rollback e persistência após restart do daemon |
| Instalador Docker sem pasta de evidências prévia | PASS, fixture POSIX isolada executada na caixa |
| MobileNet V2 QAIRT 2.51 | PASS, CPU e HTP com perfis |
| Sete gestos MediaPipe | PASS, 7/7 no HTP |
| Cinco demos QAIRT 2.51 pelo host | PASS, novas referências CPU e perfis HTP |
| Onze controles positivos/negativos | PASS, CPU/GPU/HTP |
| Onze controles inteiramente na caixa | PASS_TARGET_HTP_CONTROLS |
| Comparação legada MobileNet V1 | PASS, TFLite CPU/GPU e SNPE 2.26 CPU/HTP, com profile DSP |
| AI Hub offline | PASS numérico em CPU/GPU |
| Cliente/conta AI Hub | PASS; consulta retornou 77 dispositivos, incluindo o QCS6490/v68; sem submissão de novos jobs |
| Testes de host | 83 aprovados; um teste adicional do instalador passou no target |
| Integridade | 48 arquivos dos runtimes/modelos conferidos, nenhuma mudança |

Wi-Fi e 5G ficaram excluídos a pedido do proprietário, sem antenas. O iperf foi exercitado somente em loopback. Yocto continua conceitual. A caixa expõe apenas `/dev/video32` e `/dev/video33`, nós de codec: não havia câmera de captura disponível. O script de câmera retornou corretamente `CONFIG_REQUIRED`/78. O serviço de display estava ativo; a imagem HDMI física não foi observada. Esses limites não são apresentados como aprovação de captura ou de vídeo.

Ao final, o daemon Docker privado estava ativo, sem containers de teste restantes; o serviço nativo estava parado. Os paths, locks e bibliotecas do BSP foram preservados. O instalador Docker anterior foi guardado na própria árvore de evidências da caixa antes da atualização.

As duas correções locais do proprietário foram incorporadas: criação da pasta Docker no provisionamento e transferência/compatibilidade do layout QAIRT. O instalador Docker agora também cria a pasta por conta própria. Os testes cobrem layout plano, pasta desconhecida, checksums/manifests inválidos, conflito de paths e conteúdo exato do TAR. O deploy dos controles HTP passou a usar uma pasta de evidências única, preservando os registros anteriores.

Relatórios: [validação](../evidence/demo-regression/20261105T003157Z/release/VALIDATION.json), [auditoria dos arquivos ZIP](../evidence/demo-regression/20261105T003157Z/release/DOWNLOAD.json) e [diagnóstico de download/extração](DOWNLOAD_DIAGNOSTICS.md). As evidências brutas permanecem no workspace; as referências da galeria HTP e os resumos revisados acompanham a release 0.12.2, disponível nos links de download dos READMEs.
