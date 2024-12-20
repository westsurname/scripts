import React from 'react';
import { Box, Typography, keyframes } from '@mui/material';
import { styled } from '@mui/system';
import {
  CheckCircle,
  Error,
  Warning,
  Pending,
  CloudDone,
  CloudQueue,
  CloudOff
} from '@mui/icons-material';

const pulse = keyframes`
  0% { transform: scale(1); }
  50% { transform: scale(1.1); }
  100% { transform: scale(1); }
`;

const StatusContainer = styled(Box)(({ theme }) => ({
  display: 'inline-flex',
  alignItems: 'center',
  padding: theme.spacing(0.5, 1.5),
  borderRadius: '20px',
  gap: theme.spacing(1),
  background: 'rgba(255, 255, 255, 0.1)',
  backdropFilter: 'blur(10px)',
  border: '1px solid rgba(255, 255, 255, 0.2)',
  transition: 'all 0.2s ease-in-out',
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
  },
  '& .MuiSvgIcon-root': {
    fontSize: '1.2rem',
  },
  '&.active .MuiSvgIcon-root': {
    animation: `${pulse} 2s infinite ease-in-out`,
  },
}));

type StatusType = 'success' | 'error' | 'warning' | 'pending' | 'connected' | 'disconnected' | 'syncing';

interface StatusConfig {
  icon: React.ReactNode;
  color: string;
  background: string;
}

const statusConfigs: Record<StatusType, StatusConfig> = {
  success: {
    icon: <CheckCircle />,
    color: '#4caf50',
    background: 'rgba(76, 175, 80, 0.1)',
  },
  error: {
    icon: <Error />,
    color: '#f44336',
    background: 'rgba(244, 67, 54, 0.1)',
  },
  warning: {
    icon: <Warning />,
    color: '#ff9800',
    background: 'rgba(255, 152, 0, 0.1)',
  },
  pending: {
    icon: <Pending />,
    color: '#2196f3',
    background: 'rgba(33, 150, 243, 0.1)',
  },
  connected: {
    icon: <CloudDone />,
    color: '#4caf50',
    background: 'rgba(76, 175, 80, 0.1)',
  },
  disconnected: {
    icon: <CloudOff />,
    color: '#f44336',
    background: 'rgba(244, 67, 54, 0.1)',
  },
  syncing: {
    icon: <CloudQueue />,
    color: '#2196f3',
    background: 'rgba(33, 150, 243, 0.1)',
  },
};

interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  active?: boolean;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  active = false,
}) => {
  const config = statusConfigs[status];

  return (
    <StatusContainer
      className={active ? 'active' : ''}
      sx={{
        color: config.color,
        backgroundColor: config.background,
        borderColor: `${config.color}40`,
      }}
    >
      {config.icon}
      {label && (
        <Typography
          variant="caption"
          sx={{
            fontWeight: 500,
            textTransform: 'capitalize',
          }}
        >
          {label}
        </Typography>
      )}
    </StatusContainer>
  );
};

export default StatusBadge; 