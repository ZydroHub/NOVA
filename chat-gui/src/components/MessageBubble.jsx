import React from 'react';

export default function MessageBubble({ role, text }) {
    const isUser = role === 'user';

    return (
        <div className={`message-row message-row--${isUser ? 'user' : 'ai'}`}>
            <div className={`message-bubble message-bubble--${isUser ? 'user' : 'ai'}`}>
                <div className="message-bubble__label">{isUser ? 'You' : 'AI'}</div>
                {text}
            </div>
        </div>
    );
}
