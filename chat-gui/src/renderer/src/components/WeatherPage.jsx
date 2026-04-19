import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { apiFetch } from '../apiClient.js';

export default function WeatherPage() {
    const [weather, setWeather] = useState(null);

    const getWeatherEmoji = (code) => {
        if (code === 0) return '☀️';
        if (code === 1 || code === 2) return '🌤️';
        if (code === 3) return '☁️';
        if (code === 45 || code === 48) return '🌫️';
        if (code >= 51 && code <= 67) return '🌧️';
        if (code >= 71 && code <= 77) return '❄️';
        if (code >= 80 && code <= 82) return '⛈️';
        if (code >= 85 && code <= 86) return '❄️';
        return '🌤️';
    };

    useEffect(() => {
        let mounted = true;
        async function load() {
            try {
                const data = await apiFetch('/integrations/weather?latitude=59.3293&longitude=18.0686');
                if (mounted) setWeather(data);
            } catch (err) {
                console.error('Weather fetch failed', err);
                if (mounted) setWeather(null);
            }
        }
        load();
        const timer = setInterval(load, 120000);
        return () => {
            mounted = false;
            clearInterval(timer);
        };
    }, []);

    const daily = weather?.daily || {};
    const days = Array.isArray(daily.time) ? daily.time : [];
    const hourly = weather?.hourly || {};
    const hours = Array.isArray(hourly.time) ? hourly.time.slice(0, 12) : [];

    return (
        <motion.div
            className="w-full h-full overflow-y-auto touch-scroll-y p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
        >
            <section className="glass-card p-6 flex flex-col gap-5">
                <div>
                    <h2 className="nova-title">Weather</h2>
                    <p className="nova-subtitle">Stockholm live + hourly + 7-day outlook</p>
                </div>

                <div>
                    <h3 className="text-sm font-semibold mb-2 text-cyan-200/90">NEXT 12 HOURS</h3>
                    <div className="weather-grid">
                        {hours.length === 0 && <div className="weather-day">Hourly data unavailable.</div>}
                        {hours.map((hour, index) => (
                            <motion.div
                                key={`${hour}-${index}`}
                                className="weather-day"
                                initial={{ opacity: 0, scale: 0.94 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ duration: 0.2, delay: index * 0.02 }}
                            >
                                <h4>{hour.includes('T') ? hour.split('T')[1].slice(0, 5) : '--:--'}</h4>
                                <div className="text-xl">{getWeatherEmoji(hourly.weather_code?.[index])}</div>
                                <div>{typeof hourly.temperature_2m?.[index] === 'number' ? Math.round(hourly.temperature_2m[index]) : '-'}°</div>
                                <small>Rain {Math.round(hourly.precipitation_probability?.[index] ?? 0)}%</small>
                            </motion.div>
                        ))}
                    </div>
                </div>

                <div>
                    <h3 className="text-sm font-semibold mb-2 text-cyan-200/90">7-DAY</h3>
                    <div className="weather-grid mt-1">
                        {days.length === 0 && <div className="weather-day">Weather data unavailable.</div>}
                        {days.map((day, index) => (
                        <motion.div 
                            key={day} 
                            className="weather-day"
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.3, delay: index * 0.05 }}
                        >
                            <h4>{new Date(day).toLocaleDateString('en-US', { weekday: 'short' })}</h4>
                            <div className="text-xl">{getWeatherEmoji(daily.weather_code?.[index])}</div>
                            <div>{Math.round(daily.temperature_2m_max?.[index] ?? 0)}° / {Math.round(daily.temperature_2m_min?.[index] ?? 0)}°</div>
                            <small>Rain {Math.round(daily.precipitation_probability_max?.[index] ?? 0)}%</small>
                        </motion.div>
                    ))}
                    </div>
                </div>
            </section>
        </motion.div>
    );
}
