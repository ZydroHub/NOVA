import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, X, ChevronLeft, ChevronRight, MessageSquare } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../config.js';
import { apiFetch } from '../apiClient.js';
import { useFocusableInput } from '../contexts/KeyboardContext.jsx';
import LoadingSpinner from './LoadingSpinner';
import ErrorMessage from './ErrorMessage';

export default function Gallery() {
    const { onFocus: onKeyboardFocus, onBlur: onKeyboardBlur } = useFocusableInput(false);
    const navigate = useNavigate();
    const [images, setImages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedImageIndex, setSelectedImageIndex] = useState(null);
    const [showChatModal, setShowChatModal] = useState(false);
    const [chatPrompt, setChatPrompt] = useState('');

    useEffect(() => {
        fetchImages();
    }, []);

    const fetchImages = async () => {
        setError(null);
        try {
            const data = await apiFetch('/gallery/images');
            if (data.status === 'success') {
                setImages(data.images || []);
            }
        } catch (err) {
            setError(err?.message || 'Failed to load images');
            console.error('Failed to load images:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleImageClick = (index) => {
        setSelectedImageIndex(index);
    };

    const closeImage = () => {
        setSelectedImageIndex(null);
        setShowChatModal(false);
        setChatPrompt('');
    };

    const handleDelete = async (e) => {
        e.stopPropagation();
        if (selectedImageIndex === null) return;

        const img = images[selectedImageIndex];
        if (!confirm('Are you sure you want to delete this image?')) return;

        try {
            setError(null);
            const data = await apiFetch(`/gallery/images/${img.filename}`, { method: 'DELETE' });
            if (data.status === 'success') {
                const newImages = images.filter((_, i) => i !== selectedImageIndex);
                setImages(newImages);
                if (newImages.length === 0) {
                    closeImage();
                } else if (selectedImageIndex >= newImages.length) {
                    setSelectedImageIndex(newImages.length - 1);
                }
            } else {
                setError(data.message || 'Failed to delete image');
            }
        } catch (err) {
            setError(err?.message || 'Error deleting image');
            console.error('Error deleting image:', err);
        }
    };

    const handleChatClick = (e) => {
        e.stopPropagation();
        setShowChatModal(true);
    };

    const handleSendToChat = () => {
        if (!chatPrompt.trim()) return;

        const img = images[selectedImageIndex];
        navigate('/chat', {
            state: {
                prompt: chatPrompt,
                image: img.filename
            }
        });
    };

    const handleNext = (e) => {
        e && e.stopPropagation();
        if (selectedImageIndex !== null && selectedImageIndex < images.length - 1) {
            setSelectedImageIndex(selectedImageIndex + 1);
        }
    };

    const handlePrev = (e) => {
        e && e.stopPropagation();
        if (selectedImageIndex !== null && selectedImageIndex > 0) {
            setSelectedImageIndex(selectedImageIndex - 1);
        }
    };

    // Swipe detection
    const swipeConfidenceThreshold = 10000;
    const swipePower = (offset, velocity) => {
        return Math.abs(offset) * velocity;
    };

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="relative w-full h-full max-w-full mx-auto overflow-hidden bg-[var(--pixel-bg)] flex flex-col"
        >
            {/* Header */}
            <div className="p-4 z-10 flex justify-between items-center bg-[var(--pixel-surface)] border-b-4 border-[var(--pixel-border)]">
                <button
                    onClick={() => navigate('/')}
                    className="pixel-btn p-3 flex items-center justify-center"
                >
                    <ArrowLeft size={24} />
                </button>
                <h1 className="text-xl font-['Press_Start_2P'] text-[var(--pixel-primary)]">GALLERY</h1>
                <div className="w-12"></div> {/* Spacer for centering */}
            </div>

            {error && (
                <ErrorMessage message={error} onRetry={() => { setError(null); fetchImages(); }} />
            )}

            {/* Grid */}
            <div className="flex-1 min-h-0 overflow-y-auto p-4 scroller-pixel touch-scroll-y">
                {loading ? (
                    <LoadingSpinner label="LOADING..." className="h-full" />
                ) : images.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-[var(--pixel-secondary)] font-['VT323'] text-xl">
                        <p>NO IMAGES FOUND_</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-3 gap-3">
                        {images.map((img, index) => (
                            <div
                                key={img.filename}
                                onClick={() => handleImageClick(index)}
                                className="aspect-[9/16] bg-[var(--pixel-surface)] border-2 border-[var(--pixel-border)] relative cursor-pointer hover:border-[var(--pixel-primary)] transition-colors"
                            >
                                <img
                                    src={`${API_BASE_URL}${img.url}`}
                                    alt={img.filename}
                                    className="w-full h-full object-cover pixelated"
                                    loading="lazy"
                                />
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Modal */}
            <AnimatePresence>
                {selectedImageIndex !== null && images[selectedImageIndex] && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute inset-0 z-50 bg-black/90 flex flex-col"
                        onClick={closeImage} // Clicking background closes
                    >
                        {/* Top Bar */}
                        <div className="absolute top-4 left-4 right-4 z-50 flex justify-between">
                            <button
                                onClick={closeImage}
                                className="pixel-btn flex items-center justify-center p-2 bg-red-500 hover:bg-red-600 text-white border-white"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        {/* Bottom Bar with Chat (Left) */}
                        <div className="absolute bottom-6 left-6 z-50">
                            <button
                                onClick={handleChatClick}
                                className="pixel-btn flex items-center gap-2 bg-[var(--pixel-primary)] text-black"
                            >
                                <MessageSquare size={16} />
                                CHAT
                            </button>
                        </div>

                        {/* Bottom Bar with Delete */}
                        <div className="absolute bottom-6 right-6 z-50">
                            <button
                                onClick={handleDelete}
                                className="pixel-btn bg-red-500 text-white hover:bg-red-600 border-white"
                            >
                                DELETE
                            </button>
                        </div>

                        {/* Image Container with Swipe */}
                        <div className="flex-1 flex items-center justify-center relative w-full h-full p-8">
                            {/* Nav Arrows (Desktop/Access) */}
                            {selectedImageIndex > 0 && (
                                <button
                                    onClick={handlePrev}
                                    className="absolute left-4 z-40 pixel-btn p-2"
                                >
                                    <ChevronLeft size={20} />
                                </button>
                            )}
                            {selectedImageIndex < images.length - 1 && (
                                <button
                                    onClick={handleNext}
                                    className="absolute right-4 z-40 pixel-btn p-2"
                                >
                                    <ChevronRight size={20} />
                                </button>
                            )}

                            <motion.img
                                key={images[selectedImageIndex].filename}
                                src={`${API_BASE_URL}${images[selectedImageIndex].url}`}
                                alt={images[selectedImageIndex].filename}
                                className="max-w-full max-h-full object-contain border-4 border-[var(--pixel-border)] bg-[var(--pixel-bg)] shadow-[8px_8px_0_0_rgba(255,255,255,0.2)]"
                                initial={{ x: 300, opacity: 0 }}
                                animate={{ x: 0, opacity: 1 }}
                                exit={{ x: -300, opacity: 0 }}
                                drag="x"
                                dragConstraints={{ left: 0, right: 0 }}
                                dragElastic={0.2}
                                onDragEnd={(e, { offset, velocity }) => {
                                    const swipe = swipePower(offset.x, velocity.x);

                                    if (swipe < -swipeConfidenceThreshold) {
                                        handleNext();
                                    } else if (swipe > swipeConfidenceThreshold) {
                                        handlePrev();
                                    }
                                }}
                                onClick={(e) => e.stopPropagation()} // Prevent close on image click
                            />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Chat Modal */}
            <AnimatePresence>
                {showChatModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute inset-0 z-[60] bg-black/80 flex items-center justify-center p-6"
                        onClick={() => setShowChatModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, y: 20 }}
                            animate={{ scale: 1, y: 0 }}
                            exit={{ scale: 0.9, y: 20 }}
                            className="bg-[var(--pixel-surface)] border-4 border-[var(--pixel-border)] p-6 w-full max-w-sm shadow-[8px_8px_0_0_rgba(0,0,0,1)]"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <h3 className="text-sm font-['Press_Start_2P'] text-[var(--pixel-primary)] mb-4 uppercase leading-relaxed">QUERY IMAGE DATA</h3>
                            <textarea
                                className="w-full h-32 p-3 bg-[var(--pixel-bg)] border-2 border-[var(--pixel-border)] text-[var(--pixel-text)] font-['VT323'] text-xl resize-none focus:outline-none focus:border-[var(--pixel-primary)]"
                                placeholder="INPUT QUERY..."
                                value={chatPrompt}
                                onChange={(e) => setChatPrompt(e.target.value)}
                                onFocus={onKeyboardFocus}
                                onBlur={onKeyboardBlur}
                                autoFocus
                            />
                            <div className="flex justify-end gap-4 mt-6">
                                <button
                                    onClick={() => setShowChatModal(false)}
                                    className="pixel-btn bg-[var(--pixel-surface)] text-[var(--pixel-text)]"
                                >
                                    CANCEL
                                </button>
                                <button
                                    onClick={handleSendToChat}
                                    disabled={!chatPrompt.trim()}
                                    className="pixel-btn bg-[var(--pixel-primary)] text-black disabled:opacity-50"
                                >
                                    SEND
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
