import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { House, MessageCircle, Music2, Newspaper, CloudSun, SlidersHorizontal, Power } from 'lucide-react';
import { motion } from 'framer-motion';
import ScreenToggle from './ScreenToggle';

const items = [
    { to: '/', label: 'Home', icon: House },
    { to: '/chat', label: 'Chat', icon: MessageCircle },
    { to: '/music', label: 'Music', icon: Music2 },
    { to: '/news', label: 'News', icon: Newspaper },
    { to: '/weather', label: 'Weather', icon: CloudSun },
    { to: '/settings', label: 'Config', icon: SlidersHorizontal }
];

export default function SideNav() {
    const [showScreenToggle, setShowScreenToggle] = useState(false);

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
            
            {/* Screen Toggle Button - Large Touch Target */}
            <motion.button
                onClick={() => setShowScreenToggle(!showScreenToggle)}
                className="nova-side-btn screen-toggle-btn"
                title="Toggle screen power"
                whileTap={{ scale: 0.92 }}
            >
                <Power size={28} />
                <span>Screen</span>
            </motion.button>

            {/* Screen Toggle Modal/Dropdown */}
            {showScreenToggle && (
                <motion.div
                    className="screen-toggle-dropdown"
                    initial={{ opacity: 0, scale: 0.9, y: -10 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9, y: -10 }}
                    transition={{ duration: 0.2 }}
                >
                    <ScreenToggle />
                </motion.div>
            )}
        </aside>
    );
}
