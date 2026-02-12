import React from 'react';

export default function ConnectionBar({ status }) {
    const labels = {
        connected: 'Connected',
        disconnected: 'Disconnected — tap to retry',
        connecting: 'Connecting…',
    };

    const styles = {
        connected: 'bg-green-500/10 text-green-500',
        disconnected: 'bg-red-500/15 text-red-500',
        connecting: 'bg-yellow-500/10 text-yellow-500',
    };

    return (
        <div className={`flex items-center justify-center gap-1.5 p-1.5 text-xs font-medium transition-all duration-300 ${styles[status] || ''}`}>
            <span className={`w-2 h-2 rounded-full bg-current ${status === 'connecting' ? 'animate-pulse' : ''}`} />
            <span>{labels[status] || status}</span>
        </div>
    );
}
