import React, { useEffect, useState, useRef } from 'react';
import io from 'socket.io-client';
import Visualizer from './components/Visualizer';
import TopAudioBar from './components/TopAudioBar';
import { Mic, MicOff, Settings, X, Minus, Power, Video, VideoOff, Layout } from 'lucide-react';
import { FilesetResolver, HandLandmarker } from '@mediapipe/tasks-vision';

const socket = io('http://localhost:8000');
const { ipcRenderer } = window.require('electron');

function App() {
    const [status, setStatus] = useState('Disconnected');
    const [isConnected, setIsConnected] = useState(false); // Power state
    const [isMuted, setIsMuted] = useState(false); // Mic state
    const [isVideoOn, setIsVideoOn] = useState(false); // Video state
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [aiAudioData, setAiAudioData] = useState(new Array(64).fill(0));
    const [micAudioData, setMicAudioData] = useState(new Array(32).fill(0));
    const [fps, setFps] = useState(0);

    const [devices, setDevices] = useState([]);
    const [selectedDeviceId, setSelectedDeviceId] = useState('');
    const [showSettings, setShowSettings] = useState(false);

    // Modular Mode State
    const [isModularMode, setIsModularMode] = useState(false);
    const [elementPositions, setElementPositions] = useState({
        video: { x: 40, y: 80 }, // Initial positions (approximate)
        visualizer: { x: window.innerWidth / 2, y: window.innerHeight / 2 },
        chat: { x: window.innerWidth / 2, y: window.innerHeight - 100 }
    });
    const [activeDragElement, setActiveDragElement] = useState(null);

    // Hand Control State
    const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 });
    const [isPinching, setIsPinching] = useState(false);
    const handLandmarkerRef = useRef(null);

    // Web Audio Context for Mic Visualization
    const audioContextRef = useRef(null);
    const analyserRef = useRef(null);
    const sourceRef = useRef(null);
    const animationFrameRef = useRef(null);

    // Video Refs
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const videoIntervalRef = useRef(null);
    const lastFrameTimeRef = useRef(0);
    const frameCountRef = useRef(0);
    const lastVideoTimeRef = useRef(-1);

    // Ref to track video state for the loop (avoids closure staleness)
    const isVideoOnRef = useRef(false);
    const isModularModeRef = useRef(false);
    const elementPositionsRef = useRef(elementPositions);
    const activeDragElementRef = useRef(null);
    const lastActiveDragElementRef = useRef(null);
    const lastCursorPosRef = useRef({ x: 0, y: 0 });

    // Smoothing and Snapping Refs
    const smoothedCursorPosRef = useRef({ x: 0, y: 0 });
    const snapStateRef = useRef({ isSnapped: false, element: null, snapPos: { x: 0, y: 0 } });

    // Update refs when state changes
    useEffect(() => {
        isModularModeRef.current = isModularMode;
        elementPositionsRef.current = elementPositions;
    }, [isModularMode, elementPositions]);

    useEffect(() => {
        // Socket IO Setup
        socket.on('connect', () => setStatus('Connected'));
        socket.on('disconnect', () => setStatus('Disconnected'));
        socket.on('status', (data) => addMessage('System', data.msg));
        socket.on('audio_data', (data) => {
            setAiAudioData(data.data);
        });

        // Get Audio Devices
        navigator.mediaDevices.enumerateDevices().then(devs => {
            const audioInputs = devs.filter(d => d.kind === 'audioinput');
            setDevices(audioInputs);
            if (audioInputs.length > 0) setSelectedDeviceId(audioInputs[0].deviceId);
        });

        // Initialize Hand Landmarker
        const initHandLandmarker = async () => {
            try {
                console.log("Initializing HandLandmarker...");

                // 1. Verify Model File
                console.log("Fetching model file...");
                const response = await fetch('/hand_landmarker.task');
                if (!response.ok) {
                    throw new Error(`Failed to fetch model: ${response.status} ${response.statusText}`);
                }
                console.log("Model file found:", response.headers.get('content-type'), response.headers.get('content-length'));

                // 2. Initialize Vision
                console.log("Initializing FilesetResolver...");
                const vision = await FilesetResolver.forVisionTasks(
                    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm"
                );
                console.log("FilesetResolver initialized.");

                // 3. Create Landmarker
                console.log("Creating HandLandmarker (CPU)...");
                handLandmarkerRef.current = await HandLandmarker.createFromOptions(vision, {
                    baseOptions: {
                        modelAssetPath: `/hand_landmarker.task`,
                        delegate: "CPU" // Force CPU to avoid GPU context issues
                    },
                    runningMode: "VIDEO",
                    numHands: 1
                });
                console.log("HandLandmarker initialized successfully!");
                addMessage('System', 'Hand Tracking Ready');

            } catch (error) {
                console.error("Failed to initialize HandLandmarker:", error);
                addMessage('System', `Hand Tracking Error: ${error.message}`);
            }
        };
        initHandLandmarker();

        return () => {
            socket.off('connect');
            socket.off('disconnect');
            socket.off('status');
            socket.off('audio_data');
            stopMicVisualizer();
            stopVideo();
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

    const startVideo = async () => {
        try {
            // Request 16:9 aspect ratio
            const stream = await navigator.mediaDevices.getUserMedia({ video: { aspectRatio: 16 / 9, width: { ideal: 1280 } } });
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                videoRef.current.play();
            }

            setIsVideoOn(true);
            isVideoOnRef.current = true; // Update ref for loop

            console.log("Starting video loop...");
            requestAnimationFrame(predictWebcam);

        } catch (err) {
            console.error("Error accessing camera:", err);
            addMessage('System', 'Error accessing camera');
        }
    };

    const predictWebcam = () => {
        // Use ref for checking state to avoid closure staleness
        if (!videoRef.current || !canvasRef.current || !isVideoOnRef.current) {
            return;
        }

        // Check if video has valid dimensions to prevent MediaPipe crash
        if (videoRef.current.readyState < 2 || videoRef.current.videoWidth === 0 || videoRef.current.videoHeight === 0) {
            requestAnimationFrame(predictWebcam);
            return;
        }

        // 1. Draw Video to Canvas
        const ctx = canvasRef.current.getContext('2d');

        // Ensure canvas matches video dimensions
        if (canvasRef.current.width !== videoRef.current.videoWidth || canvasRef.current.height !== videoRef.current.videoHeight) {
            canvasRef.current.width = videoRef.current.videoWidth;
            canvasRef.current.height = videoRef.current.videoHeight;
        }

        ctx.drawImage(videoRef.current, 0, 0, canvasRef.current.width, canvasRef.current.height);

        // 2. Send Frame to Backend (Throttled)
        // Only send if connected
        if (isConnected) {
            // Simple throttle: every 5th frame roughly
            if (frameCountRef.current % 5 === 0) {
                canvasRef.current.toBlob((blob) => {
                    if (blob) {
                        socket.emit('video_frame', { image: blob });
                    }
                }, 'image/jpeg', 0.5);
            }
        }

        // 3. Hand Tracking
        let startTimeMs = performance.now();
        if (handLandmarkerRef.current && videoRef.current.currentTime !== lastVideoTimeRef.current) {
            lastVideoTimeRef.current = videoRef.current.currentTime;
            const results = handLandmarkerRef.current.detectForVideo(videoRef.current, startTimeMs);

            // Log every 100 frames to confirm loop is running
            if (frameCountRef.current % 100 === 0) {
                console.log("Tracking loop running... Last result:", results.landmarks.length > 0 ? "Hand Found" : "No Hand");
            }

            if (results.landmarks && results.landmarks.length > 0) {
                const landmarks = results.landmarks[0];

                // Log on first detection
                if (cursorPos.x === 0 && cursorPos.y === 0) {
                    console.log("First hand detection!", landmarks);
                }

                // Index Finger Tip (8)
                const indexTip = landmarks[8];
                // Thumb Tip (4)
                const thumbTip = landmarks[4];

                // Map to Screen Coords
                // User requested to flip the cursor movement: "when my hand moves left the cursor moves right flip this"
                // Previously: (1 - indexTip.x). Now: indexTip.x
                const targetX = indexTip.x * window.innerWidth;
                const targetY = indexTip.y * window.innerHeight;

                // 1. Smoothing (Lerp)
                // Factor 0.2 = smooth but responsive. Lower = smoother/slower.
                const lerpFactor = 0.2;
                smoothedCursorPosRef.current.x = smoothedCursorPosRef.current.x + (targetX - smoothedCursorPosRef.current.x) * lerpFactor;
                smoothedCursorPosRef.current.y = smoothedCursorPosRef.current.y + (targetY - smoothedCursorPosRef.current.y) * lerpFactor;

                let finalX = smoothedCursorPosRef.current.x;
                let finalY = smoothedCursorPosRef.current.y;

                // 2. Snap-to-Button Logic
                const SNAP_THRESHOLD = 50; // Pixels to snap
                const UNSNAP_THRESHOLD = 100; // Pixels to unsnap (Hysteresis)

                if (snapStateRef.current.isSnapped) {
                    // Check if we should unsnap
                    const dist = Math.sqrt(
                        Math.pow(finalX - snapStateRef.current.snapPos.x, 2) +
                        Math.pow(finalY - snapStateRef.current.snapPos.y, 2)
                    );

                    if (dist > UNSNAP_THRESHOLD) {
                        snapStateRef.current = { isSnapped: false, element: null, snapPos: { x: 0, y: 0 } };
                    } else {
                        // Stay snapped
                        finalX = snapStateRef.current.snapPos.x;
                        finalY = snapStateRef.current.snapPos.y;
                    }
                } else {
                    // Check if we should snap
                    // Find all interactive elements
                    const targets = Array.from(document.querySelectorAll('button, input, select, .draggable'));
                    let closest = null;
                    let minDist = Infinity;

                    for (const el of targets) {
                        const rect = el.getBoundingClientRect();
                        const centerX = rect.left + rect.width / 2;
                        const centerY = rect.top + rect.height / 2;
                        const dist = Math.sqrt(Math.pow(finalX - centerX, 2) + Math.pow(finalY - centerY, 2));

                        if (dist < minDist) {
                            minDist = dist;
                            closest = { el, centerX, centerY };
                        }
                    }

                    if (closest && minDist < SNAP_THRESHOLD) {
                        snapStateRef.current = {
                            isSnapped: true,
                            element: closest.el,
                            snapPos: { x: closest.centerX, y: closest.centerY }
                        };
                        finalX = closest.centerX;
                        finalY = closest.centerY;
                    }
                }

                setCursorPos({ x: finalX, y: finalY });


                // Pinch Detection (Distance between Index and Thumb)
                const distance = Math.sqrt(
                    Math.pow(indexTip.x - thumbTip.x, 2) + Math.pow(indexTip.y - thumbTip.y, 2)
                );

                const isPinchNow = distance < 0.05; // Threshold
                if (isPinchNow && !isPinching) {
                    console.log("Click triggered at", finalX, finalY);
                    const el = document.elementFromPoint(finalX, finalY);
                    if (el) {
                        // Find closest clickable element (button, input, etc.)
                        const clickable = el.closest('button, input, a, [role="button"]');
                        if (clickable && typeof clickable.click === 'function') {
                            clickable.click();
                        } else if (typeof el.click === 'function') {
                            el.click();
                        }
                    }
                }
                setIsPinching(isPinchNow);

                // Modular Mode Dragging Logic
                if (isModularModeRef.current) {
                    // Fist Detection (Simple Heuristic: Tips close to Wrist)
                    // Wrist is 0. Tips are 8, 12, 16, 20. MCPs are 5, 9, 13, 17.
                    // Check if tips are closer to wrist than MCPs (folded)
                    const isFingerFolded = (tipIdx, mcpIdx) => {
                        const tip = landmarks[tipIdx];
                        const mcp = landmarks[mcpIdx];
                        const wrist = landmarks[0];
                        const distTip = Math.sqrt(Math.pow(tip.x - wrist.x, 2) + Math.pow(tip.y - wrist.y, 2));
                        const distMcp = Math.sqrt(Math.pow(mcp.x - wrist.x, 2) + Math.pow(mcp.y - wrist.y, 2));
                        return distTip < distMcp; // Folded if tip is closer
                    };

                    const isFist = isFingerFolded(8, 5) && isFingerFolded(12, 9) && isFingerFolded(16, 13) && isFingerFolded(20, 17);

                    if (isFist) {
                        if (!activeDragElementRef.current) {
                            // Check collision with draggable elements
                            const elements = ['video', 'visualizer', 'chat'];
                            for (const id of elements) {
                                const el = document.getElementById(id);
                                if (el) {
                                    const rect = el.getBoundingClientRect();
                                    if (finalX >= rect.left && finalX <= rect.right && finalY >= rect.top && finalY <= rect.bottom) {
                                        activeDragElementRef.current = id;
                                        break;
                                    }
                                }
                            }
                        }

                        if (activeDragElementRef.current) {
                            const dx = finalX - lastCursorPosRef.current.x;
                            const dy = finalY - lastCursorPosRef.current.y;

                            // Update position
                            updateElementPosition(activeDragElementRef.current, dx, dy);
                        }
                    } else {
                        activeDragElementRef.current = null;
                    }

                    // Sync state for visual feedback (only on change)
                    if (activeDragElementRef.current !== lastActiveDragElementRef.current) {
                        setActiveDragElement(activeDragElementRef.current);
                        lastActiveDragElementRef.current = activeDragElementRef.current;
                    }
                }

                lastCursorPosRef.current = { x: finalX, y: finalY };

                // Draw Skeleton
                drawSkeleton(ctx, landmarks);
            }
        }

        // 4. FPS Calculation
        const now = performance.now();
        frameCountRef.current++;
        if (now - lastFrameTimeRef.current >= 1000) {
            setFps(frameCountRef.current);
            frameCountRef.current = 0;
            lastFrameTimeRef.current = now;
        }

        if (isVideoOnRef.current) {
            requestAnimationFrame(predictWebcam);
        }
    };

    const drawSkeleton = (ctx, landmarks) => {
        ctx.strokeStyle = '#00FFFF';
        ctx.lineWidth = 2;

        // Connections
        const connections = HandLandmarker.HAND_CONNECTIONS;
        for (const connection of connections) {
            const start = landmarks[connection.start];
            const end = landmarks[connection.end];
            ctx.beginPath();
            ctx.moveTo(start.x * canvasRef.current.width, start.y * canvasRef.current.height);
            ctx.lineTo(end.x * canvasRef.current.width, end.y * canvasRef.current.height);
            ctx.stroke();
        }
    };

    const stopVideo = () => {
        if (videoRef.current && videoRef.current.srcObject) {
            videoRef.current.srcObject.getTracks().forEach(track => track.stop());
            videoRef.current.srcObject = null;
        }
        setIsVideoOn(false);
        isVideoOnRef.current = false; // Update ref
        setFps(0);
    };

    const toggleVideo = () => {
        if (isVideoOn) {
            stopVideo();
        } else {
            startVideo();
        }
    };

    const addMessage = (sender, text) => {
        setMessages(prev => [...prev, { sender, text, time: new Date().toLocaleTimeString() }]);
    };

    const togglePower = () => {
        if (isConnected) {
            socket.emit('stop_audio');
            setIsConnected(false);
            setIsMuted(false); // Reset mute state
        } else {
            const index = devices.findIndex(d => d.deviceId === selectedDeviceId);
            socket.emit('start_audio', { device_index: index >= 0 ? index : null });
            setIsConnected(true);
            setIsMuted(false); // Start unmuted
        }
    };

    const toggleMute = () => {
        if (!isConnected) return; // Can't mute if not connected

        if (isMuted) {
            socket.emit('resume_audio');
            setIsMuted(false);
        } else {
            socket.emit('pause_audio');
            setIsMuted(true);
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

    const updateElementPosition = (id, dx, dy) => {
        setElementPositions(prev => ({
            ...prev,
            [id]: {
                x: prev[id].x + dx,
                y: prev[id].y + dy
            }
        }));
    };

    return (
        <div className="h-screen w-screen bg-black text-cyan-100 font-mono overflow-hidden flex flex-col relative selection:bg-cyan-900 selection:text-white">
            {/* Hand Cursor */}
            {isVideoOn && (
                <div
                    className={`fixed w-6 h-6 border-2 rounded-full pointer-events-none z-[100] transition-transform duration-75 ${isPinching ? 'bg-cyan-400 border-cyan-400 scale-75' : 'border-cyan-400'}`}
                    style={{
                        left: cursorPos.x,
                        top: cursorPos.y,
                        transform: 'translate(-50%, -50%)'
                    }}
                />
            )}

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
                    {/* FPS Counter */}
                    {isVideoOn && (
                        <div className="text-[10px] text-green-500 border border-green-900 px-1 rounded ml-2">
                            FPS: {fps}
                        </div>
                    )}
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
                <div
                    id="visualizer"
                    className={`absolute flex items-center justify-center pointer-events-none transition-all duration-200 ${isModularMode ? (activeDragElement === 'visualizer' ? 'border-2 border-green-500 bg-green-500/20' : 'border-2 border-yellow-500/50 bg-yellow-500/10') + ' rounded-lg' : ''}`}
                    style={{
                        left: elementPositions.visualizer.x,
                        top: elementPositions.visualizer.y,
                        transform: 'translate(-50%, -50%)',
                        width: '600px', // Fixed size for modular mode
                        height: '400px'
                    }}
                >
                    <Visualizer audioData={aiAudioData} isListening={isConnected && !isMuted} />
                    {isModularMode && <div className={`absolute top-2 right-2 text-xs ${activeDragElement === 'visualizer' ? 'text-green-500' : 'text-yellow-500'}`}>VISUALIZER</div>}
                </div>

                {/* Video Feed Overlay */}
                <div
                    id="video"
                    className={`absolute transition-all duration-200 ${isVideoOn ? 'opacity-100' : 'opacity-0 pointer-events-none'} ${isModularMode ? (activeDragElement === 'video' ? 'border-2 border-green-500 bg-green-500/20' : 'border-2 border-yellow-500/50 bg-yellow-500/10') + ' rounded-lg p-2' : ''}`}
                    style={{
                        left: elementPositions.video.x,
                        top: elementPositions.video.y,
                    }}
                >
                    {/* 16:9 Aspect Ratio Container */}
                    <div className="relative border border-cyan-500/50 rounded-lg overflow-hidden shadow-[0_0_20px_rgba(6,182,212,0.3)] w-80 aspect-video bg-black">
                        {/* Hidden Video Element (Source) */}
                        <video ref={videoRef} autoPlay muted className="absolute inset-0 w-full h-full object-cover opacity-0" />

                        <div className="absolute top-2 left-2 text-[10px] text-cyan-500 bg-black/50 px-1 rounded z-10">CAM_01</div>

                        {/* Canvas for Displaying Video + Skeleton (Ensures overlap) */}
                        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />
                    </div>
                    {isModularMode && <div className={`absolute -top-6 left-0 text-xs ${activeDragElement === 'video' ? 'text-green-500' : 'text-yellow-500'}`}>VIDEO FEED</div>}
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
                <div
                    id="chat"
                    className={`absolute w-full max-w-2xl px-4 pointer-events-auto transition-all duration-200 ${isModularMode ? (activeDragElement === 'chat' ? 'border-2 border-green-500 bg-green-500/20' : 'border-2 border-yellow-500/50 bg-yellow-500/10') + ' rounded-lg p-4' : ''}`}
                    style={{
                        left: elementPositions.chat.x,
                        top: elementPositions.chat.y,
                        transform: 'translate(-50%, 0)'
                    }}
                >
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
                    {isModularMode && <div className={`absolute -top-6 left-0 text-xs ${activeDragElement === 'chat' ? 'text-green-500' : 'text-yellow-500'}`}>CHAT MODULE</div>}
                </div>
            </div>

            {/* Footer Controls */}
            <div className="z-20 p-6 flex justify-center gap-6 pb-10">
                {/* Power Button */}
                <button
                    onClick={togglePower}
                    className={`p-4 rounded-full border-2 transition-all duration-300 ${isConnected
                        ? 'border-green-500 bg-green-500/10 text-green-500 hover:bg-green-500/20 shadow-[0_0_20px_rgba(34,197,94,0.3)]'
                        : 'border-gray-600 bg-gray-600/10 text-gray-500 hover:bg-gray-600/20'
                        }`}
                >
                    <Power size={32} />
                </button>

                {/* Mute Button */}
                <button
                    onClick={toggleMute}
                    disabled={!isConnected}
                    className={`p-4 rounded-full border-2 transition-all duration-300 ${!isConnected
                        ? 'border-gray-800 text-gray-800 cursor-not-allowed'
                        : isMuted
                            ? 'border-red-500 bg-red-500/10 text-red-500 hover:bg-red-500/20 shadow-[0_0_20px_rgba(239,68,68,0.3)]'
                            : 'border-cyan-500 bg-cyan-500/10 text-cyan-500 hover:bg-cyan-500/20 shadow-[0_0_20px_rgba(6,182,212,0.3)]'
                        }`}
                >
                    {isMuted ? <MicOff size={32} /> : <Mic size={32} />}
                </button>

                {/* Video Button */}
                <button
                    onClick={toggleVideo}
                    className={`p-4 rounded-full border-2 transition-all duration-300 ${isVideoOn
                        ? 'border-purple-500 bg-purple-500/10 text-purple-500 hover:bg-purple-500/20 shadow-[0_0_20px_rgba(168,85,247,0.3)]'
                        : 'border-cyan-900 text-cyan-700 hover:border-cyan-500 hover:text-cyan-500'
                        }`}
                >
                    {isVideoOn ? <Video size={32} /> : <VideoOff size={32} />}
                </button>

                {/* Settings Button */}
                <button
                    onClick={() => setShowSettings(!showSettings)}
                    className={`p-4 rounded-full border-2 transition-all ${showSettings ? 'border-cyan-400 text-cyan-400 bg-cyan-900/20' : 'border-cyan-900 text-cyan-700 hover:border-cyan-500 hover:text-cyan-500'
                        }`}
                >
                    <Settings size={32} />
                </button>

                {/* Layout Button */}
                <button
                    onClick={() => setIsModularMode(!isModularMode)}
                    className={`p-4 rounded-full border-2 transition-all duration-300 ${isModularMode
                        ? 'border-yellow-500 bg-yellow-500/10 text-yellow-500 hover:bg-yellow-500/20 shadow-[0_0_20px_rgba(234,179,8,0.3)]'
                        : 'border-cyan-900 text-cyan-700 hover:border-cyan-500 hover:text-cyan-500'
                        }`}
                >
                    <Layout size={32} />
                </button>
            </div>
        </div>
    );
}

export default App;
