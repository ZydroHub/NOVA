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
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 flex flex-col gap-3 scroll-smooth touch-pan-y">
            {isEmpty && (
                <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center p-10 text-gray-400">
                    <div className="text-5xl opacity-50">🦞</div>
                    <div className="text-[15px] font-medium text-gray-500">Start a conversation</div>
                    <div className="text-[13px] text-gray-400">
                        Type a message below to chat with OpenClaw
                    </div>
                </div>
            )}

            {messages.map((msg, i) => (
                <MessageBubble key={i} role={msg.role} text={msg.text} />
            ))}

            {/* Streaming AI response */}
            {streaming && streamText && (
                <div className="flex justify-start animate-message-in">
                    <div className="max-w-[80%] px-4 py-3 rounded-2xl text-[15px] leading-relaxed break-words whitespace-pre-wrap bg-slate-100 text-slate-800 rounded-bl-md border border-gray-200">
                        <div className="text-[11px] font-semibold uppercase tracking-wider mb-1 opacity-60">AI</div>
                        {streamText}
                    </div>
                </div>
            )}

            {/* Typing indicator (shown while streaming but no text yet) */}
            {streaming && !streamText && (
                <div className="flex justify-start animate-message-in">
                    <div className="flex gap-1.5 px-[18px] py-3.5 bg-slate-100 rounded-2xl rounded-bl-md border border-gray-200">
                        <div className="w-2 h-2 rounded-full bg-gray-400 animate-typing-bounce [animation-delay:0s]" />
                        <div className="w-2 h-2 rounded-full bg-gray-400 animate-typing-bounce [animation-delay:0.2s]" />
                        <div className="w-2 h-2 rounded-full bg-gray-400 animate-typing-bounce [animation-delay:0.4s]" />
                    </div>
                </div>
            )}

            <div ref={bottomRef} />
        </div>
    );
}
