import React from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Power, Keyboard, Radio, ScanLine, LayoutGrid } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../config.js';
import { apiFetch } from '../apiClient.js';
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
    const [telegramTestState, setTelegramTestState] = React.useState('idle');
    const [telegramTestError, setTelegramTestError] = React.useState('');

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

    const handleTelegramTest = async () => {
        setTelegramTestState('loading');
        setTelegramTestError('');
        try {
            const result = await apiFetch('/telegram/test-message', { method: 'POST' });
            const sentCount = Number(result?.sent || 0);
            setTelegramTestState(sentCount > 0 ? 'sent' : 'error');
            if (sentCount > 0) {
                setTelegramTestError(`Sent test message to ${sentCount} chat${sentCount === 1 ? '' : 's'}.`);
            } else {
                setTelegramTestError('No subscribed Telegram chats were found. Open Telegram and send /Nacka, /stockholm, or /test first.');
            }
        } catch (error) {
            console.error('Telegram test message failed:', error);
            setTelegramTestState('error');
            setTelegramTestError(error?.message || 'Telegram test message failed.');
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

                    <div className="pt-2 border-t-2 border-[var(--pixel-border)] space-y-3">
                        <div className="font-['VT323'] text-xl text-[var(--pixel-text)] flex items-center gap-2">
                            Telegram bot
                        </div>
                        <p className="font-['VT323'] text-lg text-[var(--pixel-secondary)]">
                            Sends a real Telegram test message to every subscribed chat. This only works after you have messaged the bot in Telegram.
                        </p>
                        {telegramTestError ? (
                            <div className={`font-['VT323'] text-lg px-3 py-2 border-2 ${telegramTestState === 'sent' ? 'bg-[rgba(0,180,120,0.18)] border-green-500 text-green-200' : 'bg-[rgba(180,0,0,0.18)] border-red-500 text-red-200'}`}>
                                {telegramTestError}
                            </div>
                        ) : null}
                        <button
                            type="button"
                            onClick={handleTelegramTest}
                            disabled={telegramTestState === 'loading'}
                            className="w-full py-4 px-6 bg-[var(--pixel-accent)] text-black font-['Press_Start_2P'] text-xs border-4 border-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:bg-[var(--pixel-primary)] active:translate-y-1 active:shadow-none transition-all flex items-center justify-center gap-3 disabled:opacity-60"
                        >
                            <span>{telegramTestState === 'loading' ? 'SENDING...' : 'SEND TELEGRAM TEST'}</span>
                        </button>
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
