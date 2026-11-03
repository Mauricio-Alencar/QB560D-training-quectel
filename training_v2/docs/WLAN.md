# WLAN na QB560D-EU

Configuração validada em 31/10/2026, horário de São Paulo. Ubuntu 20.04.3, NetworkManager 1.22.10 e interface `wlan0`.

**Revalidada em 01/11/2026 no BSP QDPA_Ubuntu20.04.003.51.303 V01.** O reflash removeu o perfil anterior. A conexão foi recriada com a credencial fornecida pelo proprietário, sem copiá-la para o material. DHCP, DNS, HTTPS 200, NTP e reativação passaram; IPv4 desta sessão: `192.168.0.26/24`. A disputa com dhcpcd reapareceu (métrica 353) e foi corrigida pelo helper existente. Resultado final: NetworkManager, métrica 600. [Evidência atual](../evidence/wlan/20261101T173943Z/summary.json). Os valores `.11` na tabela seguinte pertencem ao ensaio anterior.

## Estado configurado nesta unidade

| Item | Valor observado |
|---|---|
| SSID | `Mauricio_WIFI5G` |
| Perfil NetworkManager | `qb560d-training-wlan` |
| Banda / frequência | Wi-Fi 5 GHz, 5825 MHz, canal 165 |
| Segurança anunciada pelo AP | WPA/WPA2; perfil usa WPA-PSK |
| IPv4 | DHCP; endereço observado `192.168.0.11/24` |
| Gateway | `192.168.0.1` |
| DNS via DHCP | `181.213.132.2`, `181.213.132.3` |
| Métrica da rota IPv4 | 600 |
| IPv6 no perfil WLAN | Desativado devido à falha DHCPv6 observada nesta imagem |
| Reconexão | `connection.autoconnect=yes` |
| Persistência | Perfil salvo em `/etc/NetworkManager/system-connections/qb560d-training-wlan.nmconnection`, proprietário root, modo 600 |

O IP depende da concessão DHCP e pode mudar. A senha fornecida foi utilizada para configurar a conexão e não foi gravada neste guia, scripts, logs do laboratório ou pacote distribuível. O perfil privado do NetworkManager guarda a credencial necessária para reconectar.

O SSID usa a banda WLAN de 5 GHz. A sessão celular 5G continua com seu fluxo próprio de registro, interface RMNET e roteamento.

## Verificar a conexão atual

No computador, a partir da raiz `training_v2`:

```powershell
python host/adb_lab.py run wlan status
python host/adb_lab.py run wlan check
```

Os comandos guardam evidência datada no computador. O teste usa `curl --interface wlan0` para conferir HTTPS por essa interface, consulta DNS e mostra a rota. A validação realizada retornou HTTP 204 no endpoint de conectividade e HTTPS 200 em `example.com`. O relógio sincronizou automaticamente pelo serviço NTP após a conexão: `NTPSynchronized=yes`.

No shell da própria caixa, os equivalentes são:

```sh
nmcli --colors no device status
nmcli --colors no -f GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS,IP4.GATEWAY,IP4.DNS device show wlan0
iw dev wlan0 link
ip -4 address show dev wlan0
ip -4 route show dev wlan0
getent ahostsv4 example.com
curl --interface wlan0 --fail --connect-timeout 8 --max-time 20 -I https://example.com
timedatectl show -p NTPSynchronized
```

Esta imagem tem versões antigas das ferramentas: `ip -br` e `ping -I` não são aceitos. Use os comandos acima. Um ping opcional ao gateway pode ser feito com `ping -c 3 192.168.0.1`; a rota diretamente conectada leva o tráfego à WLAN.

## Configurar em outra unidade ou recriar o perfil

Abra um terminal interativo no target com `adb shell`, responda `root` ao login e digite a senha Linux. Primeiro, confira as redes e os perfis existentes:

```sh
nmcli radio wifi on
nmcli --colors no -f SSID,CHAN,FREQ,SIGNAL,SECURITY device wifi list ifname wlan0
nmcli --colors no -f NAME,TYPE connection show
```

Se `qb560d-training-wlan` ainda não existir, crie o perfil com IPv4 automático e IPv6 desativado:

```sh
nmcli connection add type wifi ifname wlan0 con-name qb560d-training-wlan ssid Mauricio_WIFI5G ipv4.method auto ipv4.route-metric 600 ipv6.method disabled wifi-sec.key-mgmt wpa-psk connection.autoconnect yes
nmcli --ask --wait 45 connection up qb560d-training-wlan ifname wlan0
```

Informe a senha no prompt do `nmcli --ask`. O terminal interativo evita colocar a senha no histórico do comando ou no coletor de evidência. Se o perfil já existir e ainda precisar da credencial, use apenas o segundo comando.

Para usar outro AP, substitua o SSID e escolha outro nome de perfil. Antes de alterar um perfil existente, confira se ele pertence ao laboratório. Evite criar vários perfis com o mesmo nome.

## Falha encontrada e correção aplicada

A autenticação WPA passou, mas a primeira ativação terminou com `DHCP client failed to start`. O log detalhado mostrou `failure to start DHCPv6: Address already in use`. O cliente DHCP interno do NetworkManager já estava ativo; não foi necessário instalar outro cliente DHCP.

Foi aplicado somente ao perfil WLAN:

```sh
nmcli connection modify qb560d-training-wlan ipv4.method auto ipv4.route-metric 600 ipv6.method disabled connection.autoconnect yes
nmcli --wait 45 connection up qb560d-training-wlan ifname wlan0
```

A conexão obteve IPv4 e passou nos testes de Internet. A configuração IPv6 é uma solução para a falha observada nesta unidade; pode ser reavaliada quando o BSP ou a rede forem corrigidos. O ajuste não desativa IPv6 globalmente.

Também identificamos o `dhcpcd` do BSP gerenciando a mesma interface. Ele substituiu as rotas por outras com métrica 335 enquanto o perfil NetworkManager configurava 600. Para haver um único gerenciador de WLAN, a linha global em `/etc/dhcpcd.conf` passou de `denyinterfaces bridge0` para `denyinterfaces bridge0 wlan0`, preservando as configurações Ethernet existentes. O backup fica em `/etc/dhcpcd.conf.qb560d-training-20261101T010211Z.bak`.

Esse ajuste pode ser reproduzido **somente após confirmar a mesma configuração e a disputa entre os gerenciadores**:

```sh
cd /opt/qb560d-training-payload
python3 target/wlan_owner.py
dhcpcd -x wlan0
nmcli --wait 45 connection up qb560d-training-wlan ifname wlan0
```

O helper verifica o formato esperado, faz backup e acrescenta apenas `wlan0` à exclusão existente. `dhcpcd -x wlan0` retira essa interface do daemon em execução; o daemon permanece ativo para as demais interfaces. Não reiniciamos os serviços globais. Após o ajuste, a rota padrão permaneceu com métrica 600 e o teste HTTPS por `wlan0` passou novamente. `systemd-networkd` informou `wlan0` como unmanaged.

## Operação e reconexão

Após `up/status/check`, siga o [guia SSH](SSH.md) para operar as demos pela rede e preparar o teste da câmera USB-A sem a conexão USB-C do PC. Conclua a demonstração de `down`/rádio desligado antes de entrar por SSH, ou omita-a: desligar a WLAN usada pelo SSH interrompe esse canal de controle.

```sh
# Subir o perfil salvo, sem redigitar a senha
nmcli --wait 45 connection up qb560d-training-wlan ifname wlan0

# Consultar somente propriedades sem segredo
nmcli -f connection.id,connection.autoconnect,ipv4.method,ipv4.route-metric,ipv6.method connection show qb560d-training-wlan

# Desconectar quando necessário; o perfil permanece salvo
nmcli connection down qb560d-training-wlan

# Impedir reconexão automática, se essa for a intenção do operador
nmcli connection modify qb560d-training-wlan connection.autoconnect no
```

Os atalhos do laboratório são `sh target/wlan.sh status`, `scan`, `up`, `down` e `check`, dentro de `/opt/qb560d-training-payload`. Credenciais ficam na configuração privada persistente do NetworkManager. O autoconnect passou em um cold boot físico em 01/11/2026: conexão automática em 29,02 s desde a marcação do operador, com DHCP/DNS/HTTPS200 e NTP posterior. [Resultado e limites de medição](BOOT_WLAN.md). O caminho transitório anterior continua disponível apenas com `--remote /tmp/qb560d-training` nos helpers.

## Roteamento com Ethernet e celular

A WLAN recebeu uma rota padrão com métrica 600. Uma interface com outra rota de menor métrica pode se tornar a saída padrão. Antes de medir throughput ou comparar caminhos, consulte `ip -4 route` e `ip -4 route get <IP>`.

Os ensaios celulares devem continuar vinculados à interface RMNET correta, por exemplo `curl --interface rmnet_data0 ...` e `iperf3 -B <IP_DA_RMNET> ...`, depois que houver uma sessão celular ativa. Isso permite comprovar qual caminho transporta o tráfego quando WLAN e celular coexistem.

## Diagnóstico

Para o ensaio de cold boot, análise dos serviços e a correção comprovada de DNS quando WLAN/RMNET coexistem, use [BOOT_WLAN.md](BOOT_WLAN.md). O perfil da caixa recebeu uma política DNS e rotas /32 restritas aos servidores DHCP desta WLAN. Os endereços são próprios do AP medido e não devem ser copiados para outra rede.

| Sintoma | Próxima verificação |
|---|---|
| SSID ausente | Rádio habilitado, antenas, distância, banda/canal do AP; repetir scan. |
| Autenticação falha | Confirmar SSID e credencial pelo prompt interativo; conferir segurança do AP. |
| Conectou ao AP, sem IP | Consultar DHCP e `journalctl -u NetworkManager`; separar falha IPv4 de falha IPv6. |
| IP presente, sem acesso externo | Gateway, rota padrão e endpoint acessível. |
| Acesso numérico funciona, nome falha | DNS recebido por DHCP e `getent ahostsv4`. |
| HTTPS falha por certificado/data | `date -u` e estado NTP; nesta unidade o relógio sincronizou ao obter Internet. |
| Download lento | Sinal, posição das antenas, ruído e bitrate negociado; velocidade de link não equivale a throughput útil. |

Documentação de referência: [nmcli](https://networkmanager.dev/docs/api/latest/nmcli.html) e [propriedades de conexão](https://networkmanager.dev/docs/api/latest/nm-settings-nmcli.html). Os comandos desta revisão foram conferidos no NetworkManager 1.22.10 instalado na caixa.
