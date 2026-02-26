import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import ChatHeader from './ChatHeader';
import ConnectionBar from './ConnectionBar';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import ChatSidebar from './ChatSidebar';
import { motion } from 'framer-motion';

import { useWebSocket } from '../contexts/WebSocketContext.jsx';

export default function ChatInterface({ layoutId }) {
    const location = useLocation();
    const {
        connStatus,
        connect,
        chatConnStatus,
        messages,
        setMessages,
        streamText,
        streaming,
        sendMessage,
        conversations,
        currentConvId,
        setCurrentConvId,
        createConversation,
        deleteConversation,
        thinking
    } = useWebSocket();

    const [sidebarOpen, setSidebarOpen] = useState(false);

    // ─── Actions ───────────────────────────────────────────────────────
    const send = useCallback(
        async (text, images = []) => {
            let activeConvId = currentConvId;
            if (!activeConvId) {
                const conv = await createConversation();
                if (conv) {
                    activeConvId = conv.id;
                    setCurrentConvId(conv.id);
                } else {
                    console.error("Failed to create conversation");
                    return;
                }
            }
            // Add user message immediately
            setMessages((prev) => [...prev, { role: 'user', text }]);
            sendMessage('send', { message: text, images, conv_id: activeConvId, thinking });
        },
        [sendMessage, setMessages, currentConvId, createConversation, setCurrentConvId, thinking]
    );

    // ─── Auto-select/create conversation ──────────────────────────────
    useEffect(() => {
        if (!currentConvId && conversations.length > 0) {
            setCurrentConvId(conversations[0].id);
        }
    }, [currentConvId, conversations, setCurrentConvId]);

    // ─── Auto-send from Gallery navigation ─────────────────────────────
    useEffect(() => {
        if (chatConnStatus === 'connected' && location.state?.prompt && location.state?.image && currentConvId) {
            const { prompt, image } = location.state;
            window.history.replaceState({}, document.title);
            send(prompt, [image]);
        }
    }, [chatConnStatus, location.state, send, currentConvId]);

    const abort = useCallback(() => {
        sendMessage('abort');
    }, [sendMessage]);

    const reset = useCallback(() => {
        sendMessage('reset');
    }, [sendMessage]);

    const handleNewChat = async () => {
        const conv = await createConversation();
        if (conv) setCurrentConvId(conv.id);
    };

    // ─── Render ────────────────────────────────────────────────────────
    return (
        <motion.div
            layoutId={layoutId}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.5, type: "spring" }}
            className="w-full h-full mx-auto flex bg-[var(--pixel-bg)] relative overflow-hidden"
        >
            <ChatSidebar
                isOpen={sidebarOpen}
                onClose={() => setSidebarOpen(false)}
                conversations={conversations}
                currentConvId={currentConvId}
                setCurrentConvId={setCurrentConvId}
                createConversation={createConversation}
                deleteConversation={deleteConversation}
            />

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col h-full min-w-0">
                <ChatHeader
                    connected={connStatus === 'connected'}
                    onReset={reset}
                    sidebarOpen={sidebarOpen}
                    onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
                />
                {connStatus !== 'connected' && <ConnectionBar status={connStatus} onRetry={connect} />}
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
            </div>
        </motion.div>
    );
}
