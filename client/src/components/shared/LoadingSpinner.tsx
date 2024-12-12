import React from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';
import { styled, keyframes } from '@mui/system';

const pulse = keyframes`
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
`;

const SpinnerContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: 200,
  gap: theme.spacing(2),
  '& .MuiCircularProgress-root': {
    color: theme.palette.primary.main,
  },
  '& .pulse': {
    animation: `${pulse} 1.5s ease-in-out infinite`,
  },
}));

interface LoadingSpinnerProps {
  message?: string;
  size?: number;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  message = 'Loading...', 
  size = 40 
}) => {
  return (
    <SpinnerContainer>
      <CircularProgress size={size} thickness={4} />
      <Typography 
        variant="body1" 
        color="text.secondary"
        className="pulse"
      >
        {message}
      </Typography>
    </SpinnerContainer>
  );
};

export default LoadingSpinner; 