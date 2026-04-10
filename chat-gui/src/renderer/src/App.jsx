import React, { useEffect, useRef, useState } from 'react';
import { HashRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import Home from './components/Home';
import ChatInterface from './components/ChatInterface';
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

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Home />} />
        <Route
          path="/chat"
          element={<ChatInterface />}
        />
        <Route path="/tasks" element={<TaskManager />} />
        <Route path="/tasks/add" element={<TaskAdd />} />
        <Route path="/tasks/edit" element={<TaskAdd />} />
        <Route path="/heartbeat" element={<HeartbeatManager />} />
        <Route path="/gpio" element={<GPIOControl />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
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
          <div className="flex flex-col h-screen w-screen overflow-hidden bg-[var(--pixel-bg)] text-[var(--pixel-text)]">
            <StatusBar />
            <div className="flex-1 overflow-hidden relative w-full">
              {/* CRT scanline overlay only for the route content area */}
              <RandomScanlineOverlay />
              <ErrorBoundary>
                <AnimatedRoutes />
              </ErrorBoundary>
            </div>
            <OverlayKeyboard />
          </div>
        </KeyboardProvider>
      </WebSocketProvider>
    </HashRouter>
  );
}
