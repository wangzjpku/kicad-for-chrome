/**
 * 3D 预览器组件 (PCBViewer3D)
 * 基于 Three.js 的 PCB 3D 可视化
 * 注意: 需要安装 three.js @react-three/fiber @react-three/drei
 */

import React, { useRef, useState, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment } from '@react-three/drei';
import * as THREE from 'three';

// PCB 3D 数据类型
interface PCB3DData {
  boardOutline: THREE.Vector3[][];
  footprints: Footprint3D[];
}

interface Footprint3D {
  id: string;
  position: [number, number, number];
  rotation: [number, number, number];
  size: [number, number, number];
  type: 'resistor' | 'capacitor' | 'ic' | 'connector' | 'other';
  color: string;
}

// 板子组件
function PCBBoard({ data }: { data: PCB3DData }) {
  const boardRef = useRef<THREE.Group>(null);
  
  return (
    <group ref={boardRef}>
      {/* 板子主体 - 绿色 PCB */}
      <mesh position={[0, 0, 0.8]} receiveShadow>
        <boxGeometry args={[80, 60, 1.6]} />
        <meshStandardMaterial 
          color="#1a472a" 
          roughness={0.8} 
          metalness={0.1}
        />
      </mesh>
      
      {/* 铜层 - 顶面 */}
      <mesh position={[0, 0, 1.65]} receiveShadow>
        <boxGeometry args={[79, 59, 0.035]} />
        <meshStandardMaterial 
          color="#b87333" 
          roughness={0.3} 
          metalness={0.8}
        />
      </mesh>
      
      {/* 铜层 - 底面 */}
      <mesh position={[0, 0, -1.65]} receiveShadow>
        <boxGeometry args={[79, 59, 0.035]} />
        <meshStandardMaterial 
          color="#b87333" 
          roughness={0.3} 
          metalness={0.8}
        />
      </mesh>
      
      {/* 丝印层 - 顶面 */}
      <mesh position={[0, 0, 1.68]} receiveShadow>
        <boxGeometry args={[78, 58, 0.01]} />
        <meshStandardMaterial 
          color="#ffffff" 
          roughness={0.9}
          transparent
          opacity={0.8}
        />
      </mesh>
      
      {/* 3D 封装 */}
      {data.footprints.map((fp) => (
        <Footprint3DComponent key={fp.id} footprint={fp} />
      ))}
    </group>
  );
}

// 3D 封装组件
function Footprint3DComponent({ footprint }: { footprint: Footprint3D }) {
  const meshRef = useRef<THREE.Mesh>(null);
  
  const [x, y, z] = footprint.position;
  const [rx, ry, rz] = footprint.rotation;
  const [w, h, d] = footprint.size;
  
  return (
    <mesh
      ref={meshRef}
      position={[x, y, z]}
      rotation={[rx, ry, rz]}
      castShadow
      receiveShadow
    >
      <boxGeometry args={[w, h, d]} />
      <meshStandardMaterial 
        color={footprint.color} 
        roughness={0.5}
        metalness={0.2}
      />
    </mesh>
  );
}

// 场景设置
function SceneSetup() {
  const { scene } = useThree();
  
  // 添加环境光
  React.useEffect(() => {
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(50, 50, 50);
    directionalLight.castShadow = true;
    scene.add(directionalLight);
    
    return () => {
      scene.remove(ambientLight);
      scene.remove(directionalLight);
    };
  }, [scene]);
  
  return null;
}

// 示例数据
const samplePCB3DData: PCB3DData = {
  boardOutline: [],
  footprints: [
    {
      id: 'fp1',
      position: [-20, 0, 1.7],
      rotation: [0, 0, 0],
      size: [6, 3, 1],
      type: 'resistor',
      color: '#8B4513'
    },
    {
      id: 'fp2',
      position: [0, 10, 1.7],
      rotation: [0, 0, Math.PI / 2],
      size: [5, 2.5, 1],
      type: 'capacitor',
      color: '#1E90FF'
    },
    {
      id: 'fp3',
      position: [20, -5, 1.7],
      rotation: [0, 0, 0],
      size: [15, 10, 2],
      type: 'ic',
      color: '#2F4F4F'
    }
  ]
};

interface PCBViewer3DProps {
  width?: number;
  height?: number;
  data?: PCB3DData;
}

const PCBViewer3D: React.FC<PCBViewer3DProps> = ({
  width = 600,
  height = 400,
  data = samplePCB3DData
}) => {
  const [autoRotate, setAutoRotate] = useState(true);
  
  return (
    <div style={{ width, height, background: '#1a1a1a', position: 'relative' }}>
      {/* 3D 画布 */}
      <Canvas shadows>
        <PerspectiveCamera makeDefault position={[100, 100, 100]} fov={50} />
        <OrbitControls 
          enablePan={true} 
          enableZoom={true} 
          enableRotate={true}
          autoRotate={autoRotate}
          autoRotateSpeed={0.5}
        />
        
        <SceneSetup />
        
        <Suspense fallback={null}>
          <PCBBoard data={data} />
          
          {/* 地面网格 */}
          <gridHelper args={[200, 20, 0x444444, 0x222222]} position={[0, 0, -2]} />
        </Suspense>
      </Canvas>
      
      {/* 控制面板 */}
      <div
        style={{
          position: 'absolute',
          bottom: 10,
          left: 10,
          display: 'flex',
          gap: 8,
        }}
      >
        <button
          onClick={() => setAutoRotate(!autoRotate)}
          style={{
            padding: '6px 12px',
            backgroundColor: autoRotate ? '#4a9eff' : '#3d3d3d',
            color: '#ffffff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 12,
          }}
        >
          {autoRotate ? '停止旋转' : '自动旋转'}
        </button>
      </div>
      
      {/* 信息面板 */}
      <div
        style={{
          position: 'absolute',
          top: 10,
          right: 10,
          backgroundColor: 'rgba(0,0,0,0.7)',
          color: '#ffffff',
          padding: '8px 12px',
          borderRadius: 4,
          fontSize: 11,
        }}
      >
        <div>3D 预览</div>
        <div style={{ color: '#888', marginTop: 4 }}>
          鼠标左键: 旋转 | 右键: 平移 | 滚轮: 缩放
        </div>
      </div>
    </div>
  );
};

export default PCBViewer3D;
export type { PCB3DData, Footprint3D };
