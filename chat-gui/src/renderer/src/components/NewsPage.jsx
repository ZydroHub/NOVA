import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Globe } from 'lucide-react';
import { apiFetch } from '../apiClient.js';

export default function NewsPage() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let mounted = true;
        async function load() {
            setLoading(true);
            setError(null);
            try {
                const data = await apiFetch('/integrations/swedish-alerts?limit=20');
                if (mounted) {
                    setItems(data.items || []);
                }
            } catch (err) {
                console.error('Failed to load alerts', err);
                if (mounted) {
                    setError('Failed to load alerts');
                    setItems([]);
                }
            } finally {
                if (mounted) setLoading(false);
            }
        }
        load();
        const timer = setInterval(load, 120000);
        return () => {
            mounted = false;
            clearInterval(timer);
        };
    }, []);

    const getSourceIcon = (source) => {
        if (source?.toLowerCase().includes('polisen')) return '🚔';
        if (source?.toLowerCase().includes('krisis')) return '⚠️';
        if (source?.toLowerCase().includes('sos')) return '🆘';
        return '📢';
    };

    const getSourceColor = (source) => {
        if (source?.toLowerCase().includes('polisen')) return 'border-blue-400/60 bg-blue-500/10';
        if (source?.toLowerCase().includes('krisis')) return 'border-yellow-400/60 bg-yellow-500/10';
        if (source?.toLowerCase().includes('sos')) return 'border-red-400/60 bg-red-500/10';
        return 'border-cyan-400/60 bg-cyan-500/10';
    };

    return (
        <motion.div
            className="w-full h-full min-h-0 flex flex-col gap-0 bg-transparent"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
        >
            {/* Header */}
            <div className="flex-shrink-0 px-6 py-4 border-b border-cyan-400/20">
                <div className="flex items-center gap-3">
                    <div className="text-2xl">🔔</div>
                    <div>
                        <h2 className="text-xl font-bold text-white font-['Plus_Jakarta_Sans']">SWEDISH ALERTS</h2>
                        <p className="text-xs text-cyan-300/70">Polisen • Krisinformation • SOS Alarm</p>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 min-h-0 overflow-y-auto touch-scroll-y">
                <div className="px-6 py-4 space-y-3">
                    {loading && (
                        <motion.div 
                            className="text-center py-12"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 0.3 }}
                        >
                            <div className="text-3xl mb-2 animate-pulse">⏳</div>
                            <p className="text-cyan-300">Loading alerts...</p>
                        </motion.div>
                    )}

                    {error && (
                        <div className="bg-red-500/20 border border-red-400/50 rounded-lg p-4 text-red-200 text-sm">
                            {error}
                        </div>
                    )}

                    {!loading && items.length === 0 && (
                        <motion.div 
                            className="text-center py-12"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 0.3 }}
                        >
                            <div className="text-4xl mb-2">✨</div>
                            <p className="text-cyan-300/70">No active alerts in Sweden right now</p>
                            <p className="text-xs text-cyan-300/50 mt-1">All systems clear</p>
                        </motion.div>
                    )}

                    {items.map((item, idx) => (
                        <motion.a
                            key={`${item.title}-${idx}`}
                            href={item.url || '#'}
                            target="_blank"
                            rel="noreferrer"
                            className={`block p-4 rounded-lg border transition-all hover:border-opacity-100 hover:shadow-lg cursor-pointer ${getSourceColor(item.source)}`}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.4, delay: idx * 0.05 }}
                            whileHover={{ scale: 1.02, x: 4 }}
                        >
                            <div className="flex gap-3">
                                <div className="text-2xl flex-shrink-0">{getSourceIcon(item.source)}</div>
                                <div className="flex-1 min-w-0">
                                    <div className="text-sm font-bold text-cyan-200 uppercase tracking-wider">
                                        {item.source || 'Alert'}
                                    </div>
                                    <div className="text-sm text-white mt-1 line-clamp-2">
                                        {item.title}
                                    </div>
                                    {item.location && (
                                        <div className="text-xs text-cyan-300/60 mt-1 flex items-center gap-1">
                                            <Globe size={12} />
                                            {item.location}
                                        </div>
                                    )}
                                    {item.published && (
                                        <div className="text-xs text-cyan-300/50 mt-1 opacity-70">
                                            {new Date(item.published).toLocaleString('sv-SE', { 
                                                month: 'short', 
                                                day: 'numeric', 
                                                hour: '2-digit', 
                                                minute: '2-digit' 
                                            })}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </motion.a>
                    ))}
                </div>
            </div>
        </motion.div>
    );
}
