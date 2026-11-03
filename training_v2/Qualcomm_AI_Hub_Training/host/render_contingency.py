"""Make a captioned MP4 replay from validated logs; this is not a live screen capture.

Rendering dependencies: Pillow and imageio-ffmpeg0.6.0. No API token is read.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image,ImageDraw,ImageFont


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-dir',required=True)
    p.add_argument('--encoder-packages',help='Optional isolated imageio-ffmpeg package directory')
    a=p.parse_args()
    if a.encoder_packages:sys.path.insert(0,str(Path(a.encoder_packages).resolve()))
    import imageio_ffmpeg as ff
    run=Path(a.run_dir).resolve();folder=Path(__file__).resolve().parents[1]
    source_bytes=(run/'deployment-comparison.json').read_bytes()
    result=json.loads(source_bytes)
    assert result['result']=='HOSTED_AND_TARGET_CPU_GPU_PASS'
    cloud=result['hosted'];cpu=result['target']['cpu'];gpu=result['target']['gpu']
    dest=folder/'contingencia';dest.mkdir(exist_ok=True)
    (dest/'source-comparison.json').write_bytes(source_bytes)
    proof=result['local_gpu_log_evidence'];assert all(proof.values())
    src=folder/'demo_offline/evidence/local-gpu.log';assert 'Initialized OpenCL-based API' in src.read_text(encoding='utf-8')
    vectors=lambda x:'  '.join(f'{n:.8f}' for n in x[0])
    scenes=[
      dict(seconds=9,title='AI Hub na QB560D-EU',lines=[
        'Contingência offline do laboratório D2-04',
        'Compile, inferência, profile e deploy CPU/GPU',
        'Dados reais de 1 de novembro de 2026',
        'Formato: replay de logs e resultados aprovados'],
        caption='Este vídeo reproduz os resultados reais salvos. Não é uma captura de tela ao vivo.'),
      dict(seconds=13,title='1. Contrato do modelo',lines=[
        'Algoritmo: Conv3x3, ReLU, média espacial, Flatten',
        'Entrada sintética: float32 NCHW [1, 3, 32, 32]',
        'Saída: quatro características numéricas [1, 4]',
        '',
        'Referência NumPy:',vectors(cpu['expected']),
        'A saída não representa classes de objetos.'],
        caption='A referência controlada permite validar conversão e execução antes de uma demo visual.'),
      dict(seconds=12,title='2. Jobs hospedados concluídos',lines=[
        'Dragonwing RB3 Gen 2 Vision Kit',
        'QCS6490 / Hexagon v68 / Qualcomm Linux 1.6',
        f"Compile:           {cloud['compile_job']['id']}   SUCCESS",
        f"Inference/profile: {cloud['inference_profile_job']['id']}   SUCCESS",
        'Profile: 4 entradas GPU e 0 entradas CPU',
        'TFLite exportado: 1992 bytes',
        'CPU/GPU da nossa caixa usam esse mesmo artefato.'],
        caption='O kit hospedado e a QB560D-EU têm sistemas distintos. Suas medidas ficam separadas.'),
      dict(seconds=12,title='3. Comparação numérica hospedada',lines=[
        'Referência:',vectors(cloud['expected']),
        'GPU hospedada:',vectors(cloud['actual']),
        f"Erro absoluto máximo: {cloud['max_abs_error']:.8f}",
        'Tolerância: atol=0.0001, rtol=0.001',
        'CORRECTNESS: PASS'],
        caption='Os quatro valores passaram na comparação. A validação cobre essa entrada sintética.'),
      dict(seconds=14,title='4. CPU da QB560D-EU',lines=[
        'Trecho do resultado real salvo:',
        'result: PASS',
        'backend: cpu     runtime: TFLite 2.8.4',
        'input_layout: NCHW',
        f"max_abs_error: {cpu['max_abs_error']:.3e}",
        f"median_invoke_ms: {cpu['median_invoke_ms']:.7f}",
        '10 aquecimentos e 50 inferências medidas',
        '__QB560D_EXIT__=0'],
        caption='A CPU executou o artefato baixado, com o mesmo hash e sem alterar o runtime do BSP.'),
      dict(seconds=14,title='5. GPU da QB560D-EU',lines=[
        'INFO: Created TensorFlow Lite delegate for GPU.',
        'INFO: Initialized OpenCL-based API.',
        'INFO: Created 1 GPU delegate kernels.',
        'result: PASS     runtime: TFLite 2.8.4',
        f"max_abs_error: {gpu['max_abs_error']:.3e}",
        f"median_invoke_ms: {gpu['median_invoke_ms']:.7f}",
        '10 aquecimentos e 50 inferências medidas',
        '__QB560D_EXIT__=0'],
        caption='O log confirma OpenCL e um kernel delegado. O caminho não refaz a execução em CPU.'),
      dict(seconds=14,title='6. Resultado e limites',lines=[
        'Mesmo TFLite, entrada e referência na caixa',
        f"CPU local: mediana {cpu['median_invoke_ms']:.4f} ms",
        f"GPU local: mediana {gpu['median_invoke_ms']:.4f} ms",
        f"GPU/CPU local: {gpu['median_invoke_ms']/cpu['median_invoke_ms']:.2f}x o tempo",
        'Este grafo pequeno não mostrou ganho na GPU.',
        f"Hub: estimativa {cloud['estimated_inference_us']/1000:g} ms; mediana {cloud['sample_median_us']/1000:g} ms",
        'Medições hospedadas e locais não são equivalentes.'],
        caption='O objetivo é validar o fluxo. Os tempos são de inferência, não de uma aplicação completa.'),
      dict(seconds=10,title='7. Repetição offline',lines=[
        'Na pasta do pacote, na caixa já preparada:',
        '$ sh run_target.sh cpu',
        '$ sh run_target.sh gpu',
        '',
        'Conferir PASS, hash e log OpenCL.',
        'Pacote: QB560D_AIHub_Demo_Offline.zip',
        'Modelo, tensores, código e evidências incluídos.'],
        caption='A execução local dispensa Internet e conta AI Hub. O preparo do BSP continua sendo pré-requisito.'),
      dict(seconds=8,title='Fluxo aprovado',lines=[
        'Compile e inference/profile: PASS',
        'Comparação numérica hospedada: PASS',
        'Mesmo artefato em CPU/GPU na caixa: PASS',
        'Hashes, saídas e logs preservados',
        '',
        'Replay dos resultados reais, sem credenciais.'],
        caption='Use o guia e os arquivos salvos para explicar a demonstração durante uma falha de rede.')]
    size=(1280,720);fps=10
    regular=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',28)
    title_font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',38)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
    tiny=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
    out=dest/'AIHub_QB560D_Contingencia_Replay.mp4'
    writer=ff.write_frames(str(out),size,fps=fps,codec='libx264',quality=8,
                           output_params=['-movflags','+faststart'])
    writer.send(None)
    timeline=[];start=0
    qa=folder.parent/'.build/aihub-video-qa';qa.mkdir(parents=True,exist_ok=True)
    def wrap(draw,text,font,max_width):
        words=text.split();rows=[];current=''
        for word in words:
            candidate=(current+' '+word).strip()
            if draw.textlength(candidate,font=font)>max_width and current:rows.append(current);current=word
            else:current=candidate
        if current:rows.append(current)
        return rows or ['']
    try:
        for n,scene in enumerate(scenes,1):
            base=Image.new('RGB',size,'#111722');draw=ImageDraw.Draw(base)
            draw.text((52,26),'QB560D-EU  /  QUALCOMM AI HUB',font=tiny,fill='#aeb9cb')
            draw.text((910,26),'REPLAY DE LOGS REAIS',font=tiny,fill='#66d8b4')
            draw.text((52,80),scene['title'],font=title_font,fill='white')
            body=[]
            for line in scene['lines']:body.extend(wrap(draw,line,regular,1170))
            assert len(body)<=10,(n,body)
            for line in body:assert draw.textlength(line,font=regular)<=1172,(n,line)
            captions=wrap(draw,scene['caption'],small,1168);assert len(captions)<=2,(n,captions)
            for i,line in enumerate(captions):draw.text((52,603+i*30),line,font=small,fill='#e3e9f3')
            draw.text((52,682),'Resultados de 01/11/2026. Vídeo sem áudio e sem captura de autenticação.',font=tiny,fill='#aeb9cb')
            draw.text((1170,682),f'{n}/9',font=tiny,fill='#aeb9cb')
            full=base.copy();fdraw=ImageDraw.Draw(full)
            for i,line in enumerate(body):fdraw.text((52,159+i*39),line,font=regular,fill='#dbe8f4')
            full.save(qa/f'scene-{n}.png')
            for index in range(scene['seconds']*fps):
                frame=base.copy();d=ImageDraw.Draw(frame)
                count=min(len(body),1+int(index/fps*3))
                for i,line in enumerate(body[:count]):
                    color='#66d8b4' if 'PASS' in line or 'SUCCESS' in line else '#dbe8f4'
                    d.text((52,159+i*39),line,font=regular,fill=color)
                writer.send(frame.tobytes())
            timeline.append({'number':n,'start_s':start,'end_s':start+scene['seconds'],**scene});start+=scene['seconds']
    finally:writer.close()
    def srt_time(t):return f'{t//3600:02}:{t//60%60:02}:{t%60:02},000'
    srt='\n\n'.join(f"{s['number']}\n{srt_time(s['start_s'])} --> {srt_time(s['end_s'])}\n{s['caption']}" for s in timeline)+'\n'
    (dest/'AIHub_QB560D_Contingencia_Replay.srt').write_text(srt,encoding='utf-8')
    recording={'at_host_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'kind':'REPLAY_OF_VALIDATED_LOGS',
               'live_screen_capture':False,'fresh_cloud_submission':False,'audio':False,
               'duration_s':start,'fps':fps,'size':list(size),'model_sha256':result['artifact_sha256'],
               'source_sha256':hashlib.sha256(source_bytes).hexdigest(),
               'video_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'scenes':timeline}
    (dest/'recording.json').write_text(json.dumps(recording,indent=2)+'\n',encoding='utf-8')
    frames,seconds=ff.count_frames_and_secs(str(out));assert frames==start*fps and abs(seconds-start)<.1
    (dest/'README.md').write_text('''# Vídeo de contingência

AIHub_QB560D_Contingencia_Replay.mp4: vídeo H.264 de106segundos,1280x720,sem áudio, com legendas incorporadas em português. O arquivo SRT permite reutilizar as legendas.

O vídeo reproduz logs e resultados reais aprovados. Não é captura de tela ao vivo nem nova submissão de jobs. Essa identificação aparece no início, durante e no final. Não mostra configuração de conta, token ou senha da caixa.

Os dados vêm de evidence/tiny-gpu-20261101-171619/deployment-comparison.json. recording.json registra fonte, hashes, duração e roteiro. O ZIP QB560D_AIHub_Demo_Offline.zip preserva o artefato e os executores para repetição local após o preparo da caixa.
''',encoding='utf-8')
    print(json.dumps({'video':str(out),'frames':frames,'seconds':seconds,'bytes':out.stat().st_size,'kind':recording['kind']}))


if __name__=='__main__':
    main()
