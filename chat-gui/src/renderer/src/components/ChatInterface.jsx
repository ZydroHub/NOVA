import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import ChatHeader from './ChatHeader';
import ConnectionBar from './ConnectionBar';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import ChatSidebar from './ChatSidebar';
import VirtualKeyboard from './VirtualKeyboard';
import { motion } from 'framer-motion';

import { useWebSocket } from '../contexts/WebSocketContext.jsx';
import { useKeyboardSettings } from '../contexts/KeyboardContext.jsx';

export default function ChatInterface() {
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
        fetchConversations,
        thinking,
        toggleVoice,
        isRecording,
        addEventListener,
    } = useWebSocket();

    const [sidebarOpen, setSidebarOpen] = useState(false);
    const { keyboardEnabled, focusState, setFocusState, focusedElementRef, syncInputValueRef } = useKeyboardSettings();
    const showInlineKeyboard = keyboardEnabled && focusState?.isChatInput === true;

    const closeKeyboard = useCallback(() => {
        setFocusState(null);
        focusedElementRef.current = null;
    }, [setFocusState, focusedElementRef]);

    const handleChatAreaPointerDown = useCallback(
        (e) => {
            if (!focusState?.isChatInput) return;
            const target = e.target;
            if (target?.closest?.('[data-virtual-keyboard]')) return;
            if (target?.closest?.('[data-chat-input-bar]')) return;
            if (target?.closest?.('[data-chat-messages]')) return;
            closeKeyboard();
        },
        [focusState?.isChatInput, closeKeyboard]
    );

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

    // Refetch conversations when Chat is shown and on an interval so task-created conversations appear without restart
    useEffect(() => {
        fetchConversations();
        const interval = setInterval(fetchConversations, 15000);
        return () => clearInterval(interval);
    }, [fetchConversations]);

    // ─── Auto-send from Gallery navigation ─────────────────────────────
    useEffect(() => {
        if (chatConnStatus === 'connected' && location.state?.prompt && location.state?.image && currentConvId) {
            const { prompt, image } = location.state;
            window.history.replaceState({}, document.title);
            send(prompt, [image]);
        }
    }, [chatConnStatus, location.state, send, currentConvId]);

    // When Whisper transcription is received in chat, send it to the backend so the AI responds
    useEffect(() => {
        const remove = addEventListener('voice_transcription', async (data) => {
            const text = (data.text || '').trim();
            if (!text) return;
            let convId = currentConvId;
            if (!convId && conversations.length > 0) convId = conversations[0].id;
            if (!convId) {
                const conv = await createConversation();
                if (conv) {
                    setCurrentConvId(conv.id);
                    convId = conv.id;
                }
            }
            if (convId) sendMessage('send', { message: text, conv_id: convId, thinking });
        });
        return remove;
    }, [addEventListener, currentConvId, conversations, createConversation, setCurrentConvId, sendMessage, thinking]);

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

            {/* Main Chat Area: keyboard in flow so it pushes content up (phone-style); tap outside input/keyboard closes keyboard */}
            <div
                className="flex-1 flex flex-col h-full min-w-0 min-h-0 touch-pan-y"
                onPointerDown={handleChatAreaPointerDown}
            >
                <ChatHeader
                    connected={connStatus === 'connected'}
                    onReset={reset}
                    sidebarOpen={sidebarOpen}
                    onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
                    onCloseKeyboard={closeKeyboard}
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
                    onMicPress={() => toggleVoice({ transcriptionOnly: true })}
                    isRecording={isRecording}
                    streaming={streaming}
                    disabled={connStatus !== 'connected'}
                />
                <VirtualKeyboard visible={showInlineKeyboard} mode="inline" focusedElementRef={focusedElementRef} syncInputValueRef={syncInputValueRef} />
            </div>
        </motion.div>
    );
}
