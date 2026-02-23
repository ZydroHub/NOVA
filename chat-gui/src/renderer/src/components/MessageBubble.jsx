import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function ThoughtBlock({ children }) {
    const [expanded, setExpanded] = useState(false);
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

export default function MessageBubble({ role, text }) {
    const isUser = role === 'user';

    // Parse thinking blocks: <think>...</think>
    const thinkRegex = /<think>([\s\S]*?)<\/think>/g;
    const thoughts = [];
    let match;
    let mainContent = text;

    while ((match = thinkRegex.exec(text)) !== null) {
        thoughts.push(match[1]);
    }

    // Remove all think blocks from main content
    mainContent = text.replace(thinkRegex, '').trim();

    return (
        <div className={`flex animate-message-in ${isUser ? 'justify-end' : 'justify-start'}`}>
            <div
                className={`max-w-[85%] px-4 py-3 text-[16px] leading-relaxed break-words border-2 font-['VT323'] shadow-[4px_4px_0_0_rgba(0,0,0,0.3)] ${isUser
                    ? 'bg-[var(--pixel-surface)] border-[var(--pixel-primary)] text-[var(--pixel-text)]'
                    : 'bg-[var(--pixel-bg)] border-[var(--pixel-secondary)] text-[var(--pixel-text)]'
                    }`}
            >
                <div className={`text-[12px] font-['Press_Start_2P'] uppercase tracking-wider mb-2 opacity-80 ${isUser ? 'text-[var(--pixel-primary)]' : 'text-[var(--pixel-secondary)]'}`}>
                    {isUser ? '> PLAYER 1' : '> SYSTEM'}
                </div>

                {!isUser && thoughts.length > 0 && (
                    <div className="mb-2">
                        {thoughts.map((thought, idx) => (
                            <ThoughtBlock key={idx}>{thought}</ThoughtBlock>
                        ))}
                    </div>
                )}

                <div className={`markdown-content ${isUser ? 'prose-invert' : ''}`}>
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                            a: ({ node, ...props }) => (
                                <a
                                    {...props}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="underline decoration-1 underline-offset-2 text-[var(--pixel-accent)] hover:bg-[var(--pixel-accent)] hover:text-black transition-colors"
                                />
                            ),
                            // Code blocks
                            code: ({ node, inline, className, children, ...props }) => {
                                const match = /language-(\w+)/.exec(className || '');
                                return !inline ? (
                                    <div className="border-2 border-[var(--pixel-border)] my-2 bg-black">
                                        <div className="px-3 py-1 text-xs font-mono uppercase bg-[var(--pixel-border)] text-[var(--pixel-text)]">
                                            {match ? match[1] : 'code'}
                                        </div>
                                        <pre className="p-3 overflow-x-auto">
                                            <code className={`font-mono text-sm ${className}`} {...props}>
                                                {children}
                                            </code>
                                        </pre>
                                    </div>
                                ) : (
                                    <code className="font-mono text-sm px-1.5 py-0.5 bg-black border border-[var(--pixel-border)] text-[var(--pixel-accent)]" {...props}>
                                        {children}
                                    </code>
                                );
                            },
                            // Lists
                            ul: ({ node, ...props }) => (
                                <ul className="list-square list-outside ml-4 my-2 space-y-1" {...props} />
                            ),
                            ol: ({ node, ...props }) => (
                                <ol className="list-decimal list-outside ml-4 my-2 space-y-1" {...props} />
                            ),
                            li: ({ node, ...props }) => (
                                <li className="pl-1 marker:text-[var(--pixel-accent)]" {...props} />
                            ),
                            // Headings
                            h1: ({ node, ...props }) => (
                                <h1 className="text-xl font-['Press_Start_2P'] mt-4 mb-2 first:mt-0 text-[var(--pixel-primary)]" {...props} />
                            ),
                            h2: ({ node, ...props }) => (
                                <h2 className="text-lg font-['Press_Start_2P'] mt-3 mb-2 first:mt-0 text-[var(--pixel-secondary)]" {...props} />
                            ),
                            h3: ({ node, ...props }) => (
                                <h3 className="text-base font-bold mt-2 mb-1 first:mt-0" {...props} />
                            ),
                            // Paragraphs
                            p: ({ node, ...props }) => (
                                <p className="mb-2 last:mb-0" {...props} />
                            ),
                            // Blockquotes
                            blockquote: ({ node, ...props }) => (
                                <blockquote className="border-l-4 border-[var(--pixel-accent)] pl-4 py-1 my-2 italic bg-black/30" {...props} />
                            ),
                            img: ({ node, ...props }) => (
                                <img {...props} className="border-2 border-[var(--pixel-border)] shadow-[4px_4px_0_0_rgba(0,0,0,0.5)]" />
                            )
                        }}
                    >
                        {mainContent}
                    </ReactMarkdown>
                </div>
            </div>
        </div>
    );
}
