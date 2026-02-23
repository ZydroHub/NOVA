import React, { useState } from 'react';
import { Pencil, Trash2, Check, X, Plus } from 'lucide-react';
import { useWebSocket } from '../contexts/WebSocketContext.jsx';

export default function ChatSidebar({ isOpen, onClose }) {
    const {
        conversations,
        currentConvId,
        setCurrentConvId,
        createConversation,
        deleteConversation,
        renameConversation
    } = useWebSocket();

    const [editingId, setEditingId] = useState(null);
    const [editTitle, setEditTitle] = useState('');

    const handleNewChat = async () => {
        const conv = await createConversation();
        if (conv) {
            setCurrentConvId(conv.id);
            onClose(); // Close sidebar on mobile/small screens if needed, but here we just follow user request
        }
    };

    const startEditing = (e, conv) => {
        e.stopPropagation();
        setEditingId(conv.id);
        setEditTitle(conv.title || "Untitled Chat");
    };

    const cancelEditing = (e) => {
        e.stopPropagation();
        setEditingId(null);
        setEditTitle('');
    };

    const saveRename = async (e, id) => {
        e.stopPropagation();
        if (editTitle.strip()) {
            await renameConversation(id, editTitle.strip());
        }
        setEditingId(null);
        setEditTitle('');
    };

    return (
        <>
            {/* Backdrop for overlay effect */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-40 lg:hidden"
                    onClick={onClose}
                />
            )}

            {/* Sidebar Overlay */}
            <aside
                className={`fixed top-20 left-0 bottom-0 z-50 bg-[var(--pixel-surface)] border-r-4 border-[var(--pixel-border)] transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : '-translate-x-full'} w-72 flex flex-col`}
            >
                <div className="p-4 border-b-4 border-[var(--pixel-border)] flex flex-col gap-2">
                    <button
                        onClick={handleNewChat}
                        className="pixel-btn w-full py-3 bg-[var(--pixel-primary)] text-white text-[10px] font-['Press_Start_2P'] flex items-center justify-center gap-2"
                    >
                        <Plus size={16} /> NEW CHAT
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-2 custom-scrollbar">
                    {conversations.map(conv => (
                        <div
                            key={conv.id}
                            className={`p-3 border-2 border-[var(--pixel-border)] cursor-pointer hover:bg-[var(--pixel-bg-alt)] relative group flex items-center justify-between gap-2 ${currentConvId === conv.id ? 'bg-[var(--pixel-bg-alt)] border-[var(--pixel-primary)]' : ''}`}
                            onClick={() => { setCurrentConvId(conv.id); }}
                        >
                            {editingId === conv.id ? (
                                <div className="flex items-center gap-1 w-full" onClick={e => e.stopPropagation()}>
                                    <input
                                        type="text"
                                        className="bg-[var(--pixel-bg)] text-xs font-['VT323'] border-2 border-[var(--pixel-border)] px-1 py-0.5 w-full focus:outline-none"
                                        value={editTitle}
                                        onChange={e => setEditTitle(e.target.value)}
                                        onKeyDown={e => {
                                            if (e.key === 'Enter') saveRename(e, conv.id);
                                            if (e.key === 'Escape') cancelEditing(e);
                                        }}
                                        autoFocus
                                    />
                                    <button onClick={e => saveRename(e, conv.id)} className="text-green-500 hover:text-green-400">
                                        <Check size={14} />
                                    </button>
                                    <button onClick={e => cancelEditing(e)} className="text-red-500 hover:text-red-400">
                                        <X size={14} />
                                    </button>
                                </div>
                            ) : (
                                <>
                                    <div className="text-xs font-['VT323'] truncate flex-1">{conv.title || "Untitled Chat"}</div>
                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            onClick={(e) => startEditing(e, conv)}
                                            className="p-1 hover:text-[var(--pixel-primary)] transition-colors"
                                            title="Rename"
                                        >
                                            <Pencil size={14} />
                                        </button>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); deleteConversation(conv.id); }}
                                            className="p-1 hover:text-red-500 transition-colors"
                                            title="Delete"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>
                    ))}
                </div>
            </aside>

            <style>{`
                .custom-scrollbar::-webkit-scrollbar {
                    width: 6px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: transparent;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: var(--pixel-border);
                    border-radius: 3px;
                }
            `}</style>
        </>
    );
}
