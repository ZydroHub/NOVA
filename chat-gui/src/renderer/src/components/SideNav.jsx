import React from 'react';
import { NavLink } from 'react-router-dom';
import { House, MessageCircle, Music2, Newspaper, CloudSun } from 'lucide-react';

const items = [
    { to: '/', label: 'Home', icon: House },
    { to: '/chat', label: 'Chat', icon: MessageCircle },
    { to: '/music', label: 'Music', icon: Music2 },
    { to: '/news', label: 'News', icon: Newspaper },
    { to: '/weather', label: 'Weather', icon: CloudSun }
];

export default function SideNav() {
    return (
        <aside className="nova-side-nav" aria-label="NOVA navigation">
            {items.map((item) => {
                const Icon = item.icon;
                return (
                    <NavLink
                        key={item.to}
                        to={item.to}
                        className={({ isActive }) => `nova-side-btn ${isActive ? 'active' : ''}`}
                        title={item.label}
                    >
                        <Icon size={28} />
                        <span>{item.label}</span>
                    </NavLink>
                );
            })}
        </aside>
    );
}
