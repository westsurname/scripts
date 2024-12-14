import React, { createContext, useContext, ReactNode, useState, useCallback } from 'react';
import useWebSocket from './useWebSocket.ts';
import { ProcessingItem } from '../types/ProcessingItem.ts';
import { getWebSocketUrl } from '../utils/api.ts';

type WebSocketContextType = {
  connectionStatus: string;
  processingItems: ProcessingItem[];
  setProcessingItems: React.Dispatch<React.SetStateAction<ProcessingItem[]>>;
};

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const WebSocketProvider = ({ children }: { children: ReactNode }) => {
  const [processingItems, setProcessingItems] = useState<ProcessingItem[]>([]);

  const handleProcessingItems = useCallback((newItems: ProcessingItem[]) => {
    setProcessingItems(prevItems => {
      const updatedItems = prevItems.map(prevItem => {
        const newItem = newItems.find(item => item.id === prevItem.id);
        if (!newItem) return prevItem;
        
        const statusChanged = 
          prevItem.status.cached !== newItem.status.cached ||
          prevItem.status.added !== newItem.status.added ||
          prevItem.status.mounted !== newItem.status.mounted ||
          prevItem.status.symlinked !== newItem.status.symlinked ||
          prevItem.status.status !== newItem.status.status ||
          prevItem.status.error !== newItem.status.error ||
          prevItem.progress !== newItem.progress;
        
        return statusChanged ? newItem : prevItem;
      });

      const itemsToAdd = newItems.filter(
        newItem => !updatedItems.some(item => item.id === newItem.id)
      );
      
      return [
        ...updatedItems,
        ...itemsToAdd
      ].filter(item => 
        !item.status.symlinked && 
        !(item.status.error && item.status.errorTime && 
          Date.now() - item.status.errorTime * 1000 > 5000)
      );
    });
  }, []);

  const connectionStatus = useWebSocket(getWebSocketUrl('/ws'), (data) => {
    console.log('Processing WebSocket data:', data);
    if (data.type === 'processing_status') {
      handleProcessingItems(data.items);
    }
  });

  return (
    <WebSocketContext.Provider value={{ 
      connectionStatus,
      processingItems,
      setProcessingItems
    }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};