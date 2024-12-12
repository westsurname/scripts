import React from 'react';
import { 
  Drawer, 
  List, 
  ListItem, 
  ListItemText, 
  ListItemIcon,
  Typography,
  IconButton,
  Box,
  useTheme,
  alpha,
} from '@mui/material';
import { 
  CheckCircle, 
  Error,
  Info,
  Warning,
  Close,
  Delete,
  Notifications as NotificationsIcon
} from '@mui/icons-material';
import { styled } from '@mui/system';
import { useNotifications } from '../contexts/NotificationContext.tsx';

const DrawerHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  padding: theme.spacing(2),
  background: alpha(theme.palette.background.paper, 0.9),
  backdropFilter: 'blur(10px)',
  borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
  position: 'sticky',
  top: 0,
  zIndex: 1,
}));

const NotificationList = styled(List)(({ theme }) => ({
  padding: theme.spacing(2),
  '& .MuiListItem-root': {
    marginBottom: theme.spacing(2),
    borderRadius: theme.shape.borderRadius,
    background: alpha(theme.palette.background.paper, 0.6),
    backdropFilter: 'blur(10px)',
    border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
    transition: 'all 0.2s ease-in-out',
    '&:hover': {
      background: alpha(theme.palette.background.paper, 0.8),
      transform: 'translateX(5px)',
    },
  },
}));

const EmptyState = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  padding: theme.spacing(4),
  color: theme.palette.text.secondary,
  height: '100%',
  minHeight: 400,
  textAlign: 'center',
  '& svg': {
    fontSize: 48,
    marginBottom: theme.spacing(2),
    opacity: 0.5,
  },
}));

interface NotificationCenterProps {
  open: boolean;
  onClose: () => void;
}

const NotificationCenter = ({ open, onClose }: NotificationCenterProps) => {
  const theme = useTheme();
  const { notifications, removeNotification } = useNotifications();

  const getNotificationIcon = (type: 'success' | 'error' | 'warning' | 'info') => {
    switch (type) {
      case 'success':
        return <CheckCircle color="success" />;
      case 'error':
        return <Error color="error" />;
      case 'warning':
        return <Warning color="warning" />;
      default:
        return <Info color="info" />;
    }
  };

  const formatTime = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleTimeString();
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: 380,
          background: alpha(theme.palette.background.default, 0.95),
          backdropFilter: 'blur(10px)',
        },
      }}
    >
      <DrawerHeader>
        <NotificationsIcon sx={{ mr: 1 }} />
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Notifications
        </Typography>
        <IconButton onClick={onClose} size="small">
          <Close />
        </IconButton>
      </DrawerHeader>

      {notifications.length > 0 ? (
        <NotificationList>
          {notifications.map((notification, index) => (
            <ListItem
              key={index}
              secondaryAction={
                <IconButton 
                  edge="end" 
                  onClick={() => removeNotification(notification.timestamp)}
                  size="small"
                >
                  <Delete />
                </IconButton>
              }
            >
              <ListItemIcon>
                {getNotificationIcon(notification.type)}
              </ListItemIcon>
              <ListItemText
                primary={
                  <Typography variant="subtitle2" fontWeight={600}>
                    {notification.title}
                  </Typography>
                }
                secondary={
                  <Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                      {notification.message}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatTime(notification.timestamp)}
                    </Typography>
                  </Box>
                }
              />
            </ListItem>
          ))}
        </NotificationList>
      ) : (
        <EmptyState>
          <NotificationsIcon />
          <Typography variant="h6" gutterBottom>
            No notifications
          </Typography>
          <Typography variant="body2" color="text.secondary">
            You're all caught up!
          </Typography>
        </EmptyState>
      )}
    </Drawer>
  );
};

export default NotificationCenter; 