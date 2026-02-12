import React from 'react';

export default function ChatHeader({ connected, onReset }) {
    return (
        <header className="chat-header">
            <div className="chat-header__logo">
                <div className="chat-header__icon">🦞</div>
                <div>
                    <div className="chat-header__title">OpenClaw</div>
                    <div className="chat-header__subtitle">AI Assistant</div>
                </div>
            </div>
            <div className="chat-header__actions">
                <button
                    className="header-btn"
                    onClick={onReset}
                    aria-label="Reset session"
                    title="Reset session"
                >
                    ↻
                </button>
            </div>
        </header>
    );
}
