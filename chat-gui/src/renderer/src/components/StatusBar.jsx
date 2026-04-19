import React, { useState, useEffect } from 'react';
import { Thermometer, Clock, Zap } from 'lucide-react';
import { apiFetch } from '../apiClient.js';
import { WS_BASE_URL } from '../config.js';

const toFiniteNumber = (value, fallback = 0) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
};

const StatusBar = () => {
    const [stats, setStats] = useState({
        time: new Date().toLocaleTimeString('en-GB', { hour12: false }),
        cpu_percent: 0,
        memory_percent: 0,
        temperature: 0,
        wattage: 0
    });
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        let ws = null;
        let fallbackInterval = null;
        let timeInterval = null;
        let isMounted = true;

        const applyStats = (data) => {
            if (!isMounted) return;
            setStats({
                time: data.time || new Date().toLocaleTimeString('en-GB', { hour12: false }),
                cpu_percent: toFiniteNumber(data.cpu_percent ?? data.cpu ?? 0),
                memory_percent: toFiniteNumber(data.memory_percent ?? data.ram ?? 0),
                temperature: toFiniteNumber(data.temperature ?? data.temp ?? 0),
                wattage: toFiniteNumber(data.wattage ?? data.watts ?? 0)
            });
            setConnected(true);
        };

        const fetchStats = async () => {
            try {
                const data = await apiFetch('/system/stats');
                applyStats(data);
            } catch (error) {
                console.error('Stats fetch failed:', error);
                setConnected(false);
            }
        };

        // Immediate first fetch
        fetchStats();

        // Update time every second
        timeInterval = setInterval(() => {
            if (isMounted) {
                setStats(prev => ({
                    ...prev,
                    time: new Date().toLocaleTimeString('en-GB', { hour12: false })
                }));
            }
        }, 1000);

        // Try WebSocket connection
        try {
            ws = new WebSocket(`${WS_BASE_URL}/ws/system-stats`);
            ws.onopen = () => {
                console.log('Stats WebSocket connected');
                if (isMounted) setConnected(true);
            };
            ws.onmessage = (event) => {
                try {
                    const payload = JSON.parse(event.data);
                    applyStats(payload);
                } catch (err) {
                    console.error('Stats parse error:', err);
                }
            };
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                // Start fallback polling if WebSocket fails
                if (!fallbackInterval) {
                    fallbackInterval = setInterval(fetchStats, 1500);
                }
            };
            ws.onclose = () => {
                console.log('Stats WebSocket disconnected');
                // Start fallback polling on disconnect
                if (!fallbackInterval) {
                    fallbackInterval = setInterval(fetchStats, 1500);
                }
            };
        } catch (err) {
            console.error('WebSocket init failed:', err);
            // Use HTTP polling as fallback
            fallbackInterval = setInterval(fetchStats, 1500);
        }

        return () => {
            isMounted = false;
            if (ws) {
                ws.close();
            }
            if (fallbackInterval) {
                clearInterval(fallbackInterval);
            }
            if (timeInterval) {
                clearInterval(timeInterval);
            }
        };
    }, []);

    // Helper to determine color based on usage/temp
    const getStatusColor = (value, type) => {
        if (type === 'temp') {
            if (value > 80) return 'text-red-500';
            if (value > 60) return 'text-yellow-500';
            return 'text-green-500';
        }
        // usage percentage
        if (value > 80) return 'text-red-500';
        if (value > 50) return 'text-yellow-500';
        return 'text-green-500';
    };

    return (
        <div className="w-full h-11 bg-[var(--nova-glass)] z-50 flex items-center justify-between px-4 text-sm border-b border-white/20 select-none backdrop-blur-xl">

            {/* Time */}
            <div className="flex items-center gap-2 text-cyan-200/90">
                <Clock size={16} />
                <span className="tracking-wide">{stats.time}</span>
            </div>

            {/* System Stats Container */}
            <div className="flex items-center gap-5">

                {/* CPU */}
                <div className="flex items-center gap-1 text-[var(--nova-text)]">
                    <span className="text-cyan-200/70">CPU:</span>
                    <span className={`${getStatusColor(stats.cpu_percent, 'usage')}`}>
                        {Math.round(stats.cpu_percent)}%
                    </span>
                </div>

                {/* RAM */}
                <div className="flex items-center gap-1 text-[var(--nova-text)]">
                    <span className="text-cyan-200/70">RAM:</span>
                    <span className={`${getStatusColor(stats.memory_percent, 'usage')}`}>
                        {Math.round(stats.memory_percent)}%
                    </span>
                </div>

                {/* Temp */}
                <div className="flex items-center gap-1 text-[var(--nova-text)]">
                    <Thermometer size={14} className="text-cyan-200/70" />
                    <span className={`${getStatusColor(stats.temperature, 'temp')}`}>
                        {Math.round(stats.temperature)}°
                    </span>
                </div>

                {/* Watts */}
                <div className="flex items-center gap-1 text-[var(--nova-text)]">
                    <Zap size={14} className="text-cyan-200/70" />
                    <span className="text-green-400">{stats.wattage.toFixed(1)}W</span>
                </div>

            </div>
        </div>
    );
};

export default StatusBar;
