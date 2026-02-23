import { ArrowLeft, Menu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function ChatHeader({ connected, onReset, onToggleSidebar }) {
    const navigate = useNavigate();

    return (
        <header className="h-20 min-h-[80px] flex items-center justify-between px-4 bg-[var(--pixel-surface)] border-b-4 border-[var(--pixel-border)] z-10">
            <div className="flex items-center gap-4">
                <button
                    onClick={() => navigate('/')}
                    className="pixel-btn p-3 flex items-center justify-center"
                    aria-label="Go back"
                >
                    <ArrowLeft size={24} />
                </button>

                <button
                    onClick={onToggleSidebar}
                    className="pixel-btn p-3 flex items-center justify-center"
                    aria-label="Toggle sidebar"
                >
                    <Menu size={24} />
                </button>

                <div>
                    <div className="text-2xl font-['Press_Start_2P'] tracking-tight text-[var(--pixel-primary)] leading-none mb-2">POCKET AI</div>
                    <div className="text-sm text-[var(--pixel-secondary)] font-['VT323'] leading-none tracking-widest uppercase">{connected ? 'Chat Engine Online' : 'Connecting to AI...'}</div>
                </div>
            </div>
            <div className="flex gap-2">
                <button
                    className="w-14 h-14 pixel-btn flex items-center justify-center p-0 bg-[var(--pixel-bg)]"
                    onClick={onReset}
                    aria-label="Reset session"
                    title="RESET SESSION"
                >
                    <span className="text-2xl">↻</span>
                </button>
            </div>
        </header>
    );
}
