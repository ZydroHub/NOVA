import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, X, ChevronLeft, ChevronRight, MessageSquare } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Gallery() {
    const navigate = useNavigate();
    const [images, setImages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedImageIndex, setSelectedImageIndex] = useState(null);
    const [showChatModal, setShowChatModal] = useState(false);
    const [chatPrompt, setChatPrompt] = useState('');

    const galleryUrl = `http://${window.location.hostname}:8000/gallery/images`;
    const deleteUrl = `http://${window.location.hostname}:8000/gallery/images/`;

    useEffect(() => {
        fetchImages();
    }, []);

    const fetchImages = () => {
        fetch(galleryUrl)
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    setImages(data.images);
                }
                setLoading(false);
            })
            .catch(err => {
                console.error('Failed to load images:', err);
                setLoading(false);
            });
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
            const res = await fetch(`${deleteUrl}${img.filename}`, {
                method: 'DELETE',
            });
            const data = await res.json();
            if (data.status === 'success') {
                const newImages = images.filter((_, i) => i !== selectedImageIndex);
                setImages(newImages);
                if (newImages.length === 0) {
                    closeImage();
                } else if (selectedImageIndex >= newImages.length) {
                    setSelectedImageIndex(newImages.length - 1);
                }
            } else {
                alert('Failed to delete image: ' + data.message);
            }
        } catch (error) {
            console.error('Error deleting image:', error);
            alert('Error deleting image');
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
                <h1 className="ml-4 text-xl font-bold text-slate-800">Gallery</h1>
            </div>

            {/* Grid */}
            <div className="flex-1 overflow-y-auto p-2">
                {loading ? (
                    <div className="flex items-center justify-center h-full text-slate-400">
                        Loading...
                    </div>
                ) : images.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-slate-400">
                        <p>No images found</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-3 gap-2">
                        {images.map((img, index) => (
                            <div
                                key={img.filename}
                                onClick={() => handleImageClick(index)}
                                className="aspect-[9/16] bg-slate-200 rounded-lg overflow-hidden relative group cursor-pointer"
                            >
                                <img
                                    src={`http://${window.location.hostname}:8000${img.url}`}
                                    alt={img.filename}
                                    className="w-full h-full object-cover transition-transform group-hover:scale-105"
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
                        className="absolute inset-0 z-50 bg-black flex flex-col"
                        onClick={closeImage} // Clicking background closes
                    >
                        {/* Top Bar */}
                        <div className="absolute top-4 left-4 right-4 z-50 flex justify-between">
                            <button
                                onClick={closeImage}
                                className="w-10 h-10 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-black/70 backdrop-blur-md"
                            >
                                <X size={24} />
                            </button>
                        </div>

                        {/* Bottom Bar with Chat (Left) */}
                        <div className="absolute bottom-6 left-6 z-50">
                            <button
                                onClick={handleChatClick}
                                className="px-6 py-2 rounded-full bg-blue-500/80 text-white font-medium hover:bg-blue-600/90 backdrop-blur-md shadow-lg transition-transform active:scale-95 uppercase tracking-wide text-sm flex items-center gap-2"
                            >
                                <MessageSquare size={18} />
                                Chat
                            </button>
                        </div>

                        {/* Bottom Bar with Delete */}
                        <div className="absolute bottom-6 right-6 z-50">
                            <button
                                onClick={handleDelete}
                                className="px-6 py-2 rounded-full bg-red-500/80 text-white font-medium hover:bg-red-600/90 backdrop-blur-md shadow-lg transition-transform active:scale-95 uppercase tracking-wide text-sm"
                            >
                                Delete
                            </button>
                        </div>

                        {/* Image Container with Swipe */}
                        <div className="flex-1 flex items-center justify-center relative w-full h-full">
                            {/* Nav Arrows (Desktop/Access) */}
                            {selectedImageIndex > 0 && (
                                <button
                                    onClick={handlePrev}
                                    className="absolute left-4 z-40 w-10 h-10 rounded-full bg-white/20 text-white flex items-center justify-center hover:bg-white/30 backdrop-blur-md"
                                >
                                    <ChevronLeft size={24} />
                                </button>
                            )}
                            {selectedImageIndex < images.length - 1 && (
                                <button
                                    onClick={handleNext}
                                    className="absolute right-4 z-40 w-10 h-10 rounded-full bg-white/20 text-white flex items-center justify-center hover:bg-white/30 backdrop-blur-md"
                                >
                                    <ChevronRight size={24} />
                                </button>
                            )}

                            <motion.img
                                key={images[selectedImageIndex].filename}
                                src={`http://${window.location.hostname}:8000${images[selectedImageIndex].url}`}
                                alt={images[selectedImageIndex].filename}
                                className="max-w-full max-h-full object-contain"
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
                            className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-2xl"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <h3 className="text-lg font-bold text-slate-800 mb-4">Chat about this image</h3>
                            <textarea
                                className="w-full h-32 p-3 bg-slate-100 rounded-lg text-slate-800 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="Ask a question..."
                                value={chatPrompt}
                                onChange={(e) => setChatPrompt(e.target.value)}
                                autoFocus
                            />
                            <div className="flex justify-end gap-3 mt-4">
                                <button
                                    onClick={() => setShowChatModal(false)}
                                    className="px-4 py-2 text-slate-500 hover:text-slate-700 font-medium"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSendToChat}
                                    disabled={!chatPrompt.trim()}
                                    className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    Send
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
