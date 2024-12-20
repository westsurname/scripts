import React, { useState, useEffect, useRef } from 'react';
import { Grid, Typography, Box, useTheme, alpha } from '@mui/material';
import DashboardContainer from '../components/DashboardContainer.tsx';
import ProcessingCard from '../components/ProcessingCard.tsx';
import { ProcessingItem } from '../types/ProcessingItem.ts';
import StatusBadge from '../components/shared/StatusBadge.tsx';
import NotificationCenter from '../components/NotificationCenter.tsx';
import { useWebSocketContext } from '../hooks/useWebSocketContext.tsx';

const Dashboard = () => {
  const { connectionStatus, processingItems, setProcessingItems } = useWebSocketContext();
  const theme = useTheme();
  const previousItems = useRef<ProcessingItem[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [notificationDrawerOpen, setNotificationDrawerOpen] = useState(false);
  
  useEffect(() => {
    previousItems.current = processingItems;
  }, [processingItems]);

  useEffect(() => {
    setIsConnected(connectionStatus === 'Connected');
  }, [connectionStatus]);

  return (
    <DashboardContainer>
      <NotificationCenter 
        open={notificationDrawerOpen}
        onClose={() => setNotificationDrawerOpen(false)}
      />
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom fontWeight="600">
          Processing Queue
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <StatusBadge 
            status={isConnected ? 'connected' : 'disconnected'} 
            label={connectionStatus}
            active={!isConnected} 
          />
        </Box>
      </Box>

      <Grid container spacing={3}>
        {processingItems.length > 0 ? (
          processingItems.map((item) => (
            <Grid item xs={12} sm={6} md={4} key={item.id}>
              <ProcessingCard item={item} setProcessingItems={setProcessingItems} />
            </Grid>
          ))
        ) : (
          <Grid item xs={12}>
            <Box sx={{
              textAlign: 'center',
              py: 8,
              background: alpha(theme.palette.background.paper, 0.6),
              borderRadius: '16px',
              border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            }}>
              <Typography variant="h6" gutterBottom>
                No Active Tasks
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {isConnected ? 'Queue is empty' : connectionStatus}
              </Typography>
            </Box>
          </Grid>
        )}
      </Grid>
    </DashboardContainer>
  );
};

export const fetchArrInfo = async (title: string, isMovie: boolean) => {
  try {
    const response = await fetch(
      `/api/parse?title=${encodeURIComponent(title)}&isMovie=${isMovie}`
    );
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching Arr info:', error);
    return null;
  }
};

export default Dashboard; 