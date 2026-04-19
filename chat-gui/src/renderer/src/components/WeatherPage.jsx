import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { apiFetch } from '../apiClient.js';

export default function WeatherPage() {
    const [weather, setWeather] = useState(null);

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

    return (
        <motion.div
            className="nova-page-grid"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
        >
            <section className="glass-card p-6">
                <h2 className="nova-title">Weather</h2>
                <p className="nova-subtitle">Open-Meteo 7 day overview</p>
                <div className="weather-grid mt-4">
                    {days.length === 0 && <div className="weather-day">Weather data unavailable.</div>}
                    {days.map((day, index) => (
                        <motion.div 
                            key={day} 
                            className="weather-day"
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.3, delay: index * 0.05 }}
                        >
                            <h4>{day}</h4>
                            <div>{Math.round(daily.temperature_2m_max?.[index] ?? 0)}° / {Math.round(daily.temperature_2m_min?.[index] ?? 0)}°</div>
                            <small>Rain {Math.round(daily.precipitation_probability_max?.[index] ?? 0)}%</small>
                        </motion.div>
                    ))}
                </div>
            </section>
        </motion.div>
    );
}
