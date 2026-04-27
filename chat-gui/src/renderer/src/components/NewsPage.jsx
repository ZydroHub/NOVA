import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Clock3, Globe } from 'lucide-react';
import { apiFetch } from '../apiClient.js';

const KEY_ALERT_REGION = 'pocket-ai.alertRegion';
const KEY_ALERT_UPDATE_MODE = 'pocket-ai.alertUpdateMode';
const KEY_ALERT_UPDATE_TIME = 'pocket-ai.alertUpdateTime';

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

function normalizeUpdateMode(mode) {
    if (mode === 'daily' || mode === 'weekly') return mode;
    return 'daily';
}

function normalizeTimeText(value) {
    if (typeof value === 'string' && /^\d{2}:\d{2}$/.test(value)) return value;
    return '08:00';
}

function getMsUntilNextRun(updateMode, hhmm) {
    const [hoursRaw, minutesRaw] = (hhmm || '08:00').split(':');
    const hours = Number(hoursRaw);
    const minutes = Number(minutesRaw);
    const safeHours = Number.isFinite(hours) ? Math.min(Math.max(hours, 0), 23) : 8;
    const safeMinutes = Number.isFinite(minutes) ? Math.min(Math.max(minutes, 0), 59) : 0;

    const now = new Date();
    const next = new Date(now);
    next.setHours(safeHours, safeMinutes, 0, 0);

    if (updateMode === 'weekly') {
        const targetDay = 1; // Monday
        const currentDay = next.getDay();
        let daysAhead = (targetDay - currentDay + 7) % 7;
        if (daysAhead === 0 && next <= now) {
            daysAhead = 7;
        }
        next.setDate(next.getDate() + daysAhead);
    } else if (next <= now) {
        next.setDate(next.getDate() + 1);
    }

    return Math.max(1000, next.getTime() - now.getTime());
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
    const [lastUpdated, setLastUpdated] = useState(null);
    const [updateMode, setUpdateMode] = useState(() => normalizeUpdateMode(readStoredValue(KEY_ALERT_UPDATE_MODE, 'daily')));
    const [updateTime, setUpdateTime] = useState(() => normalizeTimeText(readStoredValue(KEY_ALERT_UPDATE_TIME, '08:00')));
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
            const timeoutId = setTimeout(() => controller.abort(), 10000);

            try {
                const query = new URLSearchParams({
                    limit: '20',
                    region,
                });
                const data = await apiFetch(`/integrations/swedish-alerts?${query.toString()}`, { signal: controller.signal });
                const rawItems = Array.isArray(data?.items) ? data.items : [];
                setItems(rawItems.map(normalizeAlertItem));
                setStatistics(data?.statistics && typeof data.statistics === 'object' ? data.statistics : {});
                setLastUpdated(new Date());
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
        localStorage.setItem(KEY_ALERT_UPDATE_MODE, updateMode);
    }, [updateMode]);

    useEffect(() => {
        localStorage.setItem(KEY_ALERT_UPDATE_TIME, updateTime);
    }, [updateTime]);

    useEffect(() => {
        const intervalMs = updateMode === 'weekly' ? 7 * 24 * 60 * 60 * 1000 : 24 * 60 * 60 * 1000;
        const firstDelay = getMsUntilNextRun(updateMode, updateTime);

        const timeoutId = window.setTimeout(() => {
            loadAlerts({ initial: false });
            scheduleIntervalRef.current = window.setInterval(() => loadAlerts({ initial: false }), intervalMs);
        }, firstDelay);

        return () => {
            window.clearTimeout(timeoutId);
            if (scheduleIntervalRef.current) {
                window.clearInterval(scheduleIntervalRef.current);
                scheduleIntervalRef.current = null;
            }
        };
    }, [loadAlerts, updateMode, updateTime]);

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

    const lastUpdatedText = useMemo(() => {
        if (!lastUpdated) return 'Waiting for first update';
        return lastUpdated.toLocaleString('sv-SE', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    }, [lastUpdated]);

    return (
        <motion.div
            className="w-full h-full min-h-0 flex flex-col gap-0 bg-transparent overflow-y-auto touch-scroll-y"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
        >
            {/* Header */}
            <div className="flex-shrink-0 px-6 py-4 border-b border-cyan-400/20">
                <div className="flex items-end justify-between gap-4 flex-wrap">
                    <div>
                        <h2 className="text-2xl font-black text-white font-['Plus_Jakarta_Sans']">Swedish Alerts</h2>
                        <div className="text-[11px] mt-1 uppercase tracking-[0.22em] text-cyan-300/60">JARVIS threat monitor</div>
                    </div>
                    <div className="text-xs text-cyan-300/60">{refreshing ? 'Refreshing...' : `Last update: ${lastUpdatedText}`}</div>
                </div>

                <div className="mt-4 rounded-2xl border border-cyan-300/30 bg-cyan-500/5 p-3 space-y-3">
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                        <div className="flex items-center gap-2 flex-wrap">
                            {REGION_OPTIONS.map((option) => {
                                const active = option.value === region;
                                return (
                                    <button
                                        key={option.value}
                                        type="button"
                                        onClick={() => setRegion(option.value)}
                                        className={`px-3 py-1.5 text-xs rounded-full border font-semibold tracking-[0.14em] uppercase transition ${
                                            active
                                                ? 'border-cyan-200 bg-cyan-300/25 text-white'
                                                : 'border-cyan-400/30 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-400/20'
                                        }`}
                                    >
                                        {option.label}
                                    </button>
                                );
                            })}
                        </div>

                        <button
                            type="button"
                            onClick={() => loadAlerts({ initial: false })}
                            className="px-3 py-1.5 text-xs rounded-full border border-cyan-300/40 bg-cyan-400/15 text-cyan-50 hover:bg-cyan-300/25 transition uppercase tracking-[0.14em] font-semibold"
                        >
                            Refresh now
                        </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2 items-center">
                        <div className="md:col-span-1 text-[11px] uppercase tracking-[0.18em] text-cyan-200/80 flex items-center gap-2">
                            <Clock3 size={12} />
                            Update schedule
                        </div>
                        <select
                            value={updateMode}
                            onChange={(event) => setUpdateMode(normalizeUpdateMode(event.target.value))}
                            className="md:col-span-1 bg-slate-900/70 border border-cyan-300/30 rounded-lg px-3 py-2 text-sm text-cyan-50"
                        >
                            <option value="daily">Daily update</option>
                            <option value="weekly">Weekly update</option>
                        </select>
                        <input
                            type="time"
                            value={updateTime}
                            onChange={(event) => setUpdateTime(normalizeTimeText(event.target.value))}
                            className="md:col-span-1 bg-slate-900/70 border border-cyan-300/30 rounded-lg px-3 py-2 text-sm text-cyan-50"
                        />
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 min-h-0 overflow-y-auto touch-scroll-y">
                <div className="px-6 py-4 space-y-3">
                    {region === 'nacka' && statsEntries.length > 0 && (
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                            {statsEntries.map((entry, idx) => (
                                <motion.div
                                    key={entry.key}
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.25, delay: idx * 0.04 }}
                                    className="rounded-xl border border-cyan-300/25 bg-slate-900/60 px-3 py-2"
                                >
                                    <div className="text-[10px] uppercase tracking-[0.14em] text-cyan-200/70">{entry.key}</div>
                                    <div className="text-xl font-black text-white">{entry.value}</div>
                                </motion.div>
                            ))}
                        </div>
                    )}

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

                    {sortedItems.map((item, idx) => (
                        <motion.div
                            key={`${item.title}-${idx}`}
                            className={`block p-4 rounded-2xl border transition-all cursor-default ${getSourceColor(item.source)}`}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.4, delay: idx * 0.05 }}
                            whileHover={{ scale: 1.01 }}
                        >
                            <div className="flex gap-3">
                                <div className="text-2xl flex-shrink-0">{getSourceIcon(item.source)}</div>
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
                </div>
            </div>
        </motion.div>
    );
}
