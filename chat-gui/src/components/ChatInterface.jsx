import React, { useState, useRef, useCallback, useEffect } from 'react';
import ChatHeader from './ChatHeader';
import ConnectionBar from './ConnectionBar';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import { motion } from 'framer-motion';

const WS_URL = `ws://${window.location.hostname || '127.0.0.1'}:8000/ws`;

export default function ChatInterface({ layoutId }) {
    const [messages, setMessages] = useState([]);
    const [streaming, setStreaming] = useState(false);
    const [streamText, setStreamText] = useState('');
    const [connStatus, setConnStatus] = useState('connecting'); // connected | disconnected | connecting
    const wsRef = useRef(null);
    const reconnectTimer = useRef(null);

    // Use a ref for the message handler so ws.onmessage always calls the latest version
    const handleServerMessageRef = useRef(null);

    const handleServerMessage = useCallback((data) => {
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
                // Use functional update to get the latest streamText
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

            default:
                break;
        }
    }, []);

    // Keep the ref up to date
    handleServerMessageRef.current = handleServerMessage;

    // ─── WebSocket connection ──────────────────────────────────────────
    const connect = useCallback(() => {
        // Close existing connection if any
        if (wsRef.current) {
            wsRef.current.onclose = null; // prevent reconnect loop
            wsRef.current.close();
            wsRef.current = null;
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
            // Auto-reconnect after 3s
            reconnectTimer.current = setTimeout(connect, 3000);
        };

        ws.onerror = () => {
            // onclose will fire after this
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                // Always call the latest handler via the ref
                handleServerMessageRef.current(data);
            } catch {
                // Ignore non-JSON
            }
        };
    }, []);

    useEffect(() => {
        connect();
        return () => {
            clearTimeout(reconnectTimer.current);
            if (wsRef.current) {
                wsRef.current.onclose = null; // prevent reconnect on cleanup
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [connect]);

    // ─── Actions ───────────────────────────────────────────────────────
    const send = useCallback(
        (text) => {
            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
            // Add user message immediately
            setMessages((prev) => [...prev, { role: 'user', text }]);
            wsRef.current.send(JSON.stringify({ type: 'send', message: text }));
        },
        []
    );

    const abort = useCallback(() => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
        wsRef.current.send(JSON.stringify({ type: 'abort' }));
    }, []);

    const reset = useCallback(() => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
        wsRef.current.send(JSON.stringify({ type: 'reset' }));
    }, []);

    // ─── Render ────────────────────────────────────────────────────────
    return (
        <motion.div
            layoutId={layoutId}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.5, type: "spring" }}
            className="w-[480px] h-[800px] max-w-full max-h-screen mx-auto flex flex-col bg-white relative overflow-hidden"
        >
            <ChatHeader connected={connStatus === 'connected'} onReset={reset} />
            {connStatus !== 'connected' && <ConnectionBar status={connStatus} />}
            <MessageList
                messages={messages}
                streaming={streaming}
                streamText={streamText}
            />
            <ChatInput
                onSend={send}
                onAbort={abort}
                streaming={streaming}
                disabled={connStatus !== 'connected'}
            />
        </motion.div>
    );
}
