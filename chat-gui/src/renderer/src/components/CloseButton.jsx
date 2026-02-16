import React from 'react';
import { X } from 'lucide-react';

const CloseButton = () => {
    const handleClose = () => {
        if (window.electron && window.electron.quit) {
            window.electron.quit();
        } else {
            console.log('Close button clicked (Electron API not available)');
            // Fallback for non-electron environments or if API is missing
            window.close();
        }
    };

    return (
        <button
            onClick={handleClose}
            className="absolute top-4 right-4 z-[9999] w-10 h-10 flex items-center justify-center rounded-full bg-black/20 hover:bg-red-500/80 text-white backdrop-blur-sm transition-all duration-200 border border-white/10"
            aria-label="Close Application"
            title="Close Application"
        >
            <X size={20} />
        </button>
    );
};

export default CloseButton;
