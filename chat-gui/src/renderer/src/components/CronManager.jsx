import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Plus, Trash2, Clock, Calendar, MessageSquare, Info, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useWebSocket } from '../contexts/WebSocketContext.jsx';

// Helper to format schedule text
const formatSchedule = (schedule) => {
    if (!schedule) return 'No schedule';
    if (typeof schedule === 'string') {
        return `Cron: ${schedule}`;
    }
    if (typeof schedule === 'object') {
        if (schedule.kind === 'every') {
            const ms = schedule.everyMs;
            // Convert to largest unit
            const days = ms / (1000 * 60 * 60 * 24);
            if (days >= 1 && Number.isInteger(days)) return `Every ${days} day${days > 1 ? 's' : ''}`;
            const hours = ms / (1000 * 60 * 60);
            if (hours >= 1 && Number.isInteger(hours)) return `Every ${hours} hour${hours > 1 ? 's' : ''}`;
            const mins = ms / (1000 * 60);
            return `Every ${Math.round(mins)} minute${Math.round(mins) !== 1 ? 's' : ''}`;
        }
        if (schedule.kind === 'at') {
            return `At ${new Date(schedule.atMs).toLocaleString()}`;
        }
        return JSON.stringify(schedule);
    }
    return String(schedule);
};

export default function CronManager() {
    const navigate = useNavigate();
    const { sendMessage, addEventListener } = useWebSocket();
    const [jobs, setJobs] = useState([]);
    const [showAddForm, setShowAddForm] = useState(false);

    // Form state
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [scheduleType, setScheduleType] = useState('every'); // 'every', 'cron', 'at'

    // Interval state
    const [intervalValue, setIntervalValue] = useState(30);
    const [intervalUnit, setIntervalUnit] = useState('minutes'); // 'minutes', 'hours', 'days'

    // Cron state
    const [cronExpression, setCronExpression] = useState('*/30 * * * *');

    // Date state
    const [targetDate, setTargetDate] = useState('');

    // Payload state
    const [agentMessage, setAgentMessage] = useState('');

    useEffect(() => {
        sendMessage("cron.list", {});

        const removeListListener = addEventListener("cron_list", (data) => {
            setJobs(data.jobs || []);
        });

        const removeAddListener = addEventListener("cron_added", (data) => {
            if (data.result) {
                setShowAddForm(false);
                resetForm();
                sendMessage("cron.list", {});
            }
        });

        const removeRemoveListener = addEventListener("cron_removed", (data) => {
            sendMessage("cron.list", {});
        });

        return () => {
            removeListListener();
            removeAddListener();
            removeRemoveListener();
        };
    }, [sendMessage, addEventListener]);

    const resetForm = () => {
        setName('');
        setDescription('');
        setScheduleType('every');
        setIntervalValue(30);
        setIntervalUnit('minutes');
        setCronExpression('*/30 * * * *');
        setTargetDate('');
        setAgentMessage('');
    };

    const handleAddJob = (e) => {
        e.preventDefault();

        let schedule = null;

        if (scheduleType === 'every') {
            let ms = intervalValue * 1000 * 60; // minutes default
            if (intervalUnit === 'hours') ms *= 60;
            if (intervalUnit === 'days') ms *= 60 * 24;

            schedule = {
                kind: 'every',
                everyMs: ms
                // anchorMs is optional, defaults to now if omitted usually, or backend handles it
            };
        } else if (scheduleType === 'cron') {
            schedule = cronExpression;
        } else if (scheduleType === 'at') {
            const date = new Date(targetDate);
            schedule = {
                kind: 'at',
                atMs: date.getTime()
            };
        }

        // Construct payload
        // Validated against existing jobs: requires 'message' string, kind 'agentTurn'
        const payload = agentMessage ? {
            kind: 'agentTurn',
            message: agentMessage
        } : {};

        // Basic payload validation
        if (Object.keys(payload).length === 0 && !confirm("No agent message provided. Create job anyway?")) {
            return;
        }

        sendMessage("cron.add", {
            name,
            description,
            schedule,
            payload
        });
    };

    const handleRemoveJob = (id) => {
        if (confirm("Delete this scheduled task?")) {
            sendMessage("cron.remove", { id });
        }
    };

    return (
        <div className="w-[480px] h-full mx-auto flex flex-col bg-gray-50 text-gray-900 font-sans relative overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-4 bg-white shadow-sm z-10">
                <div className="flex items-center">
                    <button
                        onClick={() => navigate('/')}
                        className="p-2 -ml-2 rounded-full hover:bg-gray-100 transition-colors mr-2"
                    >
                        <ArrowLeft size={20} className="text-gray-600" />
                    </button>
                    <h1 className="text-lg font-bold text-gray-800">Scheduled Jobs</h1>
                </div>
                <button
                    onClick={() => setShowAddForm(!showAddForm)}
                    className={`p-2 rounded-full transition-colors ${showAddForm ? 'bg-gray-200 text-gray-600' : 'bg-blue-600 text-white shadow-md hover:bg-blue-700'}`}
                >
                    <Plus size={20} className={showAddForm ? "rotate-45 transition-transform" : "transition-transform"} />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                <AnimatePresence>
                    {showAddForm && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="bg-white rounded-xl shadow-md border border-gray-100 overflow-hidden mb-4"
                        >
                            <div className="p-4 bg-gray-50 border-b border-gray-100">
                                <h3 className="font-semibold text-sm text-gray-700">New Job</h3>
                            </div>
                            <form onSubmit={handleAddJob} className="p-4 space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1">
                                        <label className="text-xs font-medium text-gray-500 uppercase">Name</label>
                                        <input
                                            value={name} onChange={e => setName(e.target.value)}
                                            className="w-full p-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                                            placeholder="Daily Summary" required
                                        />
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-xs font-medium text-gray-500 uppercase">Description</label>
                                        <input
                                            value={description} onChange={e => setDescription(e.target.value)}
                                            className="w-full p-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                                            placeholder="Optional"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <label className="text-xs font-medium text-gray-500 uppercase">Schedule Type</label>
                                    <div className="flex bg-gray-100 p-1 rounded-lg">
                                        {['every', 'cron', 'at'].map(type => (
                                            <button
                                                key={type}
                                                type="button"
                                                onClick={() => setScheduleType(type)}
                                                className={`flex-1 py-1.5 text-xs font-medium rounded-md capitalize transition-all ${scheduleType === type ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                                                    }`}
                                            >
                                                {type}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Schedule Inputs */}
                                <div className="p-3 bg-blue-50/50 rounded-lg border border-blue-100">
                                    {scheduleType === 'every' && (
                                        <div className="flex gap-3">
                                            <div className="flex-1">
                                                <label className="text-xs text-blue-600 mb-1 block">Value</label>
                                                <input
                                                    type="number" min="1"
                                                    value={intervalValue} onChange={e => setIntervalValue(e.target.value)}
                                                    className="w-full p-2 bg-white border border-blue-200 rounded-lg text-sm"
                                                />
                                            </div>
                                            <div className="flex-1">
                                                <label className="text-xs text-blue-600 mb-1 block">Unit</label>
                                                <select
                                                    value={intervalUnit} onChange={e => setIntervalUnit(e.target.value)}
                                                    className="w-full p-2 bg-white border border-blue-200 rounded-lg text-sm"
                                                >
                                                    <option value="minutes">Minutes</option>
                                                    <option value="hours">Hours</option>
                                                    <option value="days">Days</option>
                                                </select>
                                            </div>
                                        </div>
                                    )}

                                    {scheduleType === 'cron' && (
                                        <div>
                                            <label className="text-xs text-blue-600 mb-1 block">Cron Expression</label>
                                            <input
                                                value={cronExpression} onChange={e => setCronExpression(e.target.value)}
                                                className="w-full p-2 bg-white border border-blue-200 rounded-lg text-sm font-mono"
                                                placeholder="* * * * *"
                                            />
                                        </div>
                                    )}

                                    {scheduleType === 'at' && (
                                        <div>
                                            <label className="text-xs text-blue-600 mb-1 block">Date & Time</label>
                                            <input
                                                type="datetime-local"
                                                value={targetDate} onChange={e => setTargetDate(e.target.value)}
                                                className="w-full p-2 bg-white border border-blue-200 rounded-lg text-sm"
                                            />
                                        </div>
                                    )}
                                </div>

                                <div className="space-y-1">
                                    <label className="text-xs font-medium text-gray-500 uppercase flex items-center gap-1">
                                        <MessageSquare size={12} /> Agent Message
                                    </label>
                                    <textarea
                                        value={agentMessage} onChange={e => setAgentMessage(e.target.value)}
                                        className="w-full p-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none min-h-[80px]"
                                        placeholder="What should the agent do or say when this triggers?"
                                    />
                                </div>

                                <div className="flex justify-end pt-2">
                                    <button
                                        type="button"
                                        onClick={() => setShowAddForm(false)}
                                        className="px-4 py-2 text-gray-500 text-sm font-medium hover:text-gray-700 mr-2"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 shadow-sm"
                                    >
                                        Add Job
                                    </button>
                                </div>
                            </form>
                        </motion.div>
                    )}
                </AnimatePresence>

                {jobs.length === 0 && !showAddForm ? (
                    <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                        <Clock size={48} className="mb-4 opacity-20" />
                        <p className="text-sm">No active tasks found</p>
                    </div>
                ) : (
                    jobs.map((job) => (
                        <motion.div
                            key={job.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 group hover:shadow-md transition-shadow"
                        >
                            <div className="flex justify-between items-start mb-3">
                                <div>
                                    <h3 className="font-bold text-gray-900 text-base">{job.name}</h3>
                                    {job.description && (
                                        <p className="text-sm text-gray-500 mt-0.5">{job.description}</p>
                                    )}
                                </div>
                                <button
                                    onClick={() => handleRemoveJob(job.id)}
                                    className="p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>

                            <div className="flex flex-col gap-2">
                                <div className="flex items-center text-sm text-gray-600">
                                    <div className="w-6 flex justify-center mr-2 text-gray-400">
                                        <Clock size={16} />
                                    </div>
                                    <span className="font-medium bg-gray-50 px-2 py-0.5 rounded text-gray-700 border border-gray-100">
                                        {formatSchedule(job.schedule)}
                                    </span>
                                </div>

                                {job.payload && (
                                    <div className="flex items-start text-sm text-gray-600 mt-1">
                                        <div className="w-6 flex justify-center mr-2 text-gray-400 mt-0.5">
                                            <Zap size={16} />
                                        </div>
                                        <div className="flex-1 bg-blue-50/50 p-2 rounded-lg text-blue-800 text-xs border border-blue-100">
                                            {job.payload.text || job.payload.message || JSON.stringify(job.payload)}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    ))
                )}
            </div>
        </div>
    );
}
