"""Generate local reports from preserved evidence, without contacting the target."""
import datetime as dt,json,shutil
from pathlib import Path
from update_qairt import ROOT,VERSION,DEFAULT_REMOTE,check_lock,sha,write_json
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def main():
    check_lock();mobile=ROOT/'evidence/persistent-20261101/mobilenet';gesture=ROOT.parents[1]/'demos/hand_gesture'
    stage=read(ROOT/'evidence/persistent-20261101/stage/stage-result.json');mr=read(mobile/'results.json');gr=read(gesture/'evidence/final-htp/summary.json');both=read(gesture/'evidence/final-seven-both/summary.json')
    assert stage['remote']==DEFAULT_REMOTE and stage['originals_unchanged'] and mr['originals_unchanged']
    assert gr['tested']==7 and gr['passed']==7 and read(gesture/'evidence/final-htp/system-integrity.json')['originals_unchanged']
    assert all(s['profile']['positive_cycle_events']>0 and s['profile']['accelerator_events']>0 for r in gr['results'] for s in r['stages'])
    cpu=[r for r in both['results'] if r['backend']=='cpu'];neg=read(next((gesture/'evidence/negative-dog').glob('*/result.json')))
    old=ROOT/'validation-summary.json'
    if old.exists() and not read(old).get('persistent_installation_performed'):shutil.copy2(old,ROOT/'evidence/20261101-mobilenet-validation/historical-summary.json')
    gesture_summary=dict(htp_tested=7,htp_passed=7,cpu_tested=len(cpu),cpu_passed=sum(r['passed'] for r in cpu),cpu_classification_accepted=False,cpu_discrepancy_cause='Undetermined',htp_graphs_with_positive_cycles=21,negative_image_prediction=neg['prediction'],scope=gr['results'][0]['scope'],evidence='../../demos/hand_gesture/evidence/final-htp/summary.json',comparison_evidence='../../demos/hand_gesture/evidence/final-seven-both/summary.json')
    write_json(old,dict(status='PERSISTENT_RUNTIME_VALIDATED_HTP_GESTURE_WORKSHOP_READY',completed_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),runtime_version=mr['runtime_version'],remote_validation_directory=DEFAULT_REMOTE,persistent_installation_performed=True,system_runtime_replaced=False,global_path_changed=False,reboot_tested=False,originals_unchanged=True,mobilenet=mr,hand_gesture=gesture_summary))
    lines=['HAND GESTURE: QAIRT 2.51 EM '+DEFAULT_REMOTE,'HTP: 7/7; CPU: 0/7 classes esperadas.','Scores sao saidas diretas do classificador, sem softmax adicional.','']
    for r in gr['results']:
        cr=next(c for c in cpu if c['image_sha256']==r['image_sha256'])
        lines.append(f"{Path(r['image']).name}: HTP={r['prediction']} score={r['confidence']:.8f}; CPU={cr['prediction']} score={cr['confidence']:.8f}")
        lines.append('  HTP execute por grafo (us, uma execucao): '+', '.join(s['graph']+'='+str(s['profile']['execute_us']) for s in r['stages']))
    lines+=['','Todos os 21 grafos HTP tem eventos de acelerador e ciclos positivos.','Controle negativo sem maos (cachorro): '+neg['prediction']+'.','CPU executou os grafos chamados (exit 0), mas falhou nas classes das sete fotos.','Causa da divergencia CPU nao determinada. Use HTP no workshop.','Sete fotos selecionadas nao representam acuracia em dataset ou FPS de camera.','O perfil nao inclui o pipeline completo, USB, preparacao de imagem e inicializacao.','Geometria no host e tres redes na caixa. Imagem estatica, uma mao.','Tentativas preservadas: workshop-validation (HTP 3/4, CPU 0/4), seven-htp (5/7),','fist-threshold-05 (None) e demais pastas de evidence/.','victory.jpg, test_fist.jpg e test_right_hands.jpg falharam nos ensaios iniciais.','O conjunto final usa test_victory.jpg, closed_fist.jpg e full_open_palm.png.','Os pesos e rotulos nao foram alterados. Limiares finais: palma 0.75, mao 0.2.','Hashes do BSP originais preservados. Reboot nao realizado.']
    (gesture/'RESULTADOS_GESTOS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8');write_json(gesture/'RESULTADOS_GESTOS.json',dict(htp=gr,cpu_comparison=both,negative=neg))
    (ROOT/'RESULTADOS_VALIDACAO.txt').write_text('INSTALACAO PERSISTENTE: '+DEFAULT_REMOTE+'\nRuntime: '+mr['runtime_version']+'\nOriginais preservados. Sem alteracao global de PATH. Reboot nao realizado.\n\n'+(mobile/'RESULTADOS.txt').read_text(encoding='utf-8')+'\n'+'\n'.join(lines)+'\n',encoding='utf-8')
    files=[p for p in ROOT.iterdir() if p.is_file() and p.name!='package-manifest.json']+[p for p in gesture.iterdir() if p.is_file()]
    write_json(ROOT/'package-manifest.json',dict(package='update_QIART',runtime=VERSION,default_remote=DEFAULT_REMOTE,files=[dict(path=__import__('os').path.relpath(p,ROOT).replace('\\','/'),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(files)]))
    print(json.dumps(gesture_summary,indent=2))
if __name__=='__main__':main()
