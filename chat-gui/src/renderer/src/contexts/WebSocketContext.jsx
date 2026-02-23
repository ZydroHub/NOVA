import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';

const WebSocketContext = createContext(null);

const WS_URL = `ws://${window.location.hostname || '127.0.0.1'}:8000/ws/voice`;
const CHAT_WS_URL = `ws://${window.location.hostname || '127.0.0.1'}:8000/ws/chat`;
const API_URL = `http://${window.location.hostname || '127.0.0.1'}:8000`;

export function WebSocketProvider({ children }) {
    const [connStatus, setConnStatus] = useState('connecting'); // connected | disconnected | connecting
    const [chatConnStatus, setChatConnStatus] = useState('disconnected');
    const [messages, setMessages] = useState([]); // Chat messages
    const [streamText, setStreamText] = useState('');
    const [streaming, setStreaming] = useState(false);
    const [voiceStreamText, setVoiceStreamText] = useState('');
    const [isVoiceStreaming, setIsVoiceStreaming] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [isVoskRecording, setIsVoskRecording] = useState(false);
    const [voiceStatus, setVoiceStatus] = useState('idle'); // idle | listening | thinking | speaking
    const [voskText, setVoskText] = useState('');
    const [thinking, setThinking] = useState(false);

    // Multi-conversation state
    const [conversations, setConversations] = useState([]);
    const [currentConvId, setCurrentConvId] = useState(null);

    // Generic event listeners for other components
    const eventListeners = useRef({});

    const wsRef = useRef(null);
    const reconnectTimer = useRef(null);

    const addEventListener = useCallback((type, callback) => {
        if (!eventListeners.current[type]) {
            eventListeners.current[type] = [];
        }
        eventListeners.current[type].push(callback);

        // Return unsubscribe function
        return () => {
            eventListeners.current[type] = eventListeners.current[type].filter(cb => cb !== callback);
        };
    }, []);

    const handleServerMessage = useCallback((data) => {
        // 1. Dispatch to generic listeners first
        if (eventListeners.current[data.type]) {
            eventListeners.current[data.type].forEach(cb => cb(data));
        }

        // 2. Handle core chat messages locally (or we could move this out too, but keeping it here for simplicity of migration)
        switch (data.type) {
            case 'history': {
                const history = (data.messages || []).map((m) => ({
                    role: m.role,
                    text: m.text,
                }));
                setMessages(history);
                break;
            }
            case 'stream_start':
                setStreaming(true);
                setStreamText('');
                break;
            case 'stream_delta':
                setStreamText(data.text || '');
                break;
            case 'stream_final':
                setStreaming(false);
                setMessages((prev) => [
                    ...prev,
                    { role: 'assistant', text: data.text || '' },
                ]);
                setStreamText('');
                break;
            case 'stream_error':
                setStreaming(false);
                setMessages((prev) => [
                    ...prev,
                    { role: 'assistant', text: `⚠ Error: ${data.error || 'Unknown error'}` },
                ]);
                setStreamText('');
                break;
            case 'stream_aborted':
                setStreaming(false);
                setStreamText((prevStreamText) => {
                    if (prevStreamText) {
                        setMessages((prev) => [
                            ...prev,
                            { role: 'assistant', text: prevStreamText + '\n[aborted]' },
                        ]);
                    }
                    return '';
                });
                break;
            case 'session_reset':
                setMessages([]);
                setStreamText('');
                setStreaming(false);
                break;
            case 'voice_status':
                setVoiceStatus(data.status);
                setIsRecording(data.status === 'listening');
                if (data.status === 'idle') {
                    setIsVoiceStreaming(false);
                    setVoiceStreamText('');
                }
                break;
            case 'voice_transcription':
                // Whisper transcription (final)
                setMessages((prev) => [...prev, { role: 'user', text: data.text }]);
                setVoskText('');
                break;
            case 'vosk_partial':
                setVoskText(data.text || '');
                break;
            case 'vosk_final':
                // Final Vosk result
                setMessages((prev) => [...prev, { role: 'user', text: data.text }]);
                setVoskText('');
                break;
            case 'ai_start':
                setVoiceStreamText('');
                setIsVoiceStreaming(true);
                break;
            case 'ai_delta':
                setVoiceStreamText(data.text || '');
                break;
            case 'ai_final':
                setVoiceStreamText(data.text || '');
                // We keep isVoiceStreaming true while speaking, speaking status comes from voice_status
                break;
            case 'ai_aborted':
                setVoiceStreamText((prev) => prev + ' [aborted]');
                setTimeout(() => setIsVoiceStreaming(false), 2000);
                break;
            default:
                break;
        }
    }, []);

    const connect = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.onclose = null;
            wsRef.current.close();
        }

        setConnStatus('connecting');
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
            setConnStatus('connected');
            clearTimeout(reconnectTimer.current);
        };

        ws.onclose = () => {
            setConnStatus('disconnected');
            wsRef.current = null;
            reconnectTimer.current = setTimeout(connect, 3000);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleServerMessage(data);
            } catch (e) {
                console.error("WS Parse error", e);
            }
        };
    }, [handleServerMessage]);

    const fetchConversations = useCallback(async () => {
        try {
            const resp = await fetch(`${API_URL}/conversations`);
            const data = await resp.json();
            setConversations(data);
            return data;
        } catch (e) {
            console.error("Failed to fetch conversations", e);
        }
    }, []);

    const createConversation = useCallback(async () => {
        try {
            const resp = await fetch(`${API_URL}/conversations`, { method: 'POST' });
            const data = await resp.json();
            await fetchConversations();
            return data;
        } catch (e) {
            console.error("Failed to create conversation", e);
        }
    }, [fetchConversations]);

    const deleteConversation = useCallback(async (id) => {
        try {
            await fetch(`${API_URL}/conversations/${id}`, { method: 'DELETE' });
            await fetchConversations();
            if (currentConvId === id) {
                setCurrentConvId(null);
                setMessages([]);
            }
        } catch (e) {
            console.error("Failed to delete conversation", e);
        }
    }, [currentConvId, fetchConversations]);

    const renameConversation = useCallback(async (id, newTitle) => {
        try {
            await fetch(`${API_URL}/conversations/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            });
            await fetchConversations();
        } catch (e) {
            console.error("Failed to rename conversation", e);
        }
    }, [fetchConversations]);

    const chatWsRef = useRef(null);

    const connectChat = useCallback((convId) => {
        if (chatWsRef.current) {
            chatWsRef.current.close();
        }

        setChatConnStatus('connecting');
        const ws = new WebSocket(`${CHAT_WS_URL}/${convId}`);
        chatWsRef.current = ws;

        ws.onopen = () => setChatConnStatus('connected');
        ws.onclose = () => setChatConnStatus('disconnected');
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleServerMessage(data);
            } catch (e) {
                console.error("Chat WS Parse error", e);
            }
        };
    }, [handleServerMessage]);

    useEffect(() => {
        connect();
        fetchConversations();
        return () => {
            clearTimeout(reconnectTimer.current);
            if (wsRef.current) wsRef.current.close();
            if (chatWsRef.current) chatWsRef.current.close();
        };
    }, [connect, fetchConversations]);

    useEffect(() => {
        if (currentConvId) {
            connectChat(currentConvId);
        }
    }, [currentConvId, connectChat]);

    const sendMessage = useCallback((type, payload = {}) => {
        const targetWs = chatWsRef.current?.readyState === WebSocket.OPEN ? chatWsRef.current : wsRef.current;
        if (targetWs && targetWs.readyState === WebSocket.OPEN) {
            targetWs.send(JSON.stringify({ type, ...payload }));
        } else {
            console.warn("WS not connected, cannot send", type);
        }
    }, []);
    const toggleVoice = useCallback(() => {
        sendMessage('toggle_voice');
    }, [sendMessage]);

    const startVosk = useCallback(() => {
        setIsVoskRecording(true);
        setVoskText('');
        sendMessage('start_vosk');
    }, [sendMessage]);

    const stopVosk = useCallback(() => {
        setIsVoskRecording(false);
        sendMessage('stop_vosk');
    }, [sendMessage]);

    const abort = useCallback(() => {
        sendMessage('abort');
    }, [sendMessage]);

    const toggleThinking = useCallback(() => {
        setThinking(prev => !prev);
    }, []);

    const value = {
        connStatus,
        chatConnStatus,
        messages,
        setMessages,
        streamText,
        streaming,
        isRecording: isRecording || isVoskRecording,
        isVoskRecording,
        voiceStatus,
        voskText,
        conversations,
        currentConvId,
        setCurrentConvId,
        fetchConversations,
        createConversation,
        deleteConversation,
        renameConversation,
        sendMessage,
        toggleVoice,
        startVosk,
        stopVosk,
        abort,
        addEventListener,
        voiceStreamText,
        isVoiceStreaming,
        thinking,
        toggleThinking
    };

    return (
        <WebSocketContext.Provider value={value}>
            {children}
        </WebSocketContext.Provider>
    );
}

export function useWebSocket() {
    return useContext(WebSocketContext);
}
