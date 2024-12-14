import React, { createContext, useContext, useState, useCallback } from 'react';

export interface Notification {
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: number;
}

export const NotificationContext = createContext<{
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'timestamp'>) => void;
  removeNotification: (timestamp: number) => void;
  clearAllNotifications: () => void;
}>({
  notifications: [],
  addNotification: () => {},
  removeNotification: () => {},
  clearAllNotifications: () => {},
});

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = useCallback((notification: Omit<Notification, 'timestamp'>) => {
    setNotifications(prev => [...prev, {
      ...notification,
      timestamp: Date.now()
    }]);
  }, []);

  const removeNotification = useCallback((timestamp: number) => {
    setNotifications(prev => prev.filter(notification => notification.timestamp !== timestamp));
  }, []);

  const clearAllNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  return (
    <NotificationContext.Provider value={{
      notifications,
      addNotification,
      removeNotification,
      clearAllNotifications
    }}>
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
}; 