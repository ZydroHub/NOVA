import React, { useEffect, useState } from 'react';
import { apiFetch } from '../apiClient.js';

export default function NewsPage() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let mounted = true;
        async function load() {
            setLoading(true);
            try {
                const data = await apiFetch('/integrations/swedish-alerts?limit=15');
                if (mounted) setItems(data.items || []);
            } catch (err) {
                console.error('Failed to load alerts', err);
                if (mounted) setItems([]);
            } finally {
                if (mounted) setLoading(false);
            }
        }
        load();
        const timer = setInterval(load, 60000);
        return () => {
            mounted = false;
            clearInterval(timer);
        };
    }, []);

    return (
        <div className="nova-page-grid">
            <section className="glass-card p-6">
                <h2 className="nova-title">Swedish Alerts</h2>
                <p className="nova-subtitle">Polisen, Krisinformation, and SOS Alarm sources</p>
                <div className="news-list mt-4">
                    {loading && <div className="news-item">Loading alerts...</div>}
                    {!loading && items.length === 0 && <div className="news-item">No alerts available right now.</div>}
                    {items.map((item, idx) => (
                        <a key={`${item.title}-${idx}`} className="news-item" href={item.url || '#'} target="_blank" rel="noreferrer">
                            <strong>{item.source || 'Alert'}</strong>
                            <span>{item.title}</span>
                        </a>
                    ))}
                </div>
            </section>
        </div>
    );
}
