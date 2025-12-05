import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

const Visualizer = ({ audioData, isListening }) => {
    const canvasRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let animationId;

        const draw = () => {
            const width = canvas.width;
            const height = canvas.height;
            const centerX = width / 2;
            const centerY = height / 2;
            const radius = 150;

            ctx.clearRect(0, 0, width, height);

            // Base Circle (Glow)
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius - 10, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(6, 182, 212, 0.1)';
            ctx.lineWidth = 2;
            ctx.stroke();

            if (!isListening) {
                // Idle State: Breathing Circle
                const time = Date.now() / 1000;
                const breath = Math.sin(time * 2) * 5;

                ctx.beginPath();
                ctx.arc(centerX, centerY, radius + breath, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(34, 211, 238, 0.5)';
                ctx.lineWidth = 4;
                ctx.shadowBlur = 20;
                ctx.shadowColor = '#22d3ee';
                ctx.stroke();
                ctx.shadowBlur = 0;
            } else {
                // Active State: Frequency Bars in Circle
                const bars = 64;
                const step = (Math.PI * 2) / bars;

                for (let i = 0; i < bars; i++) {
                    const value = audioData[i % audioData.length] || 0;
                    const percent = value / 255;
                    const barHeight = 20 + percent * 100; // Dynamic height

                    const angle = i * step;

                    // Start point (on circle)
                    const x1 = centerX + Math.cos(angle) * radius;
                    const y1 = centerY + Math.sin(angle) * radius;

                    // End point (outwards)
                    const x2 = centerX + Math.cos(angle) * (radius + barHeight);
                    const y2 = centerY + Math.sin(angle) * (radius + barHeight);

                    ctx.beginPath();
                    ctx.moveTo(x1, y1);
                    ctx.lineTo(x2, y2);

                    ctx.strokeStyle = `rgba(34, 211, 238, ${0.5 + percent})`;
                    ctx.lineWidth = 4;
                    ctx.lineCap = 'round';

                    ctx.shadowBlur = 15 * percent;
                    ctx.shadowColor = '#22d3ee';

                    ctx.stroke();
                    ctx.shadowBlur = 0;
                }
            }

            animationId = requestAnimationFrame(draw);
        };

        draw();
        return () => cancelAnimationFrame(animationId);
    }, [audioData, isListening]);

    return (
        <div className="relative">
            {/* Central Logo/Text */}
            <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
                <motion.div
                    animate={{ scale: isListening ? [1, 1.1, 1] : 1 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                    className="text-cyan-100 font-bold text-4xl tracking-widest drop-shadow-[0_0_15px_rgba(34,211,238,0.8)]"
                >
                    A.D.A
                </motion.div>
            </div>

            <canvas
                ref={canvasRef}
                width={800}
                height={800}
                className="w-[600px] h-[600px]"
            />
        </div>
    );
};

export default Visualizer;
