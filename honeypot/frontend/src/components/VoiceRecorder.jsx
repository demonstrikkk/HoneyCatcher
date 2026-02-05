import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Mic, Square, Loader2, Volume2, ShieldAlert, Activity, Wifi, Radio } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const VoiceRecorder = ({ sessionId, onTranscription, mode = "ai_speaks" }) => {
    const [isRecording, setIsRecording] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState(null);
    const [duration, setDuration] = useState(0);
    const mediaRecorderRef = useRef(null);
    const chunksRef = useRef([]);
    const recordingTimerRef = useRef(null);

    // Simulated waveform data
    const [bars, setBars] = useState(Array(24).fill(20));

    useEffect(() => {
        let interval;
        if (isRecording) {
            interval = setInterval(() => {
                setBars(prev => prev.map(() => Math.floor(Math.random() * 40) + 10));
            }, 100);
        } else {
            setBars(Array(24).fill(15));
        }
        return () => clearInterval(interval);
    }, [isRecording]);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

            mediaRecorderRef.current = mediaRecorder;
            chunksRef.current = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
                await uploadAudio(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            setIsRecording(true);
            setError(null);

            recordingTimerRef.current = setInterval(() => {
                setDuration(prev => prev + 1);
            }, 1000);

        } catch (err) {
            console.error('Error accessing microphone:', err);
            setError('Access Denied: Grant microphone permission to continue.');
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            clearInterval(recordingTimerRef.current);
            setDuration(0);
        }
    };

    const uploadAudio = async (blob) => {
        setIsProcessing(true);
        const formData = new FormData();
        formData.append('audio', blob, 'scammer_audio.webm');
        formData.append('sessionId', sessionId);
        formData.append('mode', mode);

        try {
            const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/voice/upload`, {
                method: 'POST',
                headers: {
                    'x-api-key': import.meta.env.VITE_API_SECRET_KEY || 'unsafe-secret-key-change-me'
                },
                body: formData
            });

            if (!response.ok) throw new Error('Failed to upload audio');

            const result = await response.json();
            if (onTranscription) {
                onTranscription(result);
            }
        } catch (err) {
            console.error('Upload failed:', err);
            setError('Signal Lost: Communication link unsuccessful.');
        } finally {
            setIsProcessing(false);
        }
    };

    return (
        <div className="relative group bg-slate-950/80 backdrop-blur-3xl border border-white/5 rounded-[2.5rem] p-8 shadow-2xl transition-all duration-500 hover:border-emerald-500/20">
            {/* Background Mesh Glow */}
            <div className={`absolute -top-24 -right-24 w-48 h-48 blur-[80px] rounded-full transition-colors duration-1000 ${isRecording ? 'bg-rose-500/20' : 'bg-emerald-500/10'}`} />

            <div className="relative z-10 flex flex-col items-center">
                {/* Status Header */}
                <div className="w-full flex justify-between items-center mb-10">
                    <div className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full ${isRecording ? 'bg-rose-500 animate-pulse' : 'bg-emerald-500'}`} />
                        <span className="text-[10px] font-bold tracking-[0.2em] text-slate-400 uppercase">
                            {isProcessing ? 'Decoding Signal' : isRecording ? 'Intercepting' : 'System Ready'}
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Activity className={`w-3 h-3 text-slate-600 ${isRecording ? 'text-rose-500' : ''}`} />
                        <Radio className={`w-3 h-3 text-slate-600 ${isProcessing ? 'text-emerald-400 animate-pulse' : ''}`} />
                        <Wifi className="w-3 h-3 text-slate-600" />
                    </div>
                </div>

                {/* Animated Waveform */}
                <div className="flex items-end justify-center gap-[3px] h-16 w-full mb-10">
                    {bars.map((height, i) => (
                        <motion.div
                            key={i}
                            animate={{ height }}
                            transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                            className={`w-1 rounded-full ${isRecording ? 'bg-gradient-to-t from-rose-500 to-orange-400' : 'bg-slate-800'}`}
                        />
                    ))}
                </div>

                {/* Central Button */}
                <div className="relative">
                    <AnimatePresence>
                        {isRecording && (
                            <>
                                <motion.div
                                    initial={{ scale: 0.8, opacity: 0 }}
                                    animate={{ scale: 2.2, opacity: 0 }}
                                    exit={{ scale: 0.8, opacity: 0 }}
                                    transition={{ repeat: Infinity, duration: 2, ease: "easeOut" }}
                                    className="absolute inset-0 bg-rose-500 rounded-full"
                                />
                                <motion.div
                                    initial={{ scale: 0.8, opacity: 0 }}
                                    animate={{ scale: 1.8, opacity: 0.1 }}
                                    exit={{ scale: 0.8, opacity: 0 }}
                                    transition={{ repeat: Infinity, duration: 2, delay: 0.5, ease: "easeOut" }}
                                    className="absolute inset-0 bg-rose-500 rounded-full"
                                />
                            </>
                        )}
                    </AnimatePresence>

                    <button
                        onClick={isRecording ? stopRecording : startRecording}
                        disabled={isProcessing}
                        className={`relative z-20 w-24 h-24 rounded-full flex items-center justify-center transition-all duration-500 ${isRecording
                            ? 'bg-rose-500 border-4 border-rose-400/50 shadow-[0_0_40px_rgba(244,63,94,0.4)]'
                            : 'bg-slate-900 border border-white/10 hover:border-emerald-500/50 shadow-xl'
                            } group-hover:scale-105 active:scale-95 disabled:grayscale disabled:opacity-50`}
                    >
                        {isProcessing ? (
                            <Loader2 className="w-10 h-10 text-emerald-400 animate-spin" />
                        ) : isRecording ? (
                            <Square className="w-10 h-10 text-white fill-white" />
                        ) : (
                            <Mic className="w-10 h-10 text-white group-hover:text-emerald-400 transition-colors" />
                        )}
                    </button>
                </div>

                <div className="mt-8 text-center">
                    <p className={`text-2xl font-bold font-mono tracking-tighter ${isRecording ? 'text-white' : 'text-slate-600'}`}>
                        {Math.floor(duration / 60)}:{((duration % 60).toString().padStart(2, '0'))}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-2 font-medium tracking-wide">
                        {isRecording ? 'VOICE ENCRYPTION ACTIVE' : 'PRESS TO SCAN VOICE SCAPE'}
                    </p>
                </div>

                {error && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="mt-6 w-full flex items-center gap-3 px-4 py-3 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-300 text-[11px] font-bold tracking-tight"
                    >
                        <ShieldAlert className="w-4 h-4 shrink-0" />
                        {error}
                    </motion.div>
                )}
            </div>

            <div className="mt-10 pt-8 border-t border-white/5 grid grid-cols-2 gap-4">
                <div className={`flex items-center gap-2 p-3 rounded-2xl border transition-all duration-300 ${mode === 'ai_speaks' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' : 'bg-white/5 border-transparent text-slate-600'}`}>
                    <Volume2 className="w-3.5 h-3.5" />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Auto-Speak</span>
                </div>
                <div className={`flex items-center gap-2 p-3 rounded-2xl border transition-all duration-300 ${mode === 'ai_suggests' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' : 'bg-white/5 border-transparent text-slate-600'}`}>
                    <Activity className="w-3.5 h-3.5" />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Suggestive</span>
                </div>
            </div>
        </div>
    );
};

export default VoiceRecorder;
