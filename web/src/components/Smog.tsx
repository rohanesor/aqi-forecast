// Hero 3D: a procedural low-poly city under a smog layer. Particle count/opacity, tint, fog distance and sun haze all
// follow the AQI, and animate smoothly when the city or day changes.
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import * as THREE from 'three';

type P = { level: number; tint: string; reduced: boolean };

function City() {
  const { mesh, windows } = useMemo(() => {
    const rnd = mulberry(7); const n = 520; const dummy = new THREE.Object3D();
    const geo = new THREE.BoxGeometry(1, 1, 1); geo.translate(0, 0.5, 0);
    const mat = new THREE.MeshStandardMaterial({ color: '#1b2233', roughness: 0.85, metalness: 0.1 });
    const mesh = new THREE.InstancedMesh(geo, mat, n);
    const wgeo = new THREE.PlaneGeometry(0.16, 0.22); const wmat = new THREE.MeshBasicMaterial({ color: '#ffcf7a' });
    const wins = new THREE.InstancedMesh(wgeo, wmat, 1600); let wi = 0;
    for (let i = 0; i < n; i++) {
      const x = (rnd() - 0.5) * 70, z = -rnd() * 60 - 4;
      if (Math.abs(x) < 3.5 && z > -14) continue;                          // keep a clear street in front
      const centre = Math.exp(-((x * x) / 500 + ((z + 30) * (z + 30)) / 900));
      const h = 1.2 + rnd() * 3 + centre * 11 * rnd(); const w = 1 + rnd() * 2, d = 1 + rnd() * 2;
      dummy.position.set(x, 0, z); dummy.scale.set(w, h, d); dummy.rotation.y = (rnd() - 0.5) * 0.15; dummy.updateMatrix(); mesh.setMatrixAt(i, dummy.matrix);
      for (let k = 0; k < 4 && wi < 1600; k++) {
        if (rnd() > 0.55) continue;
        dummy.position.set(x + (rnd() - 0.5) * w * 0.8, 0.4 + rnd() * (h - 0.6), z + d / 2 + 0.01); dummy.scale.set(1, 1, 1); dummy.rotation.set(0, 0, 0);
        dummy.updateMatrix(); wins.setMatrixAt(wi++, dummy.matrix);
      }
    }
    wins.count = wi; return { mesh, windows: wins };
  }, []);
  return <group><primitive object={mesh} /><primitive object={windows} /></group>;
}

function SmogParticles({ level, tint, reduced }: P) {
  const ref = useRef<THREE.Points>(null!); const N = 9000;
  const cur = useRef({ level, col: new THREE.Color(tint) });
  const { geo, mat } = useMemo(() => {
    const rnd = mulberry(3); const pos = new Float32Array(N * 3), seed = new Float32Array(N);
    for (let i = 0; i < N; i++) { pos[i * 3] = (rnd() - 0.5) * 90; pos[i * 3 + 1] = Math.pow(rnd(), 1.6) * 16; pos[i * 3 + 2] = -rnd() * 70 + 6; seed[i] = rnd(); }
    const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setAttribute('seed', new THREE.BufferAttribute(seed, 1));
    const mat = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.NormalBlending,
      uniforms: { uTime: { value: 0 }, uLevel: { value: level }, uCol: { value: new THREE.Color(tint) } },
      vertexShader: `uniform float uTime; uniform float uLevel; attribute float seed; varying float vA;
        void main(){ vec3 p = position; p.x += sin(uTime*0.05 + seed*40.0)*3.0 + uTime*0.35*(0.4+seed); p.x = mod(p.x+45.0, 90.0)-45.0;
          p.y += sin(uTime*0.2 + seed*12.0)*0.4;
          vec4 mv = modelViewMatrix*vec4(p,1.0); gl_Position = projectionMatrix*mv;
          float keep = step(seed, 0.12 + uLevel*0.88);
          gl_PointSize = keep * (90.0 + seed*160.0) / -mv.z; vA = keep * (0.05 + uLevel*0.16) * (1.0 - p.y/18.0); }`,
      fragmentShader: `uniform vec3 uCol; varying float vA; void main(){ vec2 c = gl_PointCoord-0.5; float d = dot(c,c);
          if(d>0.25) discard; gl_FragColor = vec4(uCol, vA*(1.0-d*4.0)); }`,
    });
    return { geo, mat };
  }, []);
  const { scene } = useThree();
  useFrame((s, dt) => {
    const k = Math.min(1, dt * 1.6);
    cur.current.level += (level - cur.current.level) * k; cur.current.col.lerp(new THREE.Color(tint), k);
    mat.uniforms.uTime.value = reduced ? 20 : s.clock.elapsedTime; mat.uniforms.uLevel.value = cur.current.level; mat.uniforms.uCol.value.copy(cur.current.col);
    const fog = scene.fog as THREE.Fog; const L = cur.current.level;
    fog.near = 6 - L * 4; fog.far = 95 - L * 70; fog.color.copy(new THREE.Color('#0b1020').lerp(cur.current.col, 0.18 + L * 0.5));
    (scene.background as THREE.Color).copy(fog.color);
  });
  return <points ref={ref} geometry={geo} material={mat} frustumCulled={false} />;
}

function Rig({ reduced }: { reduced: boolean }) {
  useFrame((s) => {
    const t = reduced ? 0 : s.clock.elapsedTime; const px = (s.pointer.x || 0) * (reduced ? 0 : 1.2);
    s.camera.position.set(Math.sin(t * 0.05) * 2 + px, 3.2 + Math.sin(t * 0.07) * 0.3, 10); s.camera.lookAt(0, 4, -30);
  });
  return null;
}

export default function Smog({ level, tint, reduced }: P) {
  return (
    <Canvas dpr={[1, 1.6]} camera={{ fov: 50, position: [0, 3, 10] }} gl={{ antialias: true, powerPreference: 'high-performance' }}
      onCreated={({ scene }) => { scene.fog = new THREE.Fog('#0b1020', 6, 95); scene.background = new THREE.Color('#0b1020'); }}>
      <ambientLight intensity={0.55} />
      <directionalLight position={[-20, 30, 10]} intensity={1.1} color="#ffd9a8" />
      <mesh rotation-x={-Math.PI / 2} position={[0, 0, -30]}><planeGeometry args={[200, 200]} /><meshStandardMaterial color="#121725" roughness={1} /></mesh>
      <City />
      <SmogParticles level={level} tint={tint} reduced={reduced} />
      <Rig reduced={reduced} />
    </Canvas>
  );
}

export function mulberry(a: number) { return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
