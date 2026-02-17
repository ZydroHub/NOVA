import React, { useState, useEffect } from 'react';
import { Activity, Thermometer, Cpu, Clock } from 'lucide-react';

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
                const response = await fetch('http://localhost:8000/system/stats');
                if (response.ok) {
                    const data = await response.json();
                    setStats(data);
                }
            } catch (error) {
                console.error('Failed to fetch system stats:', error);
            }
        };

        fetchStats();
        const interval = setInterval(fetchStats, 2000); // Update every 2 seconds

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
        <div className="w-full h-8 bg-black/80 backdrop-blur-md z-50 flex items-center justify-between px-4 text-xs font-mono border-b border-white/10 select-none">

            {/* Time */}
            <div className="flex items-center gap-2 text-cyan-400">
                <Clock size={14} />
                <span className="font-bold tracking-wider">{stats.time}</span>
            </div>

            {/* System Stats Container */}
            <div className="flex items-center gap-6">

                {/* CPU */}
                <div className="flex items-center gap-2 text-gray-300">
                    <Activity size={14} className="text-blue-400" />
                    <span className="text-gray-500">CPU:</span>
                    <span className={`font-bold ${getStatusColor(stats.cpu_percent, 'usage')}`}>
                        {stats.cpu_percent.toFixed(1)}%
                    </span>
                </div>

                {/* RAM */}
                <div className="flex items-center gap-2 text-gray-300">
                    <Cpu size={14} className="text-purple-400" />
                    <span className="text-gray-500">RAM:</span>
                    <span className={`font-bold ${getStatusColor(stats.memory_percent, 'usage')}`}>
                        {stats.memory_percent.toFixed(1)}%
                    </span>
                </div>

                {/* Temp */}
                <div className="flex items-center gap-2 text-gray-300">
                    <Thermometer size={14} className="text-orange-400" />
                    <span className="text-gray-500">TMP:</span>
                    <span className={`font-bold ${getStatusColor(stats.temperature, 'temp')}`}>
                        {stats.temperature.toFixed(1)}°C
                    </span>
                </div>

            </div>
        </div>
    );
};

export default StatusBar;
