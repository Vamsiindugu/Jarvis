import React, { useEffect, useState, useRef } from 'react';
import io from 'socket.io-client';
import Visualizer from './components/Visualizer';
import TopAudioBar from './components/TopAudioBar';
import { Mic, MicOff, Settings, X, Minus } from 'lucide-react';

const socket = io('http://localhost:8000');
const { ipcRenderer } = window.require('electron');

function App() {
    const [status, setStatus] = useState('Disconnected');
    const [isListening, setIsListening] = useState(false);
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [aiAudioData, setAiAudioData] = useState(new Array(64).fill(0));
    const [micAudioData, setMicAudioData] = useState(new Array(32).fill(0));

    const [devices, setDevices] = useState([]);
    const [selectedDeviceId, setSelectedDeviceId] = useState('');
    const [showSettings, setShowSettings] = useState(false);

    // Web Audio Context for Mic Visualization
    const audioContextRef = useRef(null);
    const analyserRef = useRef(null);
    const sourceRef = useRef(null);
    const animationFrameRef = useRef(null);

    useEffect(() => {
        // Socket IO Setup
        socket.on('connect', () => setStatus('Connected'));
        socket.on('disconnect', () => setStatus('Disconnected'));
        socket.on('status', (data) => addMessage('System', data.msg));
        socket.on('audio_data', (data) => {
            // AI Audio Data (from Backend)
            setAiAudioData(data.data);
        });

        // Get Audio Devices
        navigator.mediaDevices.enumerateDevices().then(devs => {
            const audioInputs = devs.filter(d => d.kind === 'audioinput');
            setDevices(audioInputs);
            if (audioInputs.length > 0) setSelectedDeviceId(audioInputs[0].deviceId);
        });

        return () => {
            socket.off('connect');
            socket.off('disconnect');
            socket.off('status');
            socket.off('audio_data');
            stopMicVisualizer();
        };
    }, []);

    // Start/Stop Mic Visualizer
    useEffect(() => {
        if (selectedDeviceId) {
            startMicVisualizer(selectedDeviceId);
        }
    }, [selectedDeviceId]);

    const startMicVisualizer = async (deviceId) => {
        stopMicVisualizer();
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { deviceId: { exact: deviceId } }
            });

            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
            analyserRef.current = audioContextRef.current.createAnalyser();
            analyserRef.current.fftSize = 64;

            sourceRef.current = audioContextRef.current.createMediaStreamSource(stream);
            sourceRef.current.connect(analyserRef.current);

            const updateMicData = () => {
                if (!analyserRef.current) return;
                const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
                analyserRef.current.getByteFrequencyData(dataArray);
                setMicAudioData(Array.from(dataArray));
                animationFrameRef.current = requestAnimationFrame(updateMicData);
            };

            updateMicData();
        } catch (err) {
            console.error("Error accessing microphone:", err);
        }
    };

    const stopMicVisualizer = () => {
        if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
        if (sourceRef.current) sourceRef.current.disconnect();
        if (audioContextRef.current) audioContextRef.current.close();
    };

    const addMessage = (sender, text) => {
        setMessages(prev => [...prev, { sender, text, time: new Date().toLocaleTimeString() }]);
    };

    const toggleAudio = () => {
        if (isListening) {
            socket.emit('stop_audio');
            setIsListening(false);
        } else {
            // Find index of selected device to send to backend
            // Note: Backend uses PyAudio index, Frontend uses DeviceID. 
            // This is tricky. For now, we might just send the index in the list.
            const index = devices.findIndex(d => d.deviceId === selectedDeviceId);
            socket.emit('start_audio', { device_index: index >= 0 ? index : null });
            setIsListening(true);
        }
    };

    const handleSend = (e) => {
        if (e.key === 'Enter' && inputValue.trim()) {
            socket.emit('user_input', { text: inputValue });
            addMessage('You', inputValue);
            setInputValue('');
        }
    };

    const handleMinimize = () => ipcRenderer.send('window-minimize');
    const handleMaximize = () => ipcRenderer.send('window-maximize');
    const handleClose = () => ipcRenderer.send('window-close');

    return (
        <div className="h-screen w-screen bg-black text-cyan-100 font-mono overflow-hidden flex flex-col relative selection:bg-cyan-900 selection:text-white">
            {/* Background Grid/Effects */}
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-gray-900 via-black to-black opacity-80 z-0 pointer-events-none"></div>
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 z-0 pointer-events-none"></div>

            {/* Top Bar (Draggable) */}
            <div className="z-50 flex items-center justify-between p-2 border-b border-cyan-900/30 bg-black/80 backdrop-blur-md select-none" style={{ WebkitAppRegion: 'drag' }}>
                <div className="flex items-center gap-4 pl-2">
                    <h1 className="text-xl font-bold tracking-[0.2em] text-cyan-400 drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">
                        A.D.A
                    </h1>
                    <div className="text-[10px] text-cyan-700 border border-cyan-900 px-1 rounded">
                        V2.0.0
                    </div>
                </div>

                {/* Top Visualizer (User Mic) */}
                <div className="flex-1 flex justify-center mx-4">
                    <TopAudioBar audioData={micAudioData} />
                </div>

                <div className="flex items-center gap-2 pr-2" style={{ WebkitAppRegion: 'no-drag' }}>
                    <button onClick={handleMinimize} className="p-1 hover:bg-cyan-900/50 rounded text-cyan-500 transition-colors">
                        <Minus size={18} />
                    </button>
                    <button onClick={handleMaximize} className="p-1 hover:bg-cyan-900/50 rounded text-cyan-500 transition-colors">
                        <div className="w-[14px] h-[14px] border-2 border-current rounded-[2px]" />
                    </button>
                    <button onClick={handleClose} className="p-1 hover:bg-red-900/50 rounded text-red-500 transition-colors">
                        <X size={18} />
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 relative z-10 flex flex-col items-center justify-center">
                {/* Central Visualizer (AI Audio) */}
                <div className="w-full h-full absolute inset-0 flex items-center justify-center pointer-events-none">
                    <Visualizer audioData={aiAudioData} isListening={isListening} />
                </div>

                {/* Settings Modal */}
                {showSettings && (
                    <div className="absolute top-20 right-10 bg-black/90 border border-cyan-500/50 p-4 rounded-lg z-50 w-64 backdrop-blur-xl shadow-[0_0_30px_rgba(6,182,212,0.2)]">
                        <h3 className="text-cyan-400 font-bold mb-2 text-sm uppercase tracking-wider">Audio Input</h3>
                        <select
                            value={selectedDeviceId}
                            onChange={(e) => setSelectedDeviceId(e.target.value)}
                            className="w-full bg-gray-900 border border-cyan-800 rounded p-2 text-xs text-cyan-100 focus:border-cyan-400 outline-none"
                        >
                            {devices.map((device, i) => (
                                <option key={device.deviceId} value={device.deviceId}>
                                    {device.label || `Microphone ${i + 1}`}
                                </option>
                            ))}
                        </select>
                    </div>
                )}

                {/* Chat Overlay */}
                <div className="absolute bottom-24 w-full max-w-2xl px-4 pointer-events-auto">
                    <div className="flex flex-col gap-2 max-h-60 overflow-y-auto mb-4 scrollbar-hide mask-image-gradient">
                        {messages.slice(-5).map((msg, i) => (
                            <div key={i} className="text-sm">
                                <span className="text-cyan-600">[{msg.time}]</span> <span className="font-bold text-cyan-400">{msg.sender}:</span> {msg.text}
                            </div>
                        ))}
                    </div>

                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={handleSend}
                            placeholder="ENTER COMMAND..."
                            className="flex-1 bg-black/50 border border-cyan-800 rounded p-3 text-cyan-100 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition-all placeholder-cyan-800"
                        />
                    </div>
                </div>
            </div>

            {/* Footer Controls */}
            <div className="z-20 p-6 flex justify-center gap-6 pb-10">
                <button
                    onClick={toggleAudio}
                    className={`p-4 rounded-full border-2 transition-all duration-300 ${isListening
                            ? 'border-red-500 bg-red-500/10 text-red-500 hover:bg-red-500/20 shadow-[0_0_20px_rgba(239,68,68,0.3)]'
                            : 'border-cyan-500 bg-cyan-500/10 text-cyan-500 hover:bg-cyan-500/20 shadow-[0_0_20px_rgba(6,182,212,0.3)]'
                        }`}
                >
                    {isListening ? <MicOff size={32} /> : <Mic size={32} />}
                </button>

                <button
                    onClick={() => setShowSettings(!showSettings)}
                    className={`p-4 rounded-full border-2 transition-all ${showSettings ? 'border-cyan-400 text-cyan-400 bg-cyan-900/20' : 'border-cyan-900 text-cyan-700 hover:border-cyan-500 hover:text-cyan-500'
                        }`}
                >
                    <Settings size={32} />
                </button>
            </div>
        </div>
    );
}

export default App;
