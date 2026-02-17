import React from 'react';
import { motion } from 'framer-motion';
import { MessageCircle, Settings, Camera, Music, Video, Image as GalleryIcon, Clock, Activity, Cpu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Avatar from './Avatar';

const Orbiter = ({ icon: Icon, radius, duration, initialAngle, delay = 0, onClick }) => {
    // Calculate static position based on angle and radius
    const radian = (initialAngle * Math.PI) / 180;
    const x = Math.cos(radian) * radius;
    const y = Math.sin(radian) * radius;

    return (
        <motion.div
            className="absolute top-1/2 left-1/2 w-0 h-0 z-10 pointer-events-none"
            initial={{ x, y }}
            animate={{
                y: [y - 8, y + 8, y - 8],
            }}
            transition={{
                duration: 4,
                ease: 'easeInOut',
                repeat: Infinity,
                delay: delay,
            }}
        >
            <div className="-translate-x-1/2 -translate-y-1/2 absolute top-1/2 left-1/2 pointer-events-auto">
                <div
                    onClick={onClick}
                    className="w-24 h-24 bg-white/80 backdrop-blur-md rounded-3xl text-blue-500 shadow-[0_4px_20px_rgba(0,0,0,0.08)] border border-slate-100 cursor-pointer hover:scale-110 transition-transform flex items-center justify-center active:bg-blue-50"
                >
                    <Icon size={36} />
                </div>
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
        <div className="relative w-[480px] h-full mx-auto overflow-hidden bg-white shadow-2xl">
            {/* Background Gradient - Light Theme */}
            <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-slate-50 to-indigo-50 z-0" />

            {/* Decorative circles */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-200/20 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-200/20 rounded-full blur-3xl pointer-events-none" />

            {/* Settings Button - Top Left */}
            <div className="absolute top-6 left-6 z-20">
                <button
                    onClick={() => navigate('/settings')}
                    className="w-16 h-16 bg-white/60 backdrop-blur-md rounded-2xl text-slate-500 shadow-sm border border-slate-100 hover:bg-white hover:scale-105 active:scale-95 transition-all flex items-center justify-center"
                >
                    <Settings size={32} />
                </button>
            </div>

            {/* Icons Layer - Floating */}
            <div className="absolute inset-0 z-10 pointer-events-none">
                <div className="w-full h-full relative flex items-center justify-center">
                    <Orbiter
                        icon={MessageCircle} radius={150} initialAngle={270} delay={0}
                        onClick={() => navigate('/chat')}
                    />
                    <Orbiter
                        icon={Camera} radius={150} initialAngle={330} delay={0.1}
                        onClick={() => navigate('/camera')}
                    />
                    <Orbiter
                        icon={Activity} radius={150} initialAngle={30} delay={0.2}
                        onClick={() => navigate('/heartbeat')}
                    />
                    <Orbiter
                        icon={Cpu} radius={150} initialAngle={90} delay={0.3}
                        onClick={() => navigate('/gpio')}
                    />
                    <Orbiter
                        icon={Clock} radius={150} initialAngle={150} delay={0.4}
                        onClick={() => navigate('/cron')}
                    />
                    <Orbiter
                        icon={GalleryIcon} radius={150} initialAngle={210} delay={0.5}
                        onClick={() => navigate('/gallery')}
                    />
                </div>
            </div>

            {/* Avatar Layer - Centered */}
            <div className="absolute inset-0 z-50 flex items-center justify-center pointer-events-none">
                <div className="pointer-events-auto relative">
                    <Avatar
                        onClick={handleAvatarClick}
                        variant="lg"
                        animate={true}
                    />
                </div>
            </div>
        </div>
    );
}
