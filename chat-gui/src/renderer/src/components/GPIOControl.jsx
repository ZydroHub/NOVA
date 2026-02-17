import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import { ArrowLeft, RefreshCw, Zap, Activity } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const GPIOControl = () => {
    const { sendMessage, addEventListener, connStatus } = useWebSocket();
    const isConnected = connStatus === 'connected';
    const navigate = useNavigate();
    const [pins, setPins] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedPin, setSelectedPin] = useState(null);

    // Initial fetch of GPIO state
    useEffect(() => {
        if (isConnected) {
            sendMessage('gpio.get_all');
            setLoading(false);
        }

        const handleGpioState = (data) => {
            if (data.pins) {
                setPins(data.pins);
                // Update selected pin data if it exists
                if (selectedPin) {
                    const updated = data.pins.find(p => p.pin === selectedPin.pin);
                    if (updated) setSelectedPin(updated);
                }
            }
        };

        const unsubscribeState = addEventListener('gpio_state', handleGpioState);

        return () => {
            unsubscribeState();
        };
        // Add selectedPin to dependency if we want to update it live, 
        // but handleGpioState closure captures the *current* render's selectedPin if we don't use functional updates or refs.
        // Actually, since selectedPin is in the closure of the effect *creation*, it will be stale.
        // We should use a ref for selectedPin or depend on it, 
        // but depending on it re-registers the listener which is fine.
    }, [isConnected, sendMessage, addEventListener, selectedPin]);

    const handlePinClick = (pin) => {
        if (pin.type === 'gpio' && !pin.restricted) {
            setSelectedPin(pin);
        } else {
            setSelectedPin(null);
        }
    };

    const toggleMode = () => {
        if (!selectedPin || !isConnected) return;
        const newMode = selectedPin.mode === 'output' ? 'input' : 'output';
        sendMessage('gpio.set_mode', {
            bcm: selectedPin.bcm,
            mode: newMode
        });
    };

    const toggleValue = () => {
        if (!selectedPin || selectedPin.mode !== 'output' || !isConnected) return;
        const newValue = selectedPin.value === 1 ? 0 : 1;
        sendMessage('gpio.write', {
            bcm: selectedPin.bcm,
            value: newValue
        });
    };

    const getPinColor = (pin) => {
        if (pin.type === 'power') {
            if (pin.name.includes("5V")) return "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]";
            return "bg-orange-400 shadow-[0_0_8px_rgba(251,146,60,0.4)]";
        }
        if (pin.type === 'ground') return "bg-slate-800 border-2 border-slate-700";
        if (pin.restricted) return "bg-yellow-100 border border-yellow-300";

        // GPIO Logic
        if (pin.mode === 'output') {
            return pin.value === 1
                ? "bg-green-500 shadow-[0_0_12px_rgba(34,197,94,0.6)] border border-green-400 animate-pulse"
                : "bg-green-100 border border-green-300";
        }
        if (pin.mode === 'input') {
            return pin.value === 1
                ? "bg-blue-500 shadow-[0_0_12px_rgba(59,130,246,0.6)] border border-blue-400"
                : "bg-blue-100 border border-blue-300";
        }

        return "bg-slate-200 border border-slate-300";
    };

    // Split pins into left and right columns
    const leftColumn = pins.filter((_, i) => i % 2 === 0);
    const rightColumn = pins.filter((_, i) => i % 2 !== 0);

    return (
        <div className="h-full flex flex-col bg-white overflow-hidden relative text-slate-800">
            {/* Background Gradient - Light Theme */}
            <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-slate-50 to-indigo-50 z-0" />

            {/* Background Effects */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-200/20 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-200/20 rounded-full blur-3xl pointer-events-none" />

            {/* Header */}
            <div className="flex items-center justify-between p-4 z-10">
                <button
                    onClick={() => navigate('/')}
                    className="p-2 hover:bg-slate-100/80 rounded-full transition-colors active:scale-95 text-slate-600"
                >
                    <ArrowLeft size={24} />
                </button>
                <div className="flex items-center gap-2 text-slate-700">
                    <Activity className="text-blue-500" size={20} />
                    <h1 className="text-lg font-bold tracking-wider">GPIO CONTROL</h1>
                </div>
                <div className="w-10" /> {/* Spacer */}
            </div>

            <div className="flex-1 flex gap-4 overflow-hidden z-10 h-full p-4 pt-0">

                {/* Pin Header Visualization */}
                <div className="flex-1 flex items-center justify-center h-full overflow-y-auto pb-20 no-scrollbar">
                    <div className="bg-white/60 backdrop-blur-xl p-6 rounded-3xl border border-white/40 shadow-[0_8px_32px_rgba(0,0,0,0.05)] relative">
                        {/* Board Label */}
                        <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-white px-4 py-1 rounded-full text-[10px] font-mono text-slate-500 border border-slate-200 shadow-sm uppercase tracking-wider">
                            Raspberry Pi 5 Header
                        </div>

                        <div className="flex gap-8 mt-2">
                            {/* Left Column */}
                            <div className="flex flex-col gap-3">
                                {leftColumn.map(pin => (
                                    <div key={pin.pin} className="flex items-center justify-end gap-3 h-8">
                                        <span className={`text-[10px] font-mono ${pin.type === 'gpio' ? 'text-slate-700 font-semibold' : 'text-slate-400'}`}>
                                            {pin.name}
                                        </span>
                                        <button
                                            onClick={() => handlePinClick(pin)}
                                            className={`w-4 h-4 rounded-full transition-all duration-300 ${getPinColor(pin)} ${selectedPin?.pin === pin.pin ? 'ring-4 ring-blue-100 scale-125 shadow-lg' : ''}`}
                                        />
                                        <span className="text-[9px] text-slate-400 w-3 text-center font-mono">{pin.pin}</span>
                                    </div>
                                ))}
                            </div>

                            {/* Right Column */}
                            <div className="flex flex-col gap-3">
                                {rightColumn.map(pin => (
                                    <div key={pin.pin} className="flex items-center justify-start gap-3 h-8">
                                        <span className="text-[9px] text-slate-400 w-3 text-center font-mono">{pin.pin}</span>
                                        <button
                                            onClick={() => handlePinClick(pin)}
                                            className={`w-4 h-4 rounded-full transition-all duration-300 ${getPinColor(pin)} ${selectedPin?.pin === pin.pin ? 'ring-4 ring-blue-100 scale-125 shadow-lg' : ''}`}
                                        />
                                        <span className={`text-[10px] font-mono ${pin.type === 'gpio' ? 'text-slate-700 font-semibold' : 'text-slate-400'}`}>
                                            {pin.name}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Controls Panel (Side or Overlay) */}
                <div className="w-48 bg-white/60 border border-white/40 backdrop-blur-xl p-4 flex flex-col gap-4 rounded-2xl shadow-sm h-fit self-center">
                    <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100 pb-2">
                        Pin Controls
                    </h2>

                    {selectedPin ? (
                        <div className="flex flex-col gap-4 animate-in fade-in slide-in-from-right-4 duration-300">
                            <div>
                                <div className="text-2xl font-black text-slate-800">{selectedPin.name.replace('GPIO ', '')}</div>
                                <div className="text-[10px] text-slate-400 font-mono mt-0.5">BCM: {selectedPin.bcm}</div>
                            </div>

                            <div className="space-y-1">
                                <div className="text-[10px] text-slate-400 uppercase font-medium">Current Mode</div>
                                <div className={`text-sm font-bold ${selectedPin.mode === 'output' ? 'text-green-600' : selectedPin.mode === 'input' ? 'text-blue-600' : 'text-slate-400'}`}>
                                    {selectedPin.mode.toUpperCase()}
                                </div>
                            </div>

                            <div className="space-y-1">
                                <div className="text-[10px] text-slate-400 uppercase font-medium">State</div>
                                <div className="flex items-center gap-2">
                                    <div className={`w-2 h-2 rounded-full ${selectedPin.value ? 'bg-green-500 shadow-lg shadow-green-200' : 'bg-slate-300'}`} />
                                    <div className="text-lg font-mono text-slate-700">{selectedPin.value === 1 ? 'HIGH' : 'LOW'}</div>
                                </div>
                            </div>

                            <hr className="border-slate-100 my-1" />

                            <div className="flex flex-col gap-2">
                                <button
                                    onClick={toggleMode}
                                    className="px-3 py-2 bg-white hover:bg-slate-50 rounded-xl text-xs font-semibold text-slate-700 transition-all border border-slate-200 shadow-sm active:scale-95"
                                >
                                    Set to {selectedPin.mode === 'output' ? 'INPUT' : 'OUTPUT'}
                                </button>

                                {selectedPin.mode === 'output' && (
                                    <button
                                        onClick={toggleValue}
                                        className={`px-3 py-2 rounded-xl text-xs font-bold transition-all shadow-sm active:scale-95 border ${selectedPin.value
                                            ? 'bg-red-50 text-red-600 border-red-200 hover:bg-red-100'
                                            : 'bg-green-50 text-green-600 border-green-200 hover:bg-green-100'
                                            }`}
                                    >
                                        Turn {selectedPin.value ? 'OFF' : 'ON'}
                                    </button>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center py-8 text-center text-slate-400 gap-2">
                            <Zap size={24} className="opacity-30" />
                            <span className="text-xs">Select a GPIO pin<br />to configure</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Legend */}
            <div className="absolute bottom-4 left-0 w-full flex justify-center gap-6 text-[9px] text-slate-500 uppercase tracking-wider font-medium opacity-80 z-10">
                <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-orange-400 shadow-sm" /> Power</div>
                <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-slate-800 shadow-sm" /> GND</div>
                <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-green-500 shadow-sm shadow-green-200" /> Output</div>
                <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-blue-500 shadow-sm shadow-blue-200" /> Input</div>
            </div>
        </div>
    );
};

export default GPIOControl;
