import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function MessageBubble({ role, text }) {
    const isUser = role === 'user';

    return (
        <div className={`flex animate-message-in ${isUser ? 'justify-end' : 'justify-start'}`}>
            <div
                className={`max-w-[80%] px-4 py-3 rounded-2xl text-[15px] leading-relaxed break-words ${isUser
                    ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-br-md shadow-sm'
                    : 'bg-slate-100 text-slate-800 rounded-bl-md border border-gray-200'
                    }`}
            >
                <div className="text-[11px] font-semibold uppercase tracking-wider mb-1 opacity-60">
                    {isUser ? 'You' : 'AI'}
                </div>
                <div className={`markdown-content ${isUser ? 'prose-invert' : ''}`}>
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                            // Links
                            a: ({ node, ...props }) => (
                                <a
                                    {...props}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className={`underline decoration-1 underline-offset-2 ${isUser
                                        ? 'text-white hover:text-white/80 decoration-white/50 hover:decoration-white'
                                        : 'text-blue-600 hover:text-blue-700 decoration-blue-300 hover:decoration-blue-600'
                                        }`}
                                />
                            ),
                            // Code blocks
                            code: ({ node, inline, className, children, ...props }) => {
                                const match = /language-(\w+)/.exec(className || '');
                                return !inline ? (
                                    <div className={`rounded-md overflow-hidden my-2 ${isUser ? 'bg-blue-700/50 border border-blue-400/30' : 'bg-slate-800 text-slate-200'}`}>
                                        <div className={`px-3 py-1 text-xs font-mono uppercase bg-black/20 ${isUser ? 'text-blue-100' : 'text-slate-400'}`}>
                                            {match ? match[1] : 'code'}
                                        </div>
                                        <pre className="p-3 overflow-x-auto">
                                            <code className={`font-mono text-sm ${className}`} {...props}>
                                                {children}
                                            </code>
                                        </pre>
                                    </div>
                                ) : (
                                    <code className={`font-mono text-sm px-1.5 py-0.5 rounded ${isUser
                                        ? 'bg-blue-700/30 border border-blue-400/30'
                                        : 'bg-slate-200 text-slate-700 border border-slate-300'
                                        }`} {...props}>
                                        {children}
                                    </code>
                                );
                            },
                            // Lists
                            ul: ({ node, ...props }) => (
                                <ul className="list-disc list-outside ml-4 my-2 space-y-1" {...props} />
                            ),
                            ol: ({ node, ...props }) => (
                                <ol className="list-decimal list-outside ml-4 my-2 space-y-1" {...props} />
                            ),
                            li: ({ node, ...props }) => (
                                <li className="pl-1" {...props} />
                            ),
                            // Headings
                            h1: ({ node, ...props }) => (
                                <h1 className="text-xl font-bold mt-4 mb-2 first:mt-0" {...props} />
                            ),
                            h2: ({ node, ...props }) => (
                                <h2 className="text-lg font-bold mt-3 mb-2 first:mt-0" {...props} />
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
                                <blockquote className={`border-l-4 pl-4 py-1 my-2 italic ${isUser ? 'border-white/40 bg-white/10' : 'border-blue-500 bg-blue-50 text-slate-600'}`} {...props} />
                            ),
                        }}
                    >
                        {text}
                    </ReactMarkdown>
                </div>
            </div>
        </div>
    );
}
