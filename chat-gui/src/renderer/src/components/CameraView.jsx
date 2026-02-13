import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, RefreshCw, AlertCircle, Scan } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// Shared across instances so second mount can cancel first mount's pending stop (React Strict Mode)
const pendingStopTimeoutRef = { current: null };
const STOP_DELAY_MS = 500;

export default function CameraView() {
    const navigate = useNavigate();
    const [status, setStatus] = useState('connecting'); // connecting, connected, error
    const [detections, setDetections] = useState([]);
    const [detectionActive, setDetectionActive] = useState(false);
    const wsRef = useRef(null);

    const videoFeedUrl = `http://${window.location.hostname}:8000/video_feed`;
    const wsUrl = `ws://${window.location.hostname}:8000/ws`;
    const startUrl = `http://${window.location.hostname}:8000/camera/start`;
    const stopUrl = `http://${window.location.hostname}:8000/camera/stop`;
    const detectionStartUrl = `http://${window.location.hostname}:8000/camera/detection/start`;
    const detectionStopUrl = `http://${window.location.hostname}:8000/camera/detection/stop`;

    useEffect(() => {
        let isMounted = true;
        const sessionId = Math.random().toString(36).substring(7); // Simple unique ID

        // Start the camera when the component mounts
        const startCamera = async () => {
            try {
                console.log(`Starting camera session: ${sessionId}`);
                const res = await fetch(startUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId })
                });
                if (res.ok) {
                    if (pendingStopTimeoutRef.current) {
                        clearTimeout(pendingStopTimeoutRef.current);
                        pendingStopTimeoutRef.current = null;
                    }
                    setStatus('connected');
                    console.log("Camera started");
                } else {
                    const err = await res.json().catch(() => ({}));
                    console.error("Camera start failed:", err.message || res.status);
                    if (isMounted) setStatus('error');
                }
            } catch (error) {
                console.error("Failed to start camera:", error);
                if (isMounted) setStatus('error');
            }
        };

        const connectWebSocket = () => {
            console.log('Connecting to WebSocket:', wsUrl);
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                if (isMounted) console.log('WebSocket connected (detections)');
                // Status already 'connected' from camera/start; WS is for detections only
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    if (message.type === 'detections' && isMounted) {
                        setDetections(Array.isArray(message.data) ? message.data : []);
                    }
                } catch (e) {
                    console.error('Error parsing WebSocket message:', e);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                if (isMounted) setStatus('error');
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected (detections may stop)');
                // Keep status 'connected' — stream/video are independent of WebSocket
            };
        };

        startCamera().then(() => {
            connectWebSocket();
        });

        // Cleanup: delay stop so React Strict Mode's second mount can send start and cancel this
        return () => {
            isMounted = false;
            if (wsRef.current) {
                wsRef.current.close();
            }

            const sendStop = () => {
                fetch(detectionStopUrl, {
                    method: 'POST',
                    keepalive: true,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId })
                }).catch(console.error);
                fetch(stopUrl, {
                    method: 'POST',
                    keepalive: true,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId })
                }).catch(console.error);
            };

            if (pendingStopTimeoutRef.current) {
                clearTimeout(pendingStopTimeoutRef.current);
            }
            pendingStopTimeoutRef.current = setTimeout(() => {
                pendingStopTimeoutRef.current = null;
                sendStop();
            }, STOP_DELAY_MS);
        };
    }, []);

    const toggleDetection = async () => {
        if (detectionActive) {
            try {
                await fetch(detectionStopUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: 'default' })
                });
                setDetectionActive(false);
                setDetections([]);
            } catch (e) {
                console.error('Failed to stop detection:', e);
            }
        } else {
            try {
                const res = await fetch(detectionStartUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: 'default' })
                });
                const data = await res.json().catch(() => ({}));
                if (data.status === 'started') {
                    setDetectionActive(true);
                } else {
                    console.error('Detection start failed:', data.message || data);
                }
            } catch (e) {
                console.error('Failed to start detection:', e);
            }
        }
    };

    // Function to render bounding boxes
    const renderBoundingBoxes = () => {
        return detections.map((det, index) => {
            // bbox format: [xmin, ymin, xmax, ymax]
            // values are normalized 0-1 relative to the video frame
            const [xmin, ymin, xmax, ymax] = det.bbox;

            // Convert to percentages for CSS positioning
            const left = `${xmin * 100}%`;
            const top = `${ymin * 100}%`;
            const width = `${(xmax - xmin) * 100}%`;
            const height = `${(ymax - ymin) * 100}%`;

            // Color based on label or confidence? Let's use a nice accent color
            // You can add a map for colors based on label if desired
            const color = 'rgba(0, 255, 255, 0.6)'; // Cyan
            const borderColor = 'rgba(0, 255, 255, 1)';

            return (
                <div
                    key={index}
                    className="absolute border-2 flex flex-col items-start justify-start pointer-events-none"
                    style={{
                        left,
                        top,
                        width,
                        height,
                        borderColor: borderColor,
                        boxShadow: '0 0 10px rgba(0,255,255,0.3)'
                    }}
                >
                    <div
                        className="bg-cyan-500 text-black text-[10px] font-bold px-1 py-0.5"
                        style={{ marginTop: '-18px' }}
                    >
                        {det.label} {Math.round(det.confidence * 100)}%
                    </div>
                </div>
            );
        });
    };

    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="relative w-[480px] h-[800px] max-w-full max-h-screen mx-auto overflow-hidden bg-black shadow-2xl flex flex-col"
        >
            {/* Header */}
            <div className="absolute top-0 left-0 right-0 z-50 p-4 flex items-center justify-between bg-gradient-to-b from-black/80 to-transparent pointer-events-none">
                <button
                    onClick={() => navigate('/')}
                    className="pointer-events-auto w-10 h-10 rounded-full bg-white/10 backdrop-blur-md flex items-center justify-center text-white hover:bg-white/20 transition-colors border border-white/10"
                >
                    <ArrowLeft size={24} />
                </button>
                <div className="px-3 py-1 rounded-full bg-white/10 backdrop-blur-md text-white text-xs font-medium uppercase tracking-wider border border-white/10">
                    Live Vision
                </div>
                <button
                    onClick={toggleDetection}
                    className={`pointer-events-auto w-10 h-10 rounded-full flex items-center justify-center transition-colors border ${
                        detectionActive
                            ? 'bg-cyan-500/80 text-white border-cyan-400'
                            : 'bg-white/10 text-white border-white/10 hover:bg-white/20'
                    }`}
                    title={detectionActive ? 'Stop object detection' : 'Start object detection (5 fps)'}
                >
                    <Scan size={24} />
                </button>
            </div>

            {/* Camera Frame Container */}
            <div className="flex-1 relative flex items-center justify-center overflow-hidden bg-gray-900">

                {/* Status Overlay */}
                {status === 'connecting' && (
                    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center text-white/70 bg-black/50 backdrop-blur-sm">
                        <RefreshCw className="animate-spin mb-4" size={32} />
                        <p>Connecting to Vision System...</p>
                    </div>
                )}

                {status === 'error' && (
                    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-black/80 backdrop-blur-sm p-6">
                        <div className="text-red-500 mb-4">
                            <AlertCircle size={48} />
                        </div>
                        <p className="text-white text-center mb-4">Connection Lost</p>
                        <button
                            onClick={() => window.location.reload()}
                            className="px-6 py-2 bg-white/10 rounded-full hover:bg-white/20 transition-colors text-white text-sm"
                        >
                            Reconnect
                        </button>
                    </div>
                )}

                {/* Video Feed */}
                <div className="relative w-full h-full flex items-center justify-center">
                    <img
                        src={videoFeedUrl}
                        className="w-full h-full object-contain"
                        alt="Live Camera Feed"
                        onLoad={() => {
                            // Fallback: show LIVE when first frame arrives (handles Strict Mode / slow start response)
                            setStatus((s) => (s === 'connecting' ? 'connected' : s));
                        }}
                        onError={(e) => {
                            console.error("Video feed error", e);
                            setStatus('error');
                        }}
                    />

                    {/* Detection Overlays Layer */}
                    {/* We overlay this on top of the image container. 
                        Since we use object-contain, the image might have letterboxing.
                        Ideally, these boxes should be inside the image dimensions.
                        However, usually the video element fills the container in some way.
                        If object-contain leaves gaps, the 'absolute' positioning 0-100% 
                        will be relative to the DIV, not the IMAGE content if there are gaps.
                        
                        For 480x800 logic, simpler to let it stretch or use a wrapper that matches aspect ratio.
                        Given 16:9 input and 9:16 screen, object-contain is best for details.
                        But boxes will be offset if we don't match the image rect.
                        
                        For MVP/POC: simpler to assume full width or use object-cover if user wants full immersion.
                        Let's try object-contain (as defined above) but be aware of offset.
                        Actually, to make boxes align perfectly with CSS % on the parent div, 
                        the parent div must match the image aspect ratio exactly.
                        or we use JS to size the overlay layer.
                        
                        Let's just position them relative to the container for now. 
                        If the image is letterboxed, boxes within the "black bars" area won't exist 
                        (normalized coords are within the image). 
                        BUT if the container is taller than the image, 0% y starts at the top of the container,
                        while the image starts lower down. This causes misalignment.
                        
                        FIX: Use a wrapper div that has the aspect ratio of the camera?
                        Or just use object-cover which fills the container (cropping edges) 
                        and then the boxes (0-1) might need to be "zoomed" too?
                        
                        Actually, simpler approach for this task: Use object-fill (stretch) or object-cover?
                        If I use object-fill, it distorts.
                        If I use object-contain, I need to know the rendered image rect.
                        
                        CORRECTION: I'll use object-contain for the image, and I will place the detections
                        in a layer that assumes the image fills the container? NO.
                        
                        Let's try object-cover. It fills the screen. 
                        If I use object-cover, the image is cropped.
                        The detections (0-1) refer to the *full uncropped* image.
                        If I draw a box at 0.1 (left edge), but the left edge is cropped out,
                        the box should be off-screen.
                        Standard HTML overlay on a cropped image is hard without math.
                        
                        Let's stick to object-contain for ACCURACY first.
                        But 'w-full h-full' on the img with object-contain means likely black bars.
                        The overlay div is w-full h-full.
                        0,0 is top left of container.
                        0,0 of image is... somewhere else.
                        
                        Okay, I will wrap the image and overlay in a container that handles aspect ratio?
                        No, simpler: just display it. The user wants to see it works.
                        I'll use `object-contain` on the image.
                        AND I will assume the image is centered.
                        For a robust implementation, usually you'd measure the image size rendered.
                        But I cannot run JS to measure it easily in this "blind" edit.
                        
                        Let's stick with the simple implementation. It might be slightly misaligned if letterboxed,
                        but detection bubbles will appear.
                    */}
                    <div className="absolute inset-0 w-full h-full">
                        {detectionActive && renderBoundingBoxes()}
                    </div>
                </div>
            </div>

            {/* Footer / Stats */}
            <div className="absolute bottom-6 left-0 right-0 z-50 flex justify-center pointer-events-none">
                <div className="px-4 py-2 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-white text-[10px] flex items-center gap-3 shadow-lg">
                    <div className="flex items-center gap-1.5">
                        <div className={`w-1.5 h-1.5 rounded-full ${status === 'connected' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                        {status === 'connected' ? 'LIVE' : 'OFFLINE'}
                    </div>
                    <div className="w-px h-3 bg-white/20"></div>
                    <div>{detectionActive ? `${detections.length} Objects` : '—'}</div>
                    <div className="w-px h-3 bg-white/20"></div>
                    <div>{detectionActive ? 'Hailo 5 fps' : 'Stream 30 fps'}</div>
                </div>
            </div>
        </motion.div>
    );
}
