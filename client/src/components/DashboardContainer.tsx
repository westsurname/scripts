import { Box } from '@mui/material';
import { styled } from '@mui/system';

const DashboardContainer = styled(Box)(({ theme }) => ({
  padding: theme.spacing(3),
  maxWidth: '1400px',
  margin: '0 auto',
  minHeight: '100vh',
  background: `linear-gradient(135deg, ${theme.palette.background.default} 0%, ${theme.palette.background.paper} 100%)`,
  backgroundAttachment: 'fixed',
  position: 'relative',
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: `radial-gradient(circle at 50% 0%, ${theme.palette.primary.main}15, transparent 25%)`,
    pointerEvents: 'none',
  },
  '& > *': {
    position: 'relative',
  },
}));

export default DashboardContainer; 