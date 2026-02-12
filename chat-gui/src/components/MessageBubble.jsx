import React from 'react';

export default function MessageBubble({ role, text }) {
    const isUser = role === 'user';

    return (
        <div className={`flex animate-message-in ${isUser ? 'justify-end' : 'justify-start'}`}>
            <div
                className={`max-w-[80%] px-4 py-3 rounded-2xl text-[15px] leading-relaxed break-words whitespace-pre-wrap ${isUser
                        ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-br-md shadow-sm'
                        : 'bg-slate-100 text-slate-800 rounded-bl-md border border-gray-200'
                    }`}
            >
                <div className="text-[11px] font-semibold uppercase tracking-wider mb-1 opacity-60">
                    {isUser ? 'You' : 'AI'}
                </div>
                {text}
            </div>
        </div>
    );
}
