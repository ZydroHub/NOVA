import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Power } from 'lucide-react';
import { apiFetch } from '../apiClient.js';

export default function ScreenToggle() {
    const [screenOn, setScreenOn] = useState(true);
    const [toggleLoading, setToggleLoading] = useState(false);
    const [lastToggleStatus, setLastToggleStatus] = useState('idle'); // 'idle' | 'success' | 'error'

    const handleToggleScreen = useCallback(async () => {
        setToggleLoading(true);
        const targetState = !screenOn;
        try {
            const result = await apiFetch(`/nova/screen-toggle?power_on=${targetState}`, {
                method: 'POST',
            });

            if (result.status === 'success') {
                setScreenOn(targetState);
                setLastToggleStatus('success');
                setTimeout(() => setLastToggleStatus('idle'), 2000);
            } else {
                console.error('Screen toggle error:', result.error);
                setLastToggleStatus('error');
                setTimeout(() => setLastToggleStatus('idle'), 2000);
            }
        } catch (err) {
            console.error('Screen toggle failed:', err);
            setLastToggleStatus('error');
            setTimeout(() => setLastToggleStatus('idle'), 2000);
        } finally {
            setToggleLoading(false);
        }
    }, [screenOn]);

    return (
        <motion.div
            className="w-full px-2"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
        >
            <button
                onClick={handleToggleScreen}
                disabled={toggleLoading}
                className={`w-full py-5 px-4 rounded-xl font-bold text-base transition-all flex items-center justify-center gap-3 min-h-[56px] border border-cyan-300/20 ${
                    toggleLoading
                        ? 'bg-cyan-600/20 text-cyan-300/50 cursor-wait opacity-60'
                        : lastToggleStatus === 'success'
                        ? 'bg-emerald-600/30 text-emerald-300 border-emerald-400/40'
                        : lastToggleStatus === 'error'
                        ? 'bg-red-600/30 text-red-300 border-red-400/40'
                        : screenOn
                        ? 'bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-200 border-cyan-400/30 active:scale-95'
                        : 'bg-orange-600/30 hover:bg-orange-600/50 text-orange-200 border-orange-400/30 active:scale-95'
                }`}
                title={screenOn ? 'Turn screen off' : 'Turn screen on'}
                aria-label={screenOn ? 'Turn screen off' : 'Turn screen on'}
            >
                <motion.div
                    animate={{ rotate: toggleLoading ? 360 : 0 }}
                    transition={{ duration: 1, repeat: toggleLoading ? Infinity : 0 }}
                >
                    <Power size={22} />
                </motion.div>
                <span className="text-sm font-mono">
                    {toggleLoading
                        ? 'TOGGLING...'
                        : lastToggleStatus === 'success'
                        ? 'SUCCESS'
                        : lastToggleStatus === 'error'
                        ? 'ERROR'
                        : screenOn
                        ? 'SCREEN ON'
                        : 'SCREEN OFF'}
                </span>
            </button>
        </motion.div>
    );
}
