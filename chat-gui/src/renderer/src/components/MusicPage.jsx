import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Play, Pause, SkipBack, SkipForward, Repeat, Shuffle, Volume2, Volume1 } from 'lucide-react';

export default function MusicPage() {
    const [isPlaying, setIsPlaying] = useState(false);
    const [volume, setVolume] = useState(72);

    return (
        <motion.div
            className="w-full h-full min-h-0 overflow-y-auto touch-scroll-y p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
        >
            <section className="glass-card p-6 max-w-3xl w-full mx-auto flex flex-col gap-5 min-h-full">
                <div>
                    <h2 className="nova-title">Music Control</h2>
                    <p className="nova-subtitle">Spotify-style controls are ready for integration.</p>
                </div>
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

                <div className="music-volume-panel mt-auto">
                    <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-cyan-100 font-semibold">
                            {volume === 0 ? <Volume1 size={18} /> : <Volume2 size={18} />}
                            <span>Volume</span>
                        </div>
                        <span className="text-sm text-cyan-200/70 w-12 text-right">{volume}%</span>
                    </div>
                    <input
                        type="range"
                        min="0"
                        max="100"
                        value={volume}
                        onChange={(event) => setVolume(Number(event.target.value))}
                        className="music-volume-slider"
                        aria-label="Volume adjuster"
                    />
                </div>
            </section>
        </motion.div>
    );
}
