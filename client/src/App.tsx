import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material';
import Navbar from './components/Navbar.tsx';
import Dashboard from './pages/Dashboard.tsx';
import Scripts from './pages/Scripts.tsx';
import NotificationCenter from './components/NotificationCenter.tsx';
import { NotificationProvider } from './contexts/NotificationContext.tsx';
import { CssBaseline } from '@mui/material';
import Notifications from './components/Notifications.tsx';
import { WebSocketProvider } from './hooks/useWebSocketContext.tsx';
import Import from './pages/Import.tsx';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#2196f3',
      light: '#64b5f6',
      dark: '#1976d2',
    },
    secondary: {
      main: '#ff4081',
      light: '#ff79b0',
      dark: '#c60055',
    },
    background: {
      default: '#0a1929',
      paper: '#132f4c',
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.05))',
          boxShadow: '0 0 20px rgba(0, 0, 0, 0.1)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
  },
});

function App() {
  const [notificationDrawerOpen, setNotificationDrawerOpen] = useState(false);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <NotificationProvider>
        <WebSocketProvider>
          <BrowserRouter>
            <div className="app-container">
              <Navbar onNotificationClick={() => setNotificationDrawerOpen(true)} />
              <Notifications />
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/scripts" element={<Scripts />} />
                <Route path="/import" element={<Import />} />
              </Routes>
              <NotificationCenter
                open={notificationDrawerOpen}
                onClose={() => setNotificationDrawerOpen(false)}
              />
            </div>
          </BrowserRouter>
        </WebSocketProvider>
      </NotificationProvider>
    </ThemeProvider>
  );
}

export default App; 