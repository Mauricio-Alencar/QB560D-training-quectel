"""Publish real target outputs as an offline image gallery; never fabricates predictions."""
import hashlib,html,json,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PACKAGE=ROOT/'htp251'
TITLES={'classification':'Classificação — MobileNet V1','detection':'Detecção — SSD MobileNet V1','pose':'Pose — PoseNet','gesture':'Mão recortada — Hand Landmark Lite','segmentation':'Segmentação — DeepLabV3'}
def copy(source,destination):destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
def publish(summary):
    destination=PACKAGE/'results';destination.mkdir(exist_ok=True);manifest_path=destination/'RESULTS.json';records=json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    evidence=Path(summary['evidence']);active=json.loads((PACKAGE/'models.json').read_text())['models']
    for case in summary['results']:
        if not case['passed']:continue
        task=case['task'];folder=evidence/task;record=json.loads((folder/'htp/result.json').read_text())
        assert record['passed'] and record['profile']['positive_cycle_events']>0 and record['model_sha256']==active[task]['dlc_sha256']
        target=destination/task;copy(folder/'htp/prediction.png',target/'htp.png');copy(folder/'input.png',target/'input.png');copy(next((folder/'reference'/task).glob('*.png')),target/'cpu-reference.png');copy(folder/'htp/result.json',target/'result.json');copy(folder/'htp/htp/profile.csv',target/'profile.csv')
        reference=next((folder/'reference'/task).glob('*.json'));copy(reference,target/'cpu-reference.json')
        records[task]=dict(title=TITLES[task],passed=True,model_sha256=record['model_sha256'],evidence=evidence.relative_to(ROOT).as_posix(),result=record,image_sha256=hashlib.sha256((target/'htp.png').read_bytes()).hexdigest())
    manifest_path.write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    cards=[]
    for task in TITLES:
        if task not in records:continue
        record=records[task];current=record['model_sha256']==active[task]['dlc_sha256'];result=record['result'];metric=html.escape(json.dumps(result['comparison_to_original_tflite_cpu'],ensure_ascii=False))
        cards.append('<section><h2>'+html.escape(TITLES[task])+'</h2><p>'+('HTP validado' if current else 'Resultado de uma revisão anterior')+' — QAIRT/QNN 2.51.40 — '+str(result['profile']['positive_cycle_events'])+' eventos com ciclos HTP positivos</p><div class="images">'+''.join('<figure><figcaption>'+label+'</figcaption><a href="'+task+'/'+file+'"><img src="'+task+'/'+file+'" alt="'+label+'"></a></figure>' for file,label in [('input.png','Entrada preparada'),('cpu-reference.png','Referência TFLite CPU original'),('htp.png','Saída real do HTP 2.51')])+'</div><p class="metric">'+metric+'</p><p><a href="'+task+'/result.json">Resultado JSON</a> · <a href="'+task+'/profile.csv">Perfil do acelerador</a></p></section>')
    timing=destination/'timing-summary.json'
    if timing.is_file():
        benchmark=json.loads(timing.read_text());assert benchmark['status']=='PASS_COMPARATIVE_TIMING'
        rows=''.join('<tr><td>'+html.escape(TITLES[r['task']])+'</td>'+''.join('<td style="padding:9px 22px">%.3f</td>'%r['backends'][b]['median_of_session_medians_ms'] for b in ['cpu','gpu','htp'])+'</tr>' for r in benchmark['table'])
        cards.insert(0,'<section><h2>Tempos reais de inferência (ms)</h2><p>Mediana de três medianas de sessão. 50 inferências após 10 aquecimentos, mesma imagem por tarefa.</p><table style="border-collapse:collapse;text-align:left"><thead><tr><th>Demo</th><th>CPU TFLite 2.8.4</th><th>GPU TFLite 2.8.4</th><th>HTP QNN 2.51</th></tr></thead><tbody>'+rows+'</tbody></table><p>GPU usa partição OpenCL, com operadores residuais na CPU quando necessário. SSD inclui NMS no TFLite; a medida HTP exclui NMS no host. Precisões e pipelines diferem. Não são FPS de câmera.</p><p><a href="../BENCHMARK.md">Método e comando para reproduzir</a> · <a href="timing.csv">CSV</a> · <a href="timing-summary.json">JSON completo</a></p></section>')
    extras=[];repo=ROOT
    v2=repo/'runtimes/qairt_2_51/evidence/fw-20261101-v2/results.json'
    if v2.is_file():
        result=json.loads(v2.read_text());top=result['backends']['htp']['top5'][0];source=repo/'runtimes/qairt_2_51/assets/dog_input_224.png'
        if source.exists():
            image=Image.open(source).convert('RGB').resize((640,640));canvas=Image.new('RGB',(640,700),'white');canvas.paste(image,(0,0));draw=ImageDraw.Draw(canvas)
            try:font=ImageFont.truetype('arial.ttf',20)
            except OSError:font=ImageFont.load_default()
            draw.text((10,650),'MobileNet V2 / HTP 2.51 / '+top['label']+' %.2f%%'%(100*top['softmax_probability']),fill='black',font=font);canvas.save(destination/'mobilenet-v2-htp.png');copy(v2,destination/'mobilenet-v2-result.json')
            extras.append('<h2>Classificação — MobileNet V2</h2><p>Validação anterior no mesmo firmware, preservada. A anotação usa o resultado HTP registrado.</p><img class="extra" src="mobilenet-v2-htp.png"><p><a href="mobilenet-v2-result.json">Evidência original</a></p>')
    gesture_source=repo/'demos/hand_gesture/evidence/fw-20261101/summary.json'
    if gesture_source.is_file():
        previous=json.loads(gesture_source.read_text());assert previous['tested']==7 and previous['passed']==7;figures=[];copy(gesture_source,destination/'mediapipe-summary.json')
        for record in previous['results']:
            case=gesture_source.parent/Path(record['target_run']).name;file=case/'prediction.png'
            if file.is_file():
                name='mediapipe-'+record['prediction']+'.png';copy(file,destination/name);figures.append('<figure><figcaption>'+html.escape(record['prediction'])+'</figcaption><a href="'+name+'"><img src="'+name+'"></a></figure>')
        if figures:extras.append('<h2>MediaPipe — sete gestos no HTP 2.51</h2><p>Validação anterior no mesmo firmware. Três grafos por imagem, com perfis HTP.</p><div class="images">'+''.join(figures)+'</div><p><a href="mediapipe-summary.json">Evidência original de sete gestos</a></p>')
    page='<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Resultados reais — HTP 2.51</title><style>body{font:17px Arial,sans-serif;max-width:1250px;margin:32px auto;padding:0 20px;color:#222}h1,h2{color:#210079}section{margin:36px 0 55px}.images{display:flex;gap:18px;flex-wrap:wrap}figure{margin:0;flex:1;min-width:240px;max-width:380px}img{max-width:100%;height:auto}figcaption{font-weight:bold;margin:10px 0}.metric{font:14px monospace;overflow-wrap:anywhere}.extra{max-width:500px}a{color:#210079}footer{margin:40px 0;font-size:14px}</style><h1>Resultados reais de inferência no HTP 2.51</h1><p>Cinco demos migradas. CNNs executadas na caixa; preparação da imagem, decodificação, NMS/regras e desenho no host. Comparação por imagem de referência, sem alegar acurácia em dataset ou FPS de câmera.</p>'+''.join(cards)+''.join(extras)+'<footer>Fontes das imagens: amostras TensorFlow em media/sources.json e acervo MediaPipe/PyTorch documentado em update_QIART. Os JSONs e perfis acompanham os resultados. Runtimes originais preservados.</footer></html>'
    (destination/'index.html').write_text(page,encoding='utf-8');print('REAL_OUTPUT_GALLERY:',destination/'index.html',flush=True)
if __name__=='__main__':
    latest=json.loads((PACKAGE/'LATEST.json').read_text());publish(json.loads((Path(latest['evidence'])/'summary.json').read_text()))
