import React from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import Home from './components/Home';
import ChatInterface from './components/ChatInterface';
import CameraView from './components/CameraView';
import Gallery from './components/Gallery';
import Settings from './components/Settings';
import StatusBar from './components/StatusBar';
import TaskManager from './components/TaskManager';
import HeartbeatManager from './components/HeartbeatManager';
import GPIOControl from './components/GPIOControl';
import { WebSocketProvider } from './contexts/WebSocketContext';


const AnimatedRoutes = () => {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Home />} />
        <Route
          path="/chat"
          element={<ChatInterface layoutId="avatar-hero" />}
        />
        <Route path="/camera" element={<CameraView />} />
        <Route path="/gallery" element={<Gallery />} />
        <Route path="/tasks" element={<TaskManager />} />
        <Route path="/heartbeat" element={<HeartbeatManager />} />
        <Route path="/gpio" element={<GPIOControl />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </AnimatePresence>
  );
};

export default function App() {
  return (
    <BrowserRouter>
      <WebSocketProvider>
        <div className="flex flex-col h-screen w-screen overflow-hidden bg-[var(--pixel-bg)] text-[var(--pixel-text)]">
          <StatusBar />
          <div className="flex-1 overflow-hidden relative w-full">
            <AnimatedRoutes />
          </div>
        </div>
      </WebSocketProvider>
    </BrowserRouter>
  );
}
