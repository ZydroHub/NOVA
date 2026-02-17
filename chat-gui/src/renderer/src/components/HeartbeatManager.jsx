import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Clock, Activity, Power, Save } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useWebSocket } from '../contexts/WebSocketContext.jsx';

export default function HeartbeatManager() {
    const navigate = useNavigate();
    const { sendMessage, addEventListener } = useWebSocket();
    const [status, setStatus] = useState({ active: false, schedule: null });
    const [intervalStart, setIntervalStart] = useState(30);

    const checkStatus = () => sendMessage("heartbeat.get", {});

    useEffect(() => {
        checkStatus();

        const removeStatusListener = addEventListener("heartbeat_status", (data) => {
            setStatus(data.status);
            // Parse interval from schedule if possible: */30 * * * *
            if (data.status.schedule) {
                const match = data.status.schedule.match(/\*\/(\d+)/);
                if (match) {
                    setIntervalStart(parseInt(match[1]));
                }
            }
        });

        const removeUpdateListener = addEventListener("heartbeat_updated", (data) => {
            // Refresh
            checkStatus();
        });

        return () => {
            removeStatusListener();
            removeUpdateListener();
        };
    }, [sendMessage, addEventListener]);

    const handleSave = () => {
        sendMessage("heartbeat.set", {
            active: status.active,
            interval: intervalStart
        });
    };

    const toggleActive = () => {
        const newActive = !status.active;
        setStatus({ ...status, active: newActive });
        // Auto-save on toggle? Or let user click save? 
        // Let's auto-save for better UX on toggle
        sendMessage("heartbeat.set", {
            active: newActive,
            interval: intervalStart
        });
    };

    return (
        <div className="w-[480px] h-full mx-auto flex flex-col bg-white relative overflow-hidden text-black">
            {/* Header */}
            <div className="flex items-center p-4 border-b border-gray-100 bg-white/80 backdrop-blur-md z-10">
                <button
                    onClick={() => navigate('/')}
                    className="p-2 rounded-full hover:bg-gray-100 transition-colors mr-2"
                >
                    <ArrowLeft size={20} className="text-gray-600" />
                </button>
                <div className="flex-1">
                    <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-pink-600 to-red-600">
                        System Heartbeat
                    </h1>
                </div>
            </div>

            <div className="flex-1 p-6 bg-gray-50/50 flex flex-col items-center justify-center">

                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="w-full max-w-sm bg-white rounded-3xl shadow-xl p-8 border border-pink-50 relative overflow-hidden"
                >
                    {/* Background decoration */}
                    <div className="absolute top-0 right-0 w-32 h-32 bg-pink-100 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 opacity-50" />

                    <div className="relative z-10 flex flex-col items-center text-center">
                        <div className={`w-24 h-24 rounded-full flex items-center justify-center mb-6 transition-colors duration-500 ${status.active ? 'bg-pink-100 text-pink-600 shadow-[0_0_30px_rgba(236,72,153,0.3)]' : 'bg-gray-100 text-gray-400'}`}>
                            <Activity size={48} className={status.active ? "animate-pulse" : ""} />
                        </div>

                        <h2 className="text-2xl font-bold text-gray-900 mb-2">
                            {status.active ? "Heartbeat Active" : "Heartbeat Inactive"}
                        </h2>
                        <p className="text-gray-500 text-sm mb-8">
                            {status.active
                                ? "Your agent is proactively checking for tasks in the background."
                                : "Background monitoring is disabled."}
                        </p>

                        {/* Controls */}
                        <div className="w-full space-y-6">
                            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-2xl">
                                <span className="text-sm font-medium text-gray-700">Status</span>
                                <button
                                    onClick={toggleActive}
                                    className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-pink-500 focus:ring-offset-2 ${status.active ? 'bg-green-500' : 'bg-gray-300'}`}
                                >
                                    <span className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${status.active ? 'translate-x-7' : 'translate-x-1'}`} />
                                </button>
                            </div>

                            <div className={`transition-opacity duration-300 ${status.active ? 'opacity-100' : 'opacity-50 pointer-events-none'}`}>
                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 block text-left">
                                    Check Interval (Minutes)
                                </label>
                                <div className="flex gap-2">
                                    <input
                                        type="number"
                                        min="1"
                                        max="1440"
                                        value={intervalStart}
                                        onChange={(e) => setIntervalStart(parseInt(e.target.value))}
                                        className="flex-1 px-4 py-3 bg-gray-50 rounded-xl border border-gray-100 focus:ring-2 focus:ring-pink-500/20 text-center font-bold text-gray-900"
                                    />
                                    <button
                                        onClick={handleSave}
                                        className="bg-black text-white px-6 py-3 rounded-xl font-medium hover:bg-gray-800 transition-colors flex items-center"
                                    >
                                        <Save size={18} />
                                    </button>
                                </div>
                            </div>
                        </div>

                    </div>
                </motion.div>

            </div>
        </div>
    );
}
