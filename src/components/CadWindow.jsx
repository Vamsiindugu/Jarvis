import React, { useMemo, useState, useEffect } from 'react';
import { Canvas, useLoader } from '@react-three/fiber';
import { OrbitControls, Center, Stage } from '@react-three/drei';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';

const Model = ({ url }) => {
    const geometry = useLoader(STLLoader, url);
    return (
        <mesh geometry={geometry} castShadow receiveShadow>
            <meshStandardMaterial color="#06b6d4" roughness={0.3} metalness={0.8} />
        </mesh>
    );
};

const CadWindow = ({ data, onClose }) => {
    // data format: { format: "stl", data: "base64..." } OR old { vertices... }

    // Debug log
    useEffect(() => {
        if (data) console.log("CadWindow Data:", data.format);
    }, [data]);

    const blobUrl = useMemo(() => {
        if (!data || data.format !== 'stl' || !data.data) return null;

        try {
            // Convert Base64 to Blob
            const byteCharacters = atob(data.data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'application/octet-stream' });
            return URL.createObjectURL(blob);
        } catch (e) {
            console.error("Failed to decode STL:", e);
            return null;
        }
    }, [data]);

    // Cleanup URL
    useEffect(() => {
        return () => {
            if (blobUrl) URL.revokeObjectURL(blobUrl);
        };
    }, [blobUrl]);

    return (
        <div className="w-full h-full relative group bg-gray-900 rounded-lg overflow-hidden border border-cyan-500/30">
            <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={onClose} className="bg-red-500/20 hover:bg-red-500/50 text-red-500 p-1 rounded">X</button>
            </div>

            <Canvas shadows camera={{ position: [4, 4, 4], fov: 45 }}>
                <color attach="background" args={['#101010']} />

                <Stage environment="city" intensity={0.5}>
                    {blobUrl && (
                        <Center>
                            <Model url={blobUrl} />
                        </Center>
                    )}
                </Stage>

                <OrbitControls autoRotate autoRotateSpeed={1} makeDefault />
            </Canvas>

            <div className="absolute bottom-2 left-2 text-[10px] text-cyan-500/50 font-mono tracking-widest pointer-events-none">
                CAD_ENGINE_V2: {data?.format?.toUpperCase() || "WAITING"}
            </div>
        </div>
    );
};

export default CadWindow;
