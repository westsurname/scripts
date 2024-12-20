import React from 'react';
import { Tooltip, tooltipClasses, TooltipProps } from '@mui/material';
import { styled } from '@mui/system';

const CustomTooltip = styled(({ className, ...props }: TooltipProps) => (
  <Tooltip {...props} classes={{ popper: className }} />
))(({ theme }) => ({
  [`& .${tooltipClasses.tooltip}`]: {
    backgroundColor: 'rgba(33, 33, 33, 0.9)',
    backdropFilter: 'blur(10px)',
    color: theme.palette.common.white,
    padding: theme.spacing(1, 2),
    fontSize: '0.875rem',
    maxWidth: 300,
    borderRadius: 8,
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
  },
  [`& .${tooltipClasses.arrow}`]: {
    color: 'rgba(33, 33, 33, 0.9)',
  },
}));

export default CustomTooltip; 