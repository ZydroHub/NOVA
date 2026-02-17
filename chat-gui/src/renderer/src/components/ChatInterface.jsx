import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import ChatHeader from './ChatHeader';
import ConnectionBar from './ConnectionBar';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import { motion } from 'framer-motion';

import { useWebSocket } from '../contexts/WebSocketContext.jsx';

export default function ChatInterface({ layoutId }) {
    const location = useLocation();
    const {
        connStatus,
        messages,
        setMessages, // We need this to add optimistic user messages
        streamText,
        streaming,
        sendMessage
    } = useWebSocket();

    // ─── Actions ───────────────────────────────────────────────────────
    const send = useCallback(
        (text, images = []) => {
            // Add user message immediately
            setMessages((prev) => [...prev, { role: 'user', text }]);
            sendMessage('send', { message: text, images });
        },
        [sendMessage, setMessages]
    );

    // ─── Auto-send from Gallery navigation ─────────────────────────────
    useEffect(() => {
        if (connStatus === 'connected' && location.state?.prompt && location.state?.image) {
            const { prompt, image } = location.state;
            // Clear state to prevent double send on refresh/re-render logic if needed,
            // but react-router state persists. We should probably clear it.
            // Using history.replace to clear state is safer.
            window.history.replaceState({}, document.title);

            // Send message
            send(prompt, [image]);
        }
    }, [connStatus, location.state, send]);

    const abort = useCallback(() => {
        sendMessage('abort');
    }, [sendMessage]);

    const reset = useCallback(() => {
        sendMessage('reset');
    }, [sendMessage]);

    // ─── Render ────────────────────────────────────────────────────────
    return (
        <motion.div
            layoutId={layoutId}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.5, type: "spring" }}
            className="w-[480px] h-full mx-auto flex flex-col bg-white relative overflow-hidden"
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
