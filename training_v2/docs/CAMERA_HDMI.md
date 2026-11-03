# Webcam USB e diagnóstico HDMI — 02/11/2026

## Resultado desta caixa

BSP `QDPA_Ubuntu20.04.003.51.303 V01`, kernel `5.4.219-perf`. O diagnóstico foi feito por SSH pela WLAN, com a chave pública da caixa previamente conferida por ADB. Os resultados não homologam outras unidades ou câmeras.

| Parte | Resultado e limite |
|---|---|
| Webcam USB-A | Enumerada como `1224:2a25`, `USB PHY 2.0: USB CAMERA`, driver `uvcvideo`. `/dev/video0` é captura; `/dev/video1` é um nó adicional da webcam, não usado neste teste. `/dev/video32` e `33` continuam sendo codecs. |
| Captura | O operador executou `target/camera.sh /dev/video0` e obteve `CAMERA_FRAME_CAPTURED`. O script valida o JPEG antes de publicar `media/captured/frame.jpg`. O SHA-256 foi confirmado depois por SSH. |
| Detecção CPU | SSD MobileNet V1 quantizado, TFLite C API do BSP 2.8.4; entrada uint8 `[1,300,300,3]`. Foram 3 aquecimentos e 20 execuções, com 2 threads. Mediana 35,613 ms e p95 36,740 ms, somente `invoke`. |
| Resultado semântico | `detections: []`. A inferência executou, mas a foto ainda precisa de revisão visual. Não significa aprovação de acurácia nem uma falha automática do modelo. |
| HDMI | Inicialmente sem sinal com cabo/entrada que funcionam no notebook. Reinício do serviço gráfico e barras por 30 s não resolveram sozinhos. O operador retirou/reconectou o HDMI e confirmou que apareceu imagem. A sequência recuperou a saída nesta sessão; causa exata e comportamento pós-energização continuam em aberto. |
| Webcam no HDMI | O operador confirmou imagem ao vivo durante o teste V4L2 → videoconvert → waylandsink em 640×480/25 fps, 500 quadros, sem gravar vídeo. |

As medições da captura/inferência vieram do console fornecido pelo operador; a enumeração, o hash da foto e o diagnóstico gráfico foram coletados diretamente por SSH. Consulte o [resumo de resultados distribuído](TARGET_RESULTS.md). Os logs brutos e inventários desta sessão ficam no projeto de preparação e não acompanham o pacote. Nenhuma foto pessoal foi copiada para o pacote por este diagnóstico.

Foto: `6448ccd130036faf7d14e79903553c638c014cb87756ff264519ee857f88074c`.

Modelo: `e4b118e5e4531945de2e659742c7c590f7536f8d0ed26d135abcfe83b4779d13`.

O formato encontrado antes do preview foi YUYV 1280×720 a 5 fps. O dispositivo também anuncia MJPEG até 1920×1080 a 25 fps; isso é capacidade enumerada, não um teste desse modo. A detecção acima é captura de uma imagem seguida de inferência CPU. O preview ao vivo é um teste separado, sem inferência CPU/GPU/HTP por quadro.

## Reproduzir a captura e a inferência

Siga o [guia SSH](SSH.md) antes de retirar o cabo USB-C do PC. Mantenha a fonte DC conectada. O manual QB560D V1.7, seção 4.10, informa a exclusão entre Type-C Device e Type-A Host. O mesmo manual identifica HDMI e DP over Type-C como interfaces de vídeo distintas; essa exclusão USB não comprova a causa de uma falha HDMI.

Na caixa, via SSH:

```sh
lsusb
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext

cd /opt/qb560d-training-payload
sh target/camera.sh /dev/video0 &&
sh target/ai.sh detection --image media/captured/frame.jpg
```

Use o nó de captura da webcam efetivamente enumerada; ele pode mudar em outra caixa. Não execute a inferência se a captura falhar, para não usar uma foto anterior. Para revisar o conteúdo e confirmar que a foto representa a cena pretendida, baixe-a em um PowerShell do host:

```powershell
$boxIp = Read-Host 'IPv4 atual desta caixa'
$cameraReview = Join-Path $env:TEMP 'qb560d-camera-review'
New-Item -ItemType Directory -Force $cameraReview | Out-Null
scp "root@${boxIp}:/opt/qb560d-training-payload/media/captured/frame.jpg" $cameraReview
Invoke-Item (Join-Path $cameraReview 'frame.jpg')
```

A revisão fica fora da pasta distribuída do treinamento. Uma cena com pessoa/objeto conhecido, bem iluminada e enquadrada, permite avaliar melhor a detecção; salve o resultado correspondente antes de substituir a foto.

## Diagnóstico HDMI já executado

- Weston usa `sdm-backend.so`; o serviço correto é `init_display.service`, não `weston.service` neste BSP.
- A saída DRM `DSI-1` está habilitada em 1920×1080/60 Hz. A saída `DP-1` está desconectada.
- Há um driver `lt9611uxd` associado ao conversor I2C `2-0041`; o device tree o habilita. Os logs de boot registram inicialização do LT9611UXD e referência ao firmware instalado.
- O EDID da saída DSI tem 128 bytes e contém o nome genérico `lt9611 video`, não a identificação comprovada do monitor externo. Portanto, `connected` em DSI não é critério de aprovação do HDMI físico.
- `systemctl restart init_display.service` encerrou o Weston anterior e criou um novo processo. Ao final, serviço, compositor e saída DSI estavam ativos; o SSH permaneceu acessível.
- O pipeline abaixo terminou com EOS normal após 30,068 s, mas o operador continuou vendo ausência de sinal. Isso comprova execução do pipeline no compositor, sem comprovar transmissão HDMI.

```sh
export XDG_RUNTIME_DIR=/run/user/root
export WAYLAND_DISPLAY=wayland-0
gst-launch-1.0 -e \
  videotestsrc is-live=true num-buffers=900 pattern=smpte \
  ! 'video/x-raw,width=1280,height=720,framerate=30/1' \
  ! videoconvert ! waylandsink
```

Nenhum arquivo de configuração do display, firmware ou registrador I2C foi alterado. O restart sozinho não resolveu; a recuperação visual aconteceu depois da reconexão física do HDMI. Não foi isolado se o restart era necessário ou se a reconexão sozinha teria resolvido.

O observador coletou 90 amostras com estado DSI, hash do EDID e contador de interrupções do conversor sem alteração. Não houve marcação sincronizada do instante da ação física pelo operador; portanto, esse registro não prova ausência de evento elétrico ou defeito de interrupção. A confirmação visual do operador é o critério de recuperação nesta sessão.

## Reproduzir webcam ao vivo no HDMI

Depois de obter imagem no monitor, execute na caixa por SSH:

```sh
export XDG_RUNTIME_DIR=/run/user/root
export WAYLAND_DISPLAY=wayland-0
gst-launch-1.0 -e \
  v4l2src device=/dev/video0 num-buffers=500 \
  ! 'video/x-raw,format=YUY2,width=640,height=480,framerate=25/1' \
  ! videoconvert ! waylandsink
```

Esse modo foi anunciado pela webcam e executado nesta caixa. O pipeline exibe aproximadamente 20 segundos e termina, sem salvar vídeo. A resolução da janela/câmera não altera a resolução física de 1080p da saída DSI. Para outra webcam, selecione caps compatíveis com seu inventário V4L2.

Se o HDMI ficar sem sinal nesta caixa, a sequência usada nesta sessão foi:

1. Manter fonte DC, monitor ligado/entrada selecionada e acesso SSH; deixar o USB-C do PC desconectado para usar a webcam USB-A.
2. Executar `systemctl restart init_display.service`; aguardar o Weston e o socket `/run/user/root/wayland-0` reaparecerem. Esse passo fecha aplicações gráficas.
3. Retirar o HDMI da caixa, aguardar 5 s e reconectar. Confirmar visualmente a imagem; `DSI-1 connected` sozinho não basta.
4. Executar as barras de cores ou o preview acima.

Isso é um procedimento de recuperação observado, não uma correção persistente de firmware.

## Próximas verificações físicas

1. Recuperação por reconexão e preview conjunto: concluídos nesta sessão, com confirmação visual do operador.
2. Ainda testar uma inicialização física com monitor ligado e HDMI já conectado: encerrar atividades, executar `sync` e `systemctl poweroff`, retirar DC e outras fontes de alimentação, aguardar pelo menos 10 s e religar pela fonte DC. Manter o cabo USB-C do PC desconectado e recuperar o SSH pelo IP atual.
3. Repetir as barras de cores e comparar os logs do novo boot. Se o problema reaparecer, repetir com outro monitor/TV e cabo direto para delimitar compatibilidade de sinal antes de atribuir defeito à caixa.

O cold boot com esse arranjo HDMI e a identificação da causa continuam pendentes. Não há recomendação de trocar firmware, carregar outra imagem do BSP ou escrever em registradores sem diagnóstico específico do fabricante.
