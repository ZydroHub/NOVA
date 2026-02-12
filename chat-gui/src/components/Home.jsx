import React from 'react';
import { motion } from 'framer-motion';
import { MessageCircle, Settings, Camera, Music, Video, Map as MapIcon } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Orbiter = ({ icon: Icon, radius, duration, initialAngle }) => {
    return (
        <motion.div
            className="absolute top-1/2 left-1/2 w-0 h-0 z-10"
            initial={{ rotate: initialAngle }}
            animate={{ rotate: initialAngle + 360 }}
            transition={{
                duration: duration,
                ease: 'linear',
                repeat: Infinity,
            }}
        >
            <div style={{ transform: `translate(${radius}px, -50%)` }}>
                <motion.div
                    animate={{ rotate: -(initialAngle + 360) }}
                    initial={{ rotate: -initialAngle }}
                    transition={{
                        duration: duration,
                        ease: 'linear',
                        repeat: Infinity,
                    }}
                >
                    <div className="p-4 bg-white/20 backdrop-blur-md rounded-2xl text-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.3)] border border-white/10 cursor-pointer hover:bg-white/30 transition-colors">
                        <Icon size={28} />
                    </div>
                </motion.div>
            </div>
        </motion.div>
    );
};

export default function Home() {
    const navigate = useNavigate();

    const handleAvatarClick = () => {
        navigate('/chat');
    };

    return (
        <div className="relative w-screen h-screen overflow-hidden bg-slate-900">
            {/* Background Gradient */}
            <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 z-0" />

            {/* Orbitals Layer */}
            <div className="absolute inset-0 z-10 pointer-events-none">
                <div className="w-full h-full relative">
                    <Orbiter icon={MessageCircle} radius={140} duration={25} initialAngle={0} />
                    <Orbiter icon={Camera} radius={140} duration={25} initialAngle={120} />
                    <Orbiter icon={Music} radius={140} duration={25} initialAngle={240} />

                    <Orbiter icon={Settings} radius={220} duration={35} initialAngle={60} />
                    <Orbiter icon={Video} radius={220} duration={35} initialAngle={180} />
                    <Orbiter icon={MapIcon} radius={220} duration={35} initialAngle={300} />
                </div>
            </div>

            {/* Avatar Layer - Centered absolutely on top */}
            <div className="absolute inset-0 z-50 flex items-center justify-center pointer-events-none">
                <motion.div
                    className="relative bg-cyan-500 rounded-full flex items-center justify-center w-48 h-48 shadow-[0_0_60px_rgba(6,182,212,0.8)] border-4 border-cyan-300/50 cursor-pointer pointer-events-auto"
                    onClick={handleAvatarClick}
                    whileHover={{ scale: 1.1, boxShadow: "0 0 80px rgba(6,182,212,1)" }}
                    whileTap={{ scale: 0.95 }}
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5 }}
                >
                    {/* Face Container */}
                    <motion.div
                        className="flex flex-col items-center gap-4 pointer-events-none"
                        initial={{ x: 0, y: 0 }}
                        animate={{
                            x: [0, -8, 8, 0, 0],
                            y: [0, -4, 4, 0, 0],
                        }}
                        transition={{
                            duration: 5,
                            repeat: Infinity,
                            repeatDelay: 2,
                            ease: "easeInOut"
                        }}
                    >
                        {/* Eyes */}
                        <div className="flex gap-6">
                            <div className="w-8 h-8 bg-white rounded-full relative shadow-inner">
                                <motion.div
                                    className="w-3 h-3 bg-slate-900 rounded-full absolute top-2 left-2"
                                    animate={{
                                        x: [0, 3, -3, 0],
                                        y: [0, 2, -2, 0]
                                    }}
                                    transition={{
                                        duration: 4,
                                        repeat: Infinity,
                                        repeatDelay: 1
                                    }}
                                />
                            </div>
                            <div className="w-8 h-8 bg-white rounded-full relative shadow-inner">
                                <motion.div
                                    className="w-3 h-3 bg-slate-900 rounded-full absolute top-2 left-2"
                                    animate={{
                                        x: [0, 3, -3, 0],
                                        y: [0, 2, -2, 0]
                                    }}
                                    transition={{
                                        duration: 4,
                                        repeat: Infinity,
                                        repeatDelay: 1
                                    }}
                                />
                            </div>
                        </div>
                        {/* Smile */}
                        <div className="w-16 h-8 border-b-[6px] border-white rounded-full" />
                    </motion.div>

                    {/* Tap Hint */}
                    <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 text-cyan-400 text-sm font-medium tracking-wider animate-pulse whitespace-nowrap">
                        TAP TO CHAT
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
