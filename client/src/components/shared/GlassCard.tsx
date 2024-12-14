import { Card } from '@mui/material';
import { styled } from '@mui/system';

const GlassCard = styled(Card)(({ theme }) => ({
  background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.03) 100%)',
  backdropFilter: 'blur(10px)',
  borderRadius: '16px',
  padding: '20px',
  margin: '10px',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  transition: 'all 0.3s ease-in-out',
  '&:hover': {
    transform: 'translateY(-5px)',
    boxShadow: '0 8px 25px rgba(0, 0, 0, 0.2)',
    borderColor: theme.palette.primary.main,
  },
}));

export default GlassCard; 