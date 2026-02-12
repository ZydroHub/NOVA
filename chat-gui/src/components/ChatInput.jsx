import React, { useState, useRef, useCallback } from 'react';

export default function ChatInput({ onSend, onAbort, streaming, disabled }) {
    const [text, setText] = useState('');
    const textareaRef = useRef(null);

    const handleSend = useCallback(() => {
        const trimmed = text.trim();
        if (!trimmed || streaming || disabled) return;
        onSend(trimmed);
        setText('');
        // Reset textarea height
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    }, [text, streaming, disabled, onSend]);

    const handleKeyDown = useCallback(
        (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
            }
        },
        [handleSend]
    );

    const handleInput = useCallback((e) => {
        setText(e.target.value);
        // Auto-resize textarea
        const el = e.target;
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 120) + 'px';
    }, []);

    return (
        <div className="chat-input-area">
            <div className="chat-input-wrapper">
                <textarea
                    ref={textareaRef}
                    className="chat-input"
                    value={text}
                    onChange={handleInput}
                    onKeyDown={handleKeyDown}
                    placeholder="Type a message…"
                    rows={1}
                    disabled={disabled}
                    autoComplete="off"
                    autoCorrect="off"
                />
            </div>

            {streaming ? (
                <button
                    className="abort-btn"
                    onClick={onAbort}
                    aria-label="Stop response"
                >
                    ■
                </button>
            ) : (
                <button
                    className="send-btn"
                    onClick={handleSend}
                    disabled={!text.trim() || disabled}
                    aria-label="Send message"
                >
                    ➤
                </button>
            )}
        </div>
    );
}
