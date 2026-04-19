import React, { useEffect, useState, useCallback } from 'react';
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

    const getWeatherEmoji = useCallback((code) => {
        if (code === 0) return '☀️';     // Clear
        if (code === 1 || code === 2) return '🌤️';  // Mostly clear/Partly cloudy
        if (code === 3) return '☁️';     // Overcast
        if (code === 45 || code === 48) return '🌫️';  // Foggy
        if (code >= 51 && code <= 55) return '🌧️';  // Drizzle
        if (code >= 61 && code <= 67) return '🌧️';  // Rain
        if (code >= 71 && code <= 77) return '❄️';   // Snow
        if (code >= 80 && code <= 82) return '⛈️';   // Rain showers
        if (code >= 85 && code <= 86) return '❄️';   // Snow showers
        return '🌤️';
    }, []);

    const onWakePc = useCallback(async () => {
        setWakeState('loading');
        try {
            const result = await apiFetch('/actions/wake-pc', { method: 'POST' });
            setWakeState(result.status === 'sent' ? 'sent' : 'error');
        } catch (err) {
            console.error('Wake PC failed', err);
            setWakeState('error');
        }
        setTimeout(() => setWakeState('idle'), 2500);
    }, []);

    const onNovaClick = useCallback(() => {
        toggleVoice();
    }, [toggleVoice]);

    return (
        <motion.div 
            className="nova-home touch-scroll-y"
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
                    <div className="weather-main-container">
                        <div className="weather-left">
                            <div className="weather-location">Stockholm</div>
                            <div className="weather-rain-chance">Chance of rain: {forecastDays.length > 0 ? (weather?.daily?.precipitation_probability_max?.[0] ?? 0) : '-'}%</div>
                            <div className="weather-temp-huge">{currentTemp !== '-' ? Math.round(currentTemp) : '-'}°</div>
                        </div>

                        <div className="weather-hourly-section">
                            <div className="weather-hourly-title">TODAY'S FORECAST</div>
                            <div className="weather-hourly-grid">
                                {forecastDays.length > 0 ? forecastDays.slice(0, 6).map((day, idx) => {
                                    const hourDisplay = `${String(idx * 4).padStart(2, '0')}:00`;
                                    return (
                                        <div key={`${day}-${idx}`} className="weather-hour-col">
                                            <div className="hour-time">{hourDisplay}</div>
                                            <div className="hour-emoji">{getWeatherEmoji(currentWeatherCode)}</div>
                                            <div className="hour-temp">{forecastTempsMax[idx] ? Math.round(forecastTempsMax[idx]) : '-'}°</div>
                                        </div>
                                    );
                                }) : <div className="opacity-50 text-xs col-span-6">Loading...</div>}
                            </div>
                        </div>
                    </div>

                    <div className="air-conditions-grid">
                        <div className="air-condition-item">
                            <div className="condition-label">Real Feel</div>
                            <div className="condition-value">{weather?.current?.apparent_temperature ? Math.round(weather.current.apparent_temperature) : '-'}°</div>
                        </div>
                        <div className="air-condition-item">
                            <div className="condition-label">Wind</div>
                            <div className="condition-value">{weather?.current?.wind_speed_10m ? Math.round(weather.current.wind_speed_10m) : '-'} km/h</div>
                        </div>
                        <div className="air-condition-item">
                            <div className="condition-label">Humidity</div>
                            <div className="condition-value">{weather?.current?.relative_humidity_2m ?? '-'}%</div>
                        </div>
                        <div className="air-condition-item">
                            <div className="condition-label">UV Index</div>
                            <div className="condition-value">{weather?.current?.uv_index ? Math.round(weather.current.uv_index * 10) / 10 : '-'}</div>
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
