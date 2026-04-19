import React, { useEffect, useRef, useState } from 'react';
import { HashRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import Home from './components/Home';
import ChatInterface from './components/ChatInterface';
import SideNav from './components/SideNav';
import MusicPage from './components/MusicPage';
import NewsPage from './components/NewsPage';
import WeatherPage from './components/WeatherPage';
import Settings from './components/Settings';
import StatusBar from './components/StatusBar';
import TaskManager from './components/TaskManager';
import TaskAdd from './components/TaskAdd';
import HeartbeatManager from './components/HeartbeatManager';
import GPIOControl from './components/GPIOControl';
import ErrorBoundary from './components/ErrorBoundary';
import VirtualKeyboard from './components/VirtualKeyboard';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { KeyboardProvider, useKeyboardSettings } from './contexts/KeyboardContext';

// HashRouter so routes work when the app is loaded from file:// (built Electron app)

function OverlayKeyboard() {
  const location = useLocation();
  const { keyboardEnabled, focusState, focusedElementRef, syncInputValueRef } = useKeyboardSettings();
  const isOnChatRoute = location.pathname === '/chat';
  const isOnTasksRoute = location.pathname.startsWith('/tasks');
  const show = keyboardEnabled && focusState && (!isOnChatRoute || !focusState.isChatInput) && !isOnTasksRoute;
  return <VirtualKeyboard visible={show} mode="overlay" focusedElementRef={focusedElementRef} syncInputValueRef={syncInputValueRef} />;
}

const AnimatedRoutes = () => {
  const location = useLocation();
  const [swipeDirection, setSwipeDirection] = React.useState(0);
  const [scrollStart, setScrollStart] = React.useState(0);
  const navigate = useNavigate();

  const routes = ['/', '/chat', '/music', '/news', '/weather', '/tasks', '/settings'];
  const currentIndex = routes.indexOf(location.pathname);

  const handleWheel = (e) => {
    // Only horizontal scroll detection
    if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
      e.preventDefault();
      if (e.deltaX > 50 && currentIndex < routes.length - 1) {
        navigate(routes[currentIndex + 1]);
      } else if (e.deltaX < -50 && currentIndex > 0) {
        navigate(routes[currentIndex - 1]);
      }
    }
  };

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, x: swipeDirection * 100 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -swipeDirection * 100 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        onDragEnd={(e, info) => {
          if (Math.abs(info.offset.x) > 50) {
            const direction = info.offset.x > 0 ? -1 : 1;
            setSwipeDirection(direction);
            const nextIndex = currentIndex + direction;
            if (nextIndex >= 0 && nextIndex < routes.length) {
              navigate(routes[nextIndex]);
            }
          }
        }}
        drag="x"
        dragConstraints={{ left: 0, right: 0 }}
        dragElastic={0.2}
        onWheel={handleWheel}
        style={{ cursor: 'grab' }}
      >
        <Routes location={location}>
          <Route path="/" element={<Home />} />
          <Route path="/chat" element={<ChatInterface />} />
          <Route path="/music" element={<MusicPage />} />
          <Route path="/news" element={<NewsPage />} />
          <Route path="/weather" element={<WeatherPage />} />
          <Route path="/tasks" element={<TaskManager />} />
          <Route path="/tasks/add" element={<TaskAdd />} />
          <Route path="/tasks/edit" element={<TaskAdd />} />
          <Route path="/heartbeat" element={<HeartbeatManager />} />
          <Route path="/gpio" element={<GPIOControl />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
};

function RandomScanlineOverlay() {
  const [active, setActive] = useState(false);
  const delayRef = useRef(null);
  const burstRef = useRef(null);

  useEffect(() => {
    const triggerBurst = () => {
      setActive(true);
      burstRef.current = setTimeout(() => {
        setActive(false);
        scheduleNext();
      }, 8000);
    };

    const scheduleNext = () => {
      const nextDelayMs = (20 + Math.random() * 10) * 1000;
      delayRef.current = setTimeout(triggerBurst, nextDelayMs);
    };

    // Show a first pulse quickly so users can verify the feature is working.
    delayRef.current = setTimeout(triggerBurst, 1200);

    return () => {
      if (delayRef.current) clearTimeout(delayRef.current);
      if (burstRef.current) clearTimeout(burstRef.current);
    };
  }, []);

  return (
    <>
      <div className={`scanline-overlay ${active ? 'active' : ''}`} />
      <div className={`scanline-sweep ${active ? 'active' : ''}`} />
    </>
  );
}

export default function App() {
  return (
    <HashRouter>
      <WebSocketProvider>
        <KeyboardProvider>
          <div className="flex flex-col h-screen w-screen overflow-hidden bg-[var(--nova-bg)] text-[var(--nova-text)]">
            <StatusBar />
            <div className="flex-1 overflow-hidden relative w-full flex">
              {/* CRT scanline overlay only for the route content area */}
              <RandomScanlineOverlay />
              <SideNav />
              <ErrorBoundary>
                <div className="flex-1 min-w-0 min-h-0">
                  <AnimatedRoutes />
                </div>
              </ErrorBoundary>
            </div>
            <OverlayKeyboard />
          </div>
        </KeyboardProvider>
      </WebSocketProvider>
    </HashRouter>
  );
}
