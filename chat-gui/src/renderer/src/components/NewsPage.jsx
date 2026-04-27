import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Globe } from 'lucide-react';
import { apiFetch } from '../apiClient.js';

const KEY_ALERT_REGION = 'pocket-ai.alertRegion';

const REGION_OPTIONS = [
    { value: 'nacka', label: 'Nacka' },
    { value: 'stockholm', label: 'Stockholm' },
    { value: 'sweden', label: 'Sweden' },
];

const STATS_ORDER = [
    'Alla samtal',
    'Polisen',
    'Vårdbehov',
    'Räddning',
    'Ej akuta behov',
];

const shellVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
        opacity: 1,
        y: 0,
        transition: {
            duration: 0.6,
            ease: [0.22, 1, 0.36, 1],
            when: 'beforeChildren',
            staggerChildren: 0.06,
        },
    },
};

const fadeUpVariants = {
    hidden: { opacity: 0, y: 14 },
    visible: {
        opacity: 1,
        y: 0,
        transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] },
    },
};

const listItemVariants = {
    hidden: { opacity: 0, x: -24, scale: 0.985 },
    visible: (idx) => ({
        opacity: 1,
        x: 0,
        scale: 1,
        transition: {
            duration: 0.42,
            delay: idx * 0.035,
            ease: [0.22, 1, 0.36, 1],
        },
    }),
};

function readStoredValue(key, fallback) {
    try {
        return localStorage.getItem(key) || fallback;
    } catch {
        return fallback;
    }
}

function normalizeRegion(region) {
    if (region === 'nacka' || region === 'stockholm' || region === 'sweden') return region;
    return 'nacka';
}

function toDisplayText(value) {
    if (value == null) return '';
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
        return String(value).trim();
    }
    if (Array.isArray(value)) {
        return value.map(toDisplayText).filter(Boolean).join(', ').trim();
    }
    if (typeof value === 'object') {
        const preferred = value.Description || value.description || value.name || value.title || value.Type || value.type;
        if (preferred != null) return toDisplayText(preferred);
        try {
            return JSON.stringify(value);
        } catch {
            return '';
        }
    }
    return '';
}

function normalizeAlertItem(item) {
    const source = toDisplayText(item?.source) || 'Alert';
    const title = toDisplayText(item?.title) || toDisplayText(item?.Description) || 'Untitled alert';
    const location = toDisplayText(item?.location ?? item?.Area ?? item?.area);
    const published = toDisplayText(item?.published);
    const priorityLabel = toDisplayText(item?.priority_label) || 'News';
    const priorityRank = Number(item?.priority_rank) || 0;

    return {
        ...item,
        source,
        title,
        location,
        published,
        priority_label: priorityLabel,
        priority_rank: priorityRank,
    };
}

function formatPublished(value) {
    if (!value) return '';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString('sv-SE', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

export default function NewsPage() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [region, setRegion] = useState(() => normalizeRegion(readStoredValue(KEY_ALERT_REGION, 'nacka')));
    const [statistics, setStatistics] = useState({});
    const scheduleIntervalRef = useRef(null);

    const loadAlerts = useCallback(
        async ({ initial = false } = {}) => {
            if (initial) {
                setLoading(true);
            } else {
                setRefreshing(true);
            }
            if (initial) setError(null);

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 20000);

            try {
                const query = new URLSearchParams({
                    limit: '60',
                    region,
                });
                const data = await apiFetch(`/integrations/swedish-alerts?${query.toString()}`, { signal: controller.signal });
                const rawItems = Array.isArray(data?.items) ? data.items : [];
                setItems(rawItems.map(normalizeAlertItem));
                setStatistics(data?.statistics && typeof data.statistics === 'object' ? data.statistics : {});
                setError(null);
            } catch (err) {
                console.error('Failed to load alerts', err);
                setError(err?.name === 'AbortError' ? 'Loading alerts timed out. Retry in a moment.' : 'Failed to load alerts');
                setItems([]);
            } finally {
                clearTimeout(timeoutId);
                setLoading(false);
                setRefreshing(false);
            }
        },
        [region]
    );

    useEffect(() => {
        loadAlerts({ initial: true });
    }, [loadAlerts]);

    useEffect(() => {
        localStorage.setItem(KEY_ALERT_REGION, region);
    }, [region]);

    useEffect(() => {
        scheduleIntervalRef.current = window.setInterval(() => loadAlerts({ initial: false }), 120000);

        return () => {
            if (scheduleIntervalRef.current) {
                window.clearInterval(scheduleIntervalRef.current);
                scheduleIntervalRef.current = null;
            }
        };
    }, [loadAlerts]);

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

    const sortedItems = [...items].sort((a, b) => (b.priority_rank || 0) - (a.priority_rank || 0));
    const statsEntries = useMemo(() => {
        if (region !== 'nacka') return [];
        return STATS_ORDER
            .filter((key) => statistics[key] != null && key !== 'Samverkan')
            .map((key) => ({ key, value: String(statistics[key]) }));
    }, [region, statistics]);

    return (
        <motion.div
            className="w-full h-full min-h-0 flex flex-col gap-0 bg-transparent overflow-hidden touch-pan-y"
            variants={shellVariants}
            initial="hidden"
            animate="visible"
        >
            <motion.div
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 opacity-30"
                style={{
                    background:
                        'radial-gradient(circle at 15% 12%, rgba(20, 126, 201, 0.25), transparent 28%), radial-gradient(circle at 82% 18%, rgba(27, 197, 255, 0.20), transparent 30%)',
                }}
                animate={{ opacity: [0.22, 0.34, 0.22] }}
                transition={{ duration: 6.5, repeat: Infinity, ease: 'easeInOut' }}
            />

            {/* Header */}
            <motion.div variants={fadeUpVariants} className="relative flex-shrink-0 px-6 py-4 border-b border-cyan-400/20">
                <div className="flex items-end gap-4 flex-wrap">
                    <div>
                        <motion.h2
                            className="text-2xl font-black text-white font-['Plus_Jakarta_Sans']"
                            initial={{ letterSpacing: '0.08em', opacity: 0 }}
                            animate={{ letterSpacing: '-0.01em', opacity: 1 }}
                            transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
                        >
                            Swedish Alerts
                        </motion.h2>
                    </div>
                </div>

                <div className="mt-4 rounded-2xl border border-cyan-300/30 bg-cyan-500/5 p-3 space-y-3">
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                        <div className="flex items-center gap-2 flex-wrap">
                            {REGION_OPTIONS.map((option) => {
                                const active = option.value === region;
                                return (
                                    <motion.button
                                        key={option.value}
                                        type="button"
                                        onClick={() => setRegion(option.value)}
                                        data-no-swipe-nav="true"
                                        className={`px-3 py-1.5 text-xs rounded-full border font-semibold tracking-[0.14em] uppercase transition ${
                                            active
                                                ? 'border-cyan-200 bg-cyan-300/25 text-white'
                                                : 'border-cyan-400/30 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-400/20'
                                        }`}
                                        whileHover={{ y: -1, scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                    >
                                        {option.label}
                                    </motion.button>
                                );
                            })}
                        </div>

                        <motion.button
                            type="button"
                            onClick={() => loadAlerts({ initial: false })}
                            data-no-swipe-nav="true"
                            className="px-3 py-1.5 text-xs rounded-full border border-cyan-300/40 bg-cyan-400/15 text-cyan-50 hover:bg-cyan-300/25 transition uppercase tracking-[0.14em] font-semibold"
                            whileHover={{ y: -1, scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                        >
                            Refresh now
                        </motion.button>
                    </div>

                    <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-cyan-200/80">
                        <motion.span
                            className="inline-block h-1.5 w-1.5 rounded-full bg-cyan-200"
                            animate={{ opacity: refreshing ? [0.35, 1, 0.35] : [0.9, 0.9, 0.9], scale: refreshing ? [1, 1.35, 1] : [1, 1, 1] }}
                            transition={{ duration: 0.8, repeat: Infinity, ease: 'easeInOut' }}
                        />
                        Auto refresh every 2 minutes
                    </div>
                </div>
                <AnimatePresence>
                    {refreshing && (
                        <motion.div
                            className="absolute left-0 right-0 bottom-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-300 to-transparent"
                            initial={{ opacity: 0, scaleX: 0.2 }}
                            animate={{ opacity: 1, scaleX: [0.2, 1, 0.2] }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 1.1, repeat: Infinity, ease: 'easeInOut' }}
                        />
                    )}
                </AnimatePresence>
            </motion.div>

            {/* Content */}
            <motion.div variants={fadeUpVariants} className="flex-1 min-h-0 overflow-y-auto touch-scroll-y">
                <div className="px-6 py-4 space-y-3 pb-8">
                    {region === 'nacka' && statsEntries.length > 0 && (
                        <motion.div
                            key={`stats-${region}`}
                            className="grid grid-cols-2 md:grid-cols-5 gap-2"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
                        >
                            {statsEntries.map((entry, idx) => (
                                <motion.div
                                    key={entry.key}
                                    initial={{ opacity: 0, y: 10, scale: 0.98 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.28, delay: idx * 0.05 }}
                                    className="rounded-xl border border-cyan-300/25 bg-slate-900/60 px-3 py-2"
                                    whileHover={{ y: -2, borderColor: 'rgba(154, 240, 255, 0.5)' }}
                                >
                                    <div className="text-[10px] uppercase tracking-[0.14em] text-cyan-200/70">{entry.key}</div>
                                    <div className="text-xl font-black text-white">{entry.value}</div>
                                </motion.div>
                            ))}
                        </motion.div>
                    )}

                    <AnimatePresence mode="wait">
                        {loading && (
                            <motion.div
                                key="loading"
                                className="space-y-3 py-2"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                transition={{ duration: 0.22 }}
                            >
                                {Array.from({ length: 5 }).map((_, idx) => (
                                    <motion.div
                                        key={`skeleton-${idx}`}
                                        className="rounded-2xl border border-cyan-400/20 bg-slate-900/55 px-4 py-3 overflow-hidden"
                                        initial={{ opacity: 0, y: 8 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: idx * 0.05, duration: 0.28 }}
                                    >
                                        <motion.div
                                            className="h-3 w-24 rounded bg-cyan-300/20 mb-3"
                                            animate={{ opacity: [0.3, 0.7, 0.3] }}
                                            transition={{ duration: 1.1, repeat: Infinity, delay: idx * 0.08 }}
                                        />
                                        <motion.div
                                            className="h-2.5 w-4/5 rounded bg-cyan-300/15 mb-2"
                                            animate={{ opacity: [0.25, 0.55, 0.25] }}
                                            transition={{ duration: 1.2, repeat: Infinity, delay: idx * 0.1 }}
                                        />
                                        <motion.div
                                            className="h-2 w-2/5 rounded bg-cyan-300/12"
                                            animate={{ opacity: [0.2, 0.5, 0.2] }}
                                            transition={{ duration: 1.15, repeat: Infinity, delay: idx * 0.12 }}
                                        />
                                    </motion.div>
                                ))}
                            </motion.div>
                        )}

                        {!loading && error && (
                            <motion.div
                                key="error"
                                className="bg-red-500/20 border border-red-400/50 rounded-lg p-4 text-red-200 text-sm"
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -6 }}
                                transition={{ duration: 0.3 }}
                            >
                                {error}
                            </motion.div>
                        )}

                        {!loading && !error && items.length === 0 && (
                            <motion.div
                                key="empty"
                                className="text-center py-12"
                                initial={{ opacity: 0, y: 8 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                transition={{ duration: 0.3 }}
                            >
                                <motion.div
                                    className="text-4xl mb-2"
                                    animate={{ y: [0, -4, 0], opacity: [0.6, 1, 0.6] }}
                                    transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                                >
                                    ✨
                                </motion.div>
                                <p className="text-cyan-300/70">No active alerts in Sweden right now</p>
                                <p className="text-xs text-cyan-300/50 mt-1">All systems clear</p>
                            </motion.div>
                        )}

                        {!loading && !error && items.length > 0 && (
                            <motion.div
                                key={`list-${region}`}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                transition={{ duration: 0.24 }}
                                className="space-y-3"
                            >
                                {sortedItems.map((item, idx) => (
                                    <motion.div
                                        key={`${item.title}-${idx}`}
                                        custom={idx}
                                        variants={listItemVariants}
                                        initial="hidden"
                                        animate="visible"
                                        className={`block p-4 rounded-2xl border transition-all cursor-default ${getSourceColor(item.source)}`}
                                        whileHover={{ scale: 1.012, y: -1 }}
                                    >
                                        <div className="flex gap-3">
                                            <motion.div
                                                className="text-2xl flex-shrink-0"
                                                animate={{ rotate: [0, 5, -5, 0] }}
                                                transition={{ duration: 0.65, delay: idx * 0.03 }}
                                            >
                                                {getSourceIcon(item.source)}
                                            </motion.div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <div className="text-sm font-bold text-cyan-200 uppercase tracking-wider">
                                                        {item.source || 'Alert'}
                                                    </div>
                                                    <div className="text-[10px] px-2 py-0.5 rounded-full border border-cyan-300/20 bg-cyan-400/10 text-cyan-100 font-semibold uppercase tracking-[0.18em]">
                                                        {item.priority_label || 'News'}
                                                    </div>
                                                </div>
                                                <div className="text-sm text-white mt-1 line-clamp-2 font-semibold">
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
                                                        {formatPublished(item.published)}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </motion.div>
        </motion.div>
    );
}
