import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { SkipBack, Play, Pause, SkipForward, House, Power } from 'lucide-react';
import { useWebSocket } from '../contexts/WebSocketContext.jsx';
import { apiFetch } from '../apiClient.js';
import NovaOrb from './NovaOrb';

export default function Home() {
    const { voiceStatus, toggleVoice } = useWebSocket();
    const [weather, setWeather] = useState(null);
    const [alerts, setAlerts] = useState([]);
    const [wakeState, setWakeState] = useState('idle');

    useEffect(() => {
        let mounted = true;
        async function loadData() {
            try {
                const [weatherData, alertsData] = await Promise.all([
                    apiFetch('/integrations/weather?latitude=59.3293&longitude=18.0686'),
                    apiFetch('/integrations/swedish-alerts?limit=6')
                ]);
                if (!mounted) return;
                setWeather(weatherData);
                setAlerts(alertsData.items || []);
            } catch (err) {
                console.error('Dashboard load failed', err);
            }
        }
        loadData();
        const timer = setInterval(loadData, 120000);
        return () => {
            mounted = false;
            clearInterval(timer);
        };
    }, []);

    const currentTemp = Math.round(weather?.current?.temperature_2m ?? 0);
    const forecastDays = weather?.daily?.time || [];

    const onWakePc = async () => {
        setWakeState('loading');
        try {
            const result = await apiFetch('/actions/wake-pc', { method: 'POST' });
            setWakeState(result.status === 'sent' ? 'sent' : 'error');
        } catch (err) {
            console.error('Wake PC failed', err);
            setWakeState('error');
        }
        setTimeout(() => setWakeState('idle'), 2500);
    };

    const onNovaClick = () => {
        // Trigger voice toggle when orb is clicked
        toggleVoice();
    };

    return (
        <div className="nova-home">
            {/* Left Section: NOVA Orb + Current Weather */}
            <section className="nova-home-left">
                <div className="nova-orb-section">
                    <div className="flex justify-center mb-2">
                        <NovaOrb voiceState={voiceStatus} onClick={onNovaClick} />
                    </div>
                    <div className="nova-orb-status">
                        {voiceStatus === 'idle' && '• SYSTEMS ONLINE'}
                        {voiceStatus === 'listening' && '• LISTENING...'}
                        {voiceStatus === 'speaking' && '• SPEAKING...'}
                        {voiceStatus === 'thinking' && '• PROCESSING...'}
                    </div>
                </div>

                {/* Weather Card */}
                <section className="weather-card">
                    <div className="weather-current">
                        <div className="weather-temp">{currentTemp}°</div>
                        <div className="weather-condition">Stockholm</div>
                    </div>
                    <div className="weather-hourly">
                        <div className="weather-hourly-title">TODAY'S FORECAST</div>
                        <div className="weather-hourly-grid">
                            {forecastDays.slice(0, 6).map((day, idx) => (
                                <div key={`${day}-${idx}`} className="weather-hour">
                                    <div className="text-xs">6AM+{idx * 3}h</div>
                                    <div className="text-2xl">🌤️</div>
                                    <div className="font-semibold">{Math.round(weather?.daily?.temperature_2m_max?.[idx] ?? 0)}°</div>
                                </div>
                            ))}
                        </div>
                    </div>
                    <div className="weather-conditions">
                        <div className="weather-condition-row">
                            <span className="text-xs opacity-70">Real Feel</span>
                            <span className="font-semibold">{currentTemp}°</span>
                        </div>
                        <div className="weather-condition-row">
                            <span className="text-xs opacity-70">Wind</span>
                            <span className="font-semibold">0.2 km/h</span>
                        </div>
                        <div className="weather-condition-row">
                            <span className="text-xs opacity-70">Rain %</span>
                            <span className="font-semibold">0%</span>
                        </div>
                        <div className="weather-condition-row">
                            <span className="text-xs opacity-70">UV Index</span>
                            <span className="font-semibold">3</span>
                        </div>
                    </div>
                </section>
            </section>

            {/* Right Section: 7-day + PC + Alerts */}
            <section className="nova-home-right">
                {/* 7-day Forecast */}
                <div className="forecast-7day">
                    <div className="text-xs opacity-70 mb-2">7-DAY FORECAST</div>
                    <div className="space-y-1">
                        {forecastDays.slice(0, 7).map((day, idx) => (
                            <div key={day} className="forecast-row">
                                <span className="text-sm">{['Today', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][idx]}</span>
                                <span className="text-xl">🌤️</span>
                                <span className="font-semibold ml-auto">{Math.round(weather?.daily?.temperature_2m_max?.[idx] ?? 0)}°/{Math.round(weather?.daily?.temperature_2m_min?.[idx] ?? 0)}°</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Wake PC Card */}
                <motion.button
                    whileTap={{ scale: 0.97 }}
                    onClick={onWakePc}
                    className={`wake-pc-card ${wakeState}`}
                >
                    <Power size={20} />
                    <span>
                        {wakeState === 'loading' && 'Waking...'}
                        {wakeState === 'sent' && 'Signal Sent ✓'}
                        {wakeState === 'error' && 'Failed'}
                        {wakeState === 'idle' && 'Wake PC Oscar'}
                    </span>
                </motion.button>

                {/* Swedish Alerts */}
                <div className="alerts-ticker">
                    <div className="text-xs opacity-70 mb-1">SWEDISH ALERTS</div>
                    <div className="space-y-1">
                        {alerts.slice(0, 4).map((item, idx) => (
                            <a key={`${item.title}-${idx}`} href={item.url || '#'} target="_blank" rel="noreferrer" className="alert-item">
                                <span className="alert-source">{item.source}</span>
                                <span className="alert-title">{item.title.slice(0, 45)}</span>
                            </a>
                        ))}
                        {alerts.length === 0 && <div className="text-xs opacity-50">No alerts</div>}
                    </div>
                </div>
            </section>
        </div>
    );
}
