import React, { useEffect, useState } from 'react';
import { Lock, ScanFace } from 'lucide-react';

const AuthLock = ({ socket, onAuthenticated }) => {
    const [frameSrc, setFrameSrc] = useState(null);
    const [message, setMessage] = useState("Initializing Security...");

    useEffect(() => {
        if (!socket) return;

        const handleAuthStatus = (data) => {
            console.log("Auth Status:", data);
            if (data.authenticated) {
                setMessage("Access Granted.");
                setTimeout(() => {
                    onAuthenticated(true);
                }, 1000);
            } else {
                setMessage("Look at the camera to unlock.");
            }
        };

        const handleAuthFrame = (data) => {
            setFrameSrc(`data:image/jpeg;base64,${data.image}`);
        };

        socket.on('auth_status', handleAuthStatus);
        socket.on('auth_frame', handleAuthFrame);

        return () => {
            socket.off('auth_status', handleAuthStatus);
            socket.off('auth_frame', handleAuthFrame);
        };
    }, [socket, onAuthenticated]);

    return (
        <div className="fixed inset-0 z-[9999] bg-black flex flex-col items-center justify-center text-cyan-500 font-mono select-none">
            {/* Background Grid */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-cyan-900/20 via-black to-black pointer-events-none"></div>

            <div className="relative flex flex-col items-center gap-6 p-10 border border-cyan-500/30 rounded-lg bg-black/80 backdrop-blur-xl shadow-[0_0_50px_rgba(34,211,238,0.2)]">
                <div className="text-3xl font-bold tracking-[0.3em] uppercase drop-shadow-[0_0_10px_rgba(34,211,238,0.8)] flex items-center gap-4">
                    <Lock size={32} />
                    System Locked
                </div>

                {/* Camera Feed Frame */}
                <div className="relative w-64 h-64 border-2 border-cyan-500/50 rounded-lg overflow-hidden bg-gray-900 shadow-inner flex items-center justify-center">
                    {frameSrc ? (
                        <img
                            src={frameSrc}
                            alt="Auth Camera"
                            className="w-full h-full object-cover transform scale-x-[-1]"
                        />
                    ) : (
                        <div className="animate-pulse text-cyan-800">
                            <ScanFace size={64} />
                        </div>
                    )}

                    {/* Scanning Line Animation */}
                    <div className="absolute top-0 left-0 w-full h-1 bg-cyan-400/80 shadow-[0_0_15px_cyan] animate-[scan_2s_ease-in-out_infinite]"></div>
                </div>

                <div className="text-sm tracking-widest text-cyan-300 animate-pulse">
                    {message}
                </div>
            </div>

            {/* Keyframe for scan animation */}
            <style>{`
                @keyframes scan {
                    0%, 100% { top: 0%; opacity: 0; }
                    50% { opacity: 1; }
                    100% { top: 100%; opacity: 0; }
                }
             `}</style>
        </div>
    );
};

export default AuthLock;
