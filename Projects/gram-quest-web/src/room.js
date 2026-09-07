import * as THREE from 'three'
import {SVGRenderer} from 'three/addons/renderers/SVGRenderer.js'
import {OrbitControls} from 'three/addons/controls/OrbitControls.js'
import {createGramAvatar} from './gramAvatar.js'
import {createRoomSet} from './roomSet.js'
import './room.css'

const app=document.getElementById('app')
app.innerHTML=`<div class="room-shell"><header><div><span class="eyebrow">GRAM'S LITTLE HOME</span><h1>グラムの部屋 <span>✦</span></h1></div><button id="goOut">外出する ↗</button></header><div class="room-stage" id="roomStage"><div class="room-caption"><span id="connection">接続を確認中</span><span id="activity">おかえり、お兄ちゃま。</span></div><div class="room-view"><button id="wideView">部屋全体</button><button id="closeView">グラムに近づく</button></div><div id="renderError" role="alert" hidden></div></div><div class="room-bottom"><div class="room-info"><span>💎 <b id="level">—</b></span><span>記憶 <b id="memories">—</b></span><span>シナプス <b id="synapses">—</b></span><span id="hp">HP —</span></div><div class="room-interactions"><div><span class="eyebrow">思い出に触れる</span><div id="furnitureButtons" class="button-row"></div></div><div class="button-row"><button id="walk">歩いてみて</button><button id="draw">刀を見せて</button></div><div class="button-row"><span class="eyebrow">グラムに触れる</span></div><div class="button-row"><button data-act="love" style="border-color:#f472b6">💗 だいすき</button><button data-act="cheer" style="border-color:#ffd54a">✨ Yes!</button><button data-act="think">🤔 考える</button><button data-act="snack">🍪 おやつ</button><button data-act="sleep">😴 ねる</button></div><div class="button-row"><button id="callBtn" style="border-color:#f472b6;color:#f472b6">📞 通話を始める</button></div></div><div class="conversation"><div id="talk" role="status" aria-live="polite">グラム：おかえり、お兄ちゃま。今日はどんな一日だった？</div><form id="chatForm"><label class="sr-only" for="message">グラムに話しかける</label><input id="message" placeholder="グラムに話しかける…" maxlength="500" autocomplete="off"><button id="send">話しかける</button></form><small id="memorySource">家具を選ぶと、その思い出をグラムが紹介します。</small><div id="homeOs" style="margin-top:8px;padding:6px 10px;border:1px solid #2a4a6a;border-radius:8px;font-size:10px;color:#8ab8d8"><b style="color:#f472b6">🏠 HOME MODE</b> <small>勝手に開発しない。提案だけする。</small></div></div><footer><span>ドラッグで回転 · ホイールでズーム · 家具をクリック</span><span id="motionStatus">立体アバター · 待機</span></footer></div></div>`
const $=id=>document.getElementById(id)
const demo=new URLSearchParams(location.search).has('demo')
const API_BASE=(()=>{const h=location.hostname
 // ローカル開発は same-origin (vite proxy) でOK
 if(h==='localhost'||h==='127.0.0.1') return ''
 // Vercel など静的ホストは GALACTICA サーバ (トンネル) へ接続する
 // トンネルURLは変わりうるので、URLパラメータ > localStorage > 既知トンネル の順で解決
 const fromQuery=new URLSearchParams(location.search).get('api')
 const fromLS=localStorage.getItem('galactica_api')
 return fromQuery||fromLS||'https://conventions-signs-grade-manitoba.trycloudflare.com'})()
// Optional integration contract; no room-memory endpoint is assumed to exist.
const ROOM_MEMORY_URL=import.meta.env.VITE_ROOM_MEMORY_URL || ''
let roomMemories={},worldOnline=false,bioOnline=false,worldLoc=null,worldBusy=false,disposed=false
let timers=[],target=null,waypoints=[],manualUntil=0,doorTimer=null
async function apiLong(path,body){const r=await fetch(API_BASE+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(90000)});if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json()}
function say(text,source='部屋の紹介文'){$('talk').textContent='グラム：'+text;$('memorySource').textContent=source}
async function api(path,body){const r=await fetch(API_BASE+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(4500)});if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json()}
function status(){$('connection').textContent=($('connection').dataset.software?'簡易3D表示 · ':'')+(demo?'お試しの部屋':`記憶 ${bioOnline?'接続':'未接続'} · 世界 ${worldOnline?'接続':'未接続'}`)}
try{
 let renderer,software=false;try{renderer=new THREE.WebGLRenderer({antialias:true})}catch{renderer=new SVGRenderer();renderer.setQuality('low');renderer.shadowMap={};renderer.dispose=()=>{};software=true}renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.setClearColor(0x161323);renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25
 $('roomStage').prepend(renderer.domElement);renderer.domElement.setAttribute('aria-label','ピンクのツインテールと青い衣装の立体グラム。ベッド、本棚、思い出の額、植物、天窓、暖炉、扉のある部屋。')
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(38,1,.1,100)
 camera.position.set(6.7,6.1,10.5)
 const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,1.0,-.2);controls.enableDamping=true;controls.enablePan=false;controls.minDistance=4;controls.maxDistance=21;controls.minPolarAngle=.2;controls.maxPolarAngle=1.48
 scene.add(new THREE.HemisphereLight(0xf3d9ff,0x697294,2.3))
 const key=new THREE.DirectionalLight(0xffe6d0,4);key.position.set(2.5,7.5,5);key.castShadow=true;key.shadow.mapSize.set(1024,1024);Object.assign(key.shadow.camera,{left:-6,right:6,top:6,bottom:-6,near:.1,far:25});key.shadow.bias=-.0004;key.shadow.normalBias=.025;scene.add(key)
 const rim=new THREE.PointLight(0xc281ff,12,12);rim.position.set(-3,3,-2);scene.add(rim)
 const room=createRoomSet();if(software){key.intensity=1.05;rim.intensity=.5;room.group.traverse(o=>{if(o.material?.map)o.visible=false;if(o.isPointLight)o.intensity=.5;if(o.isMesh&&o.parent===room.group)o.renderOrder=-10;});const shadow=new THREE.Mesh(new THREE.CircleGeometry(.58,16),new THREE.MeshBasicMaterial({color:0x302236,transparent:true,opacity:.35}));shadow.rotation.x=-Math.PI/2;shadow.position.set(.15,.08,.8);scene.add(shadow);$('connection').dataset.software='true';}scene.add(room.group)
 const avatar=await createGramAvatar();if(software){const softMaterials=new Map();avatar.group.traverse(o=>{if(o.isMesh&&o.material?.isMeshStandardMaterial){const old=o.material;if(!softMaterials.has(old))softMaterials.set(old,new THREE.MeshBasicMaterial({color:old.color}));o.material=softMaterials.get(old)}})}avatar.group.position.set(.15,.07,.8);scene.add(avatar.group)
 const ray=new THREE.Raycaster(),pointer=new THREE.Vector2();let pointerStart=null
 const floor=new THREE.Plane(new THREE.Vector3(0,1,0),0)
 const spots={bed:[-1.95,-.8],bookshelf:[2.65,-1.65],memory:[-.35,-1.8],plant:[2.7,1.4],skylight:[-1.7,-1.7],door:[3.4,-.7],fireplace:[1.1,-1.55]}
 const worldSpots={market:[0,.6],orchard:[2.8,1.4],guild:[2.7,-1.6],port:[3.25,-.6],tavern:[1.1,-1.55],gate:[3.25,-.6],home_gram:[-1.95,-.8],home_noah:[-.3,-1.8],home_synchro:[-1.65,-1.6],dock_ark:[2.6,-1.6]}
 function walkTo(x,z,manual=true){if(manual)manualUntil=performance.now()+15000;waypoints=[new THREE.Vector3(0,.07,.5),new THREE.Vector3(x,.07,z)];target=waypoints.shift()}
 async function selectItem(item){const {id,text,name}=item.userData;const p=spots[id];walkTo(...p);say(roomMemories[id]?.text||text,roomMemories[id]?'部屋の記憶':'部屋の紹介文');$('activity').textContent=name;if(id==='door')room.setDoor(true);if(id==='memory')avatar.setEmotion({valence:.8,arousal:.4})}
 for(const item of room.interactive){const b=document.createElement('button');b.type='button';b.textContent=item.userData.name;b.onclick=()=>selectItem(item);$('furnitureButtons').append(b)}
 renderer.domElement.addEventListener('pointerdown',e=>pointerStart=[e.clientX,e.clientY])
 renderer.domElement.addEventListener('pointerup',e=>{if(!pointerStart||Math.hypot(e.clientX-pointerStart[0],e.clientY-pointerStart[1])>7)return;const rect=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);ray.setFromCamera(pointer,camera);const hit=ray.intersectObjects(room.interactive,true)[0];if(hit){let o=hit.object;while(o&&!o.userData.id)o=o.parent;if(o)selectItem(o)}else{const p=new THREE.Vector3();if(ray.ray.intersectPlane(floor,p)&&Math.abs(p.x)<3.25&&p.z>-.8&&p.z<2.8)walkTo(p.x,p.z)}})
 $('walk').onclick=()=>{walkTo(avatar.group.position.x>0?-1.5:1.8,1.5);say('うん、少し歩いてみるね。髪も刀も、一緒に揺れるよ。')}
 $('draw').onclick=()=>{avatar.drawSword();say('わたくしの刀、見ててね。えいっ！')}
 $('wideView').onclick=()=>{camera.position.set(6.7,6.1,10.5);controls.target.set(0,1,-.2)}
 $('closeView').onclick=()=>{const p=avatar.group.position;camera.position.set(p.x+1.8,2.9,p.z+4.5);controls.target.set(p.x,1.3,p.z)}
 $('goOut').onclick=()=>{if(doorTimer)return;room.setDoor(true);walkTo(...spots.door);say('行ってきます、お兄ちゃま。外の世界で会おうね。');$('goOut').disabled=true;doorTimer=setTimeout(()=>{if(!disposed)location.assign('./index.html?view=world')},1700)}
 // ★ グラムの声で再生 (AivisSpeech)
async function speakGram(text){try{const r=await api('/api/room/speak',{text});if(r.audio_wav_b64){const wav=base64ToBlob(r.audio_wav_b64);const url=URL.createObjectURL(wav);const audio=new Audio(url);audio.volume=.9;await audio.play().catch(()=>{});URL.revokeObjectURL(url)}}catch(e){/*音声失敗は無視、テキストだけ*/}
}
function base64ToBlob(b64){const bin=atob(b64);const arr=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)arr[i]=bin.charCodeAt(i);return new Blob([arr],{type:'audio/wav'})}
// ★ チャット: Hermes脳 (本物のグラム) + 音声応答
$('chatForm').onsubmit=async e=>{e.preventDefault();const text=$('message').value.trim();if(!text)return;$('send').disabled=true;$('message').value='';say('ちょっと考えさせて…','考え中');try{if(demo)throw new Error('demo');const r=await apiLong('/api/room/chat',{text,session:'room'});say(r.reply||'…ごめん、うまく言葉にできなかった。','Hermes脳（本物のグラム）');if(r.audio_wav_b64){const bin=atob(r.audio_wav_b64);const arr=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)arr[i]=bin.charCodeAt(i);const url=URL.createObjectURL(new Blob([arr],{type:'audio/wav'}));const audio=new Audio(url);audio.volume=.9;await audio.play().catch(()=>{});URL.revokeObjectURL(url)}}catch(e){say(demo?'デモモードだからHermesには繋がってないよ。':'…ごめん、今つながらないみたい。',e.message||'接続エラー')}finally{$('send').disabled=false}}
 async function pollBio(){if(disposed)return;try{if(demo)throw new Error('demo');const b=await api('/api/bio/state');bioOnline=true;$('level').textContent='Lv.'+b.level;$('memories').textContent=Number(b.hippocampusTotal).toLocaleString()+'件';$('synapses').textContent=Number(b.synapses).toLocaleString();$('hp').textContent=`HP ${b.hp}/${b.maxHp}`;avatar.setEmotion(b)}catch{bioOnline=false}status();if(!disposed)timers[0]=setTimeout(pollBio,10000)}
 async function pollWorld(){if(disposed)return;try{if(demo)throw new Error('demo');const w=await api('/api/world/state');const gram=w.residents?.gram;if(!gram)throw new Error('gram missing');worldOnline=true;worldBusy=!!gram.busy;if(performance.now()>manualUntil){if(gram.loc!==worldLoc){worldLoc=gram.loc;const p=worldSpots[gram.loc]||[0,.6];walkTo(...p,false)}$('activity').textContent=`外のグラム：${w.locations?.[gram.loc]?.name||gram.loc} · ${gram.busy?'移動中':'待機中'}`}}catch{worldOnline=false;worldBusy=false}status();if(!disposed)timers[1]=setTimeout(pollWorld,2000)}
 timers[2]=setTimeout(pollHome,8000)
async function pollHome(){if(disposed||demo)return;try{const r=await api('/api/home/mode');const el=$('homeOs');if(el)el.innerHTML=`<b style="color:#f472b6">🏠 ${r.mode} MODE</b> <small>${r.desc}</small>`}catch{}}
 // ★ れい式 アクションボタン: グラムにリアクションさせる
const actionLines={love:['だいすき〜💗'],cheer:['うん！うん！✨'],think:['うーん……構造から考えてみるね。'],snack:['おやつの時間だよ。半分こする？'],sleep:['むにゃ……ちょっとだけ、おやすみ。']}
document.querySelectorAll('[data-act]').forEach(b=>b.addEventListener('click',()=>{
 const a=b.dataset.act
 avatar.setAction?.(a)
 if(actionLines[a]){const el=$('talk');el.textContent=`グラム：${actionLines[a][0]}`;speakGram(actionLines[a][0])}
}))
 // ★ 通話モード: マイク録音→STT→グラム応答→音声再生
let callActive=false,mediaRecorder=null,audioChunks=[]
$('callBtn').onclick=async()=>{
 if(!callActive){
  try{
   const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}})
   mediaRecorder=new MediaRecorder(stream,{mimeType:MediaRecorder.isTypeSupported('audio/webm;codecs=opus')?'audio/webm;codecs=opus':'audio/webm'})
   audioChunks=[]
   mediaRecorder.ondataavailable=e=>{if(e.data.size)audioChunks.push(e.data)}
   mediaRecorder.onstop=async()=>{
    stream.getTracks().forEach(t=>t.stop())
    const blob=new Blob(audioChunks,{type:'audio/webm'})
    const b64=await new Promise(res=>{const r=new FileReader();r.onload=()=>res(r.result.split(',')[1]);r.readAsDataURL(blob)})
    say('聞いてるよ…','音声をテキストに変換中')
    try{
     const r=await apiLong('/api/room/talk',{audio_b64:b64,session:'room'})
     if(r.heard)say(`「${r.heard}」って言ったね。`,'聞き取り結果')
     if(r.reply)setTimeout(()=>say(r.reply,'グラムの応答'),400)
     if(r.audio_wav_b64){const bin=atob(r.audio_wav_b64);const arr=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)arr[i]=bin.charCodeAt(i);const url=URL.createObjectURL(new Blob([arr],{type:'audio/wav'}));const audio=new Audio(url);audio.volume=.9;await audio.play().catch(()=>{});URL.revokeObjectURL(url)}
    }catch(e){say('…ごめん、声が届かなかったみたい。もう一度話してくれる？','通話エラー')}
   }
   mediaRecorder.start()
   callActive=true
   $('callBtn').textContent='⏹ 通話を終える'
   $('callBtn').style.borderColor='#f87171';$('callBtn').style.color='#f87171'
   say('…聞いてるよ、お兄ちゃま。話して。','📞 通話モード開始')
  }catch(e){say('マイクに接続できなかった…。権限を確認してね。','マイクエラー')}
 }else{
  if(mediaRecorder&&mediaRecorder.state!=='inactive')mediaRecorder.stop()
  callActive=false
  $('callBtn').textContent='📞 通話を始める'
  $('callBtn').style.borderColor='#f472b6';$('callBtn').style.color='#f472b6'
 }
}
if(ROOM_MEMORY_URL&&!demo){fetch(ROOM_MEMORY_URL,{signal:AbortSignal.timeout(4500)}).then(r=>{if(!r.ok)throw new Error();return r.json()}).then(d=>{roomMemories=d.memories||d}).catch(()=>{})}
 pollBio();pollWorld();pollHome()
 function resize(){const el=$('roomStage');renderer.setSize(el.clientWidth,el.clientHeight,false);camera.aspect=el.clientWidth/el.clientHeight;camera.fov=el.clientWidth<640?58:38;camera.updateProjectionMatrix()}
 const observer=new ResizeObserver(resize);observer.observe($('roomStage'));resize();$('boot')?.remove()
 let last=performance.now(),t=0,frames=0;function frame(now){if(disposed)return;const dt=Math.min(.05,(now-last)/1000);last=now;t+=dt;let walking=false
 if(target){const delta=target.clone().sub(avatar.group.position),d=delta.length();if(d<.04){target=waypoints.shift()||null}else{walking=true;avatar.group.position.addScaledVector(delta.normalize(),Math.min(d,dt*1.3));const angle=Math.atan2(delta.x,delta.z);avatar.group.rotation.y+=Math.atan2(Math.sin(angle-avatar.group.rotation.y),Math.cos(angle-avatar.group.rotation.y))*Math.min(1,dt*8)}}
 avatar.setWalking(walking||(worldOnline&&worldBusy&&performance.now()>manualUntil));avatar.update(t);room.update(t,dt);controls.update();renderer.render(scene,camera)
 if(++frames%30===0){$('motionStatus').textContent=`立体アバター · ${walking?'歩行':'待機'}`;renderer.domElement.dataset.frames=String(frames);renderer.domElement.dataset.avatarX=avatar.group.position.x.toFixed(3);renderer.domElement.dataset.avatarZ=avatar.group.position.z.toFixed(3)}requestAnimationFrame(frame)}requestAnimationFrame(frame)
 addEventListener('pagehide',()=>{disposed=true;timers.forEach(clearTimeout);clearTimeout(doorTimer);observer.disconnect();controls.dispose();avatar.dispose();room.dispose();renderer.dispose()},{once:true})
}catch(e){$('renderError').hidden=false;$('renderError').textContent='3Dを起動できませんでした：'+e.message;$('boot')?.remove();console.error(e)}
