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

    const currentTemp = weather?.current?.temperature_2m ?? '-';
    const currentWeatherCode = weather?.current?.weather_code ?? 0;
    const hourly = weather?.hourly || {};
    const hourlyTimes = Array.isArray(hourly.time) ? hourly.time : [];
    const hourlyTemps = Array.isArray(hourly.temperature_2m) ? hourly.temperature_2m : [];
    const hourlyCodes = Array.isArray(hourly.weather_code) ? hourly.weather_code : [];
    const forecastDays = Array.isArray(weather?.daily?.time) ? weather.daily.time : [];
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
        console.info('[voice] home nova click -> toggleVoice');
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
                            <div className="weather-temp-huge">{typeof currentTemp === 'number' ? Math.round(currentTemp) : '-'}°</div>
                        </div>
                    </div>

                    <motion.button
                        whileTap={{ scale: 0.96 }}
                        onClick={onWakePc}
                        className={`wake-pc-card wake-pc-card-hero ${wakeState}`}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: 0.3 }}
                    >
                        <Power size={20} />
                        <span>
                            {wakeState === 'loading' && 'Waking...'}
                            {wakeState === 'sent' && '✓ Signal Sent'}
                            {wakeState === 'error' && '✗ Failed'}
                            {wakeState === 'idle' && 'Start PC'}
                        </span>
                    </motion.button>

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

            {/* Right Section: Today + Rain + Alerts */}
            <motion.section 
                className="nova-home-right"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.2, ease: 'easeOut' }}
            >
                {/* Today's Forecast */}
                <div className="forecast-7day">
                    <div className="text-xs opacity-70 mb-2 font-semibold tracking-[0.18em]">TODAY'S FORECAST</div>
                    <div className="space-y-1">
                        {todayHours.length > 0 ? todayHours.map((entry) => {
                            return (
                                <div key={entry.key} className="forecast-row forecast-row-hourly">
                                    <span className="forecast-day text-sm font-medium">{entry.hour}</span>
                                    <span className="forecast-icon" style={{fontSize: '1.1rem', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{getWeatherEmoji(entry.code)}</span>
                                    <span className="forecast-temp font-semibold ml-auto text-sm text-cyan-100">{typeof entry.temp === 'number' ? Math.round(entry.temp) : '-'}°</span>
                                </div>
                            );
                        }) : <div className="opacity-50 text-xs">Loading hourly weather...</div>}
                    </div>
                </div>

                <motion.div
                    className="rain-chance-card"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.35, delay: 0.32 }}
                >
                    <div className="rain-chance-label">STOCKHOLM RAIN CHANCE</div>
                    <div className="rain-chance-value">{forecastDays.length > 0 ? (weather?.daily?.precipitation_probability_max?.[0] ?? 0) : '-'}%</div>
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
