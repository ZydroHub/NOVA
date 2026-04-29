import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Power, Music3, Play, Pause, SkipBack, SkipForward, Repeat } from 'lucide-react';
import { apiFetch } from '../apiClient.js';

export default function PCStatus() {
    const [pcStatus, setPcStatus] = useState('checking'); // 'checking' | 'online' | 'offline'
    const [wakeState, setWakeState] = useState('idle'); // 'idle' | 'loading' | 'sent' | 'error'
    const [isPlaying, setIsPlaying] = useState(false);
    const [lastCheckTime, setLastCheckTime] = useState(null);

    // Poll PC status every 10 seconds
    useEffect(() => {
        let mounted = true;

        const checkPcStatus = async () => {
            try {
                const result = await apiFetch('/nova/pc-status');
                if (!mounted) return;
                setPcStatus(result.status || 'offline');
                setLastCheckTime(new Date());
            } catch (err) {
                console.error('PC status check failed:', err);
                if (mounted) setPcStatus('offline');
            }
        };

        // Initial check
        checkPcStatus();

        // Poll every 10 seconds
        const interval = setInterval(checkPcStatus, 10000);

        return () => {
            mounted = false;
            clearInterval(interval);
        };
    }, []);

    const handleWakePc = useCallback(async () => {
        setWakeState('loading');
        try {
            const result = await apiFetch('/actions/wake-pc', { method: 'POST' });
            setWakeState(result.status === 'sent' ? 'sent' : 'error');
            // Refresh status after WoL attempt
            setTimeout(async () => {
                const updated = await apiFetch('/nova/pc-status');
                setPcStatus(updated.status || 'offline');
            }, 2000);
        } catch (err) {
            console.error('Wake PC failed:', err);
            setWakeState('error');
        }
        setTimeout(() => setWakeState('idle'), 2500);
    }, []);

    const statusIndicatorColor =
        pcStatus === 'online' ? 'bg-emerald-400' : pcStatus === 'offline' ? 'bg-red-400' : 'bg-yellow-400';
    const statusText = pcStatus === 'online' ? 'ONLINE' : pcStatus === 'offline' ? 'OFFLINE' : 'CHECKING...';

    return (
        <motion.div
            className="w-full"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
        >
            <div className="glass-card p-6 mb-4">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <div className={`w-3 h-3 rounded-full ${statusIndicatorColor} animate-pulse`} />
                            <h3 className="nova-title">PC-Oscar</h3>
                        </div>
                    </div>
                    <span className={`text-xs font-mono px-3 py-1 rounded-full ${
                        pcStatus === 'online' ? 'bg-emerald-900 text-emerald-300' : 'bg-red-900 text-red-300'
                    }`}>
                        {statusText}
                    </span>
                </div>

                {pcStatus === 'offline' ? (
                    // Show Start PC button when offline
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.3 }}
                    >
                        <button
                            onClick={handleWakePc}
                            disabled={wakeState === 'loading'}
                            className={`w-full py-6 px-6 rounded-lg font-bold text-lg transition-all flex items-center justify-center gap-3 min-h-[56px] ${
                                wakeState === 'loading'
                                    ? 'bg-blue-700/40 text-blue-300 cursor-wait opacity-60'
                                    : wakeState === 'sent'
                                    ? 'bg-emerald-700/40 text-emerald-300'
                                    : wakeState === 'error'
                                    ? 'bg-red-700/40 text-red-300'
                                    : 'bg-blue-600/30 hover:bg-blue-600/50 text-cyan-200 active:scale-95'
                            }`}
                        >
                            <Power size={24} />
                            {wakeState === 'loading' ? 'Sending WoL...' : wakeState === 'sent' ? 'Packet Sent!' : wakeState === 'error' ? 'Failed' : 'Start PC'}
                        </button>
                        {lastCheckTime && (
                            <p className="text-xs text-cyan-200/50 text-center mt-2">
                                Last check: {lastCheckTime.toLocaleTimeString('en-GB', { hour12: false })}
                            </p>
                        )}
                    </motion.div>
                ) : pcStatus === 'online' ? (
                    // Show music controls when online
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.3 }}
                    >
                        <div className="flex items-center gap-2 mb-4 text-cyan-200/70">
                            <Music3 size={18} />
                            <p className="text-sm">PC Music Control</p>
                        </div>
                        <div className="flex items-center justify-center gap-3 flex-wrap">
                            <button className="music-touch-btn" aria-label="Previous">
                                <SkipBack size={20} />
                            </button>
                            <button
                                className="music-touch-btn music-touch-btn-main"
                                onClick={() => setIsPlaying(!isPlaying)}
                                aria-label={isPlaying ? 'Pause' : 'Play'}
                            >
                                {isPlaying ? <Pause size={24} /> : <Play size={24} />}
                            </button>
                            <button className="music-touch-btn" aria-label="Next">
                                <SkipForward size={20} />
                            </button>
                            <button className="music-touch-btn" aria-label="Repeat">
                                <Repeat size={20} />
                            </button>
                        </div>
                        {lastCheckTime && (
                            <p className="text-xs text-cyan-200/50 text-center mt-3">
                                Last check: {lastCheckTime.toLocaleTimeString('en-GB', { hour12: false })}
                            </p>
                        )}
                    </motion.div>
                ) : (
                    // Checking state
                    <div className="flex items-center justify-center py-8">
                        <div className="animate-spin">
                            <Power size={24} className="text-cyan-200" />
                        </div>
                    </div>
                )}
            </div>
        </motion.div>
    );
}
