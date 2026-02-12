import React from 'react';

export default function ChatHeader({ connected, onReset }) {
    return (
        <header className="h-16 min-h-[64px] flex items-center justify-between px-4 bg-slate-50 border-b border-gray-200 z-10">
            <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-lg shadow-[0_2px_12px_rgba(0,149,255,0.2)]">
                    🦞
                </div>
                <div>
                    <div className="text-[17px] font-bold tracking-tight text-slate-900">OpenClaw</div>
                    <div className="text-[11px] text-slate-500 font-medium">AI Assistant</div>
                </div>
            </div>
            <div className="flex gap-2">
                <button
                    className="w-12 h-12 border-none rounded-[10px] bg-gray-200 text-gray-600 text-lg cursor-pointer flex items-center justify-center transition-all duration-150 active:scale-95 active:bg-blue-500 active:text-white"
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
