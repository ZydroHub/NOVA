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
        deleteConversation
    } = useWebSocket();

    const [sidebarOpen, setSidebarOpen] = useState(false);

    // ─── Actions ───────────────────────────────────────────────────────
    const send = useCallback(
        (text, images = []) => {
            if (!currentConvId) {
                // If no conversation selected, create one first or show error
                console.warn("No conversation selected");
                return;
            }
            // Add user message immediately
            setMessages((prev) => [...prev, { role: 'user', text }]);
            sendMessage('send', { message: text, images });
        },
        [sendMessage, setMessages, currentConvId]
    );

    // ─── Auto-select/create conversation ──────────────────────────────
    useEffect(() => {
        if (!currentConvId && conversations.length > 0) {
            setCurrentConvId(conversations[0].id);
        } else if (!currentConvId && conversations.length === 0 && chatConnStatus !== 'connecting') {
            createConversation().then(conv => {
                if (conv) setCurrentConvId(conv.id);
            });
        }
    }, [currentConvId, conversations, createConversation, setCurrentConvId, chatConnStatus]);

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
                    connected={chatConnStatus === 'connected'}
                    onReset={reset}
                    sidebarOpen={sidebarOpen}
                    onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
                />
                {chatConnStatus !== 'connected' && <ConnectionBar status={chatConnStatus} />}
                <MessageList
                    messages={messages}
                    streaming={streaming}
                    streamText={streamText}
                />
                <ChatInput
                    onSend={send}
                    onAbort={abort}
                    streaming={streaming}
                    disabled={chatConnStatus !== 'connected'}
                />
            </div>
        </motion.div>
    );
}
