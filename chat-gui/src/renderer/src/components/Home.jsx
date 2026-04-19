import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { SkipBack, Play, Pause, SkipForward, House, Power, Wind, Droplets, Sun, Eye } from 'lucide-react';
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

    const currentTemp = weather?.current?.temperature_2m ?? '-';
    const currentWeatherCode = weather?.current?.weather_code ?? 0;
    const forecastDays = weather?.daily?.time || [];
    const forecastTempsMax = weather?.daily?.temperature_2m_max || [];
    const forecastTempsMin = weather?.daily?.temperature_2m_min || [];

    const getWeatherEmoji = (code) => {
        if (code === 0 || code === 1) return '☀️';
        if (code === 2 || code === 3) return '⛅';
        if (code === 45 || code === 48) return '🌫️';
        if (code >= 51 && code <= 67) return '🌧️';
        return '🌤️';
    };

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
        <motion.div 
            className="nova-home"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
        >
            {/* Left Section: NOVA Orb + Current Weather */}
            <motion.section 
                className="nova-home-left"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.1, ease: 'easeOut' }}
            >
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
                        <div className="weather-temp">{currentTemp !== '-' ? Math.round(currentTemp) : '-'}°</div>
                        <div className="weather-condition">Stockholm, Sweden</div>
                    </div>
                    <div className="weather-hourly">
                        <div className="weather-hourly-title">HOURLY</div>
                        <div className="weather-hourly-grid">
                            {forecastDays.length > 0 ? forecastDays.slice(0, 6).map((day, idx) => (
                                <div key={`${day}-${idx}`} className="weather-hour">
                                    <div className="text-xs">+{idx * 4}h</div>
                                    <div style={{fontSize: '1.1rem'}}>{getWeatherEmoji(currentWeatherCode)}</div>
                                    <div className="font-semibold">{forecastTempsMax[idx] ? Math.round(forecastTempsMax[idx]) : '-'}°</div>
                                </div>
                            )) : <div className="opacity-50 text-xs col-span-6">Loading...</div>}
                        </div>
                    </div>
                    <div className="weather-conditions">
                        <div className="weather-condition-row">
                            <span className="text-xs opacity-70 flex items-center gap-1"><Droplets size={11} /> Feels</span>
                            <span className="font-semibold">{weather?.current?.apparent_temperature ? Math.round(weather.current.apparent_temperature) : '-'}°</span>
                        </div>
                        <div className="weather-condition-row">
                            <span className="text-xs opacity-70 flex items-center gap-1"><Droplets size={11} /> Humidity</span>
                            <span className="font-semibold">{weather?.current?.relative_humidity_2m ?? '-'}%</span>
                        </div>
                        <div className="weather-condition-row">
                            <span className="text-xs opacity-70 flex items-center gap-1"><Wind size={11} /> Wind</span>
                            <span className="font-semibold">{weather?.current?.wind_speed_10m ? Math.round(weather.current.wind_speed_10m) : '-'} km/h</span>
                        </div>
                        <div className="weather-condition-row">
                            <span className="text-xs opacity-70 flex items-center gap-1"><Sun size={11} /> UV</span>
                            <span className="font-semibold">{weather?.current?.uv_index ? Math.round(weather.current.uv_index * 10) / 10 : '-'}</span>
                        </div>
                    </div>
                </section>
            </motion.section>

            {/* Right Section: 7-day + PC + Alerts */}
            <motion.section 
                className="nova-home-right"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.2, ease: 'easeOut' }}
            >
                {/* 7-day Forecast */}
                <div className="forecast-7day">
                    <div className="text-xs opacity-70 mb-2 font-semibold">7-DAY FORECAST</div>
                    <div className="space-y-1">
                        {forecastDays.length > 0 ? forecastDays.slice(0, 7).map((day, idx) => {
                            const maxTemp = forecastTempsMax[idx] ? Math.round(forecastTempsMax[idx]) : '-';
                            const minTemp = forecastTempsMin[idx] ? Math.round(forecastTempsMin[idx]) : '-';
                            const dayName = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][idx] || `Day+${idx}`;
                            const dayWeatherCode = weather?.daily?.weather_code?.[idx] || currentWeatherCode;
                            return (
                                <div key={day} className="forecast-row">
                                    <span className="text-sm font-medium">{dayName}</span>
                                    <span style={{fontSize: '1.1rem', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{getWeatherEmoji(dayWeatherCode)}</span>
                                    <span className="font-semibold ml-auto text-sm">{maxTemp}°/{minTemp}°</span>
                                </div>
                            );
                        }) : <div className="opacity-50 text-xs">Loading forecast...</div>}
                    </div>
                </div>

                {/* Wake PC Card */}
                <motion.button
                    whileTap={{ scale: 0.93 }}
                    onClick={onWakePc}
                    className={`wake-pc-card ${wakeState}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.3 }}
                >
                    <Power size={18} />
                    <span>
                        {wakeState === 'loading' && 'Waking...'}
                        {wakeState === 'sent' && '✓ Signal Sent'}
                        {wakeState === 'error' && '✗ Failed'}
                        {wakeState === 'idle' && 'Wake PC Oscar'}
                    </span>
                </motion.button>

                {/* Swedish Alerts */}
                <motion.div 
                    className="alerts-ticker"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.4, delay: 0.4 }}
                >
                    <div className="text-xs opacity-70 mb-2 font-semibold">ALERTS</div>
                    <div className="space-y-1">
                        {alerts.length > 0 ? alerts.slice(0, 4).map((item, idx) => (
                            <a key={`${item.title}-${idx}`} href={item.url || '#'} target="_blank" rel="noreferrer" className="alert-item">
                                <span className="alert-source">{item.source || 'Alert'}</span>
                                <span className="alert-title">{item.title.slice(0, 50)}</span>
                            </a>
                        )) : <div className="text-xs opacity-50">No alerts</div>}
                    </div>
                </motion.div>
            </motion.section>
        </motion.div>
    );
}
