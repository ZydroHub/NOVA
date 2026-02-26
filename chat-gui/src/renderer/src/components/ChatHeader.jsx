import { ArrowLeft, Menu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function ChatHeader({ connected, onToggleSidebar }) {
    const navigate = useNavigate();

    return (
        <header className="h-20 min-h-[80px] grid grid-cols-3 items-center px-4 bg-[var(--pixel-surface)] border-b-4 border-[var(--pixel-border)] z-10">
            <div className="flex justify-start">
                <button
                    onClick={() => navigate('/')}
                    className="pixel-btn p-3 flex items-center justify-center"
                    aria-label="Go back"
                >
                    <ArrowLeft size={24} />
                </button>
            </div>
            <div className="flex flex-col items-center justify-center text-center">
                <div className="text-2xl font-['Press_Start_2P'] tracking-tight text-[var(--pixel-primary)] leading-none mb-2">POCKET</div>
                <div className="text-sm text-[var(--pixel-secondary)] font-['VT323'] leading-none tracking-widest uppercase">{connected ? 'Chat Engine Online' : 'Connecting to AI...'}</div>
            </div>
            <div className="flex justify-end">
                <button
                    onClick={onToggleSidebar}
                    className="pixel-btn p-3 flex items-center justify-center"
                    aria-label="Toggle sidebar"
                >
                    <Menu size={24} />
                </button>
            </div>
        </header>
    );
}
