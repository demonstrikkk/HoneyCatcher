import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, Music, Waves, Download, Share2, MoreHorizontal } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const VoicePlayer = ({ audioUrl, transcription, naturalizedText, autoPlay = true, timestamp }) => {
    const [isPlaying, setIsPlaying] = useState(false);
    const [progress, setProgress] = useState(0);
    const audioRef = useRef(null);

    // Ensure audioUrl has the correct base URL if it's a relative API path
    const formattedAudioUrl = audioUrl?.startsWith('/api')
        ? `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}${audioUrl}`
        : audioUrl;

    useEffect(() => {
        if (formattedAudioUrl && autoPlay) {
            // Slight delay to allow audio to buffer
            const timer = setTimeout(() => {
                if (audioRef.current) {
                    audioRef.current.play().catch(e => console.warn("Autoplay blocked:", e));
                }
            }, 800);
            return () => clearTimeout(timer);
        }
    }, [formattedAudioUrl, autoPlay]);

    const togglePlayback = () => {
        if (audioRef.current) {
            if (isPlaying) {
                audioRef.current.pause();
            } else {
                audioRef.current.play();
            }
            setIsPlaying(!isPlaying);
        }
    };

    return (
        <div className="group w-full bg-slate-900/40 backdrop-blur-2xl border border-white/5 rounded-3xl p-6 transition-all duration-500 hover:bg-slate-900/60 hover:border-emerald-500/30 relative">
            {/* Glossy Overlay */}
            <div className="absolute top-0 left-0 w-full h-1/2 bg-gradient-to-b from-white/5 to-transparent pointer-events-none" />

            <div className="flex flex-col gap-5">
                {/* Top Bar */}
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                            <Waves className="w-5 h-5" />
                        </div>
                        <div>
                            <h4 className="text-xs font-bold text-white uppercase tracking-widest">Acoustic Analysis</h4>
                            <p className="text-[10px] text-slate-500 font-mono tracking-tighter">
                                {timestamp ? new Date(timestamp).toLocaleTimeString() : 'SYNTHESIZED LIVE'}
                            </p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button className="p-2 rounded-lg hover:bg-white/5 text-slate-500 transition-colors">
                            <Download className="w-4 h-4" />
                        </button>
                        <button className="p-2 rounded-lg hover:bg-white/5 text-slate-500 transition-colors">
                            <MoreHorizontal className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                {/* Player Interface */}
                <div className="flex items-center gap-5 p-4 bg-black/40 rounded-2xl border border-white/5">
                    <button
                        onClick={togglePlayback}
                        className="w-14 h-14 rounded-full bg-emerald-600 flex items-center justify-center text-white hover:bg-emerald-500 transition-all duration-300 shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:scale-105 active:scale-95"
                    >
                        {isPlaying ? <Pause className="w-6 h-6 fill-white" /> : <Play className="w-6 h-6 ml-1 fill-white" />}
                    </button>

                    <div className="flex-1 space-y-3">
                        <div className="flex justify-between items-end">
                            <div className="flex items-center gap-1.5">
                                <span className={`w-1.5 h-1.5 rounded-full ${isPlaying ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
                                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest">
                                    {isPlaying ? 'Synthesizing...' : 'Transmitted'}
                                </span>
                            </div>
                            <span className="text-[10px] font-mono text-slate-500">0:00 / 0:04</span>
                        </div>

                        <div className="relative h-2 w-full bg-slate-800/50 rounded-full overflow-hidden">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: isPlaying ? '100%' : '0%' }}
                                transition={{ duration: 4, ease: "linear" }}
                                onAnimationComplete={() => setIsPlaying(false)}
                                className="absolute left-0 top-0 h-full bg-gradient-to-r from-emerald-600 to-teal-500 shadow-[0_0_15px_rgba(16,185,129,0.6)]"
                            />
                            {/* Static Pulse Grid Overlay */}
                            <div className="absolute inset-0 opacity-20 bg-[radial-gradient(circle,white_1px,transparent_1px)] bg-[size:8px_8px]" />
                        </div>
                    </div>
                </div>

                {/* Content Section */}
                <div className="space-y-4">
                    <AnimatePresence mode="wait">
                        {naturalizedText && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="relative p-4 bg-emerald-500/5 border-l-2 border-emerald-500/30 rounded-r-xl"
                            >
                                <div className="absolute top-2 right-3">
                                    <span className="text-[8px] font-black bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full uppercase tracking-tighter">Naturalized</span>
                                </div>
                                <p className="text-sm text-emerald-100 font-medium italic leading-relaxed pr-8">
                                    "{naturalizedText}"
                                </p>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {transcription && (
                        <div className="px-4">
                            <div className="flex items-center gap-2 mb-2">
                                <div className="w-1 h-3 bg-slate-700 rounded-full" />
                                <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Base Transcript</p>
                            </div>
                            <p className="text-sm text-slate-400 leading-relaxed font-light">
                                {transcription}
                            </p>
                        </div>
                    )}
                </div>
            </div>

            <audio
                ref={audioRef}
                src={formattedAudioUrl}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onEnded={() => setIsPlaying(false)}
                className="hidden"
            />
        </div>
    );
};

export default VoicePlayer;
