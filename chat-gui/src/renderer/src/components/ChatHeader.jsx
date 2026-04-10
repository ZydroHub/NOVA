import { ArrowLeft, Menu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function ChatHeader({ connected, onToggleSidebar, onCloseKeyboard }) {
    const navigate = useNavigate();

    const handleBack = () => {
        onCloseKeyboard?.();
        navigate('/');
    };

    return (
        <header className="h-16 min-h-[64px] grid grid-cols-3 items-center px-3 bg-[var(--pixel-surface)] border-b-4 border-[var(--pixel-border)] z-10">
            <div className="flex justify-start">
                <button
                    onClick={handleBack}
                    className="pixel-btn p-2 flex items-center justify-center min-h-[44px] min-w-[44px]"
                    aria-label="Go back"
                >
                    <ArrowLeft size={22} />
                </button>
            </div>
            <div className="flex flex-col items-center justify-center text-center">
                <div className="text-xl font-['Press_Start_2P'] tracking-tight text-[var(--pixel-primary)] leading-none mb-1">NOVA</div>
                <div className="text-xs text-[var(--pixel-secondary)] font-['VT323'] leading-none tracking-widest uppercase">{connected ? 'Chat Engine Online' : 'Connecting to AI...'}</div>
            </div>
            <div className="flex justify-end">
                <button
                    onClick={onToggleSidebar}
                    className="pixel-btn p-2 flex items-center justify-center min-h-[44px] min-w-[44px]"
                    aria-label="Toggle sidebar"
                >
                    <Menu size={22} />
                </button>
            </div>
        </header>
    );
}
