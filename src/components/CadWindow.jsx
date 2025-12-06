import React, { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Line, Sphere } from '@react-three/drei';
import * as THREE from 'three';

const CadWindow = ({ data, onClose }) => {
    // data format: { vertices: [[x,y,z], ...], edges: [[start, end], ...] }

    // Debug log to verify data reception
    if (data) {
        console.log("CadWindow received data:", data);
        console.log(`Vertices: ${data.vertices?.length}, Edges: ${data.edges?.length}`);
    }

    const { lines, points } = useMemo(() => {
        if (!data || !data.vertices || !data.edges) return { lines: [], points: [] };

        const l = [];
        const { vertices, edges } = data;

        edges.forEach(([start, end]) => {
            if (vertices[start] && vertices[end]) { // Basic safety check
                const startPoint = new THREE.Vector3(...vertices[start]);
                const endPoint = new THREE.Vector3(...vertices[end]);
                l.push([startPoint, endPoint]);
            }
        });

        const p = vertices.map(v => new THREE.Vector3(...v));

        return { lines: l, points: p };
    }, [data]);

    return (
        <div className="w-full h-full relative group">
            <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={onClose} className="bg-red-500/20 hover:bg-red-500/50 text-red-500 p-1 rounded">X</button>
            </div>

            <Canvas camera={{ position: [2, 2, 2], fov: 50 }}>
                <ambientLight intensity={0.5} />
                <pointLight position={[10, 10, 10]} />

                {/* Axes Helper for orientation: Red=X, Green=Y, Blue=Z */}
                <axesHelper args={[1]} />

                {/* Grid for reference */}
                <gridHelper args={[4, 10, 0x222222, 0x111111]} />

                <group>
                    {lines.map((pts, i) => (
                        <Line
                            key={`line-${i}`}
                            points={pts}
                            color="#06b6d4" // Cyan-500
                            lineWidth={2}
                        />
                    ))}
                    {points.map((pt, i) => (
                        <Sphere key={`pt-${i}`} position={pt} args={[0.02, 10, 10]}>
                            <meshStandardMaterial color="white" />
                        </Sphere>
                    ))}
                </group>

                <OrbitControls autoRotate autoRotateSpeed={2} />
            </Canvas>

            <div className="absolute bottom-2 left-2 text-[10px] text-cyan-500/50 font-mono tracking-widest pointer-events-none">
                CAD_VIEWER_V1
            </div>
        </div>
    );
};

export default CadWindow;
