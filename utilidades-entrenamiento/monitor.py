#!/usr/bin/env python3
"""Panel para iniciar, detener y seguir el entrenamiento (modelo-ia/runs)."""
import json
import re
import sqlite3
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MODEL_DIR = Path("/app/modelo-ia")
RUN_ID = re.compile(r"^\d{8}-\d{6}$")
LOG_PATH = MODEL_DIR / "entrenamiento.log"
TRAIN_COMMAND = [sys.executable, "/app/train.py", "--config", "/app/configs/default.yaml"]
_lock = threading.Lock()
_process: subprocess.Popen | None = None

PAGE = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Entrenamiento de prendas</title>
<style>
body{font-family:system-ui,sans-serif;margin:1.5rem;background:#f5f6f8;color:#222}
.card{background:#fff;border-radius:8px;padding:1rem;margin-bottom:1rem;box-shadow:0 1px 3px #0002}
progress{width:100%;height:1.2rem}table{border-collapse:collapse;width:100%}
td,th{padding:.3rem .5rem;border-bottom:1px solid #ddd;text-align:right}th:first-child,td:first-child{text-align:left}
canvas{width:100%;height:220px}select{font-size:1rem}.muted{color:#666}
</style></head><body>
<h1>Entrenamiento de prendas</h1>
<div class="card"><button id="start">Iniciar entrenamiento</button>
<button id="stop" disabled>Detener</button> <span id="tstate" class="muted"></span>
<pre id="log" class="muted" style="max-height:10rem;overflow:auto;margin:.5rem 0 0"></pre></div>
<div class="card"><label>Ejecución: <select id="run"></select></label>
<span id="state" class="muted"></span></div>
<div class="card"><h3>Progreso</h3><progress id="bar" max="100" value="0"></progress>
<div id="prog" class="muted"></div></div>
<div class="card"><h3>Pérdida por época</h3><canvas id="chart" width="900" height="220"></canvas></div>
<div class="card"><h3>Métricas de validación</h3><table id="tbl"></table></div>
<div class="card"><h3>Imágenes registradas</h3><div id="imgs" class="muted"></div></div>
<script>
const $=id=>document.getElementById(id);let pick=false;
async function j(u){const r=await fetch(u);return r.json()}
async function runs(){const l=await j('/api/runs');const s=$('run'),cur=s.value;
 s.replaceChildren(...l.map(r=>{const o=document.createElement('option');o.value=o.textContent=r;return o}));
 if(!l.length){const o=document.createElement('option');o.textContent='Sin ejecuciones todavía (inicia un entrenamiento)';o.value='';s.replaceChildren(o);return}
 if(pick){s.value=l[0];pick=false}else if(cur&&l.includes(cur))s.value=cur;}
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
 $('start').disabled=t.running;$('stop').disabled=!t.running;
 $('tstate').textContent=t.running?'Entrenando (pid '+t.pid+')':(t.returncode===null?'Detenido':'Terminó con código '+t.returncode);
 $('log').textContent=t.log}
async function post(u){const r=await fetch(u,{method:'POST',headers:{'X-Requested-With':'monitor'}});
 if(!r.ok)alert((await r.json()).error||'Error');await status()}
$('start').onclick=async()=>{pick=true;await post('/api/start')};
$('stop').onclick=()=>post('/api/stop');
(async()=>{await status();await runs();await refresh();$('run').onchange=refresh;setInterval(async()=>{await status();await runs();refresh()},3000)})();
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


def start_training() -> tuple[int, dict]:
    global _process
    with _lock:
        if _process is not None and _process.poll() is None:
            return 409, {"error": "Ya hay un entrenamiento en curso."}
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("wb") as log:
            _process = subprocess.Popen(TRAIN_COMMAND, stdout=log, stderr=subprocess.STDOUT)
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
        elif self.path == "/api/status":
            self._send(200, json.dumps(process_status()).encode(), "application/json")
        elif self.path == "/api/runs":
            self._send(200, json.dumps(list_runs()).encode(), "application/json")
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
        elif self.path == "/api/start":
            status, body = start_training()
            self._send(status, json.dumps(body).encode(), "application/json")
        elif self.path == "/api/stop":
            status, body = stop_training()
            self._send(status, json.dumps(body).encode(), "application/json")
        else:
            self._send(404, b'{"error": "No encontrado"}', "application/json")

    def log_message(self, *args) -> None:
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8090), Handler).serve_forever()
