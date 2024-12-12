import React from 'react';
import { Box, LinearProgress, Typography, alpha } from '@mui/material';
import { styled } from '@mui/system';

const ProgressContainer = styled(Box)(({ theme }) => ({
  width: '100%',
  background: alpha(theme.palette.background.paper, 0.1),
  borderRadius: 12,
  padding: theme.spacing(2),
  border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
  backdropFilter: 'blur(8px)',
}));

const StyledLinearProgress = styled(LinearProgress)(({ theme }) => ({
  height: 8,
  borderRadius: 4,
  backgroundColor: alpha(theme.palette.primary.main, 0.1),
  '& .MuiLinearProgress-bar': {
    borderRadius: 4,
    backgroundImage: `linear-gradient(45deg, 
      ${alpha(theme.palette.primary.main, 0.8)} 0%, 
      ${alpha(theme.palette.primary.light, 0.9)} 100%
    )`,
  },
}));

interface ProgressIndicatorProps {
  value: number;
  label?: string;
  showPercentage?: boolean;
  size?: 'small' | 'medium' | 'large';
  color?: 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info';
}

const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  value,
  label,
  showPercentage = true,
  size = 'medium',
  color = 'primary'
}) => {
  const height = size === 'small' ? 4 : size === 'medium' ? 8 : 12;

  return (
    <ProgressContainer>
      {label && (
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            {label}
          </Typography>
          {showPercentage && (
            <Typography variant="body2" color="text.secondary">
              {Math.round(value)}%
            </Typography>
          )}
        </Box>
      )}
      <StyledLinearProgress
        variant="determinate"
        value={value}
        color={color}
        sx={{
          height,
          '& .MuiLinearProgress-bar': {
            transition: 'transform 0.4s ease-in-out',
          },
        }}
      />
    </ProgressContainer>
  );
};

export default ProgressIndicator; 