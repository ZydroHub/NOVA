import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Power } from 'lucide-react';
import { useWebSocket } from '../contexts/WebSocketContext.jsx';
import { apiFetch } from '../apiClient.js';
import NovaOrb from './NovaOrb';

export default function Home() {
    const { voiceStatus, voiceStage, toggleVoice } = useWebSocket();
    const [weather, setWeather] = useState(null);
    const [alerts, setAlerts] = useState([]);
    const [alertsError, setAlertsError] = useState(null);
    const [wakeState, setWakeState] = useState('idle');

    useEffect(() => {
        let mounted = true;
        async function loadData() {
            try {
                const [weatherData, alertsData] = await Promise.all([
                    apiFetch('/integrations/weather?latitude=59.3293&longitude=18.0686'),
                    apiFetch('/integrations/swedish-alerts?limit=12')
                ]);
                if (!mounted) return;
                setWeather(weatherData);
                setAlerts(alertsData.items || []);
                setAlertsError(null);
            } catch (err) {
                console.error('Dashboard load failed', err);
                if (!mounted) return;
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

    const currentTemp = weather?.current?.temperature_2m ?? '-';
    const currentWeatherCode = weather?.current?.weather_code ?? 0;
    const hourly = weather?.hourly || {};
    const hourlyTimes = Array.isArray(hourly.time) ? hourly.time : [];
    const hourlyTemps = Array.isArray(hourly.temperature_2m) ? hourly.temperature_2m : [];
    const hourlyCodes = Array.isArray(hourly.weather_code) ? hourly.weather_code : [];
    const forecastDays = Array.isArray(weather?.daily?.time) ? weather.daily.time : [];
    const forecastTempsMax = Array.isArray(weather?.daily?.temperature_2m_max) ? weather.daily.temperature_2m_max : [];
    const forecastTempsMin = Array.isArray(weather?.daily?.temperature_2m_min) ? weather.daily.temperature_2m_min : [];

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

    const todayHours = useMemo(() => {
        const slots = [];
        for (let i = 0; i < Math.min(6, hourlyTimes.length); i += 1) {
            const timestamp = hourlyTimes[i] || '';
            const hour = timestamp.includes('T') ? timestamp.split('T')[1]?.slice(0, 5) : '--:--';
            slots.push({
                key: `${timestamp}-${i}`,
                hour,
                temp: hourlyTemps[i],
                code: hourlyCodes[i] ?? currentWeatherCode,
            });
        }
        return slots;
    }, [hourlyTimes, hourlyTemps, hourlyCodes, currentWeatherCode]);

    const formatDay = (dateText, idx) => {
        if (!dateText) return `Day ${idx + 1}`;
        const date = new Date(dateText);
        if (Number.isNaN(date.getTime())) return `Day ${idx + 1}`;
        return date.toLocaleDateString('en-US', { weekday: 'short' });
    };

    const formatTempRange = (minTemp, maxTemp) => {
        const low = typeof minTemp === 'number' ? Math.round(minTemp) : '-';
        const high = typeof maxTemp === 'number' ? Math.round(maxTemp) : '-';
        return `${low}° - ${high}°`;
    };

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

                {/* Weather Card */}
                <section className="weather-card home-weather-remake">
                    <div className="weather-main-container">
                        <div className="weather-left">
                            <div className="weather-location">Stockholm</div>
                                    <div className="weather-rain-chance">Chance of rain: {forecastDays.length > 0 ? (weather?.daily?.precipitation_probability_max?.[0] ?? 0) : '-'}%</div>
                                    <div className="weather-temp-huge">{typeof currentTemp === 'number' ? Math.round(currentTemp) : '-'}°</div>
                        </div>

                        <div className="weather-hourly-section">
                            <div className="weather-hourly-title">TODAY'S FORECAST</div>
                            <div className="weather-hourly-grid">
                                {todayHours.length > 0 ? todayHours.map((entry) => {
                                    return (
                                        <div key={entry.key} className="weather-hour-col">
                                            <div className="hour-time">{entry.hour}</div>
                                            <div className="hour-emoji">{getWeatherEmoji(entry.code)}</div>
                                            <div className="hour-temp">{typeof entry.temp === 'number' ? Math.round(entry.temp) : '-'}°</div>
                                        </div>
                                    );
                                }) : <div className="opacity-50 text-xs col-span-6">Loading hourly weather...</div>}
                            </div>
                        </div>
                    </div>

                    <div className="air-conditions-grid">
                        <div className="air-condition-item">
                            <div className="condition-label">Real Feel</div>
                            <div className="condition-value">{typeof weather?.current?.apparent_temperature === 'number' ? Math.round(weather.current.apparent_temperature) : '-'}°</div>
                        </div>
                        <div className="air-condition-item">
                            <div className="condition-label">Wind</div>
                            <div className="condition-value">{typeof weather?.current?.wind_speed_10m === 'number' ? Math.round(weather.current.wind_speed_10m) : '-'} km/h</div>
                        </div>
                        <div className="air-condition-item">
                            <div className="condition-label">Humidity</div>
                            <div className="condition-value">{weather?.current?.relative_humidity_2m ?? '-'}%</div>
                        </div>
                        <div className="air-condition-item">
                            <div className="condition-label">UV Index</div>
                            <div className="condition-value">{typeof weather?.current?.uv_index === 'number' ? Math.round(weather.current.uv_index * 10) / 10 : '-'}</div>
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
                    <div className="text-xs opacity-70 mb-2 font-semibold tracking-[0.18em]">7-DAY FORECAST</div>
                    <div className="space-y-1">
                        {forecastDays.length > 0 ? forecastDays.slice(0, 7).map((day, idx) => {
                            const maxTemp = typeof forecastTempsMax[idx] === 'number' ? Math.round(forecastTempsMax[idx]) : '-';
                            const minTemp = typeof forecastTempsMin[idx] === 'number' ? Math.round(forecastTempsMin[idx]) : '-';
                            const dayName = formatDay(day, idx);
                            const dayWeatherCode = weather?.daily?.weather_code?.[idx] || currentWeatherCode;
                            return (
                                <div key={day} className="forecast-row">
                                    <span className="text-sm font-medium">{dayName}</span>
                                    <span style={{fontSize: '1.1rem', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{getWeatherEmoji(dayWeatherCode)}</span>
                                    <span className="font-semibold ml-auto text-sm text-cyan-100">{formatTempRange(minTemp, maxTemp)}</span>
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
                        {wakeState === 'idle' && 'Start PC'}
                    </span>
                </motion.button>

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
                                <span className="alert-title">{item.title.slice(0, 70)}</span>
                            </div>
                        )) : <div className="text-xs opacity-50">No items yet</div>}
                    </div>
                </motion.div>
            </motion.section>
        </motion.div>
    );
}
