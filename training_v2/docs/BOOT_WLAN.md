# D1-02 e D1-07 — Boot, diagnóstico e recuperação WLAN

O ensaio separa o diagnóstico do sistema atual de um cold boot com interrupção física da alimentação. Um `reboot` não substitui esse ensaio. A medição usa o relógio UTC/monotônico do host; o horário local do BSP pode estar em outro fuso.

## Cold boot físico aprovado — 01/11/2026

Resultado revisado: **PASS_COLD_BOOT_PERSISTENCE_AND_WLAN**, uma rodada nesta caixa/BSP. O operador executou desligamento, remoção física de alimentação/USB e religação pelo observador. A marcação foi em **01/11/2026 às 19:34:12,603 (America/Sao_Paulo)**, correspondente a 22:34:12,603 UTC.

| Verificação | Resultado |
|---|---|
| Shell ADB autenticado como root | **13,938 s** desde a marcação do operador; uid 0 |
| WLAN automática | **29,016 s**, sem `wlan up`/`connection up` manual após religar |
| Boot ID | Mudou de 4af1e918-9fd1-43d5-bbb6-47156d1e4d70 para ad79661b-5a87-49cb-a330-1fcb1c5c9dbb |
| Rede | Perfil salvo, DHCP, rotas DNS persistentes, resolução e HTTPS200 |
| Relógio | NTP inicialmente não sincronizado; sincronizado no follow-up, cujo uptime inicial era 85,24 s |
| Persistência | Payload, modelos com hashes conferidos, dependências privadas, runtime QAIRT e iperf3 disponíveis em /opt |
| Smoke funcional | NumPy 1.24.4/Pillow 10.4.0 importaram; QNN 2.51.40 carregou; TFLite 2.8.4 CPU executou o modelo tiny, PASS, erro máximo 1,49e-08 |
| Startup systemd completo | **76,464 s**: kernel 2,869 s + userspace 73,594 s; `No jobs running` no follow-up |
| Falhas BSP | 11 unidades na captura precoce; **as mesmas 14 da base** após estabilização, sem novas unidades em falha |

Os 13,938/29,016 s vêm do relógio do host a partir da tecla pressionada pelo operador, incluindo reação/polling/autenticação e disponibilidade USB. Os 76,464 s são outra medida, do systemd; shell disponível não significa startup completo. Não transformar esses números em garantia de tempo para todas as caixas. Aguarde estabilizar antes de medir desempenho.

O NTP não estava sincronizado na captura inicial; o follow-up confirmou a sincronização. Não houve amostragem contínua para medir seu instante exato. A primeira lista de 11 falhas foi coletada enquanto o systemd ainda iniciava; não representa correção de três serviços. A análise das 14 unidades abaixo continua aplicável.

Evidência original preservada: `evidence/boot-wlan/20261101T215141Z/power-cycle.json` e `capture.json`. A pasta foi nomeada quando o observador iniciou; a hora real da energização é o campo `power_on_operator_mark_utc`. Revisão: `review.json`, `settled-check.log` e `post-boot-runtime-smoke.log`. O observador atualizado agora também aguarda o fim do startup antes de classificar serviços; não reescrevemos os logs da versão que já estava rodando.

A aprovação é desta referência: não corrige as falhas do BSP nem substitui a aceitação por caixa e o ensaio didático final. Nenhuma sessão celular foi ativada automaticamente no teste; o bring-up RIL continua manual.

## Diagnóstico antes do corte, 01/11/2026

Evidência: `evidence/boot-wlan/20261101-pre-power/`. Foram observadas **14 unidades em falha**, contra 11 no ensaio anterior. Os registros anteriores continuam válidos como histórico. `systemd-analyze` mostrou 2,754 s de kernel + 73,569 s de userspace = 76,324 s; isso descreve o boot já ocorrido, sem medir energização até shell.

| Unidade | Causa observada | Impacto no treinamento e encaminhamento |
|---|---|---|
| avahi-daemon | Erro ao abrir resolv.conf no chroot e ausência de protocolo utilizável | Descoberta mDNS não homologada; usar IPv4 da caixa em SSH. Rever configuração do BSP se mDNS for necessário. |
| camera_cgroup | `/sys/fs/cgroup/schedtune/camera` ausente | Ajuste de cgroup da câmera não aplicado. Não comprova funcionamento do pipeline de câmera. Revisão com BSP. |
| chg-policy | Executável sai com 255 e esgota tentativas | Política de carga não validada; não é pré-requisito da demonstração com alimentação DC. A causa interna não aparece no journal coletado. |
| dhcpd6 | `/etc/dhcp/dhcpd6.conf` ausente | Servidor DHCPv6 não configurado; o laboratório usa a caixa como cliente DHCP IPv4. |
| dnsmasq | Porta 53 já ocupada | Servidor/cache adicional não inicia. `systemd-resolved` ocupa 127.0.0.53:53; não substituir o resolver para ocultar essa falha. |
| fs-scrub-daemon | `/proc/mtd` e `/dev/ubi_ctrl` ausentes | Serviço espera armazenamento MTD/UBI ausente neste inventário. Conferir sua aplicabilidade ao produto com BSP. |
| init_post_boot | Escritas de tuning recusadas; zram já montado/ocupado | Parte do tuning de boot falhou. Demos funcionais não homologam toda a configuração de desempenho/energia. Rever idempotência com BSP. |
| ip6tables | `/etc/iptables/ip6tables.rules` ausente | Restauração dessas regras não executada; não equivale a um teste do estado atual de todas as regras. |
| ipacmdiag | Falha de bind do socket, errno 2 | Diagnóstico IPA indisponível. HTTPS/iperf por RMNET já passaram em ensaios separados. |
| iptables | `/etc/iptables/iptables.rules` ausente | Restauração dessas regras não executada. O laboratório não cria regras fictícias para limpar o estado. |
| lunch-make-scripts | Versões fixadas de flex/bison indisponíveis no apt | Etapa de instalação de ferramentas do BSP falhou. GCC e os exemplos C já foram validados separadamente; não executar upgrade global. |
| qcmap_wlan | Script retorna 1, sem detalhe no journal da unidade | Caminho QCMAP não homologado. O cliente WLAN do laboratório usa NetworkManager e passou após corrigir DNS. |
| qti_pppd | Status 203/EXEC no `/usr/bin/qti_ppp` | Caminho PPP não inicia. O laboratório celular usa RIL/RMNET, não PPP. Revisão do executável/unidade com BSP. |
| thermal-engine | `/usr/bin/thermal-engine` ausente, status 203/EXEC | Serviço de política térmica não disponível. Leituras de thermal_zone existem, mas não comprovam equivalência da política térmica. Encaminhar ao BSP. |

As unidades foram examinadas por `systemctl show`, `systemctl cat` e `journalctl -b -u`. Nenhuma foi mascarada/desabilitada, e não foi usado `reset-failed` para apresentar uma lista limpa. Corrigir dependências ausentes do BSP é uma entrega do BSP; a aceitação deste laboratório registra sua aplicabilidade e o efeito nos recursos usados.

## Correção WLAN comprovada antes do boot

O perfil `qb560d-training-wlan` já tinha autoconnect habilitado e IPv4/DHCP. A rota padrão RMNET tinha métrica 500 e WLAN 600. As consultas DNS para os servidores DHCP 181.213.132.2/3 falhavam pelo caminho celular, embora o teste UDP vinculado a wlan0 recebesse resposta. HTTPS numérico por WLAN funcionava.

Na caixa ensaiada, a recuperação que passou foi:

```sh
nmcli connection modify qb560d-training-wlan \
  ipv4.dns-priority -50 ipv4.dns-search '~.'
nmcli connection modify qb560d-training-wlan \
  +ipv4.routes '181.213.132.2/32 192.168.0.1' \
  +ipv4.routes '181.213.132.3/32 192.168.0.1'
nmcli device reapply wlan0
systemctl restart systemd-resolved
cd /opt/qb560d-training-payload
sh target/wlan.sh check
```

**Os endereços acima são os valores medidos neste AP.** Em outra rede, obtenha `IP4.DNS` e `IP4.GATEWAY` com `nmcli device show wlan0` e use os valores reais; não copie gateway/DNS deste exemplo. Não aplique a prioridade negativa se o cenário precisar de DNS privado de outra rede sem antes definir essa política. As duas rotas /32 ficam no perfil desta WLAN, não no firmware distribuído. A rota padrão celular permaneceu preservada.

O teste só com prioridade/domínio DNS, retirando as rotas /32, voltou a falhar. A combinação completa passou: DNS, HTTPS 200 vinculado à WLAN e `NTPSynchronized=yes`. Veja `dns-bound.log`, `dns-final-policy.log` e `dns-accepted-correction.log` na evidência. Esse teste não substitui a recuperação automática após boot.

Referência da prioridade e do domínio de roteamento DNS: [manual NetworkManager](https://www.networkmanager.dev/docs/api/latest/nm-settings-nmcli.html). As propriedades foram aceitas pelo nmcli 1.22 da caixa; o sucesso relatado vem dos testes locais, não da documentação de outra versão.

## Cold boot reproduzível

Antes do teste, conclua as atividades dos outros chats e salve os arquivos em uso na caixa. No PowerShell, a partir da raiz do treinamento:

```powershell
& .\provision_target\.venv\Scripts\python.exe .\training_v2\host\boot_wlan_rehearsal.py capture
& .\provision_target\.venv\Scripts\python.exe .\training_v2\host\boot_wlan_rehearsal.py operator-watch `
  --before evidence/boot-wlan/PASTA_DA_CAPTURA
```

O segundo comando pede a senha root sem salvá-la. Em um terminal já autenticado da caixa, execute `sync` e `systemctl poweroff`. Remova DC e USB, espere pelo menos dez segundos e pressione Enter no observador com a caixa ainda desligada. O programa recusa continuar se ADB ainda estiver online. Restabeleça alimentação/USB e pressione Enter imediatamente para marcar a energização.

Não execute `nmcli connection up`, `wlan up` nem comandos manuais de recuperação durante a medição. O observador mede até shell ADB autenticado, exige boot_id diferente e coleta novamente identidade, persistência, serviços, WLAN, DNS, HTTPS e relógio. O intervalo inclui a reação do operador e a disponibilidade/reconexão USB; não é uma medição elétrica de bancada. Os serviços de treinamento deixados desabilitados não precisam iniciar automaticamente.

Fechamento: power-cycle.json com novo boot_id, tempo medido e captura pós-boot; payload/modelos/runtimes persistentes; WLAN conectada automaticamente; DHCP/DNS/HTTPS aprovados e estado NTP registrado. Se alguma etapa falhar, preservar o erro e corrigir/repetir antes de marcar PASS.
