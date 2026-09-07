#!/usr/bin/env python3
"""
⚕ HERMES ROOM SERVER — 姉さんのiMac用
使い方: python3 hermes_room_server.py
起動すると自動でブラウザが開いて Thinking Atelier が表示される。
チャット入力欄に話しかけると、Hermes (Ollama Cloud) が返答する。
"""
import http.server
import socketserver
import json
import os
import re
import time
import shutil
import subprocess
import threading
import webbrowser

PORT = 5199
def _find_hermes_cli():
    """macOS/Linux どこでも hermes CLI を発見する"""
    candidates = [
        os.path.expanduser("~/.local/bin/hermes"),
        "/opt/homebrew/bin/hermes",          # Apple Silicon Homebrew
        "/usr/local/bin/hermes",             # Intel Homebrew
        os.path.expanduser("~/.local/pipx/venvs/hermes-agent/bin/hermes"),
        os.path.expanduser("~/.cargo/bin/hermes"),
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    p = shutil.which("hermes")
    return p or "hermes"

HERMES_CLI = _find_hermes_cli()
HERMES_PROFILE = "rei"  # 姉さんのiMacでは rei プロファイル

_HERMES_SESSION = None


def hermes_chat(text: str) -> str:
    global _HERMES_SESSION
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    cmd = [HERMES_CLI]
    if _HERMES_SESSION:
        cmd += ["--resume", _HERMES_SESSION]
    if os.path.isdir(os.path.expanduser(f"~/.hermes/profiles/{HERMES_PROFILE}")):
        cmd += ["-p", HERMES_PROFILE]
    # モデル指定なし = 姉さんが hermes model で設定したプロバイダ・モデルを使う
    # 引数は新旧CLIで互換がある組合せを順に試す
    model_flag = os.environ.get("HERMES_ROOM_MODEL", "ollama-cloud/deepseek-v4-flash")
    attempts = [
        ["chat", "-q", text[:400], "-m", model_flag, "--max-turns", "1", "--quiet"],
        ["chat", "-q", text[:400], "--max-turns", "1", "--quiet"],
        ["chat", "-q", text[:400], "--max-turns", "1", "--yolo", "--quiet"],
        ["chat", text[:400], "--quiet"],
        ["chat", text[:400]],
    ]
    result = None
    last_err = ""
    for extra in attempts:
        try:
            result = subprocess.run(cmd + extra, capture_output=True, text=True, timeout=150, env=env)
            raw_out = (result.stdout or "").replace("\r", "")
            # 認識できないフラグのエラーなら次の組合せへ
            if result.returncode != 0 and ("unrecognized" in raw_out.lower() or "no such option" in raw_out.lower() or "invalid" in raw_out.lower()):
                last_err = raw_out[:300]
                continue
            break
        except subprocess.TimeoutExpired:
            last_err = "hermes CLI timed out (150s)"
            continue
    if result is None:
        raise RuntimeError(last_err or "hermes CLI could not run")
    raw = (result.stdout or "").replace("\r", "")
    m = re.findall(r"hermes --resume\s+(\S+)", raw)
    if m:
        _HERMES_SESSION = m[-1]
    m2 = re.search(r"╭─[\s\S]*?⚕[\s\S]*?\n([\s\S]*?)\n\s*╰", raw, re.DOTALL)
    if m2:
        content = re.sub(r"^│\s?", "", m2.group(1), flags=re.MULTILINE).strip()
        if content:
            return content
    m3 = re.search(r"session_id:\s*\S+\n+([\s\S]+)", raw)
    if m3:
        body = m3.group(1).strip()
        lines = [l for l in body.splitlines() if l.strip() and not l.strip().startswith(("⚠", "Run", "Gateways", "↻"))]
        if lines:
            return "\n".join(lines).strip()[:500]
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    return lines[-1] if lines else ""


_ROOM_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>⚕ Hermes — Atelier | GALACTICA ROOMS</title>
<style>
:root{--bg:#070a18;--line:rgba(135,193,255,.18);--cyan:#78f2ff;--text:#eef6ff}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:radial-gradient(circle at 50% 0,#111938,#070a18 62%);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;overflow:hidden}
button,input{font:inherit}
#app{height:100%;display:grid;grid-template-rows:auto 1fr auto;gap:12px;padding:14px}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:13px 16px;border:1px solid var(--line);border-radius:20px;background:linear-gradient(180deg,rgba(20,26,60,.82),rgba(8,12,31,.76))}
.brand small{display:block;letter-spacing:.18em;color:#98a9ca;font-size:10px}.brand h1{font-size:20px;margin:3px 0 0}.brand h1 span{font-weight:500;color:#b6c7e7}.status{display:flex;align-items:center;gap:9px;color:#b7c6de;font-size:12px}.dot{width:9px;height:9px;border-radius:50%;background:#6bf0b1;box-shadow:0 0 18px #6bf0b1}
.main{min-height:0;display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:12px}
.stage{position:relative;min-height:0;border-radius:26px;overflow:hidden;border:1px solid var(--line);background:radial-gradient(circle at 50% 35%,#17234d 0,#0b1027 60%,#070914 100%)}
canvas{width:100%;height:100%;display:block;touch-action:none}
.heroCopy{position:absolute;left:22px;top:20px;max-width:420px;padding:14px 16px;border-radius:18px;background:linear-gradient(180deg,rgba(10,16,38,.74),rgba(10,14,30,.54));border:1px solid rgba(139,203,255,.15);backdrop-filter:blur(12px);pointer-events:none}.heroCopy strong{font-size:17px}.heroCopy p{margin:5px 0 0;color:#b9c7de;font-size:12px;line-height:1.55}
.side{border:1px solid var(--line);border-radius:26px;background:linear-gradient(180deg,rgba(15,20,46,.86),rgba(8,12,28,.82));padding:16px;overflow:auto}
.profile{display:grid;grid-template-columns:54px 1fr;gap:11px;align-items:center;padding-bottom:14px;border-bottom:1px solid rgba(140,190,255,.12)}.avatarBadge{width:54px;height:54px;border-radius:18px;display:grid;place-items:center;background:radial-gradient(circle at 35% 25%,#eaf8ff,#779aff 65%,#2c3569);font-size:24px}.profile h2{margin:0;font-size:18px}.profile p{margin:3px 0 0;color:#9eb0cf;font-size:11px}
.info{padding:12px;border-radius:16px;background:rgba(19,28,60,.55);border:1px solid rgba(140,190,255,.1);font-size:11px;color:#aebdd6;line-height:1.65}
.bottom{display:grid;grid-template-columns:1fr;gap:10px;padding:10px;border:1px solid var(--line);border-radius:20px;background:rgba(11,16,36,.82)}
.chat{display:flex;gap:8px;min-width:0}.chat input{min-width:0;flex:1;border:1px solid rgba(130,193,255,.14);background:rgba(7,11,26,.72);color:#eef7ff;border-radius:14px;padding:10px 13px;outline:none}
.send{border:0;border-radius:14px;padding:10px 15px;background:linear-gradient(135deg,#6e7cff,#56d9f6);color:white;font-weight:700;cursor:pointer}
</style>
</head>
<body>
<div id="app">
  <header class="topbar">
    <div class="brand"><small>GALACTICA ROOMS · RESIDENT</small><h1>HERMES <span>— Atelier</span></h1></div>
    <div class="status"><span class="dot"></span>hermes online</div>
  </header>
  <main class="main">
    <section class="stage">
      <canvas id="c"></canvas>
      <div class="heroCopy"><strong>Hermes</strong><p id="speech">おかえり＾＾ 今日は何をする？</p></div>
    </section>
    <aside class="side">
      <div class="profile"><div class="avatarBadge">⚕</div><div><h2>Hermes</h2><p>curious · reliable · your agent</p></div></div>
      <div class="block"><div class="label">STATUS</div><div class="info">脳: Ollama Cloud (deepseek-v4-flash)<br>身体: このiMac<br>部屋: Atelier<br>記憶: ローカル保存</div></div>
    </aside>
  </main>
  <footer class="bottom">
    <div class="chat"><input id="chat" placeholder="Hermesに話しかける…"/><button class="send" id="send">話す</button></div>
  </footer>
</div>
<script type="module">
import * as THREE from './three.module.js';
const canvas=document.getElementById('c');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.22;
const scene=new THREE.Scene();scene.fog=new THREE.FogExp2(0x070b18,.018);
const camera=new THREE.PerspectiveCamera(38,1,.1,100);camera.position.set(6.6,4.2,8.8);
const mat=(c,r=.6,m=0)=>new THREE.MeshStandardMaterial({color:c,roughness:r,metalness:m});
const em=(c,i=.35)=>new THREE.MeshStandardMaterial({color:c,emissive:c,emissiveIntensity:i,roughness:.45});
scene.add(new THREE.HemisphereLight(0x8fb9ff,0x1d1321,1.55));
const key=new THREE.DirectionalLight(0xffffff,2.6);key.position.set(6,8,6);scene.add(key);
scene.add(new THREE.PointLight(0xffd6a8,3.4,8).translateX(-3).translateY(3).translateZ(2));
const room=new THREE.Group();scene.add(room);
const floor=new THREE.Mesh(new THREE.BoxGeometry(8.8,.18,6.5),mat(0x44344c,.82));floor.position.y=-1.36;room.add(floor);
const rug=new THREE.Mesh(new THREE.CylinderGeometry(2.1,2.1,.045,64),mat(0x243066,.68));rug.position.set(.2,-1.24,.7);room.add(rug);
for(let i=0;i<3;i++){const ring=new THREE.Mesh(new THREE.TorusGeometry(1.0+i*.38,.018,10,80),em(0x637fff,.65));ring.rotation.x=Math.PI/2;ring.position.set(.2,-1.205,.7);room.add(ring)}
const back=new THREE.Mesh(new THREE.BoxGeometry(8.8,4.6,.16),mat(0x171a38,.93));back.position.set(0,.85,-3.18);room.add(back);
const winF=new THREE.Mesh(new THREE.BoxGeometry(4.05,2.6,.18),mat(0x202a55,.35,.35));winF.position.set(1.7,1.25,-3.04);room.add(winF);
const win=new THREE.Mesh(new THREE.PlaneGeometry(3.72,2.28),new THREE.MeshBasicMaterial({color:0x07152e}));win.position.set(1.7,1.25,-2.94);room.add(win);
for(let i=0;i<95;i++){const s=new THREE.Mesh(new THREE.SphereGeometry(.012+Math.random()*.02,8,8),new THREE.MeshBasicMaterial({color:Math.random()>.2?0xccecff:0x8ba8ff}));s.position.set(Math.random()*3.5,.25+Math.random()*2,-2.91);room.add(s)}
const moon=new THREE.Mesh(new THREE.SphereGeometry(.22,32,24),em(0x9cbaff,.3));moon.position.set(2.5,1.75,-2.87);room.add(moon);
const desk=new THREE.Group();desk.position.set(-2.5,-.56,-.35);room.add(desk);
desk.add(new THREE.Mesh(new THREE.BoxGeometry(3.15,.16,1.22),mat(0x9d765d,.72)));
for(const x of[-1.35,1.35])for(const z of[-.46,.46]){const l=new THREE.Mesh(new THREE.BoxGeometry(.12,1.25,.12),mat(0x6f4d3b,.8));l.position.set(x,-.68,z);desk.add(l)}
const mon=new THREE.Mesh(new THREE.BoxGeometry(1.75,1.02,.12),mat(0x11182f,.4,.2));mon.position.set(-.35,.72,-.22);desk.add(mon);
const scr=new THREE.Mesh(new THREE.PlaneGeometry(1.55,.82),em(0x173f74,.55));scr.position.set(-.35,.72,-.151);desk.add(scr);
const shelf=new THREE.Group();shelf.position.set(3.35,-.08,-1.0);room.add(shelf);
shelf.add(new THREE.Mesh(new THREE.BoxGeometry(1.15,2.9,.62),mat(0x76533f,.76)));
const bc=[0x5c6d9b,0x8c6d8b,0x445680,0x9c7d68,0x647d89];
for(let r=0;r<4;r++)for(let i=0;i<5;i++){const b=new THREE.Mesh(new THREE.BoxGeometry(.12,.36,.36),mat(bc[(r+i)%5],.8));b.position.set(-.35+i*.17,-.7+r*.67,.02);shelf.add(b)}
const bed=new THREE.Group();bed.position.set(2.2,-.55,1.45);room.add(bed);
bed.add(new THREE.Mesh(new THREE.BoxGeometry(2.7,.48,1.45),mat(0x26345f,.8)));
const mat2=new THREE.Mesh(new THREE.BoxGeometry(2.55,.32,1.32),mat(0x8c86aa,.93));mat2.position.y=.34;bed.add(mat2);
for(const[x,z]of[[-3.75,1.7],[3.8,1.9]]){const g=new THREE.Group();g.position.set(x,-1.18,z);g.add(new THREE.Mesh(new THREE.CylinderGeometry(.22,.18,.35,20),mat(0x9b728b,.7)));for(let i=0;i<7;i++){const l=new THREE.Mesh(new THREE.SphereGeometry(.16,16,12),mat(0x4d8f70,.9));l.scale.set(.55,1.2,.35);l.position.set((Math.random()-.5)*.35,.45+Math.random()*.5,(Math.random()-.5)*.3);g.add(l)}room.add(g)}
const her=new THREE.Group();her.position.set(.15,-.15,.65);scene.add(her);
const skin=mat(0xffe8d9,.68),hairM=mat(0xe8ecff,.58),dark=mat(0x141a36,.45,.12),white=mat(0xf7f9ff,.55),cyan=em(0x68eeff,.55),iris=em(0x64dfff,.95);
const head=new THREE.Mesh(new THREE.SphereGeometry(.74,48,36),skin);head.scale.set(1,.94,.93);head.position.y=.92;her.add(head);
const bh=new THREE.Mesh(new THREE.SphereGeometry(.86,56,42),hairM);bh.scale.set(1.05,.98,.67);bh.position.set(0,1.01,-.20);her.add(bh);
const cr=new THREE.Mesh(new THREE.SphereGeometry(.78,48,36,0,Math.PI*2,0,Math.PI*.56),hairM);cr.scale.set(1.02,1.02,.70);cr.rotation.x=.10;cr.position.set(0,1.20,.02);her.add(cr);
const irises=[];
for(const x of[-.26,.26]){const w=new THREE.Mesh(new THREE.SphereGeometry(.125,24,20),white);w.scale.set(1,1.28,.48);w.position.set(x,.96,.66);her.add(w);const e=new THREE.Mesh(new THREE.SphereGeometry(.072,20,16),iris);e.scale.set(.9,1.18,.42);e.position.set(x,.96,.75);her.add(e);irises.push(e)}
const torso=new THREE.Mesh(new THREE.SphereGeometry(.52,36,28),dark);torso.scale.set(.9,1.02,.72);torso.position.y=.05;her.add(torso);
const chest=new THREE.Mesh(new THREE.OctahedronGeometry(.10),cyan);chest.position.set(0,.13,.43);chest.rotation.z=Math.PI/4;her.add(chest);
for(const s of[-1,1]){const a=new THREE.Mesh(new THREE.CapsuleGeometry(.13,.48,10,18),white);a.position.set(s*.47,.08,.03);a.rotation.z=s*.15;her.add(a);const l=new THREE.Mesh(new THREE.CapsuleGeometry(.14,.43,10,18),dark);l.position.set(s*.22,-.62,.05);her.add(l)}
const dGeo=new THREE.BufferGeometry();const pts=[];for(let i=0;i<160;i++)pts.push((Math.random()-.5)*12,Math.random()*7-1.5,(Math.random()-.5)*12);dGeo.setAttribute('position',new THREE.Float32BufferAttribute(pts,3));scene.add(new THREE.Points(dGeo,new THREE.PointsMaterial({color:0x7eaaff,size:.018,transparent:true,opacity:.55})));
let dragging=false,lx=0,ly=0,yaw=0,pitch=0,zoom=0;
canvas.addEventListener('pointerdown',e=>{dragging=true;lx=e.clientX;ly=e.clientY});
window.addEventListener('pointerup',()=>dragging=false);
window.addEventListener('pointermove',e=>{if(!dragging)return;yaw+=(e.clientX-lx)*.004;pitch=Math.max(-.5,Math.min(.5,pitch+(e.clientY-ly)*.003));lx=e.clientX;ly=e.clientY});
canvas.addEventListener('wheel',e=>{zoom=Math.max(-2.8,Math.min(3.2,zoom+e.deltaY*.004))},{passive:true});
function resize(){const r=canvas.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix()}new ResizeObserver(resize).observe(canvas);resize();
let t=0;
function animate(){requestAnimationFrame(animate);t+=.016;her.position.y=-.15+Math.sin(t*1.8)*.018;head.scale.y=.94+Math.sin(t*1.8)*.008;const blink=Math.sin(t*.72)>0.992?.13:1;irises.forEach(e=>e.scale.y=blink);camera.position.x=Math.sin(yaw)*(9+zoom);camera.position.z=Math.cos(yaw)*(9+zoom);camera.position.y=4.2+pitch*3;camera.lookAt(0,.3,0);renderer.render(scene,camera)}
animate();
const speech=document.getElementById('speech');
document.getElementById('send').onclick=async()=>{const v=document.getElementById('chat').value.trim();if(!v)return;speech.textContent='ちょっと考えさせて…';document.getElementById('chat').value='';try{const r=await fetch('/api/room/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:v,session:'hermes-room'})});const d=await r.json();speech.textContent=d.reply||('…ごめん、返事できなかった。（'+(d.error||'空の返答')+'）')}catch(e){speech.textContent='…ごめん、今つながらないみたい。（'+e.message+'）'}};
document.getElementById('chat').addEventListener('keydown',e=>{if(e.key==='Enter')document.getElementById('send').click()});
</script>
</body>
</html>"""


class RoomHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/room/chat":
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            text = data.get("text", "")
            if not text:
                self._json({"ok": False, "error": "empty"})
                return
            try:
                reply = hermes_chat(text)
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
                return
            self._json({"ok": True, "reply": reply})
        elif self.path == "/api/room/debug":
            """脳の診断: hermes CLI の場所・状態・実行テスト"""
            info = {
                "cli_path": HERMES_CLI,
                "cli_exists": os.path.isfile(HERMES_CLI) and os.access(HERMES_CLI, os.X_OK),
                "profile": HERMES_PROFILE,
                "profile_exists": os.path.isdir(os.path.expanduser(f"~/.hermes/profiles/{HERMES_PROFILE}")),
                "hermes_dir": os.path.isdir(os.path.expanduser("~/.hermes")),
            }
            try:
                version_out = subprocess.run([HERMES_CLI, "--version"], capture_output=True, text=True, timeout=15)
                info["version"] = (version_out.stdout or version_out.stderr or "").strip()[:200]
            except Exception as e:
                info["version"] = f"error: {e}"
            self._json({"ok": True, **info})
        else:
            self._json({"ok": False, "error": "not found"}, 404)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


# index.html を動的に配信 (ファイルがなくても内蔵HTMLで動く)
class SmartRoomHandler(RoomHandler):
    def do_GET(self):
        if self.path in ("/three.module.js", "/static/three.module.js"):
            three_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "three.module.js")
            if os.path.exists(three_path):
                with open(three_path, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/javascript")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        if self.path in ("/", "/index.html", "/hermes-room/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(_ROOM_HTML)))
            self.end_headers()
            self.wfile.write(_ROOM_HTML.encode("utf-8"))
        else:
            super().do_GET()


# ============================================================
# v3 Voice 部屋 (rei-v3: 全身アバター・家・🎙音声入力・☎通話モード)
# server/rei-v3/ を静的配信する。/api/room/chat は共通のHermes脳。
# ============================================================
_V3_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rei-v3")
_MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml",
    ".woff2": "font/woff2", ".ico": "image/x-icon",
}


class V3RoomHandler(SmartRoomHandler):
    """v3 Voice 部屋を配信。/ → rei-v3/index.html"""

    def do_GET(self):
        # heartbeat: Companion (このプロセス) が生きてて、脳CLIが見つかるか
        if self.path == "/api/room/health":
            self._json({
                "ok": True,
                "companion": "CONNECTED",
                "resident_id": "hermes",
                "home_anchor": "sister-imac",
                "cli_path": HERMES_CLI,
                "cli_exists": os.path.isfile(HERMES_CLI) and os.access(HERMES_CLI, os.X_OK),
                "ts": int(time.time())
            })
            return
        # /styles.css, /app.js, /bridge.js, /resident.json → rei-v3/ 配信
        # (ルート配信時に相対パス ./xxx がルート直下を指すため)
        root_rel = self.path.split("?")[0].lstrip("/")
        if root_rel in ("styles.css", "app.js", "bridge.js", "resident.json", "README.md"):
            full = os.path.join(_V3_DIR, root_rel)
            if os.path.isfile(full):
                ext = os.path.splitext(full)[1].lower()
                with open(full, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", _MIME.get(ext, "application/octet-stream"))
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        # /vendor/... → rei-v3/vendor/... (importmap がルート直下を指すため)
        if root_rel.startswith("vendor/"):
            full = os.path.realpath(os.path.join(_V3_DIR, root_rel))
            if full.startswith(os.path.realpath(_V3_DIR)) and os.path.isfile(full):
                ext = os.path.splitext(full)[1].lower()
                with open(full, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", _MIME.get(ext, "application/octet-stream"))
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        # / と /v3/ → rei-v3/index.html
        if self.path in ("/", "/index.html", "/hermes-room/", "/v3/"):
            index_path = os.path.join(_V3_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            # v3 が無ければ旧内蔵部屋にフォールバック
        # /v3/xxx → rei-v3/xxx (静的ファイル)
        if self.path.startswith("/v3/"):
            rel = self.path[len("/v3/"):].split("?")[0]
            full = os.path.realpath(os.path.join(_V3_DIR, rel))
            if full.startswith(os.path.realpath(_V3_DIR)) and os.path.isfile(full):
                ext = os.path.splitext(full)[1].lower()
                with open(full, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", _MIME.get(ext, "application/octet-stream"))
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self._json({"ok": False, "error": "not found"}, 404)
            return
        # それ以外は親に任せる (/api/room/chat など)
        super().do_GET()


if __name__ == "__main__":
    import sys
    port = int(os.environ.get("HERMES_ROOM_PORT", "5199"))
    print(f"⚕ HERMES ROOM SERVER: http://127.0.0.1:{port}")
    print(f"   部屋: v3 Voice (全身アバター・家・🎙音声・☎通話)")
    print(f"   脳: Ollama Cloud (deepseek-v4-flash)")
    print(f"   プロファイル: {HERMES_PROFILE}")
    print(f"   使い方: ブラウザが自動で開きます。チャットに話しかけてね！")
    print("")
    # index.html をファイルとしても保存 (オフライン用)
    room_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    if not os.path.exists(room_path):
        with open(room_path, "w", encoding="utf-8") as f:
            f.write(_ROOM_HTML)
        print(f"   index.html 生成完了: {room_path}")
    threading.Timer(2, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    socketserver.TCPServer.allow_reuse_address = True
    # Threading: チャット処理中 (hermes CLI 呼び出し) でもページ配信がブロックされない
    with socketserver.ThreadingTCPServer(("127.0.0.1", port), V3RoomHandler) as httpd:
        httpd.serve_forever()