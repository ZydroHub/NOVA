import { ArrowLeft, Menu, Brain } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useWebSocket } from '../contexts/WebSocketContext.jsx';

export default function ChatHeader({ connected, onToggleSidebar }) {
    const navigate = useNavigate();
    const { thinking, toggleThinking } = useWebSocket();

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
                    <div className="text-2xl font-['Press_Start_2P'] tracking-tight text-[var(--pixel-primary)] leading-none mb-2">POCKET</div>
                    <div className="text-sm text-[var(--pixel-secondary)] font-['VT323'] leading-none tracking-widest uppercase">{connected ? 'Chat Engine Online' : 'Connecting to AI...'}</div>
                </div>
            </div>
            <div className="flex gap-2">
                <button
                    className={`w-14 h-14 pixel-btn flex items-center justify-center p-0 transition-all duration-300 ${thinking ? 'bg-[var(--pixel-primary)]' : 'bg-gray-800 opacity-50'}`}
                    onClick={toggleThinking}
                    aria-label="Toggle thinking mode"
                    title={thinking ? "THINKING MODE: ON" : "THINKING MODE: OFF"}
                >
                    <Brain size={32} color={thinking ? "black" : "gray"} />
                </button>
            </div>
        </header>
    );
}
