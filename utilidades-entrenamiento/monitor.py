#!/usr/bin/env python3
"""Panel para iniciar, detener y seguir el entrenamiento (modelo-ia/runs)."""
import json
import re
import sqlite3
import subprocess
import sys
import io
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

MODEL_DIR = Path("/app/modelo-ia")
CONFIG_DIR = Path("/app/configs")
DEFAULT_CONFIG_NAME = "default.yaml"
RUN_ID = re.compile(r"^\d{8}-\d{6}$")
LOG_PATH = MODEL_DIR / "entrenamiento.log"
_lock = threading.Lock()
_process: subprocess.Popen | None = None
MAX_IMAGE_BYTES = 10 * 1024 * 1024
_model_cache: dict = {}
EVAL_SPLITS = ("test", "val", "train")
EVAL_MAX_IMAGES = 2000
_eval_state = {"running": False, "run_id": None, "split": None, "done": 0, "total": 0, "error": None}

PAGE = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Entrenamiento de prendas</title>
<style>
body{font-family:system-ui,sans-serif;margin:1.5rem;background:#f5f6f8;color:#222}
.card{background:#fff;border-radius:8px;padding:1rem;margin-bottom:1rem;box-shadow:0 1px 3px #0002}
progress{width:100%;height:1.2rem}table{border-collapse:collapse;width:100%}
td,th{padding:.3rem .5rem;border-bottom:1px solid #ddd;text-align:right}th:first-child,td:first-child{text-align:left}
canvas{width:100%;height:220px}select{font-size:1rem}.muted{color:#666}
dialog{border:0;border-radius:8px;width:min(480px,92vw);box-shadow:0 4px 20px #0005}
.bar{background:#e5e7eb;border-radius:4px;margin:2px 0;position:relative;height:1.3rem}
.bar i{display:block;height:100%;background:#93c5fd;border-radius:4px}.bar.on i{background:#2563eb}
@media print{body>*:not(#edlg){display:none!important}
html,body{height:auto!important;overflow:visible!important;margin:0}
#edlg{position:static!important;display:block;width:100%!important;max-width:none;height:auto!important;max-height:none!important;overflow:visible!important;margin:0;box-shadow:none;padding:0}
.noprint{display:none!important}canvas{max-width:100%;height:auto!important;break-inside:avoid}
table,div[style]{break-inside:avoid}@page{margin:12mm}}
.bar span{position:absolute;left:6px;top:0;font-size:.85rem}
</style></head><body>
<h1>Entrenamiento de prendas</h1>
<div class="card"><button id="start">Nuevo entrenamiento</button>
<button id="continue">Continuar desde mejor checkpoint</button>
<label>Configuración <select id="tconfig"></select></label>
<label>Estrategia <select id="strategy">
<option value="fine_tune">Ajuste fino completo (recomendado)</option>
<option value="heads_only">Solo entrenar las cabezas</option>
</select></label>
<p class="muted">Continuar crea una nueva ejecución desde el mejor checkpoint de la ejecución seleccionada. Se reinician optimizador y scheduler; no es una reanudación exacta. Para entrenar desde cero con la receta recomendada, elige la configuración <code>desde-cero.yaml</code>.</p>
<button id="stop" disabled>Detener</button> <span id="tstate" class="muted"></span>
<pre id="log" class="muted" style="max-height:10rem;overflow:auto;margin:.5rem 0 0"></pre></div>
<div class="card"><button id="try">Probar modelo en CPU</button>
<button id="eval">Evaluar precisión por propiedad</button></div>
<div class="card"><button id="dsr">Ejecutar prueba DSR de la API</button>
<span id="dsrstate" class="muted"></span><div id="dsrout"></div></div>
<dialog id="edlg" style="width:min(940px,96vw)"><h3>Precisión por propiedad</h3>
<p class="noprint"><label>Modelo: <select id="erun"></select></label>
<label>Fotos: <select id="esplit"><option value="test">test (no usadas para entrenar)</option>
<option value="val">val</option><option value="train">train (muestra de 2000)</option></select></label>
<span class="noprint"><button id="ego">Evaluar</button> <button id="epdf" disabled>Exportar PDF</button> <button id="eclose">Cerrar</button></span></p>
<div id="estate" class="muted"></div><div id="eout"></div></dialog>
<dialog id="dlg"><h3>Probar pesos entrenados en CPU</h3>
<p><label>Modelo: <select id="mrun"></select></label></p>
<p><input type="file" id="mfile" accept="image/jpeg,image/png,image/webp"></p>
<img id="mprev" alt="" style="max-width:100%;max-height:240px;display:none">
<div id="mres"></div>
<p><button id="mgo">Predecir</button> <button id="mclose">Cerrar</button></p></dialog>
<div class="card"><label>Ejecución: <select id="run"></select></label>
<span id="state" class="muted"></span></div>
<div class="card"><h3>Progreso</h3><progress id="bar" max="100" value="0"></progress>
<div id="prog" class="muted"></div></div>
<div class="card"><h3>Pérdida por época</h3><canvas id="chart" width="900" height="220"></canvas></div>
<div class="card"><h3>Métricas de validación</h3><table id="tbl"></table></div>
<div class="card"><h3>Imágenes registradas</h3><div id="imgs" class="muted"></div></div>
<script>
const $=id=>document.getElementById(id);let pick=false,trainingRunning=false;
async function j(u){const r=await fetch(u);return r.json()}
async function runs(){const l=await j('/api/runs');const s=$('run'),cur=s.value;
 s.replaceChildren(...l.map(r=>{const o=document.createElement('option');o.value=o.textContent=r;return o}));
 if(!l.length){const o=document.createElement('option');o.textContent='Sin ejecuciones todavía (inicia un entrenamiento)';o.value='';s.replaceChildren(o);return}
 if(pick){s.value=l[0];pick=false}else if(cur&&l.includes(cur))s.value=cur;
 $('continue').disabled=trainingRunning||!s.value;}
function draw(h){const c=$('chart'),x=c.getContext('2d');x.clearRect(0,0,c.width,c.height);if(!h.length)return;
 const ser=[['train_loss',h.map(e=>e.train_loss),'#2563eb'],['val_loss',h.map(e=>e.validation.loss),'#dc2626']];
 const all=ser.flatMap(s=>s[1]),mx=Math.max(...all),mn=Math.min(...all),W=c.width-40,H=c.height-30;
 ser.forEach(([n,v,col],k)=>{x.strokeStyle=col;x.beginPath();v.forEach((y,i)=>{const px=30+(v.length>1?i/(v.length-1):0)*W,py=10+(1-(y-mn)/((mx-mn)||1))*H;i?x.lineTo(px,py):x.moveTo(px,py)});x.stroke();
 x.fillStyle=col;x.fillText(n,40+k*90,c.height-4)});x.fillStyle='#666';x.fillText(mx.toFixed(3),0,16);x.fillText(mn.toFixed(3),0,c.height-18)}
async function refresh(){const id=$('run').value;if(!id)return;
 const d=await j('/api/run/'+id);const p=d.progress||{},h=d.metrics||[];
 const total=(d.config||{}).epochs||0;
 if(p.finished){$('bar').value=100;$('prog').textContent='Entrenamiento finalizado.'}
 else if(p.batches){const pct=((p.epoch-1+p.batch/p.batches)/total)*100;$('bar').value=pct;
  $('prog').textContent=`Época ${p.epoch}/${total}, lote ${p.batch}/${p.batches}, pérdida ${p.loss.toFixed(4)} (${p.updated})`}
 else $('prog').textContent='Sin datos de progreso todavía.';
 draw(h);const t=$('tbl');t.replaceChildren();
 const hdr=['época','train loss','val loss','acc tipo','F1 color','F1 estilo'];
 const row=(c,tag)=>{const r=document.createElement('tr');c.forEach(v=>{const e=document.createElement(tag);e.textContent=v;r.append(e)});t.append(r)};
 row(hdr,'th');h.forEach(e=>row([e.epoch,e.train_loss.toFixed(4),e.validation.loss.toFixed(4),(e.validation.type_accuracy*100).toFixed(1)+'%',e.validation.color.f1.toFixed(3),e.validation.style.f1.toFixed(3)],'td'));
 $('state').textContent=d.test?' | test: acc tipo '+(d.test.type_accuracy*100).toFixed(1)+'%':'';
 $('imgs').textContent=d.images?Object.entries(d.images).map(([k,v])=>k+': '+v).join(' | ')+` | nuevas vs. previas: ${d.new_images}`:'Sin registro.'}
async function status(){const t=await j('/api/status');
 trainingRunning=t.running;$('start').disabled=t.running;$('continue').disabled=t.running||!$('run').value;
 $('stop').disabled=!t.running;
 $('tstate').textContent=t.running?'Entrenando (pid '+t.pid+')':(t.returncode===null?'Detenido':'Terminó con código '+t.returncode);
 $('log').textContent=t.log}
async function post(u){const r=await fetch(u,{method:'POST',headers:{'X-Requested-With':'monitor'}});
 if(!r.ok)alert((await r.json()).error||'Error');await status()}
$('try').onclick=async()=>{const m=await j('/api/models');const s=$('mrun');
 s.replaceChildren(...m.map(r=>{const o=document.createElement('option');o.value=r.run_id;
  o.textContent=r.run_id+' (época '+r.epoch+')';return o}));
 $('mres').textContent=m.length?'':'No hay pesos entrenados todavía.';$('mgo').disabled=!m.length;$('dlg').showModal()};
$('mclose').onclick=()=>$('dlg').close();
$('mfile').onchange=()=>{const f=$('mfile').files[0],i=$('mprev');
 if(f){i.src=URL.createObjectURL(f);i.style.display='block'}else i.style.display='none'};
function bars(title,list){const d=document.createElement('div');const h=document.createElement('b');h.textContent=title;d.append(h);
 list.forEach(e=>{const b=document.createElement('div');b.className='bar'+(e.seleccionado?' on':'');
  const i=document.createElement('i');i.style.width=(e.probabilidad*100)+'%';const t=document.createElement('span');
  t.textContent=e.valor+' '+(e.probabilidad*100).toFixed(1)+'%';b.append(i,t);d.append(b)});return d}
$('mgo').onclick=async()=>{const f=$('mfile').files[0],out=$('mres');
 if(!f){out.textContent='Elige una imagen.';return}
 out.textContent='Calculando…';
 const r=await fetch('/api/predict?run='+encodeURIComponent($('mrun').value),{method:'POST',
  headers:{'X-Requested-With':'monitor','Content-Type':'application/octet-stream'},body:f});
 const d=await r.json();if(!r.ok){out.textContent=d.error||'Error';return}
 const timing=document.createElement('p');timing.className='muted';
 timing.textContent=`CPU: carga ${d.timing_ms.model_load} ms; preparación ${d.timing_ms.preprocess} ms; inferencia ${d.timing_ms.inference} ms; total ${d.timing_ms.total} ms`;
 out.replaceChildren(timing,bars('Tipo',d.tipo),bars('Colores (top 5)',d.colores),bars('Estilos (top 5)',d.estilos))};
function pct(v){return (v*100).toFixed(1)+'%'}
function bars2(title,labels,series){const w=document.createElement('div');const h=document.createElement('b');h.textContent=title;w.append(h);
 const c=document.createElement('canvas');c.width=880;c.height=260;c.style.height='260px';w.append(c);
 const x=c.getContext('2d'),L=40,B=70,W=c.width-L-10,H=c.height-B-10,n=labels.length,g=W/n;
 x.font='11px sans-serif';x.strokeStyle='#ddd';x.fillStyle='#666';
 for(let k=0;k<=4;k++){const y=10+H*(1-k/4);x.beginPath();x.moveTo(L,y);x.lineTo(c.width-10,y);x.stroke();x.fillText((k*25)+'%',2,y+4)}
 labels.forEach((lb,i)=>{const bw=g*0.8/series.length;series.forEach((s,k)=>{const v=s.values[i],bh=H*v;
  x.fillStyle=s.color;x.fillRect(L+i*g+g*0.1+k*bw,10+H-bh,bw-1,bh)});
  x.save();x.translate(L+i*g+g/2,10+H+8);x.rotate(Math.PI/4);x.fillStyle='#333';x.fillText(lb,0,0);x.restore()});
 series.forEach((s,k)=>{x.fillStyle=s.color;x.fillRect(L+k*110,c.height-14,10,10);x.fillStyle='#333';x.fillText(s.name,L+k*110+14,c.height-5)});
 return w}
function heat(title,labels,m){const w=document.createElement('div');const h=document.createElement('b');
 h.textContent=title+' (filas: real, columnas: predicho)';w.append(h);const t=document.createElement('table');t.style.fontSize='.8rem';
 const hr=document.createElement('tr');hr.append(document.createElement('th'));labels.forEach(l=>{const e=document.createElement('th');e.textContent=l;hr.append(e)});t.append(hr);
 m.forEach((row,i)=>{const tr=document.createElement('tr');const th=document.createElement('th');th.textContent=labels[i];tr.append(th);
  const tot=row.reduce((a,b)=>a+b,0)||1;row.forEach((v,k)=>{const td=document.createElement('td');td.textContent=v;
   const a=v/tot;td.style.background=`rgba(${i===k?'37,99,235':'220,38,38'},${Math.min(1,a*(i===k?0.9:2.5))})`;td.style.color=a>0.5&&i===k?'#fff':'#222';tr.append(td)});t.append(tr)});
 w.append(t);return w}
function summary(items){const d=document.createElement('div');d.style.cssText='display:flex;gap:.75rem;flex-wrap:wrap;margin:.5rem 0';
 items.forEach(([k,v])=>{const c=document.createElement('div');c.style.cssText='background:#f1f5f9;border-radius:6px;padding:.5rem .8rem';
  const a=document.createElement('div');a.textContent=k;a.className='muted';const b=document.createElement('b');b.style.fontSize='1.3rem';b.textContent=v;c.append(a,b);d.append(c)});return d}
function nm(l){return l.map(e=>e.valor)}
function lst(a){return a.length<2?a.join(''):a.slice(0,-1).join(', ')+' y '+a[a.length-1]}
function sect(title,paras){const d=document.createElement('div');d.style.cssText='margin:.8rem 0;break-inside:avoid';
 const h=document.createElement('h4');h.textContent=title;h.style.margin='.3rem 0';d.append(h);
 paras.forEach(t=>{const p=document.createElement('p');p.style.margin='.3rem 0';p.textContent=t;d.append(p)});return d}
async function analysis(r){
 const d=await j('/api/run/'+r.run_id),m=d.metrics||[],cfg=d.config||{};
 const best=m.length?m.reduce((a,b)=>b.validation.loss<a.validation.loss?b:a):null;
 const T=r.tipo.clases,C=r.color.etiquetas.filter(e=>e.soporte>=30),S=r.estilo.etiquetas.filter(e=>e.soporte>=30);
 const byF=(a,desc)=>[...a].sort((x,y)=>desc?y.f1-x.f1:x.f1-y.f1);
 const wT=[...T].sort((a,b)=>a.recall-b.recall)[0];
 let conf='';{const i=T.findIndex(c=>c.valor===wT.valor);let bj=-1,bv=0;r.tipo.matriz[i].forEach((v,k)=>{if(k!==i&&v>bv){bv=v;bj=k}});if(bj>=0)conf=T[bj].valor}
 const macro=T.reduce((a,c)=>a+c.f1,0)/T.length;
 const stopped=best&&m.length>best.epoch;
 const gap=best?Math.abs(best.validation.type_accuracy-r.tipo.accuracy):null;
 const rare=[...C,...S].filter(e=>e.soporte<120&&e.recall<0.5);
 const simple=[
  ['¿Qué tal funciona?',['De cada 100 prendas, el modelo acierta el tipo en '+Math.round(r.tipo.accuracy*100)+'. Donde más se equivoca es con '+wT.valor+' (acierta '+Math.round(wT.recall*100)+' de cada 100'+(conf?' y suele confundirla con '+conf:'')+').']],
  ['Colores',['Reconoce bien '+lst(nm(byF(C,true).slice(0,3)))+'. Le cuesta más con '+lst(nm(byF(C,false).slice(0,3)))+', que suele pasar por alto. En '+Math.round(r.color.coincidencia_exacta*100)+' de cada 100 prendas acierta todos los colores a la vez.']],
  ['Estilos',['Reconoce bien '+lst(nm(byF(S,true).slice(0,3)))+'. Le cuesta más con '+lst(nm(byF(S,false).slice(0,3)))+'. El estilo es más subjetivo que el tipo o el color, por eso se espera menos acierto. Acierta todos los estilos de una prenda en '+Math.round(r.estilo.coincidencia_exacta*100)+' de cada 100.']],
  ['¿Aprendió bien?',[best?('Practicó '+m.length+' vueltas completas (épocas)'+(stopped?' y se detuvo solo porque dejó de mejorar; se guardó la mejor, la número '+best.epoch+'.':'.')+' El resultado en fotos que no vio al entrenar es '+(gap<0.03?'muy parecido':'algo distinto')+' al de validación, así que no parece haber memorizado las fotos.'):'Sin historial de épocas.']],
  ['¿Qué falta?',['Más fotos de lo que menos conoce'+(rare.length?' ('+lst(nm(rare).slice(0,5))+')':'')+' y revisar que sus etiquetas sean correctas. Con eso el modelo debería mejorar más que entrenándolo más tiempo.']]
 ];
 const pro=[
  ['Configuración',['MobileNetV3-Small preentrenada en ImageNet, entrada '+(cfg.image_size||'?')+' px, batch '+(cfg.batch_size||'?')+', AdamW (lr cabezas '+(cfg.learning_rate||'?')+', backbone '+(cfg.finetune_lr||'?')+'), '+(cfg.warmup_epochs||0)+' épocas de calentamiento con backbone congelado y luego ajuste fino completo, planificador coseno, label smoothing '+(cfg.label_smoothing||0)+', entropía cruzada ponderada por clase y precisión mixta. Selección del checkpoint por pérdida de validación con parada temprana (paciencia '+(cfg.early_stopping_patience||'?')+').']],
  ['Convergencia y generalización',[best?('Se ejecutaron '+m.length+' épocas; el mejor checkpoint es la '+best.epoch+' (pérdida de validación '+best.validation.loss.toFixed(3)+'). La exactitud de tipo en validación ('+pct(best.validation.type_accuracy)+') y en '+r.split+' ('+pct(r.tipo.accuracy)+') difieren '+(gap*100).toFixed(1)+' puntos, sin indicio de sobreajuste a validación. La pérdida de entrenamiento no es directamente comparable con la de validación porque incluye aumento de datos y label smoothing.'):'Sin historial.']],
  ['Tipo de prenda (softmax, una clase)',['Exactitud '+pct(r.tipo.accuracy)+' y F1 macro '+pct(macro)+' sobre '+r.n+' imágenes. La clase más débil es '+wT.valor+' (recall '+pct(wT.recall)+', precisión '+pct(wT.precision)+', n='+wT.soporte+')'+(conf?'; el error dominante es la confusión con '+conf+' según la matriz.':'.')+' Precisión alta con recall bajo indica que el modelo es conservador en esa clase.']],
  ['Color y estilo (sigmoide, multietiqueta, umbral '+r.umbral+')',['Color: F1 micro '+pct(r.color.f1)+' (precisión '+pct(r.color.precision)+', recall '+pct(r.color.recall)+'), Jaccard medio '+pct(r.color.jaccard)+', coincidencia exacta '+pct(r.color.coincidencia_exacta)+'. Estilo: F1 micro '+pct(r.estilo.f1)+' (precisión '+pct(r.estilo.precision)+', recall '+pct(r.estilo.recall)+'), Jaccard '+pct(r.estilo.jaccard)+', coincidencia exacta '+pct(r.estilo.coincidencia_exacta)+'.',
   'Recall menor que precisión en ambas tareas: el umbral fijo de 0,5 es conservador para etiquetas poco frecuentes. Las métricas se calculan solo sobre prendas con esa propiedad anotada.']],
  ['Limitaciones',['Las etiquetas proceden de anotación asistida por IA con revisión humana parcial, lo que acota el techo de calidad, sobre todo en estilo. Las etiquetas con soporte bajo'+(rare.length?' ('+lst(nm(rare).slice(0,6))+')':'')+' tienen estimaciones de alta varianza y recall bajo por desbalance. Se evalúa una imagen por prenda y no se detectan varias prendas por foto.']],
  ['Recomendaciones',['1) Calibrar un umbral por etiqueta sobre validación para equilibrar precisión y recall. 2) Aumentar y auditar ejemplos de las etiquetas minoritarias; valorar pos_weight o focal loss. 3) Revisar manualmente una muestra de etiquetas de estilo y simplificar el catálogo si hay conceptos solapados (p. ej. formal/elegante). 4) Probar mayor resolución o un backbone mayor solo si lo anterior no basta.']]
 ];
 const out=[];const t1=document.createElement('h3');t1.textContent='Análisis en palabras sencillas';out.push(t1);simple.forEach(x=>out.push(sect(x[0],x[1])));
 const t2=document.createElement('h3');t2.textContent='Análisis técnico';out.push(t2);pro.forEach(x=>out.push(sect(x[0],x[1])));return out}
function showEval(r){const o=$('eout');o.replaceChildren();
 o.append(summary([['Imágenes evaluadas',r.n],['Acierto tipo',pct(r.tipo.accuracy)],['F1 color',pct(r.color.f1)],['F1 estilo',pct(r.estilo.f1)],
  ['Colores exactos',pct(r.color.coincidencia_exacta)],['Estilos exactos',pct(r.estilo.coincidencia_exacta)]]));
 const A=document.createElement('div');o.append(A);analysis(r).then(n=>A.replaceChildren(...n));
 const T=r.tipo.clases;
 o.append(bars2('Tipo de prenda: acierto (recall) y precisión por clase',T.map(c=>c.valor),[{name:'recall',values:T.map(c=>c.recall),color:'#2563eb'},{name:'precisión',values:T.map(c=>c.precision),color:'#93c5fd'}]));
 o.append(heat('Matriz de confusión del tipo',T.map(c=>c.valor),r.tipo.matriz));
 [['Color','color'],['Estilo','estilo']].forEach(([n,k])=>{const E=r[k].etiquetas;
  o.append(bars2(n+': por etiqueta (precisión, recall, F1)',E.map(c=>c.valor+' ('+c.soporte+')'),[{name:'precisión',values:E.map(c=>c.precision),color:'#93c5fd'},{name:'recall',values:E.map(c=>c.recall),color:'#2563eb'},{name:'F1',values:E.map(c=>c.f1),color:'#16a34a'}]))});
 $('estate').textContent='Resultado de '+r.run_id+' sobre '+r.split+' (umbral '+r.umbral+'), generado el '+new Date().toLocaleString()+'. Entre paréntesis: prendas con esa etiqueta.';$('epdf').disabled=false}
let epoll=null;
async function eload(){const q='run='+encodeURIComponent($('erun').value)+'&split='+$('esplit').value;
 const d=await j('/api/eval?'+q);const st=d.estado;
 if(st.running){$('estate').textContent='Evaluando '+st.done+'/'+st.total+'…';return}
 if(st.error&&st.run_id===$('erun').value&&st.split===$('esplit').value){$('estate').textContent='Error: '+st.error}
 if(d.resultado){showEval(d.resultado)}else if(!st.error){$('eout').replaceChildren();$('estate').textContent='Sin evaluación guardada; pulsa Evaluar.'}
 if(epoll&&!st.running){clearInterval(epoll);epoll=null}}
$('eval').onclick=async()=>{const m=await j('/api/models');const s=$('erun');
 s.replaceChildren(...m.map(r=>{const o=document.createElement('option');o.value=r.run_id;o.textContent=r.run_id;return o}));
 $('eout').replaceChildren();$('estate').textContent=m.length?'':'No hay pesos entrenados todavía.';$('ego').disabled=!m.length;
 $('edlg').showModal();if(m.length)eload()};
$('erun').onchange=$('esplit').onchange=()=>{$('epdf').disabled=true;eload()};
$('epdf').onclick=()=>window.print();
$('eclose').onclick=()=>{$('edlg').close();if(epoll){clearInterval(epoll);epoll=null}};
$('ego').onclick=async()=>{const q='run='+encodeURIComponent($('erun').value)+'&split='+$('esplit').value;
 const r=await fetch('/api/eval?'+q,{method:'POST',headers:{'X-Requested-With':'monitor'}});
 if(!r.ok){alert((await r.json()).error||'Error');return}
 $('estate').textContent='Iniciando…';epoll=setInterval(eload,2000)};
$('start').onclick=async()=>{pick=true;await post('/api/start?config='+encodeURIComponent($('tconfig').value))};
$('continue').onclick=()=>post('/api/continue?run='+encodeURIComponent($('run').value)+'&strategy='+encodeURIComponent($('strategy').value)+'&config='+encodeURIComponent($('tconfig').value));
$('stop').onclick=()=>post('/api/stop');
$('dsr').onclick=async()=>{const s=$('dsrstate'),o=$('dsrout');s.textContent='Ejecutando prueba DSR (1.424 imágenes, ~15 s)…';o.replaceChildren();
 try{const r=await fetch('http://127.0.0.1:8082/test/run',{method:'POST'});
  if(!r.ok){s.textContent='Error '+r.status+': '+(await r.text()).slice(0,200);return}
  const d=await r.json(),m=d.promedio_macro_propiedades;
  s.textContent='Prueba completada: '+new Date().toLocaleString();
  o.replaceChildren(summary([['Imágenes evaluadas',d.imagenes_evaluadas],['Acierto tipo',d.tipo_prenda.accuracy_pct+'%'],
   ['Jaccard color',d.color.coincidencia_parcial_jaccard_pct+'%'],['Jaccard estilo',d.estilo.coincidencia_parcial_jaccard_pct+'%'],
   ['Promedio macro',m.porcentaje+'%'],['Criterio R11 (≥70%)',m.porcentaje>=70?'Cumple':'No cumple']]));
  const p=document.createElement('p');p.className='muted';p.textContent='Reporte guardado en '+d.resultado_guardado+' (run_id '+d.run_id+').';o.append(p);
 }catch(e){s.textContent='No se pudo conectar con la API de pruebas (http://127.0.0.1:8082): '+e}}
async function loadConfigs(){const l=await j('/api/configs');const s=$('tconfig');
 s.replaceChildren(...l.map(n=>{const o=document.createElement('option');o.value=o.textContent=n;return o}));
 if(!l.includes(s.value))s.value='default.yaml'}
(async()=>{await loadConfigs();await status();await runs();await refresh();$('run').onchange=refresh;setInterval(async()=>{await status();await runs();refresh()},3000)})();
</script></body></html>"""


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def list_runs() -> list[str]:
    runs_dir = MODEL_DIR / "runs"
    if not runs_dir.is_dir():
        return []
    return sorted((d.name for d in runs_dir.iterdir() if RUN_ID.match(d.name)), reverse=True)


def image_stats(run_id: str):
    ledger = MODEL_DIR / "registro_entrenamiento.sqlite"
    if not ledger.is_file():
        return None, 0
    try:
        with sqlite3.connect(f"file:{ledger}?mode=ro", uri=True) as db:
            counts = dict(db.execute(
                "SELECT split, COUNT(*) FROM imagen_entrenamiento WHERE run_id = ? GROUP BY split", (run_id,)
            ))
            new = db.execute(
                """SELECT COUNT(*) FROM imagen_entrenamiento a WHERE a.run_id = ? AND NOT EXISTS (
                   SELECT 1 FROM imagen_entrenamiento b WHERE b.sha256 = a.sha256 AND b.run_id < a.run_id)""",
                (run_id,),
            ).fetchone()[0]
    except sqlite3.Error:
        return None, 0
    return counts or None, new


def load_model(run_id: str):
    import torch
    from train import MultiTaskMobileNet

    path = MODEL_DIR / "runs" / run_id / "best.pt"
    mtime = path.stat().st_mtime
    cached = _model_cache.get(run_id)
    if cached and cached[0] == mtime:
        return cached[1]
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    classes = checkpoint["classes"]
    model = MultiTaskMobileNet(
        type_count=len(classes["tipo_prenda"]),
        color_count=len(classes["color"]),
        style_count=len(classes["estilo"]),
        pretrained=False,
    )
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    _model_cache.clear()
    _model_cache[run_id] = (mtime, (model, checkpoint))
    return model, checkpoint


def predict_image(run_id: str, data: bytes) -> dict:
    import torch
    from PIL import Image
    from torchvision import transforms

    request_started = time.perf_counter()
    model_load_started = time.perf_counter()
    model, checkpoint = load_model(run_id)
    model_load_ms = (time.perf_counter() - model_load_started) * 1000
    classes, size = checkpoint["classes"], checkpoint["image_size"]
    threshold = checkpoint["multilabel_threshold"]
    transform = transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
    ])
    preprocess_started = time.perf_counter()
    with Image.open(io.BytesIO(data)) as image:
        tensor = transform(image.convert("RGB")).unsqueeze(0)
    preprocess_ms = (time.perf_counter() - preprocess_started) * 1000
    inference_started = time.perf_counter()
    with torch.inference_mode():
        outputs = model(tensor)
    inference_ms = (time.perf_counter() - inference_started) * 1000
    def top(probs, labels, count, selected_min):
        order = probs.argsort(descending=True)[:count]
        return [{"valor": labels[i], "probabilidad": float(probs[i]),
                 "seleccionado": float(probs[i]) >= selected_min} for i in order]
    type_probs = outputs["type"].softmax(dim=1)[0]
    return {
        "device": "cpu",
        "timing_ms": {
            "model_load": round(model_load_ms, 2),
            "preprocess": round(preprocess_ms, 2),
            "inference": round(inference_ms, 2),
            "total": round((time.perf_counter() - request_started) * 1000, 2),
        },
        "tipo": top(type_probs, classes["tipo_prenda"], 3, float(type_probs.max())),
        "colores": top(outputs["color"].sigmoid()[0], classes["color"], 5, threshold),
        "estilos": top(outputs["style"].sigmoid()[0], classes["estilo"], 5, threshold),
    }


def _prf(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def run_evaluation(run_id: str, split: str) -> None:
    import torch
    from torch.utils.data import DataLoader
    import train

    try:
        model, checkpoint = load_model(run_id)
        classes, threshold = checkpoint["classes"], checkpoint["multilabel_threshold"]
        by_split, catalog = train.load_samples(
            Path("/app/dataset/metadata.sqlite"), Path("/app/dataset")
        )
        samples = list(by_split[split])
        if len(samples) > EVAL_MAX_IMAGES:
            samples = random.Random(42).sample(samples, EVAL_MAX_IMAGES)
        type_map = [classes["tipo_prenda"].index(n) if n in classes["tipo_prenda"] else -1
                    for n in catalog["tipo_prenda"]]
        color_cols = [catalog["color"].index(n) for n in classes["color"]]
        style_cols = [catalog["estilo"].index(n) for n in classes["estilo"]]
        with _lock:
            _eval_state["total"] = len(samples)
        loader = DataLoader(
            train.GarmentImages(samples, train.build_transform(checkpoint["image_size"])),
            batch_size=64, num_workers=4,
        )
        n_types = len(classes["tipo_prenda"])
        matrix = [[0] * n_types for _ in range(n_types)]
        stats = {k: {"counts": [[0, 0, 0, 0] for _ in classes[c]], "exact": 0, "jaccard": 0.0, "n": 0}
                 for k, c in (("color", "color"), ("estilo", "estilo"))}
        with torch.no_grad():
            for images, types, colors, styles, has_colors, has_styles in loader:
                out = model(images)
                predicted = out["type"].argmax(dim=1)
                for real, pred in zip(types.tolist(), predicted.tolist()):
                    if type_map[real] >= 0:
                        matrix[type_map[real]][pred] += 1
                for key, logits, target, cols, mask in (
                    ("color", out["color"], colors, color_cols, has_colors),
                    ("estilo", out["style"], styles, style_cols, has_styles),
                ):
                    if not mask.any():
                        continue
                    pred = logits.sigmoid()[mask] >= threshold
                    real = target[:, cols][mask] >= 0.5
                    entry = stats[key]
                    entry["n"] += int(mask.sum())
                    entry["exact"] += int((pred == real).all(dim=1).sum())
                    union = (pred | real).sum(dim=1)
                    inter = (pred & real).sum(dim=1)
                    entry["jaccard"] += float(torch.where(union > 0, inter / union.clamp(min=1), torch.ones_like(union, dtype=torch.float)).sum())
                    for i in range(pred.shape[1]):
                        c = entry["counts"][i]
                        c[0] += int((pred[:, i] & real[:, i]).sum())
                        c[1] += int((pred[:, i] & ~real[:, i]).sum())
                        c[2] += int((~pred[:, i] & real[:, i]).sum())
                        c[3] += int((~pred[:, i] & ~real[:, i]).sum())
                with _lock:
                    _eval_state["done"] += images.shape[0]

        total_types = sum(map(sum, matrix))
        type_classes = []
        for i, label in enumerate(classes["tipo_prenda"]):
            tp = matrix[i][i]
            fn = sum(matrix[i]) - tp
            fp = sum(row[i] for row in matrix) - tp
            type_classes.append({"valor": label, "soporte": tp + fn, **_prf(tp, fp, fn)})
        result = {
            "run_id": run_id, "split": split, "n": len(samples), "umbral": threshold,
            "tipo": {
                "accuracy": sum(matrix[i][i] for i in range(n_types)) / total_types if total_types else 0.0,
                "clases": type_classes, "matriz": matrix,
            },
        }
        for key in ("color", "estilo"):
            entry = stats[key]
            labels = []
            for label, (tp, fp, fn, tn) in zip(classes[key], entry["counts"]):
                total = tp + fp + fn + tn
                labels.append({"valor": label, "soporte": tp + fn,
                               "accuracy": (tp + tn) / total if total else 0.0, **_prf(tp, fp, fn)})
            tp = sum(c[0] for c in entry["counts"])
            fp = sum(c[1] for c in entry["counts"])
            fn = sum(c[2] for c in entry["counts"])
            n = entry["n"]
            result[key] = {
                "n_anotadas": n, "etiquetas": labels, **_prf(tp, fp, fn),
                "coincidencia_exacta": entry["exact"] / n if n else 0.0,
                "jaccard": entry["jaccard"] / n if n else 0.0,
            }
        (MODEL_DIR / "runs" / run_id / f"evaluacion_{split}.json").write_text(
            json.dumps(result, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as error:
        with _lock:
            _eval_state["error"] = str(error)
    finally:
        with _lock:
            _eval_state["running"] = False


def start_evaluation(run_id: str, split: str) -> tuple[int, dict]:
    if not RUN_ID.match(run_id) or split not in EVAL_SPLITS:
        return 400, {"error": "Parámetros no válidos."}
    if not (MODEL_DIR / "runs" / run_id / "best.pt").is_file():
        return 404, {"error": "Modelo no encontrado."}
    with _lock:
        if _eval_state["running"]:
            return 409, {"error": "Ya hay una evaluación en curso."}
        _eval_state.update(running=True, run_id=run_id, split=split, done=0, total=0, error=None)
    threading.Thread(target=run_evaluation, args=(run_id, split), daemon=True).start()
    return 200, {"ok": True}


def list_models() -> list[dict]:
    models = []
    for run_id in list_runs():
        checkpoint = MODEL_DIR / "runs" / run_id / "best.pt"
        if checkpoint.is_file():
            metrics = read_json(MODEL_DIR / "runs" / run_id / "metrics.json") or []
            best = min(metrics, key=lambda e: e["validation"]["loss"]) if metrics else {}
            models.append({"run_id": run_id, "epoch": best.get("epoch", "?")})
    return models


def train_command(config_name: str | None = None) -> list[str]:
    name = config_name or DEFAULT_CONFIG_NAME
    if not re.fullmatch(r"[\w.-]+\.yaml", name):
        raise ValueError("Nombre de configuración no válido.")
    if not (CONFIG_DIR / name).is_file():
        raise FileNotFoundError(f"No existe la configuración {name}.")
    return [sys.executable, "/app/train.py", "--config", str(CONFIG_DIR / name)]


def list_configs() -> list[str]:
    return sorted(path.name for path in CONFIG_DIR.glob("*.yaml"))


def continuation_command(
    run_id: str,
    strategy: str,
    model_dir: Path = MODEL_DIR,
    config_name: str | None = None,
) -> list[str]:
    if not re.fullmatch(r"\d{8}-\d{6}", run_id):
        raise ValueError("El ID de ejecución de origen no es válido.")
    if strategy not in ("fine_tune", "heads_only"):
        raise ValueError("La estrategia de continuación no es válida.")
    if not (model_dir / "runs" / run_id / "best.pt").is_file():
        raise FileNotFoundError(f"La ejecución {run_id} no tiene un mejor checkpoint para continuar.")
    return train_command(config_name) + ["--continue-from", run_id, "--strategy", strategy]


def process_status() -> dict:
    with _lock:
        running = _process is not None and _process.poll() is None
        returncode = None if _process is None or running else _process.returncode
        pid = _process.pid if running else None
    try:
        log = "\n".join(LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-15:])
    except OSError:
        log = ""
    return {"running": running, "pid": pid, "returncode": returncode, "log": log[-3000:]}


def start_training(
    run_id: str | None = None,
    strategy: str | None = None,
    config_name: str | None = None,
) -> tuple[int, dict]:
    global _process
    try:
        command = train_command(config_name)
    except (ValueError, FileNotFoundError) as error:
        return 400, {"error": str(error)}
    if run_id is not None:
        try:
            command = continuation_command(run_id, strategy or "", MODEL_DIR, config_name)
        except ValueError as error:
            return 400, {"error": str(error)}
        except FileNotFoundError as error:
            return 404, {"error": str(error)}
    elif strategy is not None:
        return 400, {"error": "Selecciona una ejecución para continuar."}
    with _lock:
        if _process is not None and _process.poll() is None:
            return 409, {"error": "Ya hay un entrenamiento en curso."}
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("wb") as log:
            _process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
    return 200, {"ok": True}


def stop_training() -> tuple[int, dict]:
    with _lock:
        if _process is None or _process.poll() is not None:
            return 409, {"error": "No hay entrenamiento en curso."}
        _process.terminate()
    return 200, {"ok": True}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/":
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif urlsplit(self.path).path == "/api/eval":
            query = parse_qs(urlsplit(self.path).query)
            run_id, split = query.get("run", [""])[0], query.get("split", [""])[0]
            if not RUN_ID.match(run_id) or split not in EVAL_SPLITS:
                self._send(400, b'{"error": "Parametros no validos"}', "application/json")
                return
            with _lock:
                state = dict(_eval_state)
            saved = read_json(MODEL_DIR / "runs" / run_id / f"evaluacion_{split}.json")
            self._send(200, json.dumps({"estado": state, "resultado": saved}).encode(), "application/json")
        elif self.path == "/api/models":
            self._send(200, json.dumps(list_models()).encode(), "application/json")
        elif self.path == "/api/status":
            self._send(200, json.dumps(process_status()).encode(), "application/json")
        elif self.path == "/api/runs":
            self._send(200, json.dumps(list_runs()).encode(), "application/json")
        elif self.path == "/api/configs":
            self._send(200, json.dumps(list_configs()).encode(), "application/json")
        elif self.path.startswith("/api/run/") and RUN_ID.match(self.path[9:]):
            run_id = self.path[9:]
            run_dir = MODEL_DIR / "runs" / run_id
            images, new = image_stats(run_id)
            data = {
                "config": read_json(run_dir / "config.json"),
                "metrics": read_json(run_dir / "metrics.json") or [],
                "progress": read_json(run_dir / "progress.json"),
                "test": read_json(run_dir / "test_metrics.json"),
                "images": images,
                "new_images": new,
            }
            self._send(200, json.dumps(data).encode(), "application/json")
        else:
            self._send(404, b"No encontrado", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        # El encabezado personalizado obliga a preflight CORS y bloquea peticiones de otros sitios.
        if self.headers.get("X-Requested-With") != "monitor":
            self._send(403, b'{"error": "Prohibido"}', "application/json")
        elif urlsplit(self.path).path == "/api/predict":
            self._predict()
        elif urlsplit(self.path).path == "/api/eval":
            query = parse_qs(urlsplit(self.path).query)
            status, body = start_evaluation(query.get("run", [""])[0], query.get("split", [""])[0])
            self._send(status, json.dumps(body).encode(), "application/json")
        elif self.path == "/api/start":
            query = parse_qs(urlsplit(self.path).query)
            status, body = start_training(config_name=query.get("config", [None])[0])
            self._send(status, json.dumps(body).encode(), "application/json")
        elif urlsplit(self.path).path == "/api/continue":
            query = parse_qs(urlsplit(self.path).query)
            status, body = start_training(
                query.get("run", [""])[0], query.get("strategy", [""])[0],
                query.get("config", [None])[0],
            )
            self._send(status, json.dumps(body).encode(), "application/json")
        elif self.path == "/api/stop":
            status, body = stop_training()
            self._send(status, json.dumps(body).encode(), "application/json")
        else:
            self._send(404, b'{"error": "No encontrado"}', "application/json")

    def _predict(self) -> None:
        run_id = parse_qs(urlsplit(self.path).query).get("run", [""])[0]
        length = int(self.headers.get("Content-Length") or 0)
        if not RUN_ID.match(run_id) or not (MODEL_DIR / "runs" / run_id / "best.pt").is_file():
            self._send(404, b'{"error": "Modelo no encontrado"}', "application/json")
        elif not 0 < length <= MAX_IMAGE_BYTES:
            self._send(413, b'{"error": "Imagen vacia o mayor de 10 MB"}', "application/json")
        else:
            data = self.rfile.read(length)
            try:
                body = json.dumps(predict_image(run_id, data)).encode()
                self._send(200, body, "application/json")
            except Exception as error:
                message = "No se pudo leer la imagen" if "cannot identify" in str(error) else str(error)
                self._send(400, json.dumps({"error": message}).encode(), "application/json")

    def log_message(self, *args) -> None:
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8090), Handler).serve_forever()
