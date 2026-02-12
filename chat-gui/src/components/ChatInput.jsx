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
        <div className="min-h-[80px] px-4 py-3 bg-slate-50 border-t border-gray-200 flex items-end gap-2.5 pb-[max(12px,env(safe-area-inset-bottom,12px))]">
            <div className="flex-1 flex items-end bg-slate-100 border border-gray-200 rounded-3xl px-[18px] py-1 transition-colors focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20">
                <textarea
                    ref={textareaRef}
                    className="flex-1 border-none bg-transparent text-slate-900 text-base leading-relaxed min-h-[48px] max-h-[120px] resize-none outline-none py-2.5 placeholder:text-gray-400"
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
                    className="w-11 h-11 rounded-full border-none bg-red-500 text-white text-lg flex items-center justify-center cursor-pointer transition-all duration-150 shrink-0 active:scale-90 active:bg-red-700"
                    onClick={onAbort}
                    aria-label="Stop response"
                >
                    ■
                </button>
            ) : (
                <button
                    className="w-11 h-11 rounded-full border-none bg-blue-500 text-white text-xl flex items-center justify-center cursor-pointer transition-all duration-150 shrink-0 active:scale-90 active:bg-blue-600 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-default"
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
