import React, { useState, useEffect } from 'react';
import { X, RefreshCw, Power, Sun, Palette } from 'lucide-react';

const KasaWindow = ({
    socket,
    position,
    onClose,
    activeDragElement,
    setActiveDragElement,
    devices,
    onMouseDown,
    zIndex = 40
}) => {
    const [isThinking, setIsThinking] = useState(false);
    const [loadingDevices, setLoadingDevices] = useState({}); // { ip: true/false }

    useEffect(() => {
        // Listen for individual updates to clear loading state
        const onUpdate = (data) => {
            if (data && data.ip) {
                setLoadingDevices(prev => {
                    const next = { ...prev };
                    delete next[data.ip];
                    return next;
                });
            }
        };

        socket.on('kasa_update', onUpdate);
        return () => socket.off('kasa_update', onUpdate);
    }, [socket]);


    const handleDiscover = () => {
        setIsThinking(true);
        socket.emit('discover_kasa');
        // Reset thinking after 5s if no response (safety)
        setTimeout(() => setIsThinking(false), 5000);
    };

    useEffect(() => {
        if (devices && devices.length > 0) {
            setIsThinking(false);
        }
    }, [devices]);

    const handleToggle = (ip, currentState) => {
        setLoadingDevices(prev => ({ ...prev, [ip]: true }));
        socket.emit('control_kasa', {
            ip: ip,
            action: currentState ? 'off' : 'on'
        });
    };


    const handleBrightness = (ip, val) => {
        socket.emit('control_kasa', {
            ip: ip,
            action: 'brightness',
            value: parseInt(val)
        });
    };

    const handleColor = (ip, hue) => {
        socket.emit('control_kasa', {
            ip: ip,
            action: 'color',
            value: { h: parseInt(hue), s: 100, v: 100 }
        });
    };

    // Color logic can be added later, keeping it simple for now as requested (Off, On, Settings)

    return (
        <div
            id="kasa"
            onMouseDown={onMouseDown}
            className={`absolute flex flex-col gap-2 p-4 rounded-xl backdrop-blur-md bg-black/60 border border-cyan-500/30 transition-all duration-200 select-none
                ${activeDragElement === 'kasa' ? 'ring-2 ring-green-500 shadow-[0_0_30px_rgba(34,197,94,0.3)]' : 'shadow-[0_0_20px_rgba(6,182,212,0.1)]'}
            `}
            style={{
                left: position.x,
                top: position.y,
                width: '320px',
                minHeight: '200px',
                transform: 'translate(-50%, -50%)',
                zIndex: zIndex
            }}
        >
            {/* Header */}
            <div data-drag-handle className="flex items-center justify-between pb-2 border-b border-white/10 mb-2 cursor-grab active:cursor-grabbing">
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${devices.length > 0 ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
                    <h3 className="font-bold text-cyan-400 tracking-wider text-sm">SMART CONTROL</h3>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 rounded hover:bg-white/10 transition-colors text-white/50 hover:text-white"
                >
                    <X size={16} />
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto max-h-[400px] scrollbar-hide">

                {devices.length === 0 && !isThinking && (
                    <div className="flex flex-col items-center justify-center p-8 text-center opacity-50">
                        <p className="text-xs mb-4">No devices found. Ensure they are on the same network.</p>
                        <button
                            onClick={handleDiscover}
                            className="flex items-center gap-2 px-4 py-2 bg-cyan-900/30 border border-cyan-500/30 rounded-lg hover:bg-cyan-500/20 hover:border-cyan-500 transition-all text-xs font-mono text-cyan-300"
                        >
                            <RefreshCw size={14} /> DISCOVER LIGHTS
                        </button>
                    </div>
                )}

                {isThinking && (
                    <div className="flex flex-col items-center justify-center p-8 gap-3">
                        <div className="w-6 h-6 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                        <span className="text-xs text-cyan-400 animate-pulse">Scanning Network...</span>
                    </div>
                )}

                {devices.map((dev) => (
                    <div key={dev.ip} className="mb-3 p-3 bg-white/5 rounded-lg border border-white/10 hover:border-cyan-500/30 transition-all">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex flex-col">
                                <span className="font-bold text-sm text-white">{dev.alias}</span>
                                <span className="text-[10px] text-white/40 font-mono">{dev.ip}</span>
                            </div>
                            <button
                                onClick={() => handleToggle(dev.ip, dev.is_on)}
                                disabled={loadingDevices[dev.ip]}
                                className={`p-2 rounded-full transition-all ${dev.is_on
                                    ? 'bg-green-500/20 text-green-400 shadow-[0_0_10px_rgba(34,197,94,0.3)]'
                                    : 'bg-white/5 text-gray-500 hover:text-white'}
                                    ${loadingDevices[dev.ip] ? 'opacity-50 cursor-not-allowed' : ''}
                                `}
                            >
                                {loadingDevices[dev.ip] ? (
                                    <div className="w-[18px] h-[18px] border-2 border-current border-t-transparent rounded-full animate-spin" />
                                ) : (
                                    <Power size={18} />
                                )}
                            </button>

                        </div>

                        {/* Controls */}
                        {dev.has_brightness && dev.is_on && (
                            <div className="flex items-center gap-2 mt-2">
                                <Sun size={14} className="text-yellow-500/70" />
                                <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    defaultValue={dev.brightness || 100}
                                    onChange={(e) => handleBrightness(dev.ip, e.target.value)}
                                    className="w-full h-1 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-cyan-400"
                                />
                            </div>
                        )}

                        {/* Color Control */}
                        {dev.has_color && dev.is_on && (
                            <div className="flex items-center gap-2 mt-2">
                                <Palette size={14} className="text-purple-500/70" />
                                <input
                                    type="range"
                                    min="0"
                                    max="360"
                                    defaultValue={(dev.hsv && dev.hsv.h) || 0}
                                    onChange={(e) => handleColor(dev.ip, e.target.value)}
                                    className="w-full h-1 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white"
                                    style={{
                                        background: 'linear-gradient(to right, red, yellow, lime, cyan, blue, magenta, red)'
                                    }}
                                />
                            </div>
                        )}
                    </div>
                ))}
            </div>
            {/* Bottom Discover (if devices exist) */}
            {devices.length > 0 && (
                <div className="pt-2 border-t border-white/10 mt-2 flex justify-end">
                    <button
                        onClick={handleDiscover}
                        className="p-1 text-white/30 hover:text-cyan-400 transition-colors"
                        title="Rescan"
                    >
                        <RefreshCw size={14} />
                    </button>
                </div>
            )}
        </div>
    );
};

export default KasaWindow;
