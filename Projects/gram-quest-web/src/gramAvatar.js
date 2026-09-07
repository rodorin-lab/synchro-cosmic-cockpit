import * as THREE from 'three'
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js'

// Smooth, articulated interpretation of the supplied pixel character.
// No portrait planes, image textures or camera-facing character sprites.
export async function createGramAvatar(opts = {}) {
  const group = new THREE.Group(); group.name = 'GramAvatar3D'
  const rig = new THREE.Group(); group.add(rig)
  const materials = new Map(), geometries = new Map()
  const material = color => { if (!materials.has(color)) materials.set(color, new THREE.MeshStandardMaterial({color, roughness:.46, metalness:.03, flatShading:false})); return materials.get(color) }
  const geo = (kind, args) => { const key=kind+args.join(','); if(!geometries.has(key))geometries.set(key,new THREE[kind](...args));return geometries.get(key) }
  function part(parent, kind, args, color, x=0,y=0,z=0) {const m=new THREE.Mesh(geo(kind,args),material(color));m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m}
  const box=(p,w,h,d,c,x=0,y=0,z=0)=>{
    const radius=Math.min(w,h,d)*.38,key=`rounded:${w},${h},${d}`
    if(!geometries.has(key))geometries.set(key,new RoundedBoxGeometry(w,h,d,3,radius))
    const m=new THREE.Mesh(geometries.get(key),material(c));m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;p.add(m);return m
  }
  // Continuous curved locks, smoothly tapered from root to tip.
  function lock(p,points,radius,color){
    const curve=new THREE.CatmullRomCurve3(points.map(v=>new THREE.Vector3(...v)))
    const g=new THREE.TubeGeometry(curve,28,1,12,false),a=g.attributes.position
    for(let i=0;i<=28;i++){const t=i/28,center=curve.getPointAt(t),r=radius*(.96-.93*Math.pow(t,1.7));
      for(let j=0;j<=12;j++){const k=i*13+j;a.setXYZ(k,center.x+(a.getX(k)-center.x)*r,center.y+(a.getY(k)-center.y)*r,center.z+(a.getZ(k)-center.z)*r)}}
    g.computeVertexNormals();geometries.set('lock:'+geometries.size,g);const m=new THREE.Mesh(g,material(color));m.castShadow=true;m.receiveShadow=true;p.add(m);return m
  }
  const ball=(p,r,c,x=0,y=0,z=0)=>part(p,'SphereGeometry',[r,32,20],c,x,y,z)
  function joint(parent,x,y,z,name){const j=new THREE.Group();j.name=name;j.position.set(x,y,z);parent.add(j);return j}
  const C={skin:0xffdfc7,hair:0xee63ac,light:0xffa1d1,dark:0x922d71,navy:0x25385b,blue:0x35a2d0,white:0xe7f4ff,gold:0xd9a24e,brown:0x713e39}
  const body=joint(rig,0,.88,0,'torso')
  part(body,'CylinderGeometry',[.23,.30,.46,32],C.navy,0,.1)
  box(body,.37,.23,.055,C.blue,0,.12,.235)
  for(let y=0;y<3;y++)for(let x=0;x<5;x++)ball(body,.022,0xaebecd,(x-2)*.055,.07+y*.05,.278)
  box(body,.52,.075,.40,C.brown,0,-.10);box(body,.11,.09,.055,C.gold,.025,-.1,.225)
  box(body,.34,.055,.08,C.white,0,.325,.17).rotation.z=-.18
  box(body,.09,.23,.06,C.light,0,.23,.26).rotation.z=.15
  for(let layer=0;layer<3;layer++){
    const radius=.30+layer*.045,y=-.20-layer*.07
    const profile=[new THREE.Vector2(radius*.83,y+.06),new THREE.Vector2(radius*.94,y+.015),new THREE.Vector2(radius,y-.055),new THREE.Vector2(radius*.98,y-.07)]
    const g=new THREE.LatheGeometry(profile,64),a=g.attributes.position
    for(let i=0;i<a.count;i++){const angle=Math.atan2(a.getX(i),a.getZ(i)),f=1+.025*Math.cos(angle*12);a.setX(i,a.getX(i)*f);a.setZ(i,a.getZ(i)*f)}
    g.computeVertexNormals();geometries.set('skirt'+layer,g);const skirt=new THREE.Mesh(g,material(layer===2?C.white:C.blue));skirt.castShadow=true;skirt.receiveShadow=true;body.add(skirt)
  }
  const head=joint(rig,0,1.67,0,'head')
  const face=ball(head,.46,C.skin,0,0,.025);face.scale.set(1,1.05,.88)
  const haircap=part(head,'SphereGeometry',[.485,48,28,0,Math.PI*2,0,Math.PI*.62],C.hair,0,.03,-.055)
  for(let i=0;i<7;i++){
    const x=(i-3)*.107,endY=.02+Math.abs(i-3)*.035
    lock(head,[[x*.72,.43,.23],[x,.30,.39],[x+.035,.16,.435],[x+.055,endY,.39]],.095,i%3===0?C.light:C.hair)
  }
  for(const side of [-1,1]){
    lock(head,[[side*.37,.28,.06],[side*.44,.05,.16],[side*.44,-.25,.18],[side*.35,-.39,.21]],.115,C.hair)
    const ear=ball(head,.08,C.skin,side*.43,-.1,.06);ear.scale.z=.55
    box(head,.155,.175,.045,0x202440,side*.19,-.06,.410)
    const eye=box(head,.113,.137,.045,0x378bb7,side*.19,-.08,.438);eye.name='eye'
    box(eye,.055,.09,.014,0x1e315d,0,.012,.027);box(eye,.027,.035,.018,0xffffff,-.022,.038,.04);box(eye,.055,.025,.018,0x7aebf3,0,-.045,.04)
    box(head,.16,.025,.06,C.navy,side*.19,.035,.41).rotation.z=side*-.08
    const cheek=ball(head,.055,0xfba1b7,side*.29,-.19,.365);cheek.scale.set(1,.42,.17)
  }
  box(head,.075,.02,.025,0xc96a84,0,-.245,.425)
  const tails=[]
  for(const side of [-1,1]){
    const tail=joint(head,side*.46,.27,-.12,side<0?'leftTwinTail':'rightTwinTail');tails.push(tail)
    const tie=ball(tail,.125,C.gold,0,0,0);tie.scale.set(.65,1,1)
    lock(tail,[[side*.03,.02,0],[side*.23,-.15,-.05],[side*.30,-.48,-.08],[side*.38,-.72,.02],[side*.46,-.68,.1]],.235,C.hair)
    lock(tail,[[side*.06,.07,.10],[side*.25,-.15,.12],[side*.32,-.45,.13],[side*.42,-.69,.08]],.105,C.light)
    for(const s of [-1,1]){const bow=part(tail,'ConeGeometry',[.115,.23,24],C.light,s*.105,.04,.14);bow.rotation.z=s*Math.PI/2;}
    ball(tail,.06,C.dark,0,.04,.17)
  }
  const arms=[],legs=[]
  for(const side of [-1,1]){
    const arm=joint(body,side*.34,.25,0,side<0?'leftArm':'rightArm');arms.push(arm)
    ball(arm,.145,C.brown);box(arm,.20,.07,.24,C.gold,0,.025,.015)
    box(arm,.17,.24,.18,C.navy,0,-.17)
    box(arm,.19,.11,.20,C.blue,0,-.30)
    ball(arm,.10,C.skin,0,-.40,.025)
    const leg=joint(rig,side*.15,.53,0,side<0?'leftLeg':'rightLeg');legs.push(leg)
    box(leg,.15,.28,.17,C.skin,0,-.12)
    box(leg,.19,.25,.22,C.navy,0,-.31,.025)
    box(leg,.22,.06,.23,C.hair,0,-.22,.025)
    box(leg,.20,.09,.31,C.navy,0,-.43,.065)
    box(leg,.21,.035,.32,C.brown,0,-.485,.065)
  }
  const sword=joint(arms[1],0,-.4,.09,'katana');sword.rotation.z=-Math.PI/2
  box(sword,.055,.22,.06,C.brown,0,-.02)
  for(let i=0;i<4;i++)box(sword,.06,.018,.065,C.gold,0,-.1+i*.05)
  box(sword,.17,.035,.12,C.gold,0,.11)
  box(sword,.065,.62,.025,0xd8e9f4,0,.44);box(sword,.016,.62,.03,0xffffff,-.027,.44)
  const tip=part(sword,'ConeGeometry',[.035,.13,12],0xe3f6ff,0,.81);tip.scale.z=.4
  const sheath=box(body,.075,.82,.09,C.brown,-.31,-.11,-.17);sheath.rotation.z=-1.1
  const auraMat=new THREE.MeshBasicMaterial({color:0xdf7ced,transparent:true,opacity:.24,side:THREE.DoubleSide,depthWrite:false})
  const aura=new THREE.Mesh(new THREE.RingGeometry(.48,.53,40),auraMat);aura.rotation.x=-Math.PI/2;aura.position.y=.016;group.add(aura)
  let emotion={valence:0,arousal:.3},walking=false,drawUntil=-1,lastT=0
  const scale=opts.scale??1;group.scale.setScalar(scale)
  function update(t){lastT=t;const wave=Math.sin(t*8),draw=Math.max(0,Math.min(1,(drawUntil-t)*2));rig.position.y=(opts.baseY??0)+.025+Math.sin(t*2)*.012+Math.max(0,emotion.valence)*.065+(walking?Math.abs(wave)*.045:0)
    body.scale.y=1+Math.sin(t*2)*.014;head.rotation.y=Math.sin(t*.6)*.09;head.rotation.z=Math.sin(t*.8)*.025
    const blink=t%4.3<.13?.08:1;head.traverse(o=>{if(o.name==='eye')o.scale.y=blink})
    arms.forEach((a,i)=>{a.rotation.x=walking?Math.sin(t*8+i*Math.PI)*.55:-.10;a.rotation.z=(i?1:-1)*.15});arms[1].rotation.x-=draw*1.4;arms[1].rotation.z+=draw*.7
    legs.forEach((l,i)=>l.rotation.x=walking?Math.sin(t*8+i*Math.PI)*.50:0)
    tails.forEach((p,i)=>{p.rotation.x=Math.sin(t*(walking?8:2)+i)*.12;p.rotation.z=(i?1:-1)*(.10+Math.sin(t*2)*.05)})
    auraMat.color.setHSL(.78+emotion.valence*.1,.75,.65);auraMat.opacity=.15+.08*Math.sin(t*(2+emotion.arousal));
    updateAction(t)
  }
  function setEmotion(e){emotion={valence:THREE.MathUtils.clamp(Number(e.valence)||0,-1,1),arousal:THREE.MathUtils.clamp(Number(e.arousal)||0,0,1)}}
  // ===== れい v2.1 移植: アクションリアクションシステム =====
  let action='idle', actionTime=0, actionDuration=0
  const actionFx = {
    love:    {dur:2.6, aura:.95, jump:true},
    cheer:   {dur:2.2, aura:.9,  jump:true},
    think:   {dur:2.6, aura:.55, tilt:-.08},
    cry:     {dur:2.6, aura:.4,  tilt:.05},
    snack:   {dur:2.4, aura:.7},
    sleep:   {dur:3.6, aura:.3,  blink:.08},
    draw:    {dur:2.2, aura:.8}
  }
  let currentAction=null, actionTime0=0
  function setAction(a){
    const fx=actionFx[a]; if(!fx) return
    currentAction=a; actionTime0=lastT; actionDuration=fx.dur
    if(fx.tilt!==undefined) rig.rotation.z=fx.tilt
  }
  function resetAction(){currentAction=null; rig.rotation.z=0}
  function updateAction(t){
    if(!currentAction) return
    const fx=actionFx[currentAction], dt=t-actionTime0
    if(fx.jump) rig.position.y+=Math.abs(Math.sin(t*6))*.05
    if(fx.blink!==undefined) head.traverse(o=>{if(o.name==='eye')o.scale.y=fx.blink})
    if(dt>fx.dur){resetAction()}
  }
  function dispose(){for(const g of geometries.values())g.dispose();for(const m of materials.values())m.dispose();aura.geometry.dispose();auraMat.dispose()}
  return {group,update,setEmotion,setWalking:w=>walking=!!w,drawSword:()=>drawUntil=lastT+1.5,setAction,dispose,rig,parts:{head,body,arms,legs,tails,sword}}
}
