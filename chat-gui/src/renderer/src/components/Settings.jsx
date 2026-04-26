import React from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Power, Keyboard, Radio, ScanLine, LayoutGrid } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../config.js';
import { useKeyboardSettings } from '../contexts/KeyboardContext.jsx';

const VERSION = '1.4.0';
const KEY_VOICE_AUTO_RECONNECT = 'pocket-ai.voiceAutoReconnect';
const KEY_SCANLINES_ENABLED = 'pocket-ai.scanlinesEnabled';
const KEY_UI_DENSITY = 'pocket-ai.uiDensity';

function readStoredBool(key, defaultValue = true) {
    try {
        const value = localStorage.getItem(key);
        if (value === null) return defaultValue;
        return value === 'true';
    } catch {
        return defaultValue;
    }
}

function readStoredDensity() {
    try {
        const value = localStorage.getItem(KEY_UI_DENSITY);
        return value === 'compact' ? 'compact' : 'comfortable';
    } catch {
        return 'comfortable';
    }
}

export default function Settings() {
    const navigate = useNavigate();
    const { keyboardEnabled, setKeyboardEnabled } = useKeyboardSettings();
    const [voiceReconnectEnabled, setVoiceReconnectEnabled] = React.useState(() => readStoredBool(KEY_VOICE_AUTO_RECONNECT, true));
    const [scanlinesEnabled, setScanlinesEnabled] = React.useState(() => readStoredBool(KEY_SCANLINES_ENABLED, true));
    const [uiDensity, setUiDensity] = React.useState(readStoredDensity);

    React.useEffect(() => {
        localStorage.setItem(KEY_VOICE_AUTO_RECONNECT, String(voiceReconnectEnabled));
        window.dispatchEvent(new CustomEvent('nova-settings-updated'));
    }, [voiceReconnectEnabled]);

    React.useEffect(() => {
        localStorage.setItem(KEY_SCANLINES_ENABLED, String(scanlinesEnabled));
        window.dispatchEvent(new CustomEvent('nova-settings-updated'));
    }, [scanlinesEnabled]);

    React.useEffect(() => {
        localStorage.setItem(KEY_UI_DENSITY, uiDensity);
        document.body.dataset.novaDensity = uiDensity;
        window.dispatchEvent(new CustomEvent('nova-settings-updated'));
    }, [uiDensity]);

    const handleCloseApp = async () => {
        try {
            await fetch(`${API_BASE_URL}/shutdown`, { method: 'POST' });
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
            <div className="flex-1 p-6 flex flex-col items-center justify-center space-y-8 overflow-y-auto">
                <div className="text-center">
                    <h2 className="text-2xl font-['VT323'] text-[var(--pixel-text)] mb-2 uppercase tracking-widest">System Configuration</h2>
                    <p className="text-[var(--pixel-secondary)] font-['VT323'] text-lg">MANAGE AI RUNTIME AND UI PREFERENCES</p>
                </div>

                <div className="w-full max-w-2xl space-y-4 p-6 border-4 border-[var(--pixel-border)] bg-[var(--pixel-surface)] shadow-[8px_8px_0_0_rgba(0,0,0,0.3)]">
                    <div className="flex items-center justify-between gap-4 py-3 border-b-2 border-[var(--pixel-border)]">
                        <span className="font-['VT323'] text-xl text-[var(--pixel-text)] flex items-center gap-2">
                            <Keyboard size={22} className="text-[var(--pixel-primary)]" />
                            Popup keyboard
                        </span>
                        <button
                            type="button"
                            role="switch"
                            aria-checked={keyboardEnabled}
                            onClick={() => setKeyboardEnabled(!keyboardEnabled)}
                            className={`relative w-14 h-8 border-4 flex-shrink-0 transition-colors ${
                                keyboardEnabled
                                    ? 'bg-[var(--pixel-accent)] border-[var(--pixel-accent)]'
                                    : 'bg-[var(--pixel-bg)] border-[var(--pixel-border)]'
                            }`}
                        >
                            <span
                                className={`absolute top-0.5 left-0.5 w-6 h-6 border-2 border-[var(--pixel-border)] bg-[var(--pixel-text)] transition-transform ${
                                    keyboardEnabled ? 'translate-x-7' : 'translate-x-0'
                                }`}
                            />
                        </button>
                    </div>

                    <div className="flex items-center justify-between gap-4 py-3 border-b-2 border-[var(--pixel-border)]">
                        <span className="font-['VT323'] text-xl text-[var(--pixel-text)] flex items-center gap-2">
                            <Radio size={22} className="text-[var(--pixel-primary)]" />
                            Voice auto reconnect
                        </span>
                        <button
                            type="button"
                            role="switch"
                            aria-checked={voiceReconnectEnabled}
                            onClick={() => setVoiceReconnectEnabled((prev) => !prev)}
                            className={`relative w-14 h-8 border-4 flex-shrink-0 transition-colors ${
                                voiceReconnectEnabled
                                    ? 'bg-[var(--pixel-accent)] border-[var(--pixel-accent)]'
                                    : 'bg-[var(--pixel-bg)] border-[var(--pixel-border)]'
                            }`}
                        >
                            <span
                                className={`absolute top-0.5 left-0.5 w-6 h-6 border-2 border-[var(--pixel-border)] bg-[var(--pixel-text)] transition-transform ${
                                    voiceReconnectEnabled ? 'translate-x-7' : 'translate-x-0'
                                }`}
                            />
                        </button>
                    </div>

                    <div className="flex items-center justify-between gap-4 py-3 border-b-2 border-[var(--pixel-border)]">
                        <span className="font-['VT323'] text-xl text-[var(--pixel-text)] flex items-center gap-2">
                            <ScanLine size={22} className="text-[var(--pixel-primary)]" />
                            Ambient scanlines
                        </span>
                        <button
                            type="button"
                            role="switch"
                            aria-checked={scanlinesEnabled}
                            onClick={() => setScanlinesEnabled((prev) => !prev)}
                            className={`relative w-14 h-8 border-4 flex-shrink-0 transition-colors ${
                                scanlinesEnabled
                                    ? 'bg-[var(--pixel-accent)] border-[var(--pixel-accent)]'
                                    : 'bg-[var(--pixel-bg)] border-[var(--pixel-border)]'
                            }`}
                        >
                            <span
                                className={`absolute top-0.5 left-0.5 w-6 h-6 border-2 border-[var(--pixel-border)] bg-[var(--pixel-text)] transition-transform ${
                                    scanlinesEnabled ? 'translate-x-7' : 'translate-x-0'
                                }`}
                            />
                        </button>
                    </div>

                    <div className="flex items-center justify-between gap-4 py-3 border-b-2 border-[var(--pixel-border)]">
                        <span className="font-['VT323'] text-xl text-[var(--pixel-text)] flex items-center gap-2">
                            <LayoutGrid size={22} className="text-[var(--pixel-primary)]" />
                            UI density
                        </span>
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                onClick={() => setUiDensity('comfortable')}
                                className={`px-3 py-1.5 border-2 font-['VT323'] text-lg ${
                                    uiDensity === 'comfortable'
                                        ? 'bg-[var(--pixel-accent)] text-black border-[var(--pixel-accent)]'
                                        : 'bg-[var(--pixel-bg)] text-[var(--pixel-text)] border-[var(--pixel-border)]'
                                }`}
                            >
                                Comfortable
                            </button>
                            <button
                                type="button"
                                onClick={() => setUiDensity('compact')}
                                className={`px-3 py-1.5 border-2 font-['VT323'] text-lg ${
                                    uiDensity === 'compact'
                                        ? 'bg-[var(--pixel-accent)] text-black border-[var(--pixel-accent)]'
                                        : 'bg-[var(--pixel-bg)] text-[var(--pixel-text)] border-[var(--pixel-border)]'
                                }`}
                            >
                                Compact
                            </button>
                        </div>
                    </div>

                    <div className="font-['VT323'] text-lg text-[var(--pixel-secondary)] pt-1">
                        Voice mode now keeps replies stable across reconnects and applies smoother TTS playback.
                    </div>

                    <button
                        onClick={handleCloseApp}
                        className="w-full py-6 px-8 bg-red-500 text-white font-['Press_Start_2P'] text-sm border-4 border-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:bg-red-600 active:translate-y-1 active:shadow-none transition-all flex items-center justify-center gap-4"
                    >
                        <Power size={24} />
                        <span>SHUTDOWN</span>
                    </button>
                </div>

                <div className="text-xs font-['Press_Start_2P'] text-[var(--pixel-border)] mt-auto pt-8">
                    VER {VERSION}
                </div>
            </div>
        </motion.div>
    );
}
