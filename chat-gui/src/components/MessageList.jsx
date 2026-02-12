import React, { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';

export default function MessageList({ messages, streaming, streamText }) {
    const bottomRef = useRef(null);

    // Auto-scroll when messages change or stream updates
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, streamText]);

    const isEmpty = messages.length === 0 && !streaming;

    return (
        <div className="message-list">
            {isEmpty && (
                <div className="message-list__empty">
                    <div className="message-list__empty-icon">🦞</div>
                    <div className="message-list__empty-text">Start a conversation</div>
                    <div className="message-list__empty-hint">
                        Type a message below to chat with OpenClaw
                    </div>
                </div>
            )}

            {messages.map((msg, i) => (
                <MessageBubble key={i} role={msg.role} text={msg.text} />
            ))}

            {/* Streaming AI response */}
            {streaming && streamText && (
                <div className="message-row message-row--ai">
                    <div className="message-bubble message-bubble--ai">
                        <div className="message-bubble__label">AI</div>
                        {streamText}
                    </div>
                </div>
            )}

            {/* Typing indicator (shown while streaming but no text yet) */}
            {streaming && !streamText && (
                <div className="message-row message-row--ai">
                    <div className="typing-indicator">
                        <div className="typing-dot" />
                        <div className="typing-dot" />
                        <div className="typing-dot" />
                    </div>
                </div>
            )}

            <div ref={bottomRef} />
        </div>
    );
}
