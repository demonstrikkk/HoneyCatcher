/**
 * WebRTC Service - P2P Audio Streaming with Backend Transcription
 * Manages WebRTC peer connections for real-time audio streaming
 * AND sends audio chunks to backend via Socket.IO for STT + AI coaching
 */

import { io } from 'socket.io-client';

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || 'http://localhost:8000';

// TURN server config (self-hosted coturn)
const TURN_URL = import.meta.env.VITE_TURN_URL || '';
const TURN_USERNAME = import.meta.env.VITE_TURN_USERNAME || '';
const TURN_CREDENTIAL = import.meta.env.VITE_TURN_CREDENTIAL || '';

class WebRTCService {
  constructor() {
    this.socket = null;
    this.peerConnection = null;
    this.localStream = null;
    this.remoteStream = null;
    this.roomId = null;
    this.role = null;
    this.isInitiator = false;
    
    // Audio chunk capture for backend transcription
    this._localMediaRecorder = null;
    this._remoteMediaRecorder = null;
    this._audioChunkInterval = null;
    this._isCapturing = false;
    
    // Callbacks
    this.onRemoteStream = null;
    this.onTranscription = null;
    this.onAICoaching = null;
    this.onIntelligenceUpdate = null;
    this.onPeerJoined = null;
    this.onPeerDisconnected = null;
    this.onConnectionStateChange = null;
    
    // ICE servers configuration - includes TURN if configured
    const iceServers = [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' },
      { urls: 'stun:stun2.l.google.com:19302' }
    ];
    
    // Add TURN server if configured (self-hosted coturn)
    if (TURN_URL) {
      iceServers.push({
        urls: [
          `turn:${TURN_URL}?transport=udp`,
          `turn:${TURN_URL}?transport=tcp`,
          `turns:${TURN_URL}?transport=tcp`
        ],
        username: TURN_USERNAME,
        credential: TURN_CREDENTIAL
      });
      console.log('🔄 TURN server configured:', TURN_URL);
    }
    
    this.iceServers = { iceServers };
    
    console.log('🎙️ WebRTC Service initialized');
  }
  
  /**
   * Initialize socket connection and join room
   */
  async connect(roomId, role = 'operator') {
    this.roomId = roomId;
    this.role = role;
    this.isInitiator = (role === 'operator'); // Operator initiates WebRTC offer
    
    return new Promise((resolve, reject) => {
      try {
        // Connect to Socket.IO
        this.socket = io(SOCKET_URL, {
          transports: ['websocket', 'polling'],
          reconnection: true,
          reconnectionAttempts: 5,
          reconnectionDelay: 1000
        });
        
        // Setup socket event handlers
        this.setupSocketHandlers();
        
        this.socket.on('connected', (data) => {
          console.log('🔌 Socket connected:', data.sid);
          
          // Join the room
          this.socket.emit('join_room', {
            room_id: roomId,
            role: role
          });
        });
        
        this.socket.on('joined_room', async (data) => {
          console.log('📞 Joined room:', data);
          
          // Start capturing local audio
          await this.startLocalStream();
          
          // Create peer connection immediately if peer is already present
          if (!data.waiting_for_peer) {
            console.log('🔗 Peer already in room, creating peer connection...');
            this.createPeerConnection();
            
            // If we're initiator (operator), create offer
            if (this.isInitiator) {
              await this.createOffer();
            }
          }
          
          resolve(data);
        });
        
        this.socket.on('connect_error', (error) => {
          console.error('❌ Socket connection error:', error);
          reject(error);
        });
        
      } catch (error) {
        console.error('❌ Connection error:', error);
        reject(error);
      }
    });
  }
  
  /**
   * Setup Socket.IO event handlers
   */
  setupSocketHandlers() {
    // Peer joined - if we're initiator, create offer
    this.socket.on('peer_joined', async (data) => {
      console.log('👤 Peer joined:', data);
      
      if (this.onPeerJoined) {
        this.onPeerJoined(data);
      }
      
      // Create WebRTC peer connection (if not already created)
      if (!this.peerConnection) {
        console.log('🔗 Creating peer connection after peer joined...');
        this.createPeerConnection();
      }
      
      // If we're initiator, create and send offer
      if (this.isInitiator) {
        await this.createOffer();
      }
    });
    
    // Received WebRTC offer
    this.socket.on('webrtc_offer', async (data) => {
      console.log('📥 Received WebRTC offer');
      
      // Create peer connection if not exists
      if (!this.peerConnection) {
        console.log('🔗 Creating peer connection to handle offer...');
        this.createPeerConnection();
      }
      
      await this.handleOffer(data.offer);
    });
    
    // Received WebRTC answer
    this.socket.on('webrtc_answer', async (data) => {
      console.log('📥 Received WebRTC answer');
      await this.handleAnswer(data.answer);
    });
    
    // Received ICE candidate
    this.socket.on('ice_candidate', async (data) => {
      console.log('🧊 Received ICE candidate');
      await this.handleIceCandidate(data.candidate);
    });
    
    // Transcription received
    this.socket.on('transcription', (data) => {
      console.log('📝 Transcription:', data.text);
      if (this.onTranscription) {
        this.onTranscription(data);
      }
    });
    
    // AI coaching received
    this.socket.on('ai_coaching', (data) => {
      console.log('🤖 AI Coaching:', data);
      if (this.onAICoaching) {
        this.onAICoaching(data);
      }
    });
    
    // Intelligence update received
    this.socket.on('intelligence_update', (data) => {
      console.log('🔍 Intelligence Update:', data);
      if (this.onIntelligenceUpdate) {
        this.onIntelligenceUpdate(data);
      }
    });
    
    // Peer disconnected
    this.socket.on('peer_disconnected', (data) => {
      console.log('👤 Peer disconnected:', data);
      if (this.onPeerDisconnected) {
        this.onPeerDisconnected(data);
      }
      this.closePeerConnection();
    });
    
    // Call ended
    this.socket.on('call_ended', (data) => {
      console.log('📞 Call ended:', data);
      this.disconnect();
    });
  }
  
  /**
   * Start capturing local audio stream
   */
  async startLocalStream() {
    try {
      console.log(`🎤 Requesting microphone access for ${this.role}...`);
      
      this.localStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,  // Disable for same-device testing
          noiseSuppression: false,  // Disable for same-device testing
          autoGainControl: true,
          sampleRate: 16000,
          channelCount: 1
        },
        video: false
      });
      
      console.log(`✅ ${this.role} microphone access granted`);
      console.log('📊 Local stream tracks:', this.localStream.getTracks().map(t => `${t.kind}: ${t.enabled} (${t.readyState})`));
      
      // Verify audio track is active
      const audioTracks = this.localStream.getAudioTracks();
      if (audioTracks.length === 0) {
        throw new Error('No audio tracks available');
      }
      
      console.log(`🔊 ${this.role} has ${audioTracks.length} audio track(s) ready`);
      
      // Start sending audio chunks to backend for transcription
      this._startLocalAudioCapture();
      
      return this.localStream;
      
    } catch (error) {
      console.error(`❌ Failed to get microphone for ${this.role}:`, error);
      if (error.name === 'NotAllowedError') {
        console.error('🚫 Microphone permission denied by user');
      } else if (error.name === 'NotFoundError') {
        console.error('🔍 No microphone device found');
      }
      throw error;
    }
  }
  
  /**
   * Create WebRTC peer connection
   */
  createPeerConnection() {
    if (this.peerConnection) {
      console.log('⚠️ Peer connection already exists');
      return;
    }
    
    this.peerConnection = new RTCPeerConnection(this.iceServers);
    
    // Add local stream tracks to peer connection
    if (this.localStream) {
      this.localStream.getTracks().forEach(track => {
        const sender = this.peerConnection.addTrack(track, this.localStream);
        console.log('🎵 Added track to peer connection:', track.kind, 'enabled:', track.enabled);
      });
      
      const audioTracks = this.localStream.getAudioTracks();
      console.log(`✅ Total audio tracks added: ${audioTracks.length}`);
    } else {
      console.warn('⚠️ No local stream available when creating peer connection!');
    }
    
    // Handle ICE candidates
    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        console.log('🧊 Sending ICE candidate:', event.candidate.type, event.candidate.protocol);
        this.socket.emit('ice_candidate', {
          candidate: event.candidate
        });
      } else {
        console.log('✅ All ICE candidates sent (null candidate received)');
      }
    };
    
    // Handle remote stream
    this.peerConnection.ontrack = (event) => {
      console.log('🎵 Received remote track:', event.track.kind, 'readyState:', event.track.readyState);
      console.log('📦 Streams in event:', event.streams.length);
      
      if (!this.remoteStream) {
        this.remoteStream = new MediaStream();
        console.log('🆕 Created new remote stream');
      }
      
      event.track.onended = () => {
        console.log('⚠️ Remote track ended:', event.track.kind);
      };
      
      this.remoteStream.addTrack(event.track);
      console.log(`✅ Remote stream now has ${this.remoteStream.getTracks().length} tracks`);
      
      if (this.onRemoteStream) {
        console.log('📢 Calling onRemoteStream callback');
        this.onRemoteStream(this.remoteStream);
      }
      
      // Start capturing remote audio for backend transcription
      this._startRemoteAudioCapture();
    };
    
    // Handle connection state changes
    this.peerConnection.onconnectionstatechange = () => {
      const state = this.peerConnection.connectionState;
      console.log('🔗 Connection state:', state);
      
      if (this.onConnectionStateChange) {
        this.onConnectionStateChange(state);
      }
      
      if (state === 'failed' || state === 'disconnected') {
        console.error('❌ Peer connection failed');
        this.reconnect();
      }
    };
    
    // Handle ICE connection state
    this.peerConnection.oniceconnectionstatechange = () => {
      const state = this.peerConnection.iceConnectionState;
      console.log('🧊 ICE connection state:', state);
      
      if (state === 'connected' || state === 'completed') {
        console.log('✅ ICE connection established - audio should flow now');
      } else if (state === 'failed') {
        console.error('❌ ICE connection failed - trying TURN servers or check firewall');
      }
    };
    
    console.log('🔗 Peer connection created');
  }
  
  /**
   * Create and send WebRTC offer
   */
  async createOffer() {
    if (!this.peerConnection) {
      this.createPeerConnection();
    }
    
    try {
      const offer = await this.peerConnection.createOffer({
        offerToReceiveAudio: true,
        offerToReceiveVideo: false
      });
      
      await this.peerConnection.setLocalDescription(offer);
      
      console.log('📤 Sending WebRTC offer');
      this.socket.emit('webrtc_offer', { offer });
      
    } catch (error) {
      console.error('❌ Failed to create offer:', error);
      throw error;
    }
  }
  
  /**
   * Handle received WebRTC offer
   */
  async handleOffer(offer) {
    if (!this.peerConnection) {
      this.createPeerConnection();
    }
    
    try {
      await this.peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
      
      const answer = await this.peerConnection.createAnswer();
      await this.peerConnection.setLocalDescription(answer);
      
      console.log('📤 Sending WebRTC answer');
      this.socket.emit('webrtc_answer', { answer });
      
    } catch (error) {
      console.error('❌ Failed to handle offer:', error);
      throw error;
    }
  }
  
  /**
   * Handle received WebRTC answer
   */
  async handleAnswer(answer) {
    try {
      console.log('📥 Setting remote description from answer');
      await this.peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
      console.log('✅ Remote description set - connection should establish');
      
    } catch (error) {
      console.error('❌ Failed to handle answer:', error);
      throw error;
    }
  }
  
  /**
   * Handle received ICE candidate
   */
  async handleIceCandidate(candidate) {
    try {
      console.log('🧊 Adding ICE candidate:', candidate.type);
      await this.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
      console.log('✅ ICE candidate added successfully');
      
    } catch (error) {
      console.error('❌ Failed to add ICE candidate:', error);
    }
  }
  
  /**
   * Attempt to reconnect peer connection
   */
  async reconnect() {
    console.log('🔄 Attempting to reconnect...');
    this.closePeerConnection();
    
    if (this.isInitiator) {
      await this.createOffer();
    }
  }
  
  /**
   * Close peer connection
   */
  closePeerConnection() {
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
      console.log('🔗 Peer connection closed');
    }
    
    if (this.remoteStream) {
      this.remoteStream.getTracks().forEach(track => track.stop());
      this.remoteStream = null;
    }
  }
  
  /**
   * Start capturing local audio and sending chunks to backend for transcription
   * This runs IN PARALLEL with the P2P WebRTC stream
   */
  _startLocalAudioCapture() {
    // Only operator can capture and send audio (realistic deployment)
    if (this.role !== 'operator') {
      console.log(`ℹ️ ${this.role} audio capture disabled (operator-only mode)`);
      return;
    }
    
    if (this._localMediaRecorder) {
      console.log(`⚠️ ${this.role} local audio capture already active`);
      return;
    }
    
    if (!this.localStream) {
      console.error(`❌ ${this.role} cannot start audio capture: no local stream`);
      return;
    }
    
    if (!this.socket || !this.socket.connected) {
      console.error(`❌ ${this.role} cannot start audio capture: socket not connected`);
      return;
    }
    
    try {
      // Choose best supported format
      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm';
      }
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/ogg;codecs=opus';
      }
      
      console.log(`🔴 Starting MediaRecorder for ${this.role} with ${mimeType}`);
      
      this._localMediaRecorder = new MediaRecorder(this.localStream, {
        mimeType,
        audioBitsPerSecond: 64000  // Lower bitrate for transcription (saves bandwidth)
      });
      
      this._localMediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0 && this.socket?.connected) {
          // Convert blob to base64 and send to backend
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64 = reader.result.split(',')[1];
            console.log(`🎤 ${this.role} SENDING chunk: ${event.data.size} bytes to backend`);
            console.log(`   📍 Socket ID: ${this.socket.id}`);
            console.log(`   🔗 Room: ${this.roomId}`);
            console.log(`   ⏱️ Timestamp: ${new Date().toISOString()}`);
            
            this.socket.emit('transcription_chunk', {
              audio: base64,
              format: 'webm',
              speaker: this.role || 'operator',
              room_id: this.roomId
            }, (ack) => {
              console.log(`✅ ${this.role} chunk ACK received from server`);
            });
          };
          reader.readAsDataURL(event.data);
        } else {
          if (!this.socket?.connected) {
            console.warn(`⚠️ ${this.role} skipped chunk: socket disconnected`);
          }
          if (!(event.data.size > 0)) {
            console.warn(`⚠️ ${this.role} skipped empty chunk`);
          }
        }
      };
      
      this._localMediaRecorder.onerror = (error) => {
        console.error(`❌ ${this.role} MediaRecorder error:`, error);
      };
      
      this._localMediaRecorder.onstart = () => {
        console.log(`✅ ${this.role} MediaRecorder started successfully`);
      };
      
      this._localMediaRecorder.onstop = () => {
        console.log(`🛑 ${this.role} MediaRecorder stopped`);
      };
      
      // Send chunks every 5 seconds for continuous automatic transcription
      this._localMediaRecorder.start(5000);
      this._isCapturing = true;
      console.log(`✅ ${this.role} local audio capture active - 5s chunks`);
      
    } catch (error) {
      console.error(`❌ Failed to start ${this.role} local audio capture:`, error);
    }
  }
  
  /**
   * Start capturing remote (incoming) audio and sending to backend
   * This captures what the other peer is saying for transcription
   */
  _startRemoteAudioCapture() {
    if (this._remoteMediaRecorder) {
      console.log(`⚠️ ${this.role} remote audio capture already active`);
      return;
    }
    
    if (!this.remoteStream) {
      console.error(`❌ ${this.role} cannot start remote capture: no remote stream`);
      return;
    }
    
    if (!this.socket || !this.socket.connected) {
      console.error(`❌ ${this.role} cannot start remote capture: socket not connected`);
      return;
    }
    
    try {
      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm';
      }
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/ogg;codecs=opus';
      }
      
      const remoteSpeaker = this.role === 'operator' ? 'scammer' : 'operator';
      console.log(`🔴 Starting remote MediaRecorder for ${remoteSpeaker} (heard by ${this.role})`);
      
      this._remoteMediaRecorder = new MediaRecorder(this.remoteStream, {
        mimeType,
        audioBitsPerSecond: 64000
      });
      
      this._remoteMediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0 && this.socket?.connected) {
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64 = reader.result.split(',')[1];
            console.log(`🔊 ${this.role} sending remote audio chunk: ${event.data.size} bytes as ${remoteSpeaker}`);
            this.socket.emit('transcription_chunk', {
              audio: base64,
              format: 'webm',
              speaker: remoteSpeaker,
              room_id: this.roomId
            });
          };
          reader.readAsDataURL(event.data);
        } else {
          console.warn(`⚠️ ${this.role} remote: skipped empty chunk or socket disconnected`);
        }
      };
      
      this._remoteMediaRecorder.onerror = (error) => {
        console.error(`❌ ${this.role} remote MediaRecorder error:`, error);
      };
      
      this._remoteMediaRecorder.onstart = () => {
        console.log(`✅ ${remoteSpeaker} remote MediaRecorder started`);
      };
      
      this._remoteMediaRecorder.onstop = () => {
        console.log(`🛑 ${remoteSpeaker} remote MediaRecorder stopped`);
      };
      
      this._remoteMediaRecorder.start(5000);
      console.log(`✅ ${this.role} remote audio capture active - hearing ${remoteSpeaker}`);
      
    } catch (error) {
      console.error(`❌ Failed to start ${this.role} remote audio capture:`, error);
    }
  }
  
  /**
   * Stop all audio capture
   */
  _stopAudioCapture() {
    if (this._localMediaRecorder && this._localMediaRecorder.state !== 'inactive') {
      try { this._localMediaRecorder.stop(); } catch (e) { /* ignore */ }
      this._localMediaRecorder = null;
    }
    
    if (this._remoteMediaRecorder && this._remoteMediaRecorder.state !== 'inactive') {
      try { this._remoteMediaRecorder.stop(); } catch (e) { /* ignore */ }
      this._remoteMediaRecorder = null;
    }
    
    this._isCapturing = false;
    console.log('⏹️ Audio capture stopped');
  }
  
  /**
   * Disconnect and cleanup
   */
  disconnect() {
    console.log('🛑 Disconnecting...');
    
    // Stop audio capture for transcription
    this._stopAudioCapture();
    
    // Stop local stream
    if (this.localStream) {
      this.localStream.getTracks().forEach(track => track.stop());
      this.localStream = null;
    }
    
    // Close peer connection
    this.closePeerConnection();
    
    // Disconnect socket
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    
    console.log('✅ Disconnected');
  }
  
  /**
   * Get connection stats
   */
  async getStats() {
    if (!this.peerConnection) {
      return null;
    }
    
    try {
      const stats = await this.peerConnection.getStats();
      const result = {
        audio: {},
        connection: {}
      };
      
      stats.forEach(report => {
        if (report.type === 'inbound-rtp' && report.kind === 'audio') {
          result.audio.inbound = {
            bytesReceived: report.bytesReceived,
            packetsReceived: report.packetsReceived,
            packetsLost: report.packetsLost,
            jitter: report.jitter
          };
        }
        
        if (report.type === 'outbound-rtp' && report.kind === 'audio') {
          result.audio.outbound = {
            bytesSent: report.bytesSent,
            packetsSent: report.packetsSent
          };
        }
        
        if (report.type === 'candidate-pair' && report.state === 'succeeded') {
          result.connection = {
            currentRoundTripTime: report.currentRoundTripTime,
            availableOutgoingBitrate: report.availableOutgoingBitrate
          };
        }
      });
      
      return result;
      
    } catch (error) {
      console.error('❌ Failed to get stats:', error);
      return null;
    }
  }
}

export default WebRTCService;
