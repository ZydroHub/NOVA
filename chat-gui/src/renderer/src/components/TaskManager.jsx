import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Plus, Trash2, Clock, Calendar, MessageSquare, Info, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useWebSocket } from '../contexts/WebSocketContext.jsx';

// Helper to format schedule text (interval or one-time at date/time)
const formatSchedule = (schedule) => {
    if (!schedule || typeof schedule !== 'object') return 'No schedule';
    if (schedule.kind === 'every') {
        const ms = schedule.everyMs;
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
    return 'Scheduled';
};

export default function TaskManager() {
    const navigate = useNavigate();
    const { sendMessage, addEventListener } = useWebSocket();
    const [jobs, setJobs] = useState([]);
    const [showAddForm, setShowAddForm] = useState(false);

    // Form state
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [scheduleType, setScheduleType] = useState('every'); // 'every' = interval, 'at' = one-time date/time

    // Interval state
    const [intervalValue, setIntervalValue] = useState(30);
    const [intervalUnit, setIntervalUnit] = useState('minutes'); // 'minutes', 'hours', 'days'

    // Date/time state (for "at" schedule)
    const [targetDate, setTargetDate] = useState('');

    // Payload state
    const [agentMessage, setAgentMessage] = useState('');

    useEffect(() => {
        sendMessage("task.list", {});

        const removeListListener = addEventListener("task_list", (data) => {
            setJobs(data.jobs || []);
        });

        const removeAddListener = addEventListener("task_added", (data) => {
            if (data.result) {
                setShowAddForm(false);
                resetForm();
                sendMessage("task.list", {});
            }
        });

        const removeRemoveListener = addEventListener("task_removed", (data) => {
            sendMessage("task.list", {});
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
            };
        } else if (scheduleType === 'at') {
            const date = new Date(targetDate);
            schedule = {
                kind: 'at',
                atMs: date.getTime()
            };
        }

        // Construct payload
        const payload = agentMessage ? {
            kind: 'agentTurn',
            message: agentMessage
        } : {};

        if (Object.keys(payload).length === 0 && !confirm("No agent message provided. Create job anyway?")) {
            return;
        }

        sendMessage("task.add", {
            name,
            description,
            schedule,
            payload
        });
    };

    const handleRemoveJob = (id) => {
        if (confirm("Delete this scheduled task?")) {
            sendMessage("task.remove", { id });
        }
    };

    return (
        <div className="w-full h-full mx-auto flex flex-col bg-[var(--pixel-bg)] text-[var(--pixel-text)] font-['VT323'] relative overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-4 bg-[var(--pixel-surface)] border-b-4 border-[var(--pixel-border)] z-10">
                <div className="flex items-center">
                    <button
                        onClick={() => navigate('/')}
                        className="pixel-btn p-2 mr-4"
                    >
                        <ArrowLeft size={20} />
                    </button>
                    <h1 className="text-xl font-['Press_Start_2P'] text-[var(--pixel-primary)]">TASK MANAGER</h1>
                </div>
                <button
                    onClick={() => setShowAddForm(!showAddForm)}
                    className={`pixel-btn p-2 transition-transform ${showAddForm ? 'bg-[var(--pixel-text)] text-black' : 'bg-[var(--pixel-accent)] text-black'}`}
                >
                    <Plus size={20} className={showAddForm ? "rotate-45" : ""} />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 scroller-pixel">
                <AnimatePresence>
                    {showAddForm && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="bg-[var(--pixel-surface)] border-4 border-[var(--pixel-border)] p-4 mb-4 shadow-[8px_8px_0_0_rgba(0,0,0,0.5)]"
                        >
                            <div className="p-2 border-b-2 border-[var(--pixel-border)] mb-4">
                                <h3 className="font-['Press_Start_2P'] text-xs text-[var(--pixel-secondary)] uppercase">NEW TASK</h3>
                            </div>
                            <form onSubmit={handleAddJob} className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1">
                                        <label className="text-sm font-medium text-gray-400 uppercase">Name</label>
                                        <input
                                            value={name} onChange={e => setName(e.target.value)}
                                            className="w-full p-2 bg-[var(--pixel-bg)] border-2 border-[var(--pixel-border)] text-[var(--pixel-text)] text-lg placeholder-[var(--pixel-border)] focus:border-[var(--pixel-primary)] outline-none"
                                            placeholder="TASK NAME..." required
                                        />
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-sm font-medium text-gray-400 uppercase">Description</label>
                                        <input
                                            value={description} onChange={e => setDescription(e.target.value)}
                                            className="w-full p-2 bg-[var(--pixel-bg)] border-2 border-[var(--pixel-border)] text-[var(--pixel-text)] text-lg placeholder-[var(--pixel-border)] focus:border-[var(--pixel-primary)] outline-none"
                                            placeholder="OPTIONAL..."
                                        />
                                    </div>
                                </div>

                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-xs font-['Press_Start_2P'] mb-2 text-[var(--pixel-secondary)]">SCHEDULE TYPE</label>
                                        <div className="flex bg-[var(--pixel-bg)] p-1 border-2 border-[var(--pixel-border)]">
                                            <button
                                                type="button"
                                                onClick={() => setScheduleType('every')}
                                                className={`flex-1 py-3 text-center font-['VT323'] text-xl transition-colors ${scheduleType === 'every'
                                                    ? 'bg-[var(--pixel-primary)] text-black'
                                                    : 'text-[var(--pixel-text)] hover:bg-[var(--pixel-surface)]'
                                                    }`}
                                            >
                                                INTERVAL
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => setScheduleType('at')}
                                                className={`flex-1 py-3 text-center font-['VT323'] text-xl transition-colors ${scheduleType === 'at'
                                                    ? 'bg-[var(--pixel-primary)] text-black'
                                                    : 'text-[var(--pixel-text)] hover:bg-[var(--pixel-surface)]'
                                                    }`}
                                            >
                                                DATE & TIME
                                            </button>
                                        </div>
                                    </div>

                                    {scheduleType === 'every' && (
                                        <div className="flex gap-4">
                                            <div className="flex-1">
                                                <label className="block text-xs font-['Press_Start_2P'] mb-2 text-[var(--pixel-secondary)]">INTERVAL</label>
                                                <input
                                                    type="number"
                                                    min="1"
                                                    value={intervalValue}
                                                    onChange={(e) => setIntervalValue(parseInt(e.target.value) || 1)}
                                                    className="pixel-input w-full"
                                                />
                                            </div>
                                            <div className="flex-1">
                                                <label className="block text-xs font-['Press_Start_2P'] mb-2 text-[var(--pixel-secondary)]">UNIT</label>
                                                <select
                                                    value={intervalUnit}
                                                    onChange={(e) => setIntervalUnit(e.target.value)}
                                                    className="pixel-select w-full h-full"
                                                >
                                                    <option value="minutes">MINUTES</option>
                                                    <option value="hours">HOURS</option>
                                                    <option value="days">DAYS</option>
                                                </select>
                                            </div>
                                        </div>
                                    )}

                                    {scheduleType === 'at' && (
                                        <div>
                                            <label className="text-xs text-[var(--pixel-primary)] mb-1 block">DATE & TIME</label>
                                            <input
                                                type="datetime-local"
                                                value={targetDate} onChange={e => setTargetDate(e.target.value)}
                                                className="w-full p-2 bg-[var(--pixel-surface)] border-2 border-[var(--pixel-border)] text-[var(--pixel-text)] text-lg"
                                                required={scheduleType === 'at'}
                                            />
                                        </div>
                                    )}
                                </div>

                                <div className="space-y-1">
                                    <label className="text-xs font-medium text-gray-400 uppercase flex items-center gap-1">
                                        <MessageSquare size={12} /> Agent Instruction
                                    </label>
                                    <textarea
                                        value={agentMessage} onChange={e => setAgentMessage(e.target.value)}
                                        className="w-full p-3 bg-[var(--pixel-bg)] border-2 border-[var(--pixel-border)] text-[var(--pixel-text)] text-lg focus:border-[var(--pixel-primary)] outline-none min-h-[80px] resize-none"
                                        placeholder="INSTRUCTIONS FOR AGENT..."
                                    />
                                </div>

                                <div className="flex justify-end pt-2 gap-4">
                                    <button
                                        type="button"
                                        onClick={() => setShowAddForm(false)}
                                        className="pixel-btn bg-[var(--pixel-bg)] text-[var(--pixel-text)]"
                                    >
                                        CANCEL
                                    </button>
                                    <button
                                        type="submit"
                                        className="pixel-btn bg-[var(--pixel-primary)] text-black"
                                    >
                                        ADD TASK
                                    </button>
                                </div>
                            </form>
                        </motion.div>
                    )}
                </AnimatePresence>

                {jobs.length === 0 && !showAddForm ? (
                    <div className="flex flex-col items-center justify-center py-20 text-[var(--pixel-border)]">
                        <Clock size={48} className="mb-4 opacity-50" />
                        <p className="text-xl">NO ACTIVE TASKS</p>
                    </div>
                ) : (
                    jobs.map((job) => (
                        <motion.div
                            key={job.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-[var(--pixel-surface)] p-5 border-4 border-[var(--pixel-border)] shadow-[4px_4px_0_0_rgba(0,0,0,0.5)] group"
                        >
                            <div className="flex justify-between items-start mb-3">
                                <div>
                                    <h3 className="font-['Press_Start_2P'] text-[var(--pixel-text)] text-xs mb-1 uppercase leading-relaxed text-[#c0caf5]">{job.name}</h3>
                                    {job.description && (
                                        <p className="text-lg text-gray-500 mt-0.5">{job.description}</p>
                                    )}
                                </div>
                                <button
                                    onClick={() => handleRemoveJob(job.id)}
                                    className="p-2 text-red-500 hover:bg-red-900/30 border-2 border-transparent hover:border-red-500 transition-all opacity-0 group-hover:opacity-100"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>

                            <div className="flex flex-col gap-2">
                                <div className="flex items-center text-sm text-[var(--pixel-secondary)]">
                                    <div className="w-6 flex justify-center mr-2 opacity-70">
                                        <Clock size={16} />
                                    </div>
                                    <span className="font-medium bg-[var(--pixel-bg)] px-2 py-0.5 border border-[var(--pixel-border)]">
                                        {formatSchedule(job.schedule)}
                                    </span>
                                </div>

                                {job.payload && (
                                    <div className="flex items-start text-sm text-gray-400 mt-1">
                                        <div className="w-6 flex justify-center mr-2 opacity-70 mt-0.5">
                                            <Zap size={16} />
                                        </div>
                                        <div className="flex-1 bg-[var(--pixel-bg)] p-2 border border-[var(--pixel-border)] text-[var(--pixel-primary)] text-sm font-['VT323']">
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
