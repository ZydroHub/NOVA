import React, { useEffect, useRef, useState } from 'react';
import MessageBubble from './MessageBubble';

function ThoughtBlock({ children }) {
    const [expanded, setExpanded] = useState(true); // Default expanded for streaming
    return (
        <div className={`thought-container ${expanded ? 'thought-expanded' : ''}`}>
            <div className="thought-header" onClick={() => setExpanded(!expanded)}>
                <span className="thought-title">Thought Process</span>
                <span className="thought-icon">▼</span>
            </div>
            {expanded && (
                <div className="thought-content">
                    {children}
                </div>
            )}
        </div>
    );
}

export default function MessageList({ messages, streaming, streamText }) {
    const bottomRef = useRef(null);

    // Auto-scroll when messages change or stream updates
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, streamText]);

    // Parse streamText for thinking logic
    const thinkRegex = /<think>([\s\S]*?)(?:<\/think>|$)/; // Non-greedy or until end
    const match = streamText.match(thinkRegex);
    let thoughtText = '';
    let hasCompleteThink = false;
    let mainContent = streamText;

    if (match) {
        thoughtText = match[1];
        hasCompleteThink = streamText.includes('</think>');
        // If it's complete, remove it from main content. 
        // If not, mainContent is usually empty or small until </think> is reached.
        if (hasCompleteThink) {
            mainContent = streamText.replace(/<think>[\s\S]*?<\/think>/, '').trim();
        } else {
            mainContent = ''; // Wait for finish
        }
    }

    const isEmpty = messages.length === 0 && !streaming;

    return (
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 flex flex-col gap-4 scroll-smooth touch-pan-y scroller-pixel">
            {isEmpty && (
                <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center p-10 opacity-50">
                    <div className="text-6xl font-['Press_Start_2P'] text-[var(--pixel-secondary)] animate-pulse">?</div>
                    <div className="text-xl font-['VT323'] text-[var(--pixel-text)]">INITIALIZE CHAT PROTOCOL</div>
                    <div className="text-sm font-['VT323'] text-[var(--pixel-border)]">
                        WAITING FOR INPUT...
                    </div>
                </div>
            )}

            {messages.map((msg, i) => (
                <MessageBubble key={i} role={msg.role} text={msg.text} />
            ))}

            {/* Streaming AI response */}
            {streaming && streamText && (
                <div className="flex justify-start animate-message-in">
                    <div className="max-w-[85%] px-4 py-3 text-[16px] leading-relaxed break-words border-2 font-['VT323'] shadow-[4px_4px_0_0_rgba(0,0,0,0.3)] bg-[var(--pixel-bg)] border-[var(--pixel-secondary)] text-[var(--pixel-text)]">
                        <div className="text-[12px] font-['Press_Start_2P'] uppercase tracking-wider mb-2 opacity-80 text-[var(--pixel-secondary)]">
                            {'> SYSTEM'}
                        </div>

                        {thoughtText && (
                            <ThoughtBlock>{thoughtText}{!hasCompleteThink && <span className="animate-blink">_</span>}</ThoughtBlock>
                        )}

                        <div className="markdown-content">
                            {mainContent} {(!thoughtText || hasCompleteThink) && <span className="animate-blink">_</span>}
                        </div>
                    </div>
                </div>
            )}

            {/* Typing indicator (shown while streaming but no text yet) */}
            {streaming && !streamText && (
                <div className="flex justify-start animate-message-in">
                    <div className="flex gap-2 px-4 py-4 bg-[var(--pixel-bg)] border-2 border-[var(--pixel-secondary)] shadow-[4px_4px_0_0_rgba(0,0,0,0.3)]">
                        <div className="w-3 h-3 bg-[var(--pixel-secondary)] animate-bounce [animation-delay:0s]" />
                        <div className="w-3 h-3 bg-[var(--pixel-secondary)] animate-bounce [animation-delay:0.2s]" />
                        <div className="w-3 h-3 bg-[var(--pixel-secondary)] animate-bounce [animation-delay:0.4s]" />
                    </div>
                </div>
            )}

            <div ref={bottomRef} />
        </div>
    );
}
