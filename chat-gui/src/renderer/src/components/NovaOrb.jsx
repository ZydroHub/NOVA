import React from 'react';
import { motion } from 'framer-motion';

const ACTIVE_STATES = new Set(['listening', 'speaking']);

export default function NovaOrb({ voiceState = 'idle' }) {
    const isActive = ACTIVE_STATES.has(voiceState);

    return (
        <div className="nova-orb-wrap" aria-label="NOVA core orb">
            <motion.div
                className={`nova-orb ${isActive ? 'nova-orb-active' : 'nova-orb-idle'}`}
                animate={{
                    scale: isActive ? [1, 1.07, 1] : [1, 1.02, 1],
                    boxShadow: isActive
                        ? [
                            '0 0 30px rgba(26,209,255,0.25), inset 0 0 40px rgba(39,123,255,0.22)',
                            '0 0 48px rgba(26,209,255,0.45), inset 0 0 52px rgba(39,123,255,0.32)',
                            '0 0 30px rgba(26,209,255,0.25), inset 0 0 40px rgba(39,123,255,0.22)'
                        ]
                        : [
                            '0 0 24px rgba(26,209,255,0.18), inset 0 0 30px rgba(39,123,255,0.16)',
                            '0 0 32px rgba(26,209,255,0.24), inset 0 0 40px rgba(39,123,255,0.2)',
                            '0 0 24px rgba(26,209,255,0.18), inset 0 0 30px rgba(39,123,255,0.16)'
                        ]
                }}
                transition={{ duration: isActive ? 1.05 : 3.6, repeat: Infinity, ease: 'easeInOut' }}
            >
                <div className="nova-orb-core">NOVA</div>
            </motion.div>
            <div className={`nova-orb-ring ${isActive ? 'nova-orb-ring-fast' : 'nova-orb-ring-slow'}`} />
        </div>
    );
}
