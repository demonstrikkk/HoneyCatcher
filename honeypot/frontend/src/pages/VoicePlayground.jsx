import React, { useState, useEffect, useRef } from 'react';
import { Mic, Shield, Volume2, History, Languages, ArrowLeft, Terminal, Cpu, Ghost, Zap, Waves, Activity } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import VoiceRecorder from '../components/VoiceRecorder';
import VoicePlayer from '../components/VoicePlayer';
import AISuggestionPanel from '../components/AISuggestionPanel';
import Navbar from '../components/Navbar';

const VoicePlayground = () => {
    const [sessionId] = useState(`voice-session-${Math.random().toString(36).substr(2, 9)}`);
    const [mode, setMode] = useState('ai_speaks');
    const [history, setHistory] = useState([]);
    const [lastResult, setLastResult] = useState(null);
    const timelineEndRef = useRef(null);

    const handleTranscription = (result) => {
        setLastResult(result);
        const newHistory = [
            ...history,
            { role: 'scammer', text: result.transcription, timestamp: new Date() },
            {
                role: 'agent',
                text: result.reply,
                naturalized: result.naturalizedReply,
                audioUrl: result.audioUrl,
                timestamp: new Date()
            }
        ];
        setHistory(newHistory);
    };

    useEffect(() => {
        timelineEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [history]);

    return (
        <div className="min-h-screen bg-[#020202] text-slate-300 selection:bg-emerald-500/30 overflow-x-hidden font-sans">
            {/* Immersive Background Effects */}
            <div className="fixed inset-0 pointer-events-none overflow-hidden">
                <div className="absolute top-0 -left-1/4 w-1/2 h-1/2 bg-emerald-500/5 blur-[120px] rounded-full animate-pulse" />
                <div className="absolute bottom-0 -right-1/4 w-1/2 h-1/2 bg-emerald-500/5 blur-[120px] rounded-full" />
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay" />
            </div>

            <Navbar />

            <main className="relative z-10 max-w-[1400px] mx-auto px-6 pt-24 pb-20">
                {/* Header Section */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-16"
                >
                    <div className="space-y-4">
                        <div className="flex items-center gap-3">
                            <div className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-black text-emerald-400 tracking-[0.2em] uppercase">
                                Experimental Lab v2.0
                            </div>
                            <div className="flex -space-x-2">
                                {[1, 2, 3].map(i => (
                                    <div key={i} className="w-5 h-5 rounded-full border-2 border-[#020202] bg-slate-800" />
                                ))}
                            </div>
                        </div>
                        <h1 className="text-5xl md:text-7xl font-black text-white tracking-tighter leading-none">
                            VOICE <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-teal-400">PLAYGROUND</span>
                        </h1>
                        <p className="max-w-xl text-slate-500 text-lg font-medium leading-relaxed">
                            Experience the future of deceptive cyber-defense. Intercept, analyze, and neutralize voice threats with our multilingual agentic core.
                        </p>
                    </div>

                    <div className="flex items-center gap-8 p-6 bg-white/[0.02] border border-white/5 rounded-3xl backdrop-blur-xl">
                        <div className="text-center">
                            <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-1">Status</p>
                            <div className="flex items-center gap-2 text-emerald-400">
                                <Activity className="w-4 h-4" />
                                <span className="text-sm font-black">ACTIVE</span>
                            </div>
                        </div>
                        <div className="w-[1px] h-10 bg-white/5" />
                        <div className="text-center">
                            <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-1">Encrypted</p>
                            <span className="text-sm font-black text-white">AES-256</span>
                        </div>
                    </div>
                </motion.div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                    {/* Control Panel (Left) */}
                    <div className="lg:col-span-5 space-y-10">
                        {/* Mode Switcher */}
                        <section className="space-y-4">
                            <h3 className="flex items-center gap-2 text-[11px] font-black text-slate-600 uppercase tracking-[0.3em] font-mono ml-1">
                                <Cpu className="w-3 h-3" /> Core Logic Path
                            </h3>
                            <div className="grid grid-cols-2 gap-4">
                                <button
                                    onClick={() => setMode('ai_speaks')}
                                    className={`relative group p-6 rounded-[2rem] border-2 transition-all duration-500 overflow-hidden ${mode === 'ai_speaks'
                                        ? 'bg-emerald-600/10 border-emerald-500/50 shadow-[0_20px_40px_rgba(16,185,129,0.15)] shadow-emerald-500/10'
                                        : 'bg-white/5 border-transparent hover:bg-white/10'
                                        }`}
                                >
                                    <div className={`absolute top-0 right-0 p-3 ${mode === 'ai_speaks' ? 'text-emerald-400' : 'text-slate-700'}`}>
                                        <Zap className="w-5 h-5 fill-current" />
                                    </div>
                                    <Volume2 className={`w-8 h-8 mb-4 ${mode === 'ai_speaks' ? 'text-emerald-400' : 'text-slate-500'}`} />
                                    <h4 className={`text-sm font-black uppercase tracking-tight mb-1 ${mode === 'ai_speaks' ? 'text-white' : 'text-slate-500'}`}>Fully Autonomous</h4>
                                    <p className="text-[10px] text-slate-600 font-medium leading-tight">AI synthesizes and responds directly.</p>
                                </button>

                                <button
                                    onClick={() => setMode('ai_suggests')}
                                    className={`relative group p-6 rounded-[2rem] border-2 transition-all duration-500 overflow-hidden ${mode === 'ai_suggests'
                                        ? 'bg-emerald-600/10 border-emerald-500/50 shadow-[0_20px_40px_rgba(16,185,129,0.15)] shadow-emerald-500/10'
                                        : 'bg-white/5 border-transparent hover:bg-white/10'
                                        }`}
                                >
                                    <div className={`absolute top-0 right-0 p-3 ${mode === 'ai_suggests' ? 'text-emerald-400' : 'text-slate-700'}`}>
                                        <Shield className="w-5 h-5 fill-current" />
                                    </div>
                                    <Ghost className={`w-8 h-8 mb-4 ${mode === 'ai_suggests' ? 'text-emerald-400' : 'text-slate-500'}`} />
                                    <h4 className={`text-sm font-black uppercase tracking-tight mb-1 ${mode === 'ai_suggests' ? 'text-white' : 'text-slate-500'}`}>AI Shadowing</h4>
                                    <p className="text-[10px] text-slate-600 font-medium leading-tight">AI provides the perfect script to speak.</p>
                                </button>
                            </div>
                        </section>

                        {/* Input System */}
                        <section className="space-y-4">
                            <h3 className="text-[11px] font-black text-slate-600 uppercase tracking-[0.3em] font-mono ml-1">Transmission Interface</h3>
                            <VoiceRecorder
                                sessionId={sessionId}
                                mode={mode}
                                onTranscription={handleTranscription}
                            />
                        </section>

                        {/* Real-time Intel Suggestion */}
                        <AnimatePresence>
                            {mode === 'ai_suggests' && lastResult && (
                                <section className="space-y-4">
                                    <h3 className="text-[11px] font-black text-emerald-500 uppercase tracking-[0.3em] font-mono ml-1">Tactical Analysis</h3>
                                    <AISuggestionPanel
                                        suggestion={lastResult.naturalizedReply}
                                        originalText={lastResult.reply}
                                    />
                                </section>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* Timeline Analysis (Right) */}
                    <div className="lg:col-span-7">
                        <div className="relative h-[600px] lg:h-[850px] bg-slate-900/30 backdrop-blur-3xl border border-white/5 rounded-[3rem] flex flex-col overflow-hidden shadow-3xl">
                            {/* Terminal Header */}
                            <div className="p-8 border-b border-white/5 flex items-center justify-between bg-black/20">
                                <div className="flex items-center gap-4">
                                    <div className="flex gap-1.5">
                                        <div className="w-3 h-3 rounded-full bg-rose-500/30" />
                                        <div className="w-3 h-3 rounded-full bg-amber-500/30" />
                                        <div className="w-3 h-3 rounded-full bg-emerald-500/30" />
                                    </div>
                                    <div className="h-6 w-[1px] bg-white/10 mx-2" />
                                    <div className="flex flex-col">
                                        <span className="text-[11px] font-black text-white uppercase tracking-widest flex items-center gap-2">
                                            <Terminal className="w-3 h-3 text-emerald-400" /> Session Terminal
                                        </span>
                                        <span className="text-[9px] font-mono text-slate-600">ID://{sessionId.toUpperCase()}</span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl">
                                        <span className="text-[10px] font-black text-emerald-400 font-mono italic tracking-widest">{history.length} PACKETS</span>
                                    </div>
                                </div>
                            </div>

                            {/* Interaction Feed */}
                            <div className="flex-1 overflow-y-auto p-8 space-y-12 custom-scrollbar">
                                {history.length === 0 ? (
                                    <div className="h-full flex flex-col items-center justify-center text-center px-16 space-y-8">
                                        <div className="relative">
                                            <div className="absolute inset-0 bg-emerald-500/20 blur-3xl rounded-full" />
                                            <div className="relative w-32 h-32 rounded-[2.5rem] bg-emerald-500/5 border border-white/5 flex items-center justify-center text-slate-700">
                                                <Waves className="w-16 h-16 animate-pulse" />
                                            </div>
                                        </div>
                                        <div className="space-y-4">
                                            <h4 className="text-2xl font-black text-white tracking-tight uppercase">Monitoring Frequencies</h4>
                                            <p className="text-slate-500 text-sm font-medium leading-relaxed">
                                                Waiting for inbound voice transmission. The system will automatically detect threat profiles and language patterns.
                                            </p>
                                        </div>
                                        <div className="grid grid-cols-2 gap-4 w-full max-w-sm">
                                            <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5 text-[10px] font-bold text-slate-600 uppercase tracking-widest">STT Engine: Whisper Base</div>
                                            <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5 text-[10px] font-bold text-slate-600 uppercase tracking-widest">TTS Engine: Piper v1</div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-12">
                                        {history.map((msg, idx) => (
                                            <motion.div
                                                key={idx}
                                                initial={{ opacity: 0, x: msg.role === 'scammer' ? -30 : 30 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                className={`flex flex-col ${msg.role === 'scammer' ? 'items-start' : 'items-end'}`}
                                            >
                                                <div className={`max-w-[90%] md:max-w-[80%] space-y-4 ${msg.role === 'scammer' ? 'text-left' : 'text-right'}`}>
                                                    <div className={`flex items-center gap-3 mb-2 ${msg.role === 'scammer' ? 'flex-row' : 'flex-row-reverse'}`}>
                                                        <div className={`w-2 h-2 rounded-full ${msg.role === 'scammer' ? 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]' : 'bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.6)]'}`} />
                                                        <span className={`text-[10px] font-black uppercase tracking-[0.2em] font-mono ${msg.role === 'scammer' ? 'text-rose-500' : 'text-emerald-400'}`}>
                                                            {msg.role === 'scammer' ? 'THREAT_SOURCE' : 'AGENT_CORE'}
                                                        </span>
                                                        <span className="text-[9px] font-mono text-slate-700">{msg.timestamp.toLocaleTimeString()}</span>
                                                    </div>

                                                    {msg.role === 'scammer' ? (
                                                        <div className="relative group/msg">
                                                            <div className="absolute -inset-1 bg-gradient-to-r from-rose-500/10 to-transparent blur opacity-0 group-hover/msg:opacity-100 transition-opacity" />
                                                            <div className="relative bg-slate-800/80 backdrop-blur-xl border border-white/5 rounded-[2rem] rounded-tl-none p-6 text-white shadow-2xl transition-all">
                                                                <p className="text-base font-medium leading-relaxed text-slate-200">
                                                                    {msg.text}
                                                                </p>
                                                            </div>
                                                        </div>
                                                    ) : (
                                                        <VoicePlayer
                                                            audioUrl={msg.audioUrl}
                                                            transcription={msg.text}
                                                            naturalizedText={msg.naturalized}
                                                            timestamp={msg.timestamp}
                                                            autoPlay={idx === history.length - 1 && mode === 'ai_speaks'}
                                                        />
                                                    )}
                                                </div>
                                            </motion.div>
                                        ))}
                                        <div ref={timelineEndRef} />
                                    </div>
                                )}
                            </div>

                            {/* Interface Footer */}
                            <div className="p-6 bg-black/40 border-t border-white/5 backdrop-blur-xl flex items-center justify-between">
                                <div className="flex items-center gap-4 text-[10px] font-bold text-slate-600 uppercase tracking-[0.3em]">
                                    <div className="flex items-center gap-1.5">
                                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]" />
                                        <span> Uplink Stable</span>
                                    </div>
                                    <span className="mx-2">•</span>
                                    <span>Latency: 24ms</span>
                                </div>
                                <div className="flex gap-2">
                                    <div className="w-12 h-1 bg-slate-800 rounded-full" />
                                    <div className="w-6 h-1 bg-emerald-500 rounded-full" />
                                    <div className="w-12 h-1 bg-slate-800 rounded-full" />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            <style jsx="true">{`
                .scrollbar-none::-webkit-scrollbar {
                    display: none;
                }
                .custom-scrollbar::-webkit-scrollbar {
                    width: 4px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: transparent;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 10px;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            `}</style>
        </div>
    );
};

export default VoicePlayground;
