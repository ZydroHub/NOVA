import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Power } from 'lucide-react';
import { useWebSocket } from '../contexts/WebSocketContext.jsx';
import { apiFetch } from '../apiClient.js';
import NovaOrb from './NovaOrb';
import PCStatus from './PCStatus';

export default function Home() {
    const { voiceStatus, voiceStage, toggleVoice } = useWebSocket();
    const [weather, setWeather] = useState(null);
    const [alerts, setAlerts] = useState([]);
    const [alertsError, setAlertsError] = useState(null);

    useEffect(() => {
        let mounted = true;
        async function loadData() {
            const [weatherResult, alertsResult] = await Promise.allSettled([
                apiFetch('/integrations/weather?latitude=59.3293&longitude=18.0686'),
                apiFetch('/integrations/swedish-alerts?limit=12&region=sweden')
            ]);

            if (!mounted) return;

            if (weatherResult.status === 'fulfilled') {
                setWeather(weatherResult.value);
            } else {
                console.error('Weather load failed', weatherResult.reason);
                setWeather(null);
            }

            if (alertsResult.status === 'fulfilled') {
                setAlerts(alertsResult.value?.items || []);
                setAlertsError(null);
            } else {
                console.error('Alerts load failed', alertsResult.reason);
                setAlerts([]);
                setAlertsError('Could not load alerts right now.');
            }
        }
        loadData();
        const timer = setInterval(loadData, 120000);
        return () => {
            mounted = false;
            clearInterval(timer);
        };
    }, []);

    const currentWeatherCode = weather?.current?.weather_code ?? 0;
    const hourly = weather?.hourly || {};
    const hourlyTimes = Array.isArray(hourly.time) ? hourly.time : [];
    const hourlyTemps = Array.isArray(hourly.temperature_2m) ? hourly.temperature_2m : [];
    const hourlyCodes = Array.isArray(hourly.weather_code) ? hourly.weather_code : [];
    const alertsSorted = useMemo(() => {
        return [...alerts].sort((a, b) => (b.priority_rank || 0) - (a.priority_rank || 0));
    }, [alerts]);

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

    const onNovaClick = useCallback(() => {
        console.info('[voice] home nova click -> toggleVoice');
        toggleVoice();
    }, [toggleVoice]);

    const stageLabel = {
        idle: '• SYSTEMS ONLINE',
        listening: '• LISTENING FOR VOICE...',
        transcribing: '• TURNING SPEECH INTO TEXT...',
        thinking: '• THINKING ABOUT RESPONSE...',
        generating: '• GENERATING RESPONSE TEXT...',
        speaking: '• TURNING TEXT INTO SPEECH...',
    }[voiceStage] || '• SYSTEMS ONLINE';

    return (
        <motion.div 
            className="nova-home touch-scroll-y overflow-y-auto h-full min-h-0"
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
                        {stageLabel}
                    </div>
                </div>

                <PCStatus />

            </motion.section>

            {/* Right Section: Today + Alerts */}
            <motion.section 
                className="nova-home-right"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.2, ease: 'easeOut' }}
            >
                <motion.div
                    className="weather-today-card"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.35, delay: 0.32 }}
                >
                    <div className="weather-today-head">
                        <div>
                            <div className="rain-chance-label">TODAY'S WEATHER</div>
                            <div className="weather-today-subtitle">Stockholm</div>
                        </div>
                        <div className="weather-today-icon">{getWeatherEmoji(currentWeatherCode)}</div>
                    </div>

                    <div className="weather-today-grid">
                        <div className="weather-today-item">
                            <span className="weather-today-item-label">Rain</span>
                            <span className="weather-today-item-value">{weather?.daily?.precipitation_probability_max?.[0] ?? '-'}%</span>
                        </div>
                        <div className="weather-today-item">
                            <span className="weather-today-item-label">Wind</span>
                            <span className="weather-today-item-value">{typeof weather?.current?.wind_speed_10m === 'number' ? Math.round(weather.current.wind_speed_10m) : '-'} km/h</span>
                        </div>
                        <div className="weather-today-item">
                            <span className="weather-today-item-label">Feels like</span>
                            <span className="weather-today-item-value">{typeof weather?.current?.apparent_temperature === 'number' ? Math.round(weather.current.apparent_temperature) : '-'}°</span>
                        </div>
                        <div className="weather-today-item">
                            <span className="weather-today-item-label">Humidity</span>
                            <span className="weather-today-item-value">{weather?.current?.relative_humidity_2m ?? '-'}%</span>
                        </div>
                    </div>
                </motion.div>

                {/* Swedish Alerts */}
                <motion.div 
                    className="alerts-ticker"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.4, delay: 0.4 }}
                >
                    <div className="text-xs opacity-70 mb-2 font-semibold tracking-[0.18em]">LATEST NEWS & ALERTS</div>
                    <div className="space-y-1">
                        {alertsError && <div className="text-xs opacity-70">{alertsError}</div>}
                        {alertsSorted.length > 0 ? alertsSorted.slice(0, 4).map((item, idx) => (
                            <div key={`${item.title}-${idx}`} className="alert-item alert-item-static">
                                <div className="alert-row-top">
                                    <span className="alert-source">{item.source || 'Alert'}</span>
                                    <span className="alert-priority">{item.priority_label || 'News'}</span>
                                </div>
                                <span className="alert-title">{item.title}</span>
                            </div>
                        )) : <div className="text-xs opacity-50">No items yet</div>}
                    </div>
                </motion.div>
            </motion.section>
        </motion.div>
    );
}
