import React from 'react';
import { motion } from 'framer-motion';

const ACTIVE_STATES = new Set(['listening', 'speaking']);

export default function NovaOrb({ voiceState = 'idle', onClick }) {
    const isActive = ACTIVE_STATES.has(voiceState);

    return (
        <motion.div
            className="nova-orb-wrap"
            aria-label="NOVA core orb"
            onClick={onClick}
            style={{ cursor: 'pointer' }}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.96 }}
        >
            <motion.div
                className={`nova-orb ${isActive ? 'nova-orb-active' : 'nova-orb-idle'}`}
                animate={{
                    y: isActive ? [0, -12, 0] : [0, -6, 0],
                    boxShadow: isActive
                        ? [
                            '0 -8px 32px rgba(26,209,255,0.35), inset 0 0 40px rgba(39,123,255,0.28)',
                            '0 12px 48px rgba(26,209,255,0.55), inset 0 0 56px rgba(39,123,255,0.4)',
                            '0 -8px 32px rgba(26,209,255,0.35), inset 0 0 40px rgba(39,123,255,0.28)'
                        ]
                        : [
                            '0 -4px 24px rgba(26,209,255,0.2), inset 0 0 30px rgba(39,123,255,0.16)',
                            '0 8px 36px rgba(26,209,255,0.32), inset 0 0 44px rgba(39,123,255,0.24)',
                            '0 -4px 24px rgba(26,209,255,0.2), inset 0 0 30px rgba(39,123,255,0.16)'
                        ]
                }}
                transition={{ duration: isActive ? 0.9 : 2.8, repeat: Infinity, ease: 'easeInOut' }}
            >
                <div className="nova-orb-core">NOVA</div>
            </motion.div>
            <motion.div
                className={`nova-orb-ring ${isActive ? 'nova-orb-ring-fast' : 'nova-orb-ring-slow'}`}
                animate={{ y: isActive ? [0, -12, 0] : [0, -6, 0] }}
                transition={{ duration: isActive ? 0.9 : 2.8, repeat: Infinity, ease: 'easeInOut' }}
            />
        </motion.div>
    );
}
