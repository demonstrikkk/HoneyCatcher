import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader, AlertCircle, CheckCircle, Brain, Shield, Database } from 'lucide-react';
import Navbar from '../components/Navbar.jsx';
import GlassCard from '../components/GlassCard.jsx';
import { simulateScamMessage, fetchSession } from '../services/api.js';
import { cn } from '../utils.js';
import { motion, AnimatePresence } from 'framer-motion';

const Playground = () => {
    const [sessionId] = useState(`test-${Date.now()}`);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [sessionData, setSessionData] = useState(null);
    const [autoRefresh, setAutoRefresh] = useState(true);
    const [sessionCreated, setSessionCreated] = useState(false);
    const messagesEndRef = useRef(null);

    // Preset scam messages for quick testing
    const presetMessages = [
        "Your bank account will be blocked in 24 hours. Call 9876543210 immediately.",
        "URGENT: KYC verification pending. Click https://secure-bank-verify.com now.",
        "Congratulations! You won ₹50,000. Share your UPI ID to claim.",
        "Your ATM card is blocked. Update details at support@fake-bank.com",
        "Police complaint filed against you. Pay ₹20,000 fine to 9999888877@paytm"
    ];

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Auto-refresh session data
    useEffect(() => {
        if (!autoRefresh || !sessionCreated) return;

        const interval = setInterval(async () => {
            if (sessionId) {
                const data = await fetchSession(sessionId);
                if (data) {
                    setSessionData(data);
                    // Update messages with full history
                    if (data.history && data.history.length > messages.length) {
                        setMessages(data.history);
                    }
                }
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [sessionId, autoRefresh, messages.length, sessionCreated]);

    const handleSend = async (text = input) => {
        if (!text.trim()) return;

        const userMessage = {
            sender: 'scammer',
            content: text,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            const response = await simulateScamMessage(sessionId, text);
            setSessionCreated(true);

            if (response && response.reply) {
                const agentMessage = {
                    sender: 'agent',
                    content: response.reply,
                    timestamp: new Date()
                };
                setMessages(prev => [...prev, agentMessage]);
            }

            // Fetch updated session data
            const data = await fetchSession(sessionId);
            if (data) setSessionData(data);

        } catch (error) {
            console.error('Error sending message:', error);
        } finally {
            setLoading(false);
        }
    };

    const intel = sessionData?.extracted_intelligence || {};
    const hasIntel = Object.values(intel).some(arr => arr && arr.length > 0);

    return (
        <div className="h-screen bg-background overflow-hidden flex flex-col">
            <Navbar />

            <div className="flex-1 flex gap-6 p-6 pt-24 overflow-hidden max-w-[1800px] mx-auto w-full">
                {/* Left Panel - Quick Actions */}
                <div className="w-80 space-y-4 overflow-y-auto">
                    <GlassCard className="p-0 overflow-hidden">
                        <div className="bg-primary/10 p-4 border-b border-white/5">
                            <h3 className="font-bold flex items-center gap-2">
                                <Brain size={18} className="text-primary" />
                                Test Scenarios
                            </h3>
                            <p className="text-xs text-gray-400 mt-1">Click to inject</p>
                        </div>
                        <div className="p-4 space-y-2 max-h-96 overflow-y-auto">
                            {presetMessages.map((msg, i) => (
                                <button
                                    key={i}
                                    onClick={() => handleSend(msg)}
                                    disabled={loading}
                                    className="w-full text-left p-3 bg-white/5 hover:bg-white/10 border border-white/5 hover:border-primary/30 rounded-lg text-xs transition-all group"
                                >
                                    <div className="text-gray-300 group-hover:text-white line-clamp-2">
                                        {msg}
                                    </div>
                                </button>
                            ))}
                        </div>
                    </GlassCard>

                    {/* Session Stats */}
                    <GlassCard>
                        <h3 className="font-bold mb-4 flex items-center gap-2">
                            <Shield size={18} className="text-emerald-400" />
                            Detection Status
                        </h3>
                        {sessionData ? (
                            <div className="space-y-3">
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-gray-400">Threat Level</span>
                                    <span className={cn(
                                        "font-bold text-lg",
                                        sessionData.scam_score > 0.8 ? "text-red-500" :
                                            sessionData.scam_score > 0.5 ? "text-yellow-500" : "text-emerald-500"
                                    )}>
                                        {((sessionData.scam_score || 0) * 100).toFixed(0)}%
                                    </span>
                                </div>
                                <div className="w-full bg-black/50 rounded-full h-2 overflow-hidden">
                                    <motion.div
                                        className={cn(
                                            "h-full",
                                            sessionData.scam_score > 0.8 ? "bg-red-500" :
                                                sessionData.scam_score > 0.5 ? "bg-yellow-500" : "bg-emerald-500"
                                        )}
                                        initial={{ width: 0 }}
                                        animate={{ width: `${(sessionData.scam_score || 0) * 100}%` }}
                                        transition={{ duration: 0.5 }}
                                    />
                                </div>
                                <div className="pt-2 space-y-2 text-sm">
                                    <div className="flex items-center gap-2">
                                        {sessionData.is_confirmed_scam ? (
                                            <>
                                                <AlertCircle size={14} className="text-red-500" />
                                                <span className="text-red-400">SCAM CONFIRMED</span>
                                            </>
                                        ) : (
                                            <>
                                                <CheckCircle size={14} className="text-emerald-500" />
                                                <span className="text-gray-400">Analyzing...</span>
                                            </>
                                        )}
                                    </div>
                                    <div className="text-xs text-gray-500">
                                        Messages: <span className="text-white font-mono">{sessionData.message_count || 0}</span>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="text-sm text-gray-500 text-center py-4">
                                Send a message to start
                            </div>
                        )}
                    </GlassCard>
                </div>

                {/* Center Panel - Chat */}
                <div className="flex-1 flex flex-col gap-4 min-w-0">
                    <GlassCard className="flex-1 overflow-hidden flex flex-col p-0">
                        <div className="p-4 border-b border-white/5 flex justify-between items-center bg-black/20 shrink-0">
                            <div>
                                <h2 className="font-bold text-lg">Live Testing Arena</h2>
                                <p className="text-xs text-gray-400 font-mono">Session: {sessionId}</p>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className={cn(
                                    "w-2 h-2 rounded-full animate-pulse",
                                    sessionData?.is_confirmed_scam ? "bg-red-500" : "bg-emerald-500"
                                )} />
                                <span className="text-xs text-gray-400">
                                    {loading ? 'Agent typing...' : 'Ready'}
                                </span>
                            </div>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto p-6 space-y-4">
                            {messages.length === 0 ? (
                                <div className="h-full flex items-center justify-center text-center">
                                    <div className="space-y-4">
                                        <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
                                            <Send size={24} className="text-primary" />
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-gray-300 mb-2">Start Testing</h3>
                                            <p className="text-sm text-gray-500 max-w-md">
                                                Type a scam message or use a preset scenario to see the AI agent in action.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <AnimatePresence>
                                    {messages.map((msg, i) => (
                                        <motion.div
                                            key={i}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ duration: 0.3 }}
                                            className={cn(
                                                "flex gap-3",
                                                msg.sender === 'agent' ? "justify-start" : "justify-end"
                                            )}
                                        >
                                            {msg.sender === 'agent' && (
                                                <div className="w-8 h-8 bg-primary/20 rounded-full flex items-center justify-center shrink-0">
                                                    <Shield size={16} className="text-primary" />
                                                </div>
                                            )}
                                            <div className={cn(
                                                "max-w-[70%] p-4 rounded-2xl",
                                                msg.sender === 'agent'
                                                    ? "bg-surface border border-white/5 rounded-tl-sm"
                                                    : "bg-red-500/10 border border-red-500/20 rounded-tr-sm"
                                            )}>
                                                <p className="text-sm leading-relaxed text-gray-200">
                                                    {msg.content}
                                                </p>
                                                <span className="text-[10px] text-gray-500 mt-2 block">
                                                    {new Date(msg.timestamp).toLocaleTimeString()}
                                                </span>
                                            </div>
                                            {msg.sender !== 'agent' && (
                                                <div className="w-8 h-8 bg-red-500/20 rounded-full flex items-center justify-center shrink-0">
                                                    <AlertCircle size={16} className="text-red-500" />
                                                </div>
                                            )}
                                        </motion.div>
                                    ))}
                                </AnimatePresence>
                            )}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Input */}
                        <div className="p-4 border-t border-white/5 bg-black/20 shrink-0">
                            <div className="flex gap-3">
                                <input
                                    type="text"
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyPress={(e) => e.key === 'Enter' && !loading && handleSend()}
                                    placeholder="Type a scam message to test the agent..."
                                    disabled={loading}
                                    className="flex-1 bg-surface border border-white/10 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-primary/50 transition-colors disabled:opacity-50"
                                />
                                <button
                                    onClick={() => handleSend()}
                                    disabled={loading || !input.trim()}
                                    className="bg-primary hover:bg-primary/80 disabled:bg-primary/20 px-6 py-3 rounded-lg font-semibold text-sm transition-all flex items-center gap-2 disabled:cursor-not-allowed"
                                >
                                    {loading ? (
                                        <>
                                            <Loader size={16} className="animate-spin" />
                                            Analyzing
                                        </>
                                    ) : (
                                        <>
                                            <Send size={16} />
                                            Send
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </GlassCard>
                </div>

                {/* Right Panel - Intelligence */}
                <div className="w-96 space-y-4 overflow-y-auto">
                    <GlassCard className="p-0 overflow-hidden">
                        <div className="bg-yellow-500/10 p-4 border-b border-white/5">
                            <h3 className="font-bold flex items-center gap-2">
                                <Database size={18} className="text-yellow-500" />
                                Extracted Intelligence
                            </h3>
                            <p className="text-xs text-gray-400 mt-1">Real-time extraction</p>
                        </div>
                        <div className="p-4 space-y-4 max-h-[600px] overflow-y-auto">
                            {hasIntel ? (
                                <>
                                    {intel.bank_accounts?.length > 0 && (
                                        <div className="space-y-2">
                                            <div className="text-xs font-semibold text-blue-400 uppercase tracking-wider">
                                                Bank Accounts
                                            </div>
                                            {intel.bank_accounts.map((item, i) => (
                                                <div key={i} className="bg-blue-500/10 border border-blue-500/20 px-3 py-2 rounded text-sm font-mono text-gray-200 break-all">
                                                    {item}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    {intel.upi_ids?.length > 0 && (
                                        <div className="space-y-2">
                                            <div className="text-xs font-semibold text-orange-400 uppercase tracking-wider">
                                                UPI IDs
                                            </div>
                                            {intel.upi_ids.map((item, i) => (
                                                <div key={i} className="bg-orange-500/10 border border-orange-500/20 px-3 py-2 rounded text-sm font-mono text-gray-200 break-all">
                                                    {item}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    {intel.phone_numbers?.length > 0 && (
                                        <div className="space-y-2">
                                            <div className="text-xs font-semibold text-green-400 uppercase tracking-wider">
                                                Phone Numbers
                                            </div>
                                            {intel.phone_numbers.map((item, i) => (
                                                <div key={i} className="bg-green-500/10 border border-green-500/20 px-3 py-2 rounded text-sm font-mono text-gray-200 break-all">
                                                    {item}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    {intel.urls?.length > 0 && (
                                        <div className="space-y-2">
                                            <div className="text-xs font-semibold text-cyan-400 uppercase tracking-wider">
                                                Phishing Links
                                            </div>
                                            {intel.urls.map((item, i) => (
                                                <div key={i} className="bg-cyan-500/10 border border-cyan-500/20 px-3 py-2 rounded text-sm font-mono text-gray-200 break-all">
                                                    {item}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    {intel.scam_keywords?.length > 0 && (
                                        <div className="space-y-2">
                                            <div className="text-xs font-semibold text-yellow-400 uppercase tracking-wider">
                                                Scam Keywords
                                            </div>
                                            <div className="flex flex-wrap gap-2">
                                                {intel.scam_keywords.map((item, i) => (
                                                    <span key={i} className="bg-yellow-500/10 border border-yellow-500/20 px-2 py-1 rounded text-xs text-gray-200">
                                                        {item}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </>
                            ) : (
                                <div className="text-center py-10 text-gray-600 italic">
                                    <Database size={32} className="mx-auto mb-2 opacity-30" />
                                    No intelligence extracted yet.<br />
                                    <span className="text-xs">Send messages to see extraction in action</span>
                                </div>
                            )}
                        </div>
                    </GlassCard>
                </div>
            </div>
        </div>
    );
};

export default Playground;
