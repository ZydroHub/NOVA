import React from 'react';

export default function ConnectionBar({ status }) {
    const labels = {
        connected: 'Connected',
        disconnected: 'Disconnected — tap to retry',
        connecting: 'Connecting…',
    };

    return (
        <div className={`connection-bar connection-bar--${status}`}>
            <span className={`connection-dot ${status === 'connecting' ? 'connection-dot--pulse' : ''}`} />
            <span>{labels[status] || status}</span>
        </div>
    );
}
