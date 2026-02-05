import React from 'react';
import { Quote, Copy, MessageSquare, Mic, Check, Zap, Target, Sparkles, BrainCircuit } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const AISuggestionPanel = ({ suggestion, originalText, onAction }) => {
    const [copied, setCopied] = React.useState(false);

    const copyToClipboard = () => {
        navigator.clipboard.writeText(suggestion);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    if (!suggestion) return null;

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 30 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            className="group relative bg-[#0a100d] border border-emerald-500/20 rounded-[2.5rem] p-8 shadow-[0_0_50px_rgba(16,185,129,0.05)] overflow-hidden"
        >
            {/* Background Atmosphere */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 blur-[100px] rounded-full -mr-20 -mt-20 group-hover:bg-emerald-500/10 transition-colors" />
            <div className="absolute inset-x-0 bottom-0 h-1 bg-gradient-to-r from-transparent via-emerald-500/30 to-transparent opacity-50" />

            <div className="relative z-10">
                {/* Header Section */}
                <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-4">
                        <div className="relative">
                            <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                                <BrainCircuit className="w-6 h-6" />
                            </div>
                            <motion.div
                                animate={{ scale: [1, 1.2, 1] }}
                                transition={{ repeat: Infinity, duration: 3 }}
                                className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full border-2 border-[#0a100d]"
                            />
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <h4 className="text-sm font-black text-emerald-50 font-sans tracking-tight uppercase">Tactical Suggestion</h4>
                                <div className="px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-[9px] font-bold text-emerald-400 flex items-center gap-1">
                                    <Target className="w-2.5 h-2.5" /> HIGH CONFIDENCE
                                </div>
                            </div>
                            <p className="text-[10px] text-emerald-500/60 font-medium tracking-[0.1em] uppercase mt-0.5">Recommended Counter-Reply</p>
                        </div>
                    </div>

                    <button
                        onClick={copyToClipboard}
                        className="p-3 rounded-2xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-emerald-400 border border-white/5 transition-all duration-300"
                    >
                        {copied ? <Check className="w-5 h-5 text-emerald-400" /> : <Copy className="w-5 h-5" />}
                    </button>
                </div>

                {/* Main Content Area */}
                <div className="relative p-7 bg-white/[0.02] border border-white/5 rounded-3xl overflow-hidden mb-8 group/quote">
                    <div className="absolute top-0 left-0 w-2 h-full bg-emerald-500/20" />
                    <Quote className="absolute -left-2 -top-2 w-16 h-16 text-emerald-500/5 rotate-12" />

                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.2 }}
                        className="text-xl md:text-2xl font-semibold text-white leading-[1.4] pl-5 pr-4 select-all"
                    >
                        {suggestion}
                    </motion.p>

                    <div className="mt-6 pl-5 flex items-center gap-2 text-[10px] font-bold text-emerald-500/50 uppercase tracking-widest">
                        <Sparkles className="w-3 h-3" />
                        Naturalized for maximum deception
                    </div>
                </div>

                {/* Footer Controls */}
                <div className="flex flex-col sm:flex-row gap-4">
                    <button
                        onClick={() => onAction && onAction('speak')}
                        className="flex-1 group/btn relative flex items-center justify-center gap-3 py-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-2xl font-black text-sm transition-all duration-300 shadow-[0_10px_30px_rgba(16,185,129,0.25)] hover:-translate-y-1 active:translate-y-0"
                    >
                        <Mic className="w-5 h-5 transition-transform group-hover/btn:scale-110" />
                        MARK AS SPOKEN
                        <Zap className="w-4 h-4 text-emerald-200" />
                    </button>
                    <button
                        onClick={() => onAction && onAction('ignore')}
                        className="px-8 py-4 bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white rounded-2xl font-bold text-sm transition-all border border-white/5"
                    >
                        IGNORE
                    </button>
                </div>

                {/* Semantic Context */}
                {originalText && (
                    <div className="mt-8 pt-6 border-t border-emerald-500/10">
                        <div className="flex items-center gap-2 mb-3">
                            <span className="text-[9px] font-black text-emerald-500/40 uppercase tracking-[0.2em]">Strategy Core</span>
                            <div className="flex-1 h-[1px] bg-emerald-500/10" />
                        </div>
                        <p className="text-xs text-slate-500 italic leading-relaxed pl-3 border-l border-emerald-500/20">
                            "{originalText}"
                        </p>
                    </div>
                )}
            </div>
        </motion.div>
    );
};

export default AISuggestionPanel;
