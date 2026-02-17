import React from 'react';
import { motion } from 'framer-motion';

export default function Avatar({
    className = "",
    variant = "lg", // 'sm' | 'lg'
    onClick,
    animate = true
}) {
    // Defines size constants for each variant
    const styles = {
        sm: {
            size: "w-9 h-9",
            gapConfig: "gap-1 mt-1",
            eyeGap: "gap-1.5",
            eyeSize: "w-2 h-2",
            mouthSize: "w-3 h-0.5 border-b-[1.5px]"
        },
        lg: {
            // Reduced from w-48 h-48 to w-32 h-32 as requested
            size: "w-32 h-32",
            gapConfig: "gap-3 mt-3", // Scaled down from gap-5 mt-4
            eyeGap: "gap-5",          // Scaled down from gap-8
            eyeSize: "w-6 h-6",       // Scaled down from w-10 h-10
            mouthSize: "w-4 h-2 border-b-[2px]" // Scaled down
        }
    };

    const currentStyle = styles[variant] || styles.lg;

    // Allow overriding width/height via className if needed, but default to variant size
    const containerClasses = `relative bg-white rounded-[40px] flex items-center justify-center ${currentStyle.size} shadow-[0_8px_40px_rgba(0,149,255,0.15)] border border-blue-100 ${onClick ? 'cursor-pointer' : ''} ${className}`;

    // Eye animation variants
    const eyeVariants = {
        blink: {
            scaleY: [1, 0.1, 1],
            transition: {
                duration: 0.25,
                repeat: Infinity,
                repeatDelay: 3.5
            }
        },
        static: {
            scaleY: 1
        }
    };

    // Head container animation (The square/circle itself moves)
    const headVariants = {
        lookAround: {
            x: ["0%", "5%", "0%", "-5%", "0%", "0%", "0%", "3%", "0%"],
            y: ["0%", "-2%", "0%", "2%", "0%", "0%", "-2%", "0%", "0%"],
            rotate: [0, 5, 0, -5, 0, 0, 0, 3, 0],
            transition: {
                x: { duration: 5, repeat: Infinity, repeatDelay: 5, ease: "easeInOut" },
                y: { duration: 5, repeat: Infinity, repeatDelay: 5, ease: "easeInOut" },
                rotate: { duration: 5, repeat: Infinity, repeatDelay: 5, ease: "easeInOut" },
                opacity: { duration: 0.5 },
                scale: { duration: 0.5 }
            },
            opacity: 1,
            scale: 1
        },
        static: {
            x: 0,
            y: 0,
            rotate: 0,
            opacity: 1,
            scale: 1
        }
    };

    // Face features animation (Eyes/Mouth move MORE to simulate 3D depth/parallax)
    const faceVariants = {
        lookAround: {
            x: ["0%", "15%", "0%", "-15%", "0%", "0%", "0%", "8%", "0%"],
            y: ["0%", "-8%", "0%", "8%", "0%", "0%", "-8%", "0%", "0%"],
            transition: {
                duration: 5,
                repeat: Infinity,
                repeatDelay: 5,
                ease: "easeInOut"
            }
        },
        static: {
            x: 0,
            y: 0
        }
    };

    return (
        <motion.div
            className={containerClasses}
            onClick={onClick}
            whileHover={onClick ? { scale: 1.05, boxShadow: "0 12px 50px rgba(0,149,255,0.2)" } : {}}
            whileTap={onClick ? { scale: 0.95 } : {}}
            initial={animate ? { opacity: 0, scale: 0.5 } : {}}
            animate={animate ? "lookAround" : "static"} // Animate head container
            variants={headVariants}
            transition={{ duration: 0.5 }}
        >
            {/* Face Container */}
            <motion.div
                className={`flex flex-col items-center justify-center ${currentStyle.gapConfig}`}
                variants={faceVariants}
                animate={animate ? "lookAround" : "static"}
            >
                {/* Eyes */}
                <div className={`flex ${currentStyle.eyeGap}`}>
                    <motion.div
                        className={`${currentStyle.eyeSize} bg-cyan-400 rounded-full shadow-[0_0_15px_rgba(34,211,238,0.6)]`}
                        variants={eyeVariants}
                        animate={animate ? "blink" : "static"}
                    />
                    <motion.div
                        className={`${currentStyle.eyeSize} bg-cyan-400 rounded-full shadow-[0_0_15px_rgba(34,211,238,0.6)]`}
                        variants={eyeVariants}
                        animate={animate ? "blink" : "static"}
                    />
                </div>

                {/* Mouth */}
                <div className={`${currentStyle.mouthSize} border-slate-700/30 rounded-full`} />
            </motion.div>
        </motion.div>
    );
}
