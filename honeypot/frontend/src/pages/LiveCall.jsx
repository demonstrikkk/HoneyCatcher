import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Mic, MicOff, Phone, PhoneOff, Lightbulb, Activity, 
  AlertTriangle, Shield, Terminal, Users, Waves, 
  Zap, Target, TrendingUp, Radio
} from 'lucide-react';
import Navbar from '../components/Navbar';

const LiveCall = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const searchParams = new URLSearchParams(location.search);
  
  const callId = searchParams.get('call_id');
  const role = searchParams.get('role'); // "operator" or "scammer"
  
  const [isConnected, setIsConnected] = useState(false);
  const [status, setStatus] = useState('Connecting...');
  const [transcript, setTranscript] = useState([]);
  const [aiCoaching, setAiCoaching] = useState([]);
  const [entities, setEntities] = useState([]);
  const [threatLevel, setThreatLevel] = useState(0);
  const [tactics, setTactics] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [participantConnected, setParticipantConnected] = useState(false);
  
  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);
  
  // WebSocket connection
  useEffect(() => {
    if (!callId || !role) {
      navigate('/voice-playground');
      return;
    }
    
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      stopRecording();
    };
  }, [callId, role]);
  
  const connectWebSocket = () => {
    const WS_BASE = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/api';
    const wsUrl = `${WS_BASE}/call/connect?call_id=${callId}&role=${role}`;
    
    wsRef.current = new WebSocket(wsUrl);
    
    wsRef.current.onopen = () => {
      console.log('✅ WebSocket connected');
      setIsConnected(true);
      setStatus(role === 'operator' ? 'Waiting for scammer...' : 'Connected');
    };
    
    wsRef.current.onmessage = async (event) => {
      const data = JSON.parse(event.data);
      console.log('[WS RECEIVED]', data.type, '| Fields:', Object.keys(data).join(', '));
      if (data.type === 'ai_response_sent') {
        console.log('[AI_RESPONSE_SENT] Text:', data.text?.substring(0, 50), '| Strategy:', data.strategy);
      }
      handleWebSocketMessage(data);
    };
    
    wsRef.current.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      setStatus('Connection error');
    };
    
    wsRef.current.onclose = () => {
      console.log('🔌 WebSocket closed');
      setIsConnected(false);
      setStatus('Disconnected');
    };
  };
  
  const handleWebSocketMessage = async (data) => {
    switch (data.type) {
      case 'connected':
        setStatus(data.waiting_for_scammer ? 'Waiting for scammer...' : 'Connected');
        break;
      
      case 'participant_joined':
        setParticipantConnected(true);
        setStatus('Call active');
        if (role === 'operator') {
          setTranscript(prev => [...prev, {
            type: 'system',
            text: '🟢 Scammer has joined the call',
            timestamp: new Date().toISOString()
          }]);
        }
        break;
      
      case 'participant_left':
        setParticipantConnected(false);
        setStatus(`${data.role} left the call`);
        setTranscript(prev => [...prev, {
          type: 'system',
          text: `🔴 ${data.role} left the call`,
          timestamp: new Date().toISOString()
        }]);
        break;
      
      case 'audio_stream':
        // Queue incoming audio for playback
        await playIncomingAudio(data.audio, data.format);
        break;
      
      case 'transcription':
        // Add transcription to transcript (operator only)
        if (role === 'operator') {
          setTranscript(prev => [...prev, {
            speaker: data.speaker,
            text: data.text,
            language: data.language,
            timestamp: data.timestamp
          }]);
        }
        break;
      
      case 'ai_response_sent':
        // NEW: AI spoke to scammer — show text transcript to operator (no audio)
        if (role === 'operator') {
          // Add AI's response to transcript for operator to monitor
          setTranscript(prev => [...prev, {
            type: 'ai_response',
            speaker: 'ai',
            text: data.text,
            timestamp: data.timestamp
          }]);
          // Also add to coaching panel for context
          if (data.strategy || data.intent) {
            setAiCoaching(prev => [...prev, {
              text: `🤖 AI spoke: "${data.text}"`,
              strategy: data.strategy,
              intent: data.intent
            }]);
          }
          // NO audio playback — operator monitors silently, scammer hears the AI
        }
        break;
      
      case 'intelligence_update':
        // Update intelligence panel (operator only)
        if (role === 'operator') {
          if (data.entities) setEntities(prev => [...prev, ...data.entities]);
          if (data.threat_level !== undefined) setThreatLevel(data.threat_level);
          if (data.tactics) setTactics(prev => [...prev, ...data.tactics]);
        }
        break;
      
      case 'call_ended':
        setStatus('Call ended');
        stopRecording();
        setTimeout(() => {
          navigate('/dashboard');
        }, 2000);
        break;
      
      case 'text_message':
        setTranscript(prev => [...prev, {
          speaker: data.from,
          text: data.text,
          type: 'text',
          timestamp: new Date().toISOString()
        }]);
        break;
      
      case 'pong':
        // Heartbeat response
        break;
      
      case 'error':
        console.error('Server error:', data.message);
        setStatus(`Error: ${data.message}`);
        break;
    }
  };
  
  const playIncomingAudio = async (audioBase64, format) => {
    try {
      // Add to queue with proper format detection
      const actualFormat = format === 'mp3' ? 'audio/mpeg' : (format === 'wav' ? 'audio/wav' : 'audio/webm');
      audioQueueRef.current.push({ audioBase64, format, mimeType: actualFormat });
      
      // Start playing if not already playing
      if (!isPlayingRef.current) {
        await playNextInQueue();
      }
    } catch (error) {
      console.error('Audio playback error:', error);
    }
  };
  
  const playNextInQueue = async () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }
    
    isPlayingRef.current = true;
    const { audioBase64, format, mimeType } = audioQueueRef.current.shift();
    
    try {
      // Decode base64 to blob with proper MIME type
      const audioBlob = base64ToBlob(audioBase64, mimeType || `audio/${format}`);
      const audioUrl = URL.createObjectURL(audioBlob);
      
      // Create audio element and play
      const audio = new Audio(audioUrl);
      
      // Add error recovery
      audio.onerror = async (e) => {
        console.error('Audio playback failed, trying Web Audio API fallback...', e);
        URL.revokeObjectURL(audioUrl);
        
        // Try Web Audio API fallback
        try {
          await playAudioWithWebAudioAPI(audioBlob);
          playNextInQueue(); // Play next
        } catch (fallbackError) {
          console.error('Web Audio API fallback also failed:', fallbackError);
          playNextInQueue(); // Skip and play next
        }
      };
      
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        playNextInQueue(); // Play next in queue
      };
      
      // Ensure audio context is ready
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      }
      
      // Resume audio context if suspended (browser autoplay policy)
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }
      
      await audio.play();
    } catch (error) {
      console.error('Audio decode error:', error);
      playNextInQueue(); // Skip and play next
    }
  };

  const playAudioWithWebAudioAPI = async (audioBlob) => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
    }
    
    const arrayBuffer = await audioBlob.arrayBuffer();
    const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer);
    
    const source = audioContextRef.current.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContextRef.current.destination);
    
    return new Promise((resolve, reject) => {
      source.onended = resolve;
      source.onerror = reject;
      source.start(0);
    });
  };
  
  const base64ToBlob = (base64, mimeType) => {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
  };
  
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 48000,
          channelCount: 1
        } 
      });
      
      // Try preferred formats in order (WAV is easier for streaming, WebM as fallback)
      let mimeType = 'audio/webm;codecs=opus';
      let format = 'webm';
      
      if (MediaRecorder.isTypeSupported('audio/wav')) {
        mimeType = 'audio/wav';
        format = 'wav';
      } else if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
        format = 'webm';
      } else if (MediaRecorder.isTypeSupported('audio/webm')) {
        mimeType = 'audio/webm';
        format = 'webm';
      }
      
      console.log('Using audio format:', mimeType);
      
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: 128000
      });
      
      mediaRecorderRef.current.ondataavailable = async (event) => {
        if (event.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
          // Convert to base64 and send
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64 = reader.result.split(',')[1];
            wsRef.current.send(JSON.stringify({
              type: 'audio_chunk',
              audio: base64,
              format
            }));
          };
          reader.readAsDataURL(event.data);
        }
      };
      
      // Send audio chunks every 1 second
      mediaRecorderRef.current.start(1000);
      setIsRecording(true);
      setStatus(role === 'operator' ? 'Recording (Call active)' : 'In call');
      
    } catch (error) {
      console.error('Microphone error:', error);
      alert(`Failed to access microphone: ${error.message}`);
    }
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
    setIsRecording(false);
  };
  
  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };
  
  const endCall = async () => {
    if (confirm('Are you sure you want to end this call?')) {
      try {
        const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
        await fetch(`${API_BASE}/call/end/${callId}`, {
          method: 'POST',
          headers: {
            'x-api-key': import.meta.env.VITE_API_SECRET || 'unsafe-secret-key-change-me'
          }
        });
      } catch (error) {
        console.error('End call error:', error);
      }
      
      stopRecording();
      navigate('/dashboard');
    }
  };
  
  const requestCoaching = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'request_coaching' }));
    }
  };
  
  const getThreatColor = () => {
    if (threatLevel < 0.3) return 'text-emerald-400';
    if (threatLevel < 0.7) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getThreatBgColor = () => {
    if (threatLevel < 0.3) return 'bg-emerald-400';
    if (threatLevel < 0.7) return 'bg-yellow-400';
    return 'bg-red-400';
  };

  return (
    <div className="min-h-screen bg-[#020202] text-slate-300 selection:bg-emerald-500/30 overflow-x-hidden font-sans">
      {/* Immersive Background Effects */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 -left-1/4 w-1/2 h-1/2 bg-emerald-500/5 blur-[120px] rounded-full animate-pulse" />
        <div className="absolute bottom-0 -right-1/4 w-1/2 h-1/2 bg-emerald-500/5 blur-[120px] rounded-full" />
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay" />
      </div>

      <Navbar />

      <main className="relative z-10 max-w-[1600px] mx-auto px-6 pt-24 pb-20">
        {/* Header Section */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-6">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className={`px-3 py-1 rounded-full border text-[10px] font-black tracking-[0.2em] uppercase ${
                  isConnected 
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                    : 'bg-red-500/10 border-red-500/20 text-red-400'
                }`}>
                  {isConnected ? '● LIVE' : '○ OFFLINE'}
                </div>
                <div className="px-3 py-1 rounded-full bg-white/[0.02] border border-white/5 text-[10px] font-black text-slate-400 tracking-widest">
                  {role === 'operator' ? '👤 OPERATOR' : '📞 CALLER'}
                </div>
              </div>
              
              <h1 className="text-4xl md:text-6xl font-black text-white tracking-tighter leading-none mb-3">
                {role === 'operator' ? (
                  <>OPERATOR <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-teal-400">CONSOLE</span></>
                ) : (
                  <>LIVE <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-teal-400">CALL</span></>
                )}
              </h1>
              
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-slate-600" />
                  <span className="text-slate-600 font-mono">ID:</span>
                  <span className="text-emerald-400 font-mono font-bold">{callId}</span>
                </div>
                <div className="w-[1px] h-4 bg-white/10" />
                <span className="text-slate-400 font-medium">{status}</span>
              </div>
            </div>

            {/* Call Stats */}
            <div className="flex items-center gap-6 p-6 bg-white/[0.02] border border-white/5 rounded-2xl backdrop-blur-xl">
              <div className="text-center">
                <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-1">Status</p>
                <div className="flex items-center gap-2">
                  {participantConnected ? (
                    <>
                      <Activity className="w-4 h-4 text-emerald-400" />
                      <span className="text-sm font-black text-emerald-400">ACTIVE</span>
                    </>
                  ) : (
                    <>
                      <Radio className="w-4 h-4 text-yellow-400 animate-pulse" />
                      <span className="text-sm font-black text-yellow-400">WAITING</span>
                    </>
                  )}
                </div>
              </div>
              {role === 'operator' && (
                <>
                  <div className="w-[1px] h-10 bg-white/5" />
                  <div className="text-center">
                    <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-1">Threat</p>
                    <span className={`text-sm font-black ${getThreatColor()}`}>
                      {(threatLevel * 100).toFixed(0)}%
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Call Panel */}
          <div className="lg:col-span-2 space-y-8">
            {/* Controls Panel */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-8 bg-white/[0.02] border border-white/5 rounded-3xl backdrop-blur-xl"
            >
              <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="flex gap-4 w-full md:w-auto">
                  <button
                    onClick={toggleRecording}
                    disabled={!participantConnected && role === 'operator'}
                    className={`group relative flex-1 md:flex-none px-8 py-4 rounded-xl font-black transition-all overflow-hidden ${
                      isRecording
                        ? 'bg-red-500 hover:bg-red-600 text-white'
                        : 'bg-emerald-500 hover:bg-emerald-600 text-black disabled:bg-slate-800 disabled:text-slate-600 disabled:cursor-not-allowed'
                    }`}
                  >
                    <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform" />
                    <div className="relative flex items-center justify-center gap-3">
                      {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                      <span>{isRecording ? 'STOP' : 'START'}</span>
                    </div>
                  </button>
                  
                  {role === 'operator' && (
                    <button
                      onClick={requestCoaching}
                      disabled={!participantConnected}
                      className="group relative px-8 py-4 bg-white/[0.02] hover:bg-white/[0.05] border border-emerald-500/20 text-emerald-400 rounded-xl font-black disabled:opacity-30 disabled:cursor-not-allowed transition-all overflow-hidden"
                    >
                      <div className="absolute inset-0 bg-emerald-500/10 translate-y-full group-hover:translate-y-0 transition-transform" />
                      <div className="relative flex items-center gap-3">
                        <Lightbulb className="w-5 h-5" />
                        <span className="hidden md:inline">AI HELP</span>
                      </div>
                    </button>
                  )}
                </div>
                
                <button
                  onClick={endCall}
                  className="group relative w-full md:w-auto px-8 py-4 bg-red-500/20 hover:bg-red-500 border border-red-500/50 text-red-400 hover:text-white rounded-xl font-black transition-all overflow-hidden"
                >
                  <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform" />
                  <div className="relative flex items-center justify-center gap-3">
                    <PhoneOff className="w-5 h-5" />
                    <span>END CALL</span>
                  </div>
                </button>
              </div>
              
              {role === 'operator' && !participantConnected && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-6 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl"
                >
                  <div className="flex items-center gap-3 text-yellow-400">
                    <Radio className="w-5 h-5 animate-pulse shrink-0" />
                    <span className="font-semibold">Waiting for scammer to join... Share the scammer link to begin.</span>
                  </div>
                </motion.div>
              )}
            </motion.div>

            {/* Transcript Panel (Operator Only) */}
            {role === 'operator' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="p-8 bg-white/[0.02] border border-white/5 rounded-3xl backdrop-blur-xl"
              >
                <div className="flex items-center gap-3 mb-6">
                  <Terminal className="w-5 h-5 text-emerald-400" />
                  <h2 className="font-black text-emerald-400 uppercase text-sm tracking-wider">Live Transcript</h2>
                </div>
                
                <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                  {transcript.length === 0 ? (
                    <div className="text-center py-12">
                      <Waves className="w-12 h-12 text-slate-700 mx-auto mb-4 opacity-50" />
                      <p className="text-slate-600 font-medium">Conversation will appear here...</p>
                    </div>
                  ) : (
                    transcript.map((msg, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className={`p-4 rounded-xl border ${
                          msg.type === 'system' ? 'bg-white/[0.02] border-white/10 text-slate-400' :
                          msg.type === 'ai_suggestion' ? 'bg-emerald-500/10 border-emerald-500/20' :
                          msg.speaker === 'scammer' ? 'bg-red-500/10 border-red-500/20' :
                          'bg-emerald-500/10 border-emerald-500/20'
                        }`}
                      >
                        <div className="flex justify-between items-start mb-2">
                          <span className={`font-black text-xs uppercase tracking-wider ${
                            msg.type === 'system' ? 'text-slate-500' :
                            msg.type === 'ai_suggestion' ? 'text-emerald-400' :
                            msg.speaker === 'scammer' ? 'text-red-400' : 'text-emerald-400'
                          }`}>
                            {msg.type === 'system' ? '• System' :
                             msg.type === 'ai_suggestion' ? '💡 AI Assistant' :
                             msg.speaker === 'scammer' ? '🔴 Target' : '🟢 You'}
                          </span>
                          <span className="text-xs text-slate-600 font-mono">
                            {new Date(msg.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-slate-300 font-medium leading-relaxed">{msg.text}</p>
                      </motion.div>
                    ))
                  )}
                </div>
              </motion.div>
            )}
            
            {/* Simple Status for Scammer */}
            {role === 'scammer' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="p-12 bg-white/[0.02] border border-white/5 rounded-3xl backdrop-blur-xl"
              >
                <div className="text-center py-12">
                  <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-emerald-500/20 border-2 border-emerald-500/50 mb-6">
                    <Phone className={`w-12 h-12 text-emerald-400 ${isRecording ? 'animate-pulse' : ''}`} />
                  </div>
                  <h2 className="text-3xl font-black text-white mb-3 tracking-tight">
                    {isRecording ? 'Call in Progress' : 'Ready to Connect'}
                  </h2>
                  <p className="text-slate-400 text-lg font-medium">
                    {isRecording ? 'Speak naturally...' : 'Click Start to begin the call'}
                  </p>
                </div>
              </motion.div>
            )}
          </div>

          {/* Operator Intelligence Panel */}
          {role === 'operator' && (
            <div className="space-y-6">
              {/* AI Response Log */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="p-6 bg-white/[0.02] border border-white/5 rounded-2xl backdrop-blur-xl"
              >
                <div className="flex items-center gap-3 mb-4">
                  <Lightbulb className="w-5 h-5 text-emerald-400" />
                  <h3 className="font-black text-emerald-400 uppercase text-sm tracking-wider">What AI Said</h3>
                </div>
                {aiCoaching.length === 0 ? (
                  <p className="text-slate-600 text-sm font-medium">AI responses to scammer will appear here...</p>
                ) : (
                  <div className="space-y-3">
                    {aiCoaching.map((item, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl"
                      >
                        <p className="text-emerald-200 text-sm font-medium leading-relaxed">{typeof item === 'string' ? item : item.text}</p>
                      </motion.div>
                    ))}
                  </div>
                )}
              </motion.div>

              {/* Threat Level */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.05 }}
                className="p-6 bg-white/[0.02] border border-white/5 rounded-2xl backdrop-blur-xl"
              >
                <div className="flex items-center gap-3 mb-4">
                  <AlertTriangle className="w-5 h-5 text-yellow-400" />
                  <h3 className="font-black text-yellow-400 uppercase text-sm tracking-wider">Threat Level</h3>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center gap-4">
                    <div className="flex-1 h-3 bg-white/5 rounded-full overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${threatLevel * 100}%` }}
                        transition={{ duration: 0.5 }}
                        className={`h-full transition-all duration-500 ${getThreatBgColor()}`}
                      />
                    </div>
                    <span className={`font-black text-lg ${getThreatColor()}`}>
                      {(threatLevel * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-xs font-bold text-slate-600 uppercase tracking-wider">
                    <span>Low</span>
                    <span>Medium</span>
                    <span>High</span>
                  </div>
                </div>
              </motion.div>

              {/* Entities */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
                className="p-6 bg-white/[0.02] border border-white/5 rounded-2xl backdrop-blur-xl"
              >
                <div className="flex items-center gap-3 mb-4">
                  <Target className="w-5 h-5 text-blue-400" />
                  <h3 className="font-black text-blue-400 uppercase text-sm tracking-wider">Extracted Info</h3>
                </div>
                <div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
                  {entities.length === 0 ? (
                    <p className="text-slate-600 text-sm font-medium">No entities detected yet</p>
                  ) : (
                    entities.map((entity, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl text-blue-200 text-sm"
                      >
                        <span className="font-bold text-blue-300">{entity.type}:</span> {entity.value}
                      </motion.div>
                    ))
                  )}
                </div>
              </motion.div>

              {/* Tactics */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 }}
                className="p-6 bg-white/[0.02] border border-white/5 rounded-2xl backdrop-blur-xl"
              >
                <div className="flex items-center gap-3 mb-4">
                  <Shield className="w-5 h-5 text-orange-400" />
                  <h3 className="font-black text-orange-400 uppercase text-sm tracking-wider">Tactics Detected</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {tactics.length === 0 ? (
                    <p className="text-slate-600 text-sm font-medium">No tactics detected yet</p>
                  ) : (
                    tactics.map((tactic, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="px-3 py-1.5 bg-orange-500/10 border border-orange-500/20 rounded-full text-orange-300 text-xs font-bold uppercase tracking-wider"
                      >
                        {tactic}
                      </motion.div>
                    ))
                  )}
                </div>
              </motion.div>
            </div>
          )}
        </div>
      </main>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.02);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(16, 185, 129, 0.3);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(16, 185, 129, 0.5);
        }
      `}</style>
    </div>
  );
};

export default LiveCall;
