import React from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import Home from './components/Home';
import ChatInterface from './components/ChatInterface';
import CameraView from './components/CameraView';
import Gallery from './components/Gallery';
import Settings from './components/Settings';
import StatusBar from './components/StatusBar';
import CronManager from './components/CronManager';
import HeartbeatManager from './components/HeartbeatManager';
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
        <Route path="/cron" element={<CronManager />} />
        <Route path="/heartbeat" element={<HeartbeatManager />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </AnimatePresence>
  );
};

export default function App() {
  return (
    <BrowserRouter>
      <WebSocketProvider>
        <div className="flex flex-col h-screen w-screen overflow-hidden bg-black text-white">
          <StatusBar />
          <div className="flex-1 overflow-hidden relative w-full">
            <AnimatedRoutes />
          </div>
        </div>
      </WebSocketProvider>
    </BrowserRouter>
  );
}
