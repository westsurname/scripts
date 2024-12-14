import { useRef } from 'react';
import { useNotifications } from '../contexts/NotificationContext.tsx';
import useWebSocket from '../hooks/useWebSocket.ts';

interface NotificationCache {
  [key: string]: number;
}

const Notifications = () => {
  const { addNotification } = useNotifications();
  const notificationCache = useRef<NotificationCache>({});
  const NOTIFICATION_COOLDOWN = 5000;
  
  useWebSocket('/ws', (data) => {
    try {
      if (data.type === 'notification') {
        const notification = data.notification;
        const notificationKey = `${notification.type}-${notification.title}-${notification.message}`;
        const now = Date.now();
        
        if (!notificationCache.current[notificationKey] || 
            now - notificationCache.current[notificationKey] > NOTIFICATION_COOLDOWN) {
          
          notificationCache.current[notificationKey] = now;
          
          addNotification({
            type: notification.type,
            title: notification.title,
            message: notification.message
          });
          
          Object.keys(notificationCache.current).forEach(key => {
            if (now - notificationCache.current[key] > NOTIFICATION_COOLDOWN) {
              delete notificationCache.current[key];
            }
          });
        }
      }
    } catch (error) {
      console.error('Error processing notification:', error);
    }
  });

  return null;
};

export default Notifications; 