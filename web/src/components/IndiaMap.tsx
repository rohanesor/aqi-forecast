// 3D India map (India's official boundary, Natural Earth India point-of-view) with one glowing pillar per trained city:
// height = forecast AQI for the chosen day, colour = CPCB category. Click a pillar to switch city.
import { Canvas, useFrame } from '@react-three/fiber';
import { Html, OrbitControls } from '@react-three/drei';
import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { cat } from '../aqi';
import { CityIndex, getJSON } from '../data';

const LON0 = 82.5, LAT0 = 22.5, S = 0.42;
const proj = (lon: number, lat: number) => [(lon - LON0) * S * Math.cos((LAT0 * Math.PI) / 180), (lat - LAT0) * S] as const;

function Land({ rings }: { rings: number[][][] }) {
  const { geo, edges } = useMemo(() => {
    const shapes = rings.map((r) => { const s = new THREE.Shape(); r.forEach(([lo, la], i) => { const [x, y] = proj(lo, la); i ? s.lineTo(x, y) : s.moveTo(x, y); }); return s; });
    const geo = new THREE.ExtrudeGeometry(shapes, { depth: 0.35, bevelEnabled: true, bevelSize: 0.05, bevelThickness: 0.05, bevelSegments: 2 });
    geo.rotateX(-Math.PI / 2);
    return { geo, edges: new THREE.EdgesGeometry(geo, 30) };
  }, [rings]);
  return (
    <group>
      <mesh geometry={geo} receiveShadow><meshStandardMaterial color="#2a3a66" emissive="#101a3a" roughness={0.7} metalness={0.1} /></mesh>
      <lineSegments geometry={edges}><lineBasicMaterial color="#7d9bf0" transparent opacity={0.8} /></lineSegments>
    </group>
  );
}

function Pillar({ c, aqi, active, onPick }: { c: CityIndex; aqi: number; active: boolean; onPick: () => void }) {
  const ref = useRef<THREE.Mesh>(null!); const [hover, setHover] = useState(false);
  const [x, z] = proj(c.lon!, c.lat!); const target = 0.4 + (aqi / 500) * 6; const col = cat(aqi).colour;
  useFrame((_, dt) => { const s = ref.current.scale; s.y += (target - s.y) * Math.min(1, dt * 3); ref.current.position.y = 0.4 + s.y / 2; });
  return (
    <group position={[x, 0, -z]}>
      <mesh ref={ref} scale={[1, 0.01, 1]} onClick={(e) => { e.stopPropagation(); onPick(); }}
        onPointerOver={() => { setHover(true); document.body.style.cursor = 'pointer'; }} onPointerOut={() => { setHover(false); document.body.style.cursor = ''; }}>
        <cylinderGeometry args={[0.32, 0.32, 1, 32]} />
        <meshStandardMaterial color={col} emissive={col} emissiveIntensity={active || hover ? 0.35 : 0.15} roughness={0.45} />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.42, 0]}><ringGeometry args={[0.45, active ? 0.75 : 0.55, 48]} /><meshBasicMaterial color={col} transparent opacity={active ? 0.8 : 0.35} /></mesh>
      <Html position={[0, target + 0.9, 0]} center distanceFactor={11} zIndexRange={[10, 0]}>
        <button className={`map-tag ${active ? 'on' : ''}`} onClick={onPick} style={{ borderColor: col }}>
          <b>{c.city}</b><span>{Math.round(aqi)}</span>
        </button>
      </Html>
    </group>
  );
}

export default function IndiaMap({ cities, values, active, onPick, reduced }: { cities: CityIndex[]; values: Record<string, number>; active: string; onPick: (slug: string) => void; reduced: boolean }) {
  const [rings, setRings] = useState<number[][][] | null>(null);
  useEffect(() => { getJSON<number[][][]>('india.json').then(setRings).catch(() => setRings([])); }, []);
  return (
    <Canvas dpr={[1, 1.6]} camera={{ position: [0, 12, 11], fov: 40 }} shadows>
      <color attach="background" args={['#0a0f1d']} />
      <ambientLight intensity={0.9} /><hemisphereLight args={["#9fb8ff", "#0a0f1d", 0.6]} />
      <directionalLight position={[6, 14, 8]} intensity={1.3} castShadow />
      <pointLight position={[-8, 6, -6]} intensity={40} color="#5d7bd6" />
      {rings && <Land rings={rings} />}
      {cities.filter((c) => c.lat != null && c.lon != null).map((c) => (
        <Pillar key={c.slug} c={c} aqi={values[c.slug] ?? c.latest_aqi} active={c.slug === active} onPick={() => onPick(c.slug)} />
      ))}
      <OrbitControls enablePan={false} minDistance={10} maxDistance={28} maxPolarAngle={1.25} autoRotate={!reduced} autoRotateSpeed={0.35} target={[0, 0, 0]} />
    </Canvas>
  );
}
