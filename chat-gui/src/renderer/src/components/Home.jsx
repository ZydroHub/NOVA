import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, Settings, Camera, Image as GalleryIcon, Code } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Avatar from './Avatar';
import { useWebSocket } from '../contexts/WebSocketContext.jsx';
import { useRef, useState, useEffect } from 'react';

const MenuButton = ({ icon: Icon, label, onClick, color }) => (
    <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={onClick}
        className="pixel-btn flex flex-col items-center justify-center gap-2 w-full min-h-[72px] min-w-0"
        style={{ borderColor: color, color: color }}
    >
        <Icon size={32} />
        <span className="text-xs">{label}</span>
    </motion.button>
);

export default function Home() {
    const navigate = useNavigate();
    const {
        toggleVoice,
        startVosk,
        stopVosk,
        isRecording,
        isVoskRecording,
        voiceStatus,
        voskText,
        voiceStreamText,
        isVoiceStreaming
    } = useWebSocket();

    const [showBubble, setShowBubble] = useState(false);
    const bubbleTimeoutRef = useRef(null);

    useEffect(() => {
        const active = isVoiceStreaming || voiceStatus === 'speaking';
        if (active) {
            if (bubbleTimeoutRef.current) clearTimeout(bubbleTimeoutRef.current);
            setShowBubble(true);
        } else if (showBubble) {
            bubbleTimeoutRef.current = setTimeout(() => {
                setShowBubble(false);
            }, 1000);
        }
        return () => {
            if (bubbleTimeoutRef.current) clearTimeout(bubbleTimeoutRef.current);
        };
    }, [isVoiceStreaming, voiceStatus, showBubble]);

    const displayVoiceText = voiceStreamText.trim();

    const pressTimer = useRef(null);
    const [isHoldMode, setIsHoldMode] = useState(false);

    const handleMouseDown = () => {
        setIsHoldMode(false);
        pressTimer.current = setTimeout(() => {
            setIsHoldMode(true);
            startVosk();
        }, 400); // 400ms threshold for hold
    };

    const handleMouseUp = () => {
        if (pressTimer.current) {
            clearTimeout(pressTimer.current);
            pressTimer.current = null;
        }

        if (isHoldMode) {
            stopVosk();
            setIsHoldMode(false);
        } else {
            // It was a quick tap
            toggleVoice();
        }
    };

    // Also handle mouse leave to prevent getting stuck in hold mode
    const handleMouseLeave = () => {
        if (isHoldMode) {
            stopVosk();
            setIsHoldMode(false);
        }
        if (pressTimer.current) {
            clearTimeout(pressTimer.current);
            pressTimer.current = null;
        }
    };

    return (
        <div className="relative w-full h-full overflow-hidden bg-[var(--pixel-bg)] flex flex-col items-center justify-center p-4">

            {/* Settings button top left */}
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => navigate('/settings')}
                className="absolute top-3 left-3 z-30 p-4 rounded-lg border-2 border-[var(--pixel-border)] bg-[var(--pixel-surface)] shadow-[4px_4px_0_0_rgba(0,0,0,0.5)]"
                style={{ color: '#7dcfff' }}
                aria-label="Settings"
            >
                <Settings size={36} />
            </motion.button>

            {/* Avatar - Centered (higher z when bubble visible so it's not covered by buttons) */}
            <div
                className={`mb-12 relative ${showBubble ? 'z-20' : 'z-10'}`}
                onMouseDown={handleMouseDown}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseLeave}
            >
                <Avatar
                    variant="xl"
                    animate={true}
                    expression={voiceStatus}
                    className={`cursor-pointer transition-all duration-300 ${isRecording ? 'scale-110' : 'hover:scale-105'}`}
                />

                {/* Vosk Real-time Transcription Overlay */}
                <AnimatePresence>
                    {isVoskRecording && voskText && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.8, y: -10 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.8 }}
                            className="absolute left-[90px] top-[70px] w-[180px] bg-black/80 backdrop-blur-md p-3 border-2 border-[var(--pixel-accent)] shadow-[4px_4px_0_0_rgba(0,0,0,0.5)] z-50 rounded-lg rounded-tl-none"
                        >
                            <p className="text-[var(--pixel-accent)] text-[10px] leading-relaxed break-words whitespace-pre-wrap max-h-[120px] overflow-y-auto touch-scroll-y">
                                {voskText}
                            </p>
                            {/* Decorative pointer arrow (top left pointing to avatar) */}
                            <div className="absolute left-[-10px] top-[-2px] w-0 h-0 border-r-[10px] border-r-[var(--pixel-accent)] border-b-[10px] border-b-transparent" />
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* AI Response Bubble - below avatar, pointer up toward avatar */}
                <AnimatePresence>
                    {showBubble && displayVoiceText && (
                        <motion.div
                            initial={{ opacity: 0, x: -20, scale: 0.9 }}
                            animate={{ opacity: 1, x: 0, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            className="absolute left-1/2 top-[150px] -translate-x-1/2 w-[220px] bg-[var(--pixel-surface)] p-4 border-4 border-[var(--pixel-primary)] shadow-[6px_6px_0_0_rgba(0,0,0,0.5)] z-50 rounded-xl"
                        >
                            {/* Pointer arrow at top center pointing up to avatar */}
                            <div className="absolute left-1/2 top-[-14px] -translate-x-1/2 w-0 h-0 border-l-[12px] border-l-transparent border-r-[12px] border-r-transparent border-b-[14px] border-b-[var(--pixel-primary)]" />
                            <p className="text-[var(--pixel-primary)] text-sm font-['VT323'] leading-tight break-words">
                                {displayVoiceText}
                            </p>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Main Menu Grid - 4 buttons: Chat, Vision, Agent, Gallery */}
            <div className="grid grid-cols-2 gap-3 z-10 w-full max-w-[520px]">
                <MenuButton icon={MessageCircle} label="CHAT" onClick={() => navigate('/chat')} color="var(--pixel-primary)" />
                <MenuButton icon={Camera} label="VISION" onClick={() => navigate('/camera')} color="var(--pixel-accent)" />
                <MenuButton icon={Code} label="AGENT" onClick={() => navigate('/tasks')} color="#f7768e" />
                <MenuButton icon={GalleryIcon} label="GALLERY" onClick={() => navigate('/gallery')} color="var(--pixel-secondary)" />
            </div>

            {/* Decorative BG Elements */}
            <div className="absolute inset-0 pointer-events-none opacity-10"
                style={{
                    backgroundImage: 'linear-gradient(var(--pixel-border) 1px, transparent 1px), linear-gradient(90deg, var(--pixel-border) 1px, transparent 1px)',
                    backgroundSize: '40px 40px'
                }}
            />
        </div>
    );
}
