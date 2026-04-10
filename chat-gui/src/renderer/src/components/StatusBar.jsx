import React, { useState, useEffect } from 'react';
import { Activity, Thermometer, Cpu, Clock } from 'lucide-react';
import { apiFetch } from '../apiClient.js';

const toFiniteNumber = (value, fallback = 0) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
};

const StatusBar = () => {
    const [stats, setStats] = useState({
        time: '--:--:--',
        cpu_percent: 0,
        memory_percent: 0,
        temperature: 0
    });

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const data = await apiFetch('/system/stats');
                setStats({
                    time: data.time || new Date().toLocaleTimeString('en-GB', { hour12: false }),
                    cpu_percent: toFiniteNumber(data.cpu_percent ?? data.cpu ?? 0),
                    memory_percent: toFiniteNumber(data.memory_percent ?? data.ram ?? 0),
                    temperature: toFiniteNumber(data.temperature ?? data.temp ?? 0)
                });
            } catch (error) {
                console.error('Failed to fetch system stats:', error);
            }
        };

        fetchStats();
        const interval = setInterval(fetchStats, 2000);

        return () => clearInterval(interval);
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
        <div className="w-full h-7 bg-[var(--pixel-surface)] z-50 flex items-center justify-between px-2 text-[10px] uppercase font-['Press_Start_2P'] border-b-4 border-[var(--pixel-border)] select-none">

            {/* Time */}
            <div className="flex items-center gap-2 text-[var(--pixel-primary)]">
                <Clock size={12} />
                <span className="tracking-widest">{stats.time}</span>
            </div>

            {/* System Stats Container */}
            <div className="flex items-center gap-4">

                {/* CPU */}
                <div className="flex items-center gap-1 text-[var(--pixel-text)]">
                    <span className="text-[var(--pixel-secondary)]">CPU:</span>
                    <span className={`${getStatusColor(stats.cpu_percent, 'usage')}`}>
                        {Math.round(stats.cpu_percent)}%
                    </span>
                </div>

                {/* RAM */}
                <div className="flex items-center gap-1 text-[var(--pixel-text)]">
                    <span className="text-[var(--pixel-secondary)]">RAM:</span>
                    <span className={`${getStatusColor(stats.memory_percent, 'usage')}`}>
                        {Math.round(stats.memory_percent)}%
                    </span>
                </div>

                {/* Temp */}
                <div className="flex items-center gap-1 text-[var(--pixel-text)]">
                    <span className="text-[var(--pixel-secondary)]">TMP:</span>
                    <span className={`${getStatusColor(stats.temperature, 'temp')}`}>
                        {Math.round(stats.temperature)}°
                    </span>
                </div>

            </div>
        </div>
    );
};

export default StatusBar;
