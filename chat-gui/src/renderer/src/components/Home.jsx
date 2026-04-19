import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { SkipBack, Play, Pause, SkipForward, House, Power } from 'lucide-react';
import { useWebSocket } from '../contexts/WebSocketContext.jsx';
import { apiFetch } from '../apiClient.js';
import NovaOrb from './NovaOrb';

export default function Home() {
    const { voiceStatus } = useWebSocket();
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

    return (
        <div className="nova-page-grid">
            <section className="glass-card p-6 relative overflow-hidden">
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <h1 className="text-5xl font-semibold tracking-tight">Good afternoon</h1>
                        <p className="nova-subtitle mt-2">Welcome back, ZydroHub</p>
                    </div>
                    <div className="flex items-center gap-2 text-cyan-100/80">
                        <House size={20} />
                        <span>NOVA Home</span>
                    </div>
                </div>

                <div className="mt-6 flex justify-center">
                    <NovaOrb voiceState={voiceStatus} />
                </div>
            </section>

            <section className="glass-card p-6">
                <h3 className="nova-title">Weather</h3>
                <div className="mt-4 text-6xl font-bold text-cyan-200">{currentTemp}°</div>
                <p className="nova-subtitle">Stockholm via Open-Meteo</p>
                <div className="weather-grid mt-5">
                    {forecastDays.slice(0, 7).map((day, idx) => (
                        <div key={day} className="weather-day">
                            <h4>{day.slice(5)}</h4>
                            <div>
                                {Math.round(weather?.daily?.temperature_2m_max?.[idx] ?? 0)}°
                            </div>
                            <small>{Math.round(weather?.daily?.precipitation_probability_max?.[idx] ?? 0)}% rain</small>
                        </div>
                    ))}
                </div>
            </section>

            <section className="glass-card p-6">
                <h3 className="nova-title">PC Control</h3>
                <p className="nova-subtitle">Acer Predator · PC-Oscar</p>
                <motion.button
                    whileTap={{ scale: 0.97 }}
                    onClick={onWakePc}
                    className={`wake-btn mt-6 ${wakeState}`}
                >
                    <Power size={26} />
                    <span>
                        {wakeState === 'loading' && 'Sending Magic Packet...'}
                        {wakeState === 'sent' && 'Wake Signal Sent'}
                        {wakeState === 'error' && 'Wake Failed'}
                        {wakeState === 'idle' && 'Wake PC'}
                    </span>
                </motion.button>
            </section>

            <section className="glass-card p-6">
                <h3 className="nova-title">Music</h3>
                <p className="nova-subtitle">Spotify-style controls</p>
                <div className="music-card mt-5">
                    <div className="music-progress" />
                    <div className="music-controls">
                        <button className="round-btn" aria-label="Previous"><SkipBack size={22} /></button>
                        <button className="round-btn round-btn-main" aria-label="Play"><Play size={24} /></button>
                        <button className="round-btn" aria-label="Pause"><Pause size={22} /></button>
                        <button className="round-btn" aria-label="Next"><SkipForward size={22} /></button>
                    </div>
                </div>
            </section>

            <section className="glass-card p-6 col-span-2">
                <h3 className="nova-title">Swedish Alerts</h3>
                <div className="news-list mt-4">
                    {alerts.length === 0 && <div className="news-item">No alert feed data yet.</div>}
                    {alerts.map((item, index) => (
                        <a key={`${item.title}-${index}`} className="news-item" href={item.url || '#'} target="_blank" rel="noreferrer">
                            <strong>{item.source || 'Alert'}</strong>
                            <span>{item.title}</span>
                        </a>
                    ))}
                </div>
            </section>
        </div>
    );
}
