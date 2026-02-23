import React from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Power } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Settings() {
    const navigate = useNavigate();

    const handleCloseApp = async () => {
        try {
            await fetch('http://localhost:8000/shutdown', { method: 'POST' });
        } catch (e) {
            console.error('Failed to notify backend of shutdown:', e);
        }

        if (window.electron && window.electron.quit) {
            window.electron.quit();
        } else {
            console.log('Close button clicked (Electron API not available)');
            window.close();
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, type: "spring" }}
            className="relative w-full h-full max-w-full mx-auto overflow-hidden bg-[var(--pixel-bg)] flex flex-col"
        >
            {/* Header */}
            <div className="flex items-center p-4 bg-[var(--pixel-surface)] border-b-4 border-[var(--pixel-border)] z-10">
                <button
                    onClick={() => navigate('/')}
                    className="pixel-btn flex items-center justify-center p-2"
                >
                    <ArrowLeft size={20} />
                </button>
                <h1 className="ml-4 text-xl font-['Press_Start_2P'] text-[var(--pixel-primary)]">SETTINGS</h1>
            </div>

            {/* Content */}
            <div className="flex-1 p-6 flex flex-col items-center justify-center space-y-8">
                <div className="text-center">
                    <h2 className="text-2xl font-['VT323'] text-[var(--pixel-text)] mb-2 uppercase tracking-widest">System Configuration</h2>
                    <p className="text-[var(--pixel-secondary)] font-['VT323'] text-lg">MANAGE TERMINAL PREFERENCES</p>
                </div>

                <div className="w-full max-w-xs p-6 border-4 border-[var(--pixel-border)] bg-[var(--pixel-surface)] shadow-[8px_8px_0_0_rgba(0,0,0,0.3)]">
                    <button
                        onClick={handleCloseApp}
                        className="w-full py-6 px-8 bg-red-500 text-white font-['Press_Start_2P'] text-sm border-4 border-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:bg-red-600 active:translate-y-1 active:shadow-none transition-all flex items-center justify-center gap-4"
                    >
                        <Power size={24} />
                        <span>SHUTDOWN</span>
                    </button>
                </div>

                <div className="text-xs font-['Press_Start_2P'] text-[var(--pixel-border)] mt-auto pt-12">
                    VER 1.0.0
                </div>
            </div>
        </motion.div>
    );
}
