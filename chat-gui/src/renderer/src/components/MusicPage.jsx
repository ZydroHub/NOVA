import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Play, Pause, SkipBack, SkipForward, Repeat, Shuffle } from 'lucide-react';

export default function MusicPage() {
    const [isPlaying, setIsPlaying] = useState(false);

    return (
        <motion.div
            className="nova-page-grid"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
        >
            <section className="glass-card p-6">
                <h2 className="nova-title">Music Control</h2>
                <p className="nova-subtitle">Spotify-style controls are ready for integration.</p>
                <div className="music-card mt-6">
                    <div>
                        <p className="text-xl font-semibold">No Track Selected</p>
                        <p className="text-sm opacity-70">Connect playback source later</p>
                    </div>
                    <div className="music-progress" />
                    <div className="music-controls">
                        <button className="round-btn" aria-label="Shuffle"><Shuffle size={22} /></button>
                        <button className="round-btn" aria-label="Previous"><SkipBack size={22} /></button>
                        <button 
                            className="round-btn round-btn-main" 
                            aria-label={isPlaying ? "Pause" : "Play"}
                            onClick={() => setIsPlaying(!isPlaying)}
                        >
                            {isPlaying ? <Pause size={24} /> : <Play size={24} />}
                        </button>
                        <button className="round-btn" aria-label="Next"><SkipForward size={22} /></button>
                        <button className="round-btn" aria-label="Repeat"><Repeat size={22} /></button>
                    </div>
                </div>
            </section>
        </motion.div>
    );
}
