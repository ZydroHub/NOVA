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
    const current = weather?.current || {};

    const formatTempRange = (minTemp, maxTemp) => {
        const low = typeof minTemp === 'number' ? Math.round(minTemp) : '-';
        const high = typeof maxTemp === 'number' ? Math.round(maxTemp) : '-';
        return `${low}° - ${high}°`;
    };

    return (
        <motion.div
            className="weather-page w-full h-full min-h-0 overflow-y-auto touch-scroll-y p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
        >
            <section className="weather-shell glass-card p-4 sm:p-6 flex flex-col gap-5">
                <div className="weather-hero">
                    <div className="weather-hero-copy">
                        <div className="weather-kicker">Stockholm live weather</div>
                        <h2 className="nova-title">Weather</h2>
                        <p className="weather-hero-subtitle">Hourly forecasts, daily ranges, and current conditions in one glance.</p>
                    </div>
                    <div className="weather-hero-temp">
                        <div className="weather-hero-value">{typeof current.temperature_2m === 'number' ? Math.round(current.temperature_2m) : '-'}°</div>
                        <div className="weather-hero-meta">
                            <span>{getWeatherEmoji(current.weather_code ?? 0)}</span>
                            <span>{typeof current.apparent_temperature === 'number' ? `${Math.round(current.apparent_temperature)}° feels like` : 'Feels-like unavailable'}</span>
                        </div>
                    </div>
                </div>

                <div className="weather-metrics-grid">
                    <div className="weather-metric-card">
                        <span>Wind</span>
                        <strong>{typeof current.wind_speed_10m === 'number' ? `${Math.round(current.wind_speed_10m)} km/h` : '-'}</strong>
                    </div>
                    <div className="weather-metric-card">
                        <span>Humidity</span>
                        <strong>{typeof current.relative_humidity_2m === 'number' ? `${Math.round(current.relative_humidity_2m)}%` : '-'}</strong>
                    </div>
                    <div className="weather-metric-card">
                        <span>UV Index</span>
                        <strong>{typeof current.uv_index === 'number' ? Math.round(current.uv_index * 10) / 10 : '-'}</strong>
                    </div>
                    <div className="weather-metric-card weather-metric-card-highlight">
                        <span>Rain chance</span>
                        <strong>{typeof daily.precipitation_probability_max?.[0] === 'number' ? `${Math.round(daily.precipitation_probability_max[0])}%` : '-'}</strong>
                    </div>
                </div>

                <div className="weather-section">
                    <div className="weather-section-title">Next 12 hours</div>
                    <div className="weather-grid weather-grid-wide">
                        {hours.length === 0 && <div className="weather-day weather-empty">Hourly data unavailable.</div>}
                        {hours.map((hour, index) => (
                            <motion.div
                                key={`${hour}-${index}`}
                                className="weather-day weather-day-compact"
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

                <div className="weather-section">
                    <div className="weather-section-title">7-day outlook</div>
                    <div className="weather-grid weather-grid-wide mt-1">
                        {days.length === 0 && <div className="weather-day weather-empty">Weather data unavailable.</div>}
                        {days.map((day, index) => (
                            <motion.div 
                                key={day} 
                                className="weather-day weather-day-wide"
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ duration: 0.3, delay: index * 0.05 }}
                            >
                                <h4>{new Date(day).toLocaleDateString('en-US', { weekday: 'short' })}</h4>
                                <div className="text-xl">{getWeatherEmoji(daily.weather_code?.[index])}</div>
                                <div>{formatTempRange(daily.temperature_2m_min?.[index], daily.temperature_2m_max?.[index])}</div>
                                <small>Rain {Math.round(daily.precipitation_probability_max?.[index] ?? 0)}%</small>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>
        </motion.div>
    );
}
