import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

const app = document.getElementById('app');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x201821);
scene.fog = new THREE.FogExp2(0x241a24, 0.010);

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.30;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
app.appendChild(renderer.domElement);

const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, .08, 120);
camera.position.set(10.4, 6.5, 11.6);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.55, -0.6);
controls.enableDamping = true;
controls.dampingFactor = .065;
controls.enablePan = false;
controls.minDistance = 4.5;
controls.maxDistance = 18;
controls.maxPolarAngle = Math.PI * .49;
controls.minPolarAngle = .42;

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), .20, .45, .88);
bloom.threshold = .82; bloom.strength = .28; bloom.radius = .34;
composer.addPass(bloom);

const C = {
  wall: 0x5a3f49, wall2: 0x473944, floor: 0x8c6654, wood: 0x90684e, woodDark: 0x5d4438,
  cream: 0xfff4e8, paper: 0xeadcc7, metal: 0x5d5c65, blue: 0x91a9cc, plant: 0x6f956f,
  pot: 0xb98572, whiteDog: 0xfff2e5, muzzle: 0xffead5, dark: 0x32221f, pink: 0xff9cae,
  cat: 0xc3b5a9, catWhite: 0xeee5dc
};
const std = (color, rough = .75, metal = 0) => new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: metal });
const phys = (o) => new THREE.MeshPhysicalMaterial(o);
const MAT = {
  wall: std(C.wall, .92), wall2: std(C.wall2, .92), floor: std(C.floor, .94), wood: std(C.wood, .84), woodDark: std(C.woodDark, .86),
  cream: std(C.cream, .95), paper: std(C.paper, .96), metal: std(C.metal, .48, .22), blue: std(C.blue, .68), plant: std(C.plant, .9), pot: std(C.pot, .9),
  dog: phys({ color: C.whiteDog, roughness: .78, sheen: 1, sheenColor: new THREE.Color(0xfff7ef), sheenRoughness: .5 }),
  muzzle: std(C.muzzle, .82), dark: std(C.dark, .52), pink: std(C.pink, .58), black: std(0x232127, .42, .05),
  cat: std(C.cat, 1), catWhite: std(C.catWhite, 1)
};
const root = new THREE.Group(); scene.add(root);
function add(mesh, parent = root) { mesh.castShadow = true; mesh.receiveShadow = true; parent.add(mesh); return mesh; }
function box(s, mat, p, r = [0, 0, 0], parent = root, rad = 0) { const g = rad ? new RoundedBoxGeometry(s[0], s[1], s[2], 5, rad) : new THREE.BoxGeometry(...s); const m = new THREE.Mesh(g, mat); m.position.set(...p); m.rotation.set(...r); return add(m, parent); }
function sph(r, mat, p, scale = [1, 1, 1], parent = root, seg = 32) { const m = new THREE.Mesh(new THREE.SphereGeometry(r, seg, seg), mat); m.position.set(...p); m.scale.set(...scale); return add(m, parent); }
function cyl(rt, rb, h, mat, p, r = [0, 0, 0], parent = root, seg = 24) { const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat); m.position.set(...p); m.rotation.set(...r); return add(m, parent); }
function torus(R, r, mat, p, rot = [0, 0, 0], parent = root, arc = Math.PI * 2) { const m = new THREE.Mesh(new THREE.TorusGeometry(R, r, 12, 44, arc), mat); m.position.set(...p); m.rotation.set(...rot); return add(m, parent); }
function capsule(rad, len, mat, p, rot = [0, 0, 0], parent = root) { const m = new THREE.Mesh(new THREE.CapsuleGeometry(rad, len, 10, 20), mat); m.position.set(...p); m.rotation.set(...rot); return add(m, parent); }
function segment(a, b, r, mat, parent = root) { const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), v = B.clone().sub(A), len = v.length(); const m = new THREE.Mesh(new THREE.CapsuleGeometry(r, Math.max(.01, len - 2 * r), 8, 18), mat); m.position.copy(A).add(B).multiplyScalar(.5); m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), v.normalize()); return add(m, parent); }
function textMat(text, { w = 512, h = 256, bg = 'rgba(0,0,0,0)', color = '#f3eae2', size = 38, serif = false } = {}) { const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d'); x.fillStyle = bg; x.fillRect(0, 0, w, h); x.fillStyle = color; x.textAlign = 'center'; x.textBaseline = 'middle'; x.font = `500 ${size}px ${serif ? 'Georgia' : 'system-ui'}`; const lines = text.split('\n'); lines.forEach((ln, i) => x.fillText(ln, w / 2, h / 2 + (i - (lines.length - 1) / 2) * size * 1.2)); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false }); }
function tube(points, r, mat, parent = root) { const curve = new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p)), false, 'centripetal', .45); return add(new THREE.Mesh(new THREE.TubeGeometry(curve, 28, r, 10, false), mat), parent); }

// ===== ROOM SHELL =====
box([11.8, .18, 7.9], MAT.floor, [0, -.11, -.3]);
box([11.8, 5.3, .18], MAT.wall, [0, 2.52, -4.16]);
box([.18, 5.3, 7.9], MAT.wall2, [-5.9, 2.52, -.3]);
box([.18, 5.3, 1.62], MAT.wall2, [5.9, 2.52, -3.32]);
box([.18, 5.3, 1.26], MAT.wall2, [5.9, 2.52, 3.02]);
box([4.25, .04, 3.05], std(0xc7b4a9, .98), [1.7, .015, -1.45], [], root, .18);
box([3.5, .04, 2.1], std(0x8c7c92, .98), [-1.8, .015, 1.5], [], root, .16);

// ===== WINDOW + CITY =====
const sky = new THREE.Mesh(new THREE.PlaneGeometry(5.9, 4.42), new THREE.ShaderMaterial({ side: THREE.DoubleSide, depthWrite: false, vertexShader: `varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`, fragmentShader: `varying vec2 vUv;void main(){vec3 top=vec3(.05,.07,.16),mid=vec3(.35,.23,.45),low=vec3(.86,.44,.50);vec3 c=mix(low,mid,smoothstep(.0,.42,vUv.y));c=mix(c,top,smoothstep(.42,1.,vUv.y));gl_FragColor=vec4(c,1.);}` }));
sky.position.set(6.18, 2.65, -.15); sky.rotation.y = -Math.PI / 2; root.add(sky);
const glass = new THREE.Mesh(new THREE.PlaneGeometry(5.9, 4.42), new THREE.MeshPhysicalMaterial({ color: 0x7d94b9, transparent: true, opacity: .13, roughness: .06, transmission: .45 })); glass.position.set(5.78, 2.65, -.15); glass.rotation.y = -Math.PI / 2; root.add(glass);
for (const z of [-3.0, 0, 2.7]) box([.09, 4.42, .09], MAT.metal, [5.75, 2.65, z]);
for (const y of [.45, 4.85]) box([.09, .09, 5.9], MAT.metal, [5.75, y, -.15], [0, 0, Math.PI / 2]);
const city = new THREE.Group(); city.position.set(6.42, .08, -.2); root.add(city);
for (let i = 0; i < 92; i++) { const z = -3 + Math.random() * 5.8, h = .32 + Math.random() * 2.3, x = .15 + Math.random() * 1.0; box([.10 + Math.random() * .18, h, .10 + Math.random() * .18], std([0x39475f, 0x29354c, 0x4a415d][i % 3], .76), [x, h / 2, z], [], city, .02); if (i % 2 === 0) sph(.017, new THREE.MeshBasicMaterial({ color: [0xffd39c, 0xa3caff, 0xeab3d6][i % 3] }), [x - .06, h * .68, z + .07], [1, 1, 1], city, 8).castShadow = false; }
for (let i = 0; i < 8; i++) { const m = new THREE.Mesh(new THREE.ConeGeometry(.52 + Math.random() * .6, 1.1 + Math.random() * .9, 4), std(0x302e45, .95)); m.position.set(7.5, -.05, -3.1 + i * .85); m.rotation.y = .75; root.add(m); }

// ===== BOOKSHELF =====
const shelf = new THREE.Group(); shelf.position.set(-3.72, 0, -3.80); root.add(shelf);
box([4.0, 4.38, .47], std(0x684c3d, .88), [0, 2.12, 0], [], shelf, .06);
box([3.62, 4.0, .45], std(0x332831, .95), [0, 2.12, .12], [], shelf, .04);
for (let r = 0; r < 4; r++) { box([3.62, .08, .49], MAT.wood, [0, .58 + r * .92, .16], [], shelf, .02); const strip = box([3.35, .025, .035], new THREE.MeshStandardMaterial({ color: 0xffd2a0, emissive: 0xffaf68, emissiveIntensity: 2.2 }), [0, .66 + r * .92, .43], [], shelf, .01); strip.castShadow = false; }
const bookCols = [0x886a69, 0x6e7991, 0xb99775, 0x71816d, 0x947b9a, 0x526476, 0xb87c6e, 0x6f675f];
for (let r = 0; r < 4; r++) { let x = -1.63; for (let i = 0; i < 16; i++) { const bw = .11 + Math.random() * .12, bh = .45 + Math.random() * .25; if (x + bw > 1.58) break; box([bw, bh, .29], std(bookCols[(i + r * 3) % bookCols.length], .9), [x + bw / 2, .74 + r * .92 + bh / 2 - .34, .38], [], shelf, .012); x += bw + .03; } }
sph(.22, std(0xb8c7c8, .55), [.95, 3.37, .52], [1, 1, 1], shelf); torus(.29, .024, MAT.metal, [.95, 3.37, .52], [0, .3, 0], shelf);
box([.34, .22, .16], MAT.black, [-.95, 2.45, .48], [], shelf, .04); cyl(.09, .09, .05, MAT.metal, [-.95, 2.45, .59], [Math.PI / 2, 0, 0], shelf);
const wallQuote = box([2.42, 1.02, .03], textMat('Better questions\ncreate better futures.', { w: 600, h: 240, size: 46, serif: true }), [-4.28, 3.92, -4.01], [], root, .02); wallQuote.castShadow = false;
const starMap = box([1.34, 1.48, .04], textMat('SAME SKY\nBRIGHTER\nTOMORROWS', { w: 440, h: 520, size: 36 }), [-.95, 3.58, -4.01], [], root, .03); starMap.castShadow = false;

// ===== DESK =====
const desk = new THREE.Group(); desk.position.set(-1.48, 0, .88); desk.rotation.y = -.10; root.add(desk);
box([4.42, .16, 1.56], MAT.wood, [0, 1.06, 0], [], desk, .08);
for (const x of [-1.82, 1.82]) for (const z of [-.56, .56]) box([.12, 1.06, .12], MAT.woodDark, [x, .53, z], [], desk, .035);
cyl(.04, .04, .95, MAT.metal, [-1.25, 1.58, -.42], [], desk); box([1.67, 1.03, .08], MAT.black, [-.75, 2.10, -.45], [0, .08, 0], desk, .06); const screen = box([1.53, .89, .012], textMat('IDEAS / PEOPLE / POSSIBILITIES\n\nBetter questions → better futures', { w: 780, h: 430, size: 31 }), [-.75, 2.10, -.405], [0, .08, 0], desk, .02); screen.castShadow = false;
box([1.05, .05, .72], MAT.metal, [.78, 1.17, .10], [0, .06, 0], desk, .035); box([1.05, .64, .05], MAT.metal, [.78, 1.49, -.20], [-.90, .06, 0], desk, .035); const ls = box([.96, .55, .012], textMat('THINKING\nATELIER', { w: 500, h: 300, size: 44 }), [.78, 1.48, -.17], [-.90, .06, 0], desk, .02); ls.castShadow = false;
box([1.08, .05, .34], std(0xd8d3cf, .78), [-.55, 1.17, .35], [0, .03, 0], desk, .04); cyl(.14, .13, .23, MAT.cream, [.25, 1.22, .50], [], desk); box([.70, .035, .50], MAT.paper, [1.42, 1.17, .40], [0, -.04, 0], desk, .025);
for (let i = 0; i < 5; i++) box([.08, .012, .08], std([0xe8c9ca, 0xc4d5e9, 0xd7c8e5][i % 3], .9), [1.18 + i * .10, 1.20, .07], [], desk, .01);
const bot = new THREE.Group(); bot.position.set(-1.73, 1.19, .37); desk.add(bot); sph(.16, MAT.cream, [0, .17, 0], [1, 1, 1], bot); box([.23, .17, .18], MAT.black, [0, .17, .13], [], bot, .07); sph(.025, new THREE.MeshBasicMaterial({ color: 0x9fe7ff }), [-.05, .18, .225], [1, 1, 1], bot, 12); sph(.025, new THREE.MeshBasicMaterial({ color: 0x9fe7ff }), [.05, .18, .225], [1, 1, 1], bot, 12); cyl(.11, .11, .18, MAT.cream, [0, -.03, 0], [], bot);
cyl(.12, .10, .20, MAT.pot, [1.82, 1.21, -.42], [], desk); for (let i = 0; i < 7; i++) { const a = i * .9; const leaf = sph(.10, MAT.plant, [1.82 + Math.cos(a) * .15, 1.40 + (i % 3) * .08, -.42 + Math.sin(a) * .12], [.48, 1.4, .25], desk, 18); leaf.rotation.z = a * .45; }

// ===== DAYBED + CAT =====
const day = new THREE.Group(); day.position.set(2.38, 0, -2.80); root.add(day);
box([3.36, .55, 1.56], std(0xb9aca5, .95), [0, .50, 0], [], day, .18); box([3.26, .30, 1.46], std(0xd9d0c9, .97), [0, .86, 0], [], day, .17); box([3.35, 1.10, .25], std(0xa5959d, .96), [0, 1.18, -.64], [], day, .12);
for (let i = 0; i < 4; i++) box([.65, .52, .20], std([0xc7bec5, 0xaeb5ca, 0xd7c5b6, 0x9d9cad][i], .95), [-1.15 + i * .75, 1.22, -.45], [0, 0, .05 * (i - 1)], day, .14);
for (let i = 0; i < 3; i++) box([1.10, .08, .78], std([0x9e91a0, 0xc6b5aa, 0x7789a2][i], .97), [.55 + i * .30, 1.08, .20 + i * .09], [0, .05 * i, .08 * i], day, .07);
const cat = new THREE.Group(); cat.position.set(-.72, 1.14, .18); day.add(cat); sph(.36, MAT.cat, [0, 0, 0], [1.45, .60, .80], cat); sph(.20, MAT.catWhite, [.47, .08, .02], [1, .9, 1], cat); for (const z of [-.10, .10]) { const e = new THREE.Mesh(new THREE.ConeGeometry(.07, .15, 3), MAT.cat); e.position.set(.48, .24, z); e.rotation.z = -.04; cat.add(e); } const catTail = torus(.32, .055, MAT.cat, [-.28, .05, 0], [Math.PI / 2, .12, .15], cat, Math.PI * 1.35);
cyl(.42, .40, .08, MAT.wood, [4.15, .64, -2.70]); cyl(.06, .06, .55, MAT.metal, [4.15, .35, -2.70]); cyl(.19, .19, .03, MAT.metal, [4.15, .06, -2.70]); sph(.14, new THREE.MeshStandardMaterial({ color: 0xffdfb8, emissive: 0xffbf76, emissiveIntensity: 2.0 }), [4.15, .92, -2.70], [1, 1, 1]);

// ===== PLANTS + FAVORITE THINGS =====
function plant(x, z, s = 1) { const g = new THREE.Group(); g.position.set(x, 0, z); root.add(g); cyl(.18, .14, .28, MAT.pot, [0, .15, 0], [], g); for (let i = 0; i < 10; i++) { const a = i * .73; const leaf = sph(.14, MAT.plant, [Math.cos(a) * .22, .45 + (i % 4) * .11, Math.sin(a) * .22], [.45, 1.45, .24], g, 18); leaf.rotation.z = a * .45; } g.scale.setScalar(s); return g; }
plant(-5.05, 2.75, 1.15); plant(4.95, -3.15, .95); plant(5.10, 2.30, .72); plant(-4.85, -2.00, .78);
for (let j = 0; j < 3; j++) { const g = new THREE.Group(); g.position.set(-5.5, 4.85, -1.0 + j * .65); root.add(g); for (let i = 0; i < 10; i++) { const leaf = sph(.08, MAT.plant, [Math.sin(i * .8) * .07, -i * .25, 0], [.5, 1.25, .22], g, 14); leaf.rotation.z = i * .45; } }
const objects = new THREE.Group(); objects.position.set(4.25, 0, 2.55); root.add(objects); box([1.35, .08, .70], MAT.wood, [0, .75, 0], [], objects, .05); box([.42, .25, .20], MAT.black, [-.35, .92, 0], [], objects, .04); cyl(.10, .10, .05, MAT.metal, [-.35, .92, .12], [Math.PI / 2, 0, 0], objects); sph(.22, std(0xb9c7c8, .55), [.18, 1.00, 0], [1, 1, 1], objects); torus(.29, .022, MAT.metal, [.18, 1.00, 0], [0, .3, 0], objects); cyl(.04, .04, .36, MAT.metal, [.53, .94, 0], [], objects); sph(.10, std(0xd7c7b3, .7), [.53, 1.15, 0], [.8, 1.4, .8], objects);

// ===== REI: CUTE MOCHI DOG =====
const rei = new THREE.Group(); rei.position.set(.45, 0, .35); root.add(rei); rei.userData.isRei = true;
const avatar = new THREE.Group(); rei.add(avatar);
const body = sph(.55, MAT.dog, [0, .78, 0], [.88, 1.02, .82], avatar, 48);
const head = sph(.76, MAT.dog, [0, 1.58, .04], [1.02, .93, .94], avatar, 56);
const muzzle = sph(.30, MAT.muzzle, [0, 1.42, .66], [1.18, .58, .45], avatar, 32);
for (const [x, rz] of [[-.65, .42], [.65, -.42]]) { const ear = sph(.27, MAT.dog, [x, 1.72, .02], [.76, 1.18, .55], avatar, 32); ear.rotation.z = rz; }
// forehead curl: signature from the sticker character
const curl = tube([[-.12, 2.12, .58], [-.12, 2.36, .62], [.08, 2.42, .62], [.22, 2.31, .62], [.08, 2.20, .62]], .038, MAT.dark, avatar);
// face
const eyeParts = [];
for (const x of [-.25, .25]) { const e = sph(.080, MAT.dark, [x, 1.68, .72], [.72, 1.12, .45], avatar, 24); eyeParts.push(e); }
const browL = capsule(.022, .14, MAT.dark, [-.25, 1.88, .71], [0, 0, Math.PI / 2 + .05], avatar); const browR = capsule(.022, .14, MAT.dark, [.25, 1.88, .71], [0, 0, Math.PI / 2 - .05], avatar);
const nose = sph(.095, MAT.dark, [0, 1.48, .84], [1.05, .76, .65], avatar, 24);
function mouthArc(cx) { const pts = []; for (let i = 0; i < 20; i++) { const a = i / 19 * Math.PI; pts.push(new THREE.Vector3(cx + Math.cos(a) * .13, 1.36 - Math.sin(a) * .075, .82)); } return add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: C.dark })), avatar); }
const mouthL = mouthArc(-.11), mouthR = mouthArc(.11);
for (const x of [-.42, .42]) { const c = new THREE.Mesh(new THREE.CircleGeometry(.12, 28), new THREE.MeshBasicMaterial({ color: C.pink, transparent: true, opacity: .40, depthWrite: false })); c.position.set(x, 1.37, .82); avatar.add(c); }
// limbs / paws
const armL = new THREE.Group(); armL.position.set(-.50, .92, .03); avatar.add(armL); capsule(.13, .38, MAT.dog, [0, -.08, 0], [0, 0, .12], armL); sph(.12, MAT.dog, [0, -.37, .03], [1, 1, 1], armL, 24);
const armR = new THREE.Group(); armR.position.set(.50, .92, .03); avatar.add(armR); capsule(.13, .38, MAT.dog, [0, -.08, 0], [0, 0, -.12], armR); sph(.12, MAT.dog, [0, -.37, .03], [1, 1, 1], armR, 24);
for (const x of [-.24, .24]) sph(.20, MAT.dog, [x, .17, .12], [1.0, .70, 1.25], avatar, 28);
const tail = torus(.20, .058, MAT.dog, [.52, .68, -.46], [0, 1.16, .16], avatar, Math.PI * 1.55);
// little paw-print detail on body
for (const [x, y, r] of [[0, .84, .045], [-.055, .90, .025], [.055, .90, .025], [-.075, .84, .022], [.075, .84, .022]]) sph(r, new THREE.MeshBasicMaterial({ color: 0xffc7d0, transparent: true, opacity: .42 }), [x, y, .515], [1, 1, .1], avatar, 12);

// hearts / tears / snack props
const hearts = new THREE.Group(); rei.add(hearts); hearts.visible = false;
function heart(x, y, z, s=.07) { const shape = new THREE.Shape(); shape.moveTo(0, 0); shape.bezierCurveTo(-1, -1, -2, .3, 0, 2); shape.bezierCurveTo(2, .3, 1, -1, 0, 0); const m = new THREE.Mesh(new THREE.ShapeGeometry(shape), new THREE.MeshBasicMaterial({ color: 0xff5576, side: THREE.DoubleSide })); m.scale.setScalar(s); m.position.set(x, y, z); hearts.add(m); }
for (let i = 0; i < 7; i++) heart((Math.random() - .5) * 1.5, 1.4 + Math.random() * 1.2, .45 + Math.random() * .25, .045 + Math.random() * .025);
const tears = new THREE.Group(); rei.add(tears); tears.visible = false; for (const x of [-.25, .25]) { const t = new THREE.Mesh(new THREE.SphereGeometry(.045, 18, 14), new THREE.MeshBasicMaterial({ color: 0x8ed1ff, transparent: true, opacity: .82 })); t.scale.set(.65, 1.55, .45); t.position.set(x, 1.52, .79); tears.add(t); }
const snack = new THREE.Group(); rei.add(snack); snack.visible = false; box([.34, .26, .12], std(0xf3b65d, .78), [.42, .82, .72], [], snack, .04); const cheese = new THREE.Mesh(new THREE.ConeGeometry(.17, .33, 3), std(0xffcb4f, .76)); cheese.rotation.z = Math.PI / 2; cheese.position.set(.62, .93, .73); snack.add(cheese);

// ===== LIGHTING =====
scene.add(new THREE.HemisphereLight(0xc6d5f2, 0x5b3f33, 1.55));
const sun = new THREE.DirectionalLight(0xffe7d2, 3.0); sun.position.set(3.7, 8, 5); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); scene.add(sun);
function light(pos, intensity = 16, distance = 4.8, color = 0xffbd7c) { const l = new THREE.PointLight(color, intensity, distance, 2); l.position.set(...pos); l.castShadow = true; scene.add(l); return l; }
light([-3.6, 3.8, -3.0], 20, 5.2); light([-1.0, 3.2, -2.8], 15, 4.6, 0xffd7a6); light([3.6, 2.9, -2.5], 15, 4.6); light([4.3, 1.3, -2.7], 12, 3.6); light([.5, 2.8, 2.6], 10, 4.2, 0xffe4d4); light([5.1, 3.2, 0], 8, 4.5, 0xa1c1ff);

// dust motes
const dp = []; for (let i = 0; i < 180; i++) dp.push((Math.random() - .5) * 10, Math.random() * 5, (Math.random() - .5) * 7); const dg = new THREE.BufferGeometry(); dg.setAttribute('position', new THREE.Float32BufferAttribute(dp, 3)); const dust = new THREE.Points(dg, new THREE.PointsMaterial({ color: 0xffe4c7, size: .018, transparent: true, opacity: .28 })); root.add(dust);

// ===== NAVIGATION / AVATAR MOVEMENT =====
const focuses = {
  room: { cam: [10.4, 6.5, 11.6], target: [0, 1.55, -.6], dog: [.45, 0, .35], place: 'Thinking Atelier', line: 'ここが私の部屋。ゆっくりしていってね。' },
  rei: { cam: [4.0, 2.8, 4.9], target: [.45, 1.15, .35], dog: [.45, 0, .35], place: 'れいのところ', line: 'おかえり〜♡ ちゃんとここにいるよ。' },
  desk: { cam: [2.4, 3.2, 5.1], target: [-1.45, 1.35, .25], dog: [-.15, 0, 1.55], place: 'Desk', line: 'ここでアイデアを整理するの。面白い問い、持ってきた？' },
  bookshelf: { cam: [1.2, 3.6, 3.1], target: [-3.7, 2.15, -3.72], dog: [-2.35, 0, -2.55], place: 'Bookshelf', line: '分野がバラバラな本を隣同士に置くの、好きなんだ。' },
  daybed: { cam: [6.1, 2.6, 1.1], target: [2.38, 1.0, -2.80], dog: [1.25, 0, -2.05], place: 'Daybed', line: 'ここは解決する場所じゃなくて、話す場所。猫もいるよ。' },
  window: { cam: [3.4, 3.3, .9], target: [5.55, 2.55, -.2], dog: [3.55, 0, -.95], place: 'Window', line: '同じ空の下で、世界はまだ続いてる。' },
  objects: { cam: [6.0, 2.4, 5.0], target: [4.25, 1.0, 2.55], dog: [3.05, 0, 2.10], place: 'Favorite Things', line: '意味のある小物って、思考の足跡みたいで好き。' }
};
let camGoal = null, targetGoal = null, dogGoal = new THREE.Vector3(.45, 0, .35), dogWalking = false;
function speak(text, duration = 6500) { const el = document.getElementById('bubble'); document.getElementById('bubbleText').textContent = text; el.classList.add('show'); clearTimeout(speak.t); speak.t = setTimeout(() => el.classList.remove('show'), duration); }
function focus(name, moveDog = true) { const f = focuses[name]; if (!f) return; camGoal = new THREE.Vector3(...f.cam); targetGoal = new THREE.Vector3(...f.target); if (moveDog) { dogGoal.set(...f.dog); dogWalking = rei.position.distanceTo(dogGoal) > .2; } document.getElementById('placeText').textContent = f.place; speak(f.line); }
document.querySelectorAll('[data-focus]').forEach(b => b.addEventListener('click', () => focus(b.dataset.focus)));

// ===== ACTION STATE MACHINE =====
let action = 'idle', actionTime = 0, actionDuration = 0;
const base = { browL: browL.rotation.z, browR: browR.rotation.z, armL: armL.rotation.z, armR: armR.rotation.z };
const actionLines = {
  love: ['happy', 'だいすき〜♡'], cheer: ['excited', 'Yes! Yes! ✨'], think: ['thinking', 'うーん……構造から考えてみるね。'], cry: ['sad', 'しくしく……でも、そばにいてね。'], snack: ['snack time', 'おやつの時間だよ。半分こする？'], sleep: ['sleepy', 'むにゃ……ちょっとだけ、おやすみ。']
};
function setAction(a, duration = 2.6) { action = a; actionTime = 0; actionDuration = duration; hearts.visible = a === 'love'; tears.visible = a === 'cry'; snack.visible = a === 'snack'; document.getElementById('moodText').textContent = actionLines[a]?.[0] || 'calm'; if (actionLines[a]) speak(actionLines[a][1]); }
document.querySelectorAll('[data-action]').forEach(b => b.addEventListener('click', () => setAction(b.dataset.action, b.dataset.action === 'sleep' ? 3.6 : 2.6)));
function resetExpression() { action = 'idle'; actionTime = 0; actionDuration = 0; hearts.visible = false; tears.visible = false; snack.visible = false; document.getElementById('moodText').textContent = 'calm'; }

// ===== CHAT / VOICE / CALL BRIDGE =====
const chatInput = document.getElementById('chatInput');
const micBtn = document.getElementById('micBtn');
const callBtn = document.getElementById('callBtn');
const callPanel = document.getElementById('callPanel');
const callStatus = document.getElementById('callStatus');
const callTime = document.getElementById('callTime');
const liveTranscript = document.getElementById('liveTranscript');
const audioMeter = document.getElementById('audioMeter');
const muteBtn = document.getElementById('muteBtn');
const endCallBtn = document.getElementById('endCallBtn');

let callActive = false, callMuted = false, callStartedAt = 0, callTimer = null;
let micStream = null, audioContext = null, analyser = null, meterRAF = null;
let recognition = null, recognitionMode = null, recognitionShouldRestart = false;
let ttsSpeaking = false;
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function localReply(text) {
  const clean = String(text || '').trim();
  if (/おはよう|こんにちは|こんばんは|やっほ/.test(clean)) return 'うん、聞いてるよ＾＾ 今日は何を一緒に考える？';
  if (/かわいい|可愛い/.test(clean)) return 'えへへ、ほんと？ じゃあ、もうちょっとここにいて♡';
  if (/疲れ|つかれ/.test(clean)) return '今日は解決しなくてもいいよ。猫のところで少し休もっか。';
  return `うん、聞いてるよ＾＾「${clean}」\nそれ、もう少し一緒に考えてみようか。`;
}

function playReplyVoice(text, audioUrl) {
  if (!callActive) return;
  if (audioUrl) {
    const audio = new Audio(audioUrl);
    ttsSpeaking = true; pauseRecognitionForVoice();
    audio.onended = () => { ttsSpeaking = false; resumeCallRecognition(); };
    audio.onerror = () => { ttsSpeaking = false; resumeCallRecognition(); };
    audio.play().catch(() => { ttsSpeaking = false; resumeCallRecognition(); });
    return;
  }
  if (!('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text.replace(/\n/g, ' '));
  u.lang = 'ja-JP'; u.rate = .98; u.pitch = 1.06; u.volume = 1;
  ttsSpeaking = true; pauseRecognitionForVoice();
  u.onend = () => { ttsSpeaking = false; resumeCallRecognition(); };
  u.onerror = () => { ttsSpeaking = false; resumeCallRecognition(); };
  speechSynthesis.speak(u);
}

async function handleUserMessage(text, source = 'text') {
  const v = String(text || '').trim(); if (!v) return;
  focus('rei', false); setAction('love', 1.6);
  liveTranscript.textContent = source === 'voice' ? `YOU: ${v}` : liveTranscript.textContent;
  let result = null;
  if (window.REI_ROOM_BRIDGE) result = await window.REI_ROOM_BRIDGE.chat({ text: v, source, place: document.getElementById('placeText').textContent });
  const reply = result?.text || result?.reply || localReply(v);
  if (result?.action && actionLines[result.action]) setAction(result.action, 2.2);
  speak(reply, 7600);
  if (callActive) {
    callStatus.textContent = window.REI_ROOM_BRIDGE?.connected ? `接続中 · ${window.REI_ROOM_BRIDGE.mode}` : 'ローカル通話デモ';
    liveTranscript.textContent = `YOU: ${v}\nREI: ${reply}`;
    // グラム脳 (AivisSpeech) の wav を優先: base64 → blob URL
    let audioRef = result?.audioUrl || result?.audio_url;
    if (!audioRef && result?.audioWavB64) {
      try {
        const bin = atob(result.audioWavB64);
        const arr = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
        audioRef = URL.createObjectURL(new Blob([arr], { type: 'audio/wav' }));
      } catch (e) {}
    }
    playReplyVoice(reply, audioRef);
  }
  window.REI_ROOM_BRIDGE?.emit?.('room_reply_rendered', { text: reply, source });
}

function sendLocal() { const v = chatInput.value.trim(); if (!v) return; chatInput.value = ''; handleUserMessage(v, 'text'); }
document.getElementById('sendBtn').addEventListener('click', sendLocal);
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendLocal(); });
document.getElementById('cinematicBtn').addEventListener('click', () => document.body.classList.toggle('cinematic'));

function makeRecognition(mode) {
  if (!SpeechRecognition) return null;
  const r = new SpeechRecognition();
  r.lang = 'ja-JP'; r.interimResults = true; r.continuous = mode === 'call';
  r.onstart = () => { micBtn.classList.add('listening'); if (mode === 'call') callStatus.textContent = '聞いてるよ…'; };
  r.onresult = e => {
    let interim = '', finals = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const txt = e.results[i][0].transcript;
      if (e.results[i].isFinal) finals += txt; else interim += txt;
    }
    if (mode === 'dictation') chatInput.value = finals || interim;
    if (mode === 'call') liveTranscript.textContent = interim ? `YOU: ${interim} …` : (finals ? `YOU: ${finals}` : liveTranscript.textContent);
    if (finals.trim()) {
      if (mode === 'dictation') { chatInput.value = finals.trim(); chatInput.focus(); }
      else handleUserMessage(finals.trim(), 'voice');
    }
  };
  r.onerror = e => {
    console.warn('[REI voice] recognition error:', e.error);
    if (mode === 'call') callStatus.textContent = `音声認識: ${e.error}`;
  };
  r.onend = () => {
    micBtn.classList.remove('listening');
    if (mode === 'call' && callActive && recognitionShouldRestart && !callMuted && !ttsSpeaking) {
      setTimeout(() => { try { r.start(); } catch {} }, 260);
    }
  };
  return r;
}

function stopRecognition() {
  recognitionShouldRestart = false;
  if (recognition) { try { recognition.stop(); } catch {} }
  recognition = null; recognitionMode = null; micBtn.classList.remove('listening');
}
function pauseRecognitionForVoice() { if (recognitionMode === 'call' && recognition) { recognitionShouldRestart = false; try { recognition.stop(); } catch {} } }
function resumeCallRecognition() {
  if (!callActive || callMuted || !SpeechRecognition) return;
  recognition = makeRecognition('call'); recognitionMode = 'call'; recognitionShouldRestart = true;
  try { recognition.start(); } catch {}
}

micBtn.addEventListener('click', () => {
  if (callActive) { callMuted = !callMuted; muteBtn.click(); return; }
  if (!SpeechRecognition) { speak('このブラウザでは音声入力が使えないみたい。Chrome系ブラウザなら使える可能性が高いよ。'); return; }
  if (recognitionMode === 'dictation' && recognition) { stopRecognition(); return; }
  stopRecognition(); recognition = makeRecognition('dictation'); recognitionMode = 'dictation'; recognitionShouldRestart = false;
  try { recognition.start(); } catch (e) { console.warn(e); }
});

async function setupAudioMeter() {
  if (!navigator.mediaDevices?.getUserMedia) throw new Error('getUserMedia unsupported');
  micStream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
  audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioContext.createMediaStreamSource(micStream); analyser = audioContext.createAnalyser(); analyser.fftSize = 256; source.connect(analyser);
  const data = new Uint8Array(analyser.frequencyBinCount);
  const draw = () => { if (!callActive || !analyser) return; analyser.getByteFrequencyData(data); const avg = data.reduce((a,b)=>a+b,0)/data.length; audioMeter.style.width = `${Math.max(3, Math.min(100, avg * .72))}%`; meterRAF = requestAnimationFrame(draw); }; draw();
  return micStream;
}

async function startCall() {
  if (callActive) return;
  callActive = true; callMuted = false; callStartedAt = Date.now(); callPanel.classList.add('show'); callBtn.classList.add('active'); callBtn.textContent = '☎ 通話中';
  callStatus.textContent = 'マイク接続中…'; liveTranscript.textContent = 'れいとの音声リンクを開始しています。';
  try {
    const stream = await setupAudioMeter();
    callStatus.textContent = window.REI_ROOM_BRIDGE?.connected ? `接続中 · ${window.REI_ROOM_BRIDGE.mode}` : 'ローカル通話デモ · マイクON';
    await window.REI_ROOM_BRIDGE?.startCall?.({ stream, capabilities: { browserSTT: !!SpeechRecognition, browserTTS: 'speechSynthesis' in window } });
    resumeCallRecognition();
    speak('つながったよ。声で話してみて＾＾');
    playReplyVoice('つながったよ。声で話してみて。');
  } catch (e) {
    callStatus.textContent = 'マイクを許可すると通話できます'; liveTranscript.textContent = String(e?.message || e);
  }
  clearInterval(callTimer); callTimer = setInterval(() => { const sec = Math.floor((Date.now()-callStartedAt)/1000); callTime.textContent = `${String(Math.floor(sec/60)).padStart(2,'0')}:${String(sec%60).padStart(2,'0')}`; }, 500);
}

async function endCall() {
  if (!callActive) return;
  callActive = false; stopRecognition(); speechSynthesis?.cancel?.(); clearInterval(callTimer); callTimer = null; callTime.textContent = '00:00'; callBtn.classList.remove('active'); callBtn.textContent = '☎ 通話'; callPanel.classList.remove('show');
  if (meterRAF) cancelAnimationFrame(meterRAF); meterRAF = null; analyser = null; audioMeter.style.width = '3%';
  micStream?.getTracks?.().forEach(t => t.stop()); micStream = null; if (audioContext) { try { await audioContext.close(); } catch {} } audioContext = null;
  await window.REI_ROOM_BRIDGE?.stopCall?.({ reason: 'user-ended' });
}
callBtn.addEventListener('click', () => callActive ? endCall() : startCall());
endCallBtn.addEventListener('click', endCall);
muteBtn.addEventListener('click', () => {
  callMuted = !callMuted; micStream?.getAudioTracks?.().forEach(t => t.enabled = !callMuted); muteBtn.textContent = callMuted ? '🔇 ミュート中' : '🎙 ミュート';
  if (callMuted) stopRecognition(); else resumeCallRecognition();
  callStatus.textContent = callMuted ? 'ミュート中' : (window.REI_ROOM_BRIDGE?.connected ? `接続中 · ${window.REI_ROOM_BRIDGE.mode}` : 'ローカル通話デモ · マイクON');
});

// Public hooks for Gram/Hermes/backend adapters.
window.REI_ROOM_API = {
  speak,
  focus,
  setAction,
  receive(text, meta = {}) { if (meta.action && actionLines[meta.action]) setAction(meta.action, 2.2); speak(String(text), 7600); if (callActive) playReplyVoice(String(text), meta.audioUrl); },
  async startCall() { return startCall(); },
  async endCall() { return endCall(); },
  getState() { return { callActive, callMuted, action, place: document.getElementById('placeText').textContent, bridgeMode: window.REI_ROOM_BRIDGE?.mode || 'none' }; }
};

// click REI cycles friendly reaction
const ray = new THREE.Raycaster(), pointer = new THREE.Vector2(); let clickCycle = 0;
renderer.domElement.addEventListener('pointerdown', e => { const r = renderer.domElement.getBoundingClientRect(); pointer.x = (e.clientX - r.left) / r.width * 2 - 1; pointer.y = -(e.clientY - r.top) / r.height * 2 + 1; ray.setFromCamera(pointer, camera); if (ray.intersectObject(rei, true).length) { clickCycle = (clickCycle + 1) % 3; setAction(['love', 'cheer', 'think'][clickCycle], 2.4); } });

// ===== ROOM TOUR =====
const tourOrder = ['rei', 'desk', 'bookshelf', 'daybed', 'window', 'objects', 'room']; let tourIndex = 0, touring = false, tourTimer = null;
function runTourStep() { if (!touring) return; focus(tourOrder[tourIndex]); tourIndex++; if (tourIndex >= tourOrder.length) { touring = false; tourIndex = 0; document.getElementById('tourBtn').textContent = 'Room Tour'; return; } tourTimer = setTimeout(runTourStep, 4200); }
document.getElementById('tourBtn').addEventListener('click', () => { touring = !touring; clearTimeout(tourTimer); if (touring) { document.getElementById('tourBtn').textContent = 'Stop Tour'; tourIndex = 0; runTourStep(); } else { document.getElementById('tourBtn').textContent = 'Room Tour'; } });

// ===== ANIMATION =====
const clock = new THREE.Clock(); let elapsed = 0, blinkClock = 0, nextBlink = 2.3 + Math.random() * 2.5;
function lerpAngle(current, target, amount) { return current + Math.atan2(Math.sin(target - current), Math.cos(target - current)) * amount; }
function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(.033, clock.getDelta()); elapsed += dt; actionTime += dt; blinkClock += dt; controls.update();
  if (camGoal) { camera.position.lerp(camGoal, .048); controls.target.lerp(targetGoal, .048); if (camera.position.distanceTo(camGoal) < .03) { camGoal = null; targetGoal = null; } }

  // Dog walking between room anchors
  const delta = dogGoal.clone().sub(rei.position); const dist = delta.length();
  if (dist > .035) { const step = Math.min(dist, dt * 1.15); rei.position.add(delta.normalize().multiplyScalar(step)); const yaw = Math.atan2(delta.x, delta.z); rei.rotation.y = lerpAngle(rei.rotation.y, yaw, .12); dogWalking = true; }
  else { dogWalking = false; rei.rotation.y = lerpAngle(rei.rotation.y, -.10, .035); }
  avatar.position.y = Math.sin(elapsed * 1.7) * .008 + (dogWalking ? Math.abs(Math.sin(elapsed * 8)) * .055 : 0);
  body.scale.y = 1.02 + Math.sin(elapsed * 1.8) * .008;
  tail.rotation.z = Math.sin(elapsed * (dogWalking ? 7 : 2.3)) * .18;

  // Blink. Always returns to base automatically.
  if (blinkClock > nextBlink) { blinkClock = 0; nextBlink = 2.2 + Math.random() * 3.3; eyeParts.forEach(e => e.scale.y = .10); setTimeout(() => eyeParts.forEach(e => e.scale.y = 1.12), 110); }

  // Every frame calculates targets from action, so eyebrows can never get stuck.
  let browLT = base.browL, browRT = base.browR, armLT = base.armL, armRT = base.armR, tilt = 0, bounce = 0;
  if (action === 'love') { browLT = Math.PI / 2 + .13; browRT = Math.PI / 2 - .13; armLT = 1.12; armRT = -1.12; bounce = Math.abs(Math.sin(elapsed * 5)) * .035; }
  if (action === 'cheer') { armLT = 1.45; armRT = -1.45; bounce = Math.abs(Math.sin(elapsed * 6)) * .10; }
  if (action === 'think') { browLT = Math.PI / 2 + .22; browRT = Math.PI / 2 + .03; armLT = .95; tilt = -.08; }
  if (action === 'cry') { browLT = Math.PI / 2 - .28; browRT = Math.PI / 2 + .28; armLT = .42; armRT = -.42; tilt = .05; }
  if (action === 'snack') { armRT = -.78; tilt = -.03; }
  if (action === 'sleep') { browLT = Math.PI / 2; browRT = Math.PI / 2; tilt = -.18; eyeParts.forEach(e => e.scale.y = .08); }
  browL.rotation.z = THREE.MathUtils.lerp(browL.rotation.z, browLT, .12); browR.rotation.z = THREE.MathUtils.lerp(browR.rotation.z, browRT, .12); armL.rotation.z = THREE.MathUtils.lerp(armL.rotation.z, armLT, .12); armR.rotation.z = THREE.MathUtils.lerp(armR.rotation.z, armRT, .12); avatar.rotation.z = THREE.MathUtils.lerp(avatar.rotation.z, tilt, .08); avatar.position.y += bounce;
  if (action !== 'idle' && actionTime > actionDuration) resetExpression();

  hearts.children.forEach((h, i) => { h.position.y += dt * (.18 + i * .014); h.rotation.z = Math.sin(elapsed + i) * .18; if (h.position.y > 3.1) h.position.y = 1.4; });
  cat.scale.y = 1 + Math.sin(elapsed * 1.1) * .012; catTail.rotation.z = Math.sin(elapsed * .7) * .10; bot.rotation.y = Math.sin(elapsed * .8) * .18; dust.rotation.y = elapsed * .006;
  composer.render();
}
animate();

addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); composer.setSize(innerWidth, innerHeight); });
setTimeout(() => focus('room', false), 350);
