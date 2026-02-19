import { useState, useEffect, useMemo, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, TestTube, Loader } from 'lucide-react';
import { useWebRTC } from '../hooks/useWebRTC';
import GlassCard from '../components/GlassCard';
import API from '../services/api';

const LiveCallWebRTC = () => {
  const { callId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);

  const roleParam = searchParams.get('role');
  const role = roleParam === 'scammer' ? 'scammer' : 'operator';

  const [callInfo, setCallInfo] = useState(null);
  const [isMuted, setIsMuted] = useState(false);
  const [isRemoteMuted, setIsRemoteMuted] = useState(false);
  const [remoteVolume, setRemoteVolume] = useState(1.0);
  const [showStats, setShowStats] = useState(false);
  const [audioNeedsEnable, setAudioNeedsEnable] = useState(true);
  const [testingVT, setTestingVT] = useState(false);
  const [vtResults, setVtResults] = useState(null);
  const [vtError, setVtError] = useState(null);
  const isMounted = useRef(true);

  const {
    isConnected,
    isPeerConnected,
    connectionState,
    error,
    transcripts = [],
    aiCoaching,
    intelligence = { entities: [], tactics: [], threatLevel: 0 },
    stats,
    remoteAudioRef,
    toggleMute,
    disconnect
  } = useWebRTC(callId, role);

  /* ─────────────────────────────────────────────
     Lifecycle
  ───────────────────────────────────────────── */

  useEffect(() => {
    isMounted.current = true;

    if (!callId) {
      navigate('/dashboard');
      return;
    }

    const fetchCallInfo = async () => {
      try {
        const res = await API.get(`/call/info/${callId}`);
        if (isMounted.current) {
          setCallInfo(res.data);
        }
      } catch (err) {
        console.error('Failed to fetch call info:', err);
      }
    };

    fetchCallInfo();

    return () => {
      isMounted.current = false;
      disconnect();
    };
  }, [callId, navigate, disconnect]);

  /* ─────────────────────────────────────────────
     Derived Values
  ───────────────────────────────────────────── */

  const connectionLabel = useMemo(() => {
    if (connectionState === 'connected') return 'text-green-400';
    if (connectionState === 'connecting') return 'text-yellow-400';
    return 'text-red-400';
  }, [connectionState]);

  const threatColor = useMemo(() => {
    if (intelligence.threatLevel < 0.3) return 'bg-green-500';
    if (intelligence.threatLevel < 0.7) return 'bg-yellow-500';
    return 'bg-red-500';
  }, [intelligence.threatLevel]);

  /* ─────────────────────────────────────────────
     Handlers
  ───────────────────────────────────────────── */

  const handleEndCall = async () => {
    try {
      await API.post(`/webrtc/room/${callId}/end`);
    } catch (err) {
      console.error(err);
    } finally {
      disconnect();
      navigate('/dashboard');
    }
  };

  const handleToggleMute = () => {
    toggleMute();
    setIsMuted(prev => !prev);
  };

  const handleToggleRemoteMute = () => {
    if (remoteAudioRef.current) {
      remoteAudioRef.current.muted = !remoteAudioRef.current.muted;
      setIsRemoteMuted(!remoteAudioRef.current.muted);
    }
  };

  const handleRemoteVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setRemoteVolume(newVolume);
    if (remoteAudioRef.current) {
      remoteAudioRef.current.volume = newVolume;
    }
  };

  const handleEnableAudio = async () => {
    if (remoteAudioRef.current) {
      try {
        console.log('🔊 Attempting to enable audio playback...');
        await remoteAudioRef.current.play();
        setAudioNeedsEnable(false);
        console.log('✅ Audio enabled successfully');
      } catch (err) {
        console.error('❌ Failed to enable audio:', err);
      }
    }
  };

  const handleTestVirusTotal = async () => {
    setTestingVT(true);
    setVtError(null);
    setVtResults(null);

    try {
      console.log('🧪 Testing VirusTotal with sample URLs...');
      const response = await API.post('/test-virustotal', {
        urls: [
          'http://malware.testing.google.test/testing/malware/',
          'https://www.google.com'
        ]
      });
      console.log('✅ VirusTotal test results:', response.data);
      setVtResults(response.data);
    } catch (error) {
      console.error('❌ VirusTotal test failed:', error);
      setVtError(error.response?.data?.detail || error.message);
    } finally {
      setTestingVT(false);
    }
  };

  // Update remote audio settings whenever they change
  useEffect(() => {
    if (remoteAudioRef?.current) {
      remoteAudioRef.current.volume = remoteVolume;
      remoteAudioRef.current.muted = isRemoteMuted;
    }
  }, [remoteVolume, isRemoteMuted, remoteAudioRef]);

  /* ─────────────────────────────────────────────
     UI
  ───────────────────────────────────────────── */

  return (
    <div className="min-h-screen bg-background py-8 px-4">

      {/* Hidden Remote Audio Element - controlled via UI buttons below */}
      <audio
        ref={remoteAudioRef}
        autoPlay
        playsInline
        className="hidden"
      />

      <div className="max-w-7xl mx-auto space-y-6">

        {/* Audio Enable Banner */}
        {audioNeedsEnable && isPeerConnected && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-yellow-500/20 border-2 border-yellow-500/50 rounded-lg p-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">🔊</span>
                <div>
                  <p className="text-white font-semibold">Enable Audio Playback</p>
                  <p className="text-yellow-200 text-sm">Click the button to hear the other person</p>
                </div>
              </div>
              <button
                onClick={handleEnableAudio}
                className="bg-yellow-500 hover:bg-yellow-600 text-black font-semibold px-6 py-2 rounded-lg transition-colors"
              >
                Enable Audio
              </button>
            </div>
          </motion.div>
        )}

        {/* HEADER */}
        <GlassCard className="p-6">
          <div className="flex items-center justify-between">

            <div>
              <h1 className="text-2xl font-bold text-white">
                Live Call — {role === 'operator' ? '👤 Operator' : '☠️ Scammer'}
              </h1>
              <p className="text-gray-400 text-sm mt-1">
                {isPeerConnected
                  ? '🔗 Peer Connected'
                  : isConnected
                    ? '⏳ Waiting for peer...'
                    : '🔌 Connecting...'}
              </p>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-sm text-right">
                <div className="text-gray-400 text-xs">Connection</div>
                <div className={`font-medium ${connectionLabel}`}>
                  {connectionState}
                </div>
              </div>

              <button
                onClick={() => setShowStats(s => !s)}
                className="px-3 py-2 bg-white/10 rounded text-white text-sm"
              >
                {showStats ? 'Hide Stats' : 'Stats'}
              </button>

              <button
                onClick={handleEndCall}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 rounded text-white font-medium"
              >
                End Call
              </button>
            </div>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-500/20 border border-red-500 rounded text-red-200 text-sm">
              ⚠ {error}
            </div>
          )}
        </GlassCard>

        {/* MAIN GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* AUDIO CONTROL - OPERATOR ONLY */}
          {role === 'operator' && (
          <GlassCard className="p-6 space-y-4">
            <h2 className="text-lg font-semibold text-white">🎤 Audio Control</h2>

            {/* Microphone Control */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm text-gray-300">
                <span>🎤 Microphone</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${isMuted ? 'bg-red-500/20 text-red-300' : 'bg-green-500/20 text-green-300'}`}>
                  {isMuted ? 'Muted' : 'Active'}
                </span>
              </div>

              <button
                onClick={handleToggleMute}
                className={`w-full py-3 rounded font-medium flex justify-center items-center gap-2 transition-colors ${
                  isMuted ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'
                } text-white`}
              >
                {isMuted ? <MicOff size={18} /> : <Mic size={18} />}
                {isMuted ? 'Unmute Mic' : 'Mute Mic'}
              </button>
            </div>

            {/* Divider */}
            <div className="border-t border-white/10 my-4"></div>

            {/* Remote Audio (Speaker) Control */}
            <div className="space-y-3">
              <div className="flex justify-between text-sm text-gray-300">
                <span>🔊 Remote Audio</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  isPeerConnected 
                    ? isRemoteMuted ? 'bg-red-500/20 text-red-300' : 'bg-green-500/20 text-green-300'
                    : 'bg-gray-500/20 text-gray-400'
                }`}>
                  {!isPeerConnected ? 'Not Connected' : isRemoteMuted ? 'Muted' : 'Playing'}
                </span>
              </div>

              <button
                onClick={handleToggleRemoteMute}
                disabled={!isPeerConnected}
                className={`w-full py-2 rounded font-medium flex justify-center items-center gap-2 transition-colors text-sm ${
                  !isPeerConnected
                    ? 'bg-gray-500/30 text-gray-500 cursor-not-allowed'
                    : isRemoteMuted 
                      ? 'bg-red-500/40 hover:bg-red-500/60 text-red-200' 
                      : 'bg-blue-500/40 hover:bg-blue-500/60 text-blue-200'
                }`}
              >
                {isRemoteMuted ? '🔇 Unmute Speaker' : '🔊 Mute Speaker'}
              </button>

              {/* Volume Slider */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-gray-400">
                  <span>Volume</span>
                  <span>{Math.round(remoteVolume * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={remoteVolume}
                  onChange={handleRemoteVolumeChange}
                  disabled={!isPeerConnected}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed
                    [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 
                    [&::-webkit-slider-thumb]:bg-blue-500 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:cursor-pointer"
                />
              </div>

              {/* Recording indicator */}
              <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded text-xs text-blue-200">
                <p>✅ Audio recording automatically every 5 seconds</p>
                <p className="mt-1 opacity-80">Transcriptions appear instantly as you speak</p>
              </div>
            </div>
          </GlassCard>
          )}
          {role !== 'operator' && (
          <GlassCard className="p-6 space-y-4">
            <h2 className="text-lg font-semibold text-white">🎤 Audio Control</h2>
            <div className="p-4 bg-gray-500/10 border border-gray-500/30 rounded text-center text-gray-300">
              <p>Audio controls available for operator only</p>
            </div>
          </GlassCard>
          )}

          {/* TRANSCRIPT */}
          <GlassCard className="p-6 h-[600px] flex flex-col">
            <h2 className="text-lg font-semibold text-white mb-4">🎙 Transcript</h2>

            <div className="flex-1 overflow-y-auto space-y-3">
              {transcripts.length === 0 && (
                <p className="text-gray-400 text-sm text-center mt-8">
                  Waiting for conversation...
                </p>
              )}

              <AnimatePresence>
                {transcripts.map((t, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`p-3 rounded text-sm ${t.speaker === 'operator'
                        ? 'bg-blue-500/20 border border-blue-500/30'
                        : 'bg-purple-500/20 border border-purple-500/30'
                      }`}
                  >
                    <div className="font-medium text-gray-200 mb-1">
                      {t.speaker === 'operator' ? 'You' : 'Scammer'}
                    </div>
                    <p className="text-white">{t.text}</p>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </GlassCard>

          {/* OPERATOR PANEL */}
          {role === 'operator' && (
            <GlassCard className="p-6 h-[600px] overflow-y-auto space-y-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white">🤖 AI Intelligence</h2>
                <button
                  onClick={handleTestVirusTotal}
                  disabled={testingVT}
                  className="flex items-center gap-2 px-3 py-1.5 bg-purple-500/20 hover:bg-purple-500/30 
                           border border-purple-500/50 rounded text-xs font-semibold text-purple-300
                           disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {testingVT ? (
                    <>
                      <Loader size={14} className="animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <TestTube size={14} />
                      Test VT
                    </>
                  )}
                </button>
              </div>

              {/* VirusTotal Test Results */}
              {vtResults && (
                <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                  <h3 className="text-sm font-semibold text-purple-300 mb-3 flex items-center gap-2">
                    <TestTube size={14} />
                    VirusTotal Test Results
                  </h3>
                  <div className="space-y-2">
                    {vtResults.results?.map((result, idx) => (
                      <div key={idx} className="bg-black/30 p-3 rounded text-xs">
                        <div className="font-mono text-gray-400 mb-2 break-all">{result.url}</div>
                        <div className={`font-semibold ${result.is_safe ? 'text-green-400' : 'text-red-400'}`}>
                          {result.summary}
                        </div>
                        {result.findings?.length > 0 && (
                          <div className="mt-2 text-gray-500">
                            {result.findings.slice(0, 3).join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {vtError && (
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <h3 className="text-sm font-semibold text-red-300 mb-2">Test Failed</h3>
                  <p className="text-xs text-red-400">{vtError}</p>
                </div>
              )}

              {/* Threat */}
              {intelligence.threatLevel > 0 && (
                <div>
                  <div className="text-sm text-yellow-200 mb-2">Threat Level</div>
                  <div className="w-full bg-gray-700 h-2 rounded overflow-hidden">
                    <motion.div
                      className={`h-full ${threatColor}`}
                      animate={{ width: `${intelligence.threatLevel * 100}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Coaching */}
              {aiCoaching?.suggestions?.length > 0 && (
                <div className="space-y-2 text-sm">
                  {aiCoaching.suggestions.map((s, i) => (
                    <div key={i} className="p-2 bg-yellow-500/20 border border-yellow-500 rounded">
                      💡 {s}
                    </div>
                  ))}
                </div>
              )}
            </GlassCard>
          )}
        </div>
      </div>
    </div>
  );
};

export default LiveCallWebRTC;
