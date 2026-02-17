import React from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Power } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Settings() {
    const navigate = useNavigate();

    const handleCloseApp = () => {
        if (window.electron && window.electron.quit) {
            window.electron.quit();
        } else {
            console.log('Close button clicked (Electron API not available)');
            window.close();
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, type: "spring" }}
            className="relative w-[480px] h-full max-w-full mx-auto overflow-hidden bg-slate-50 shadow-2xl flex flex-col"
        >
            {/* Header */}
            <div className="flex items-center p-4 bg-white shadow-sm z-10">
                <button
                    onClick={() => navigate('/')}
                    className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 hover:bg-slate-200 transition-colors"
                >
                    <ArrowLeft size={24} />
                </button>
                <h1 className="ml-4 text-xl font-bold text-slate-800">Settings</h1>
            </div>

            {/* Content */}
            <div className="flex-1 p-6 flex flex-col items-center justify-center space-y-8">
                <div className="text-center">
                    <h2 className="text-2xl font-bold text-slate-800 mb-2">Application Settings</h2>
                    <p className="text-slate-500">Manage your application preferences</p>
                </div>

                <button
                    onClick={handleCloseApp}
                    className="w-full max-w-xs py-4 px-6 bg-red-500 text-white rounded-xl shadow-lg hover:bg-red-600 transition-colors flex items-center justify-center space-x-3 active:scale-95"
                >
                    <Power size={24} />
                    <span className="text-lg font-medium">Close Application</span>
                </button>

                <div className="text-xs text-slate-400 mt-auto pt-12">
                    Version 1.0.0
                </div>
            </div>
        </motion.div>
    );
}
