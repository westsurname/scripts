import React from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Button, 
  Box,
  IconButton,
  alpha,
  Badge,
  Avatar
} from '@mui/material';
import { 
  Dashboard, 
  Code, 
  Settings,
  Notifications,
  DarkMode,
  LightMode,
  CloudUpload
} from '@mui/icons-material';
import { Link, useLocation } from 'react-router-dom';
import { styled } from '@mui/system';
import { useNotifications } from '../contexts/NotificationContext.tsx';

const GlassAppBar = styled(AppBar)(({ theme }) => ({
  background: alpha(theme.palette.background.paper, 0.7),
  backdropFilter: 'blur(20px)',
  borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
  boxShadow: 'none',
}));

const NavButton = styled(Button, {
  shouldForwardProp: (prop) => prop !== 'component' && prop !== 'selected'
})<{ component?: React.ElementType; to?: string }>(({ theme }) => ({
  margin: theme.spacing(0, 1),
  padding: theme.spacing(1, 2),
  borderRadius: '12px',
  textTransform: 'none',
  fontWeight: 500,
  transition: 'all 0.2s ease-in-out',
  '&:hover': {
    backgroundColor: alpha(theme.palette.primary.main, 0.1),
    transform: 'translateY(-2px)',
  },
  '&.Mui-selected': {
    backgroundColor: alpha(theme.palette.primary.main, 0.2),
  },
}));

const StyledIconButton = styled(IconButton)(({ theme }) => ({
  borderRadius: '12px',
  padding: theme.spacing(1),
  transition: 'all 0.2s ease-in-out',
  '&:hover': {
    backgroundColor: alpha(theme.palette.primary.main, 0.1),
    transform: 'translateY(-2px)',
  },
}));

const Logo = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
  '& svg': {
    fontSize: '2rem',
    color: theme.palette.primary.main,
  },
}));

interface NavbarProps {
  onNotificationClick: () => void;
  onThemeToggle?: () => void;
  isDarkMode?: boolean;
}

const Navbar: React.FC<NavbarProps> = ({ 
  onNotificationClick, 
  onThemeToggle,
  isDarkMode = true 
}) => {
  const location = useLocation();
  const { notifications } = useNotifications();

  return (
    <GlassAppBar position="sticky" elevation={0}>
      <Toolbar sx={{ justifyContent: 'space-between' }}>
        <Logo>
          <Code fontSize="large" />
          <Typography variant="h6" component={Link} to="/" sx={{ 
            textDecoration: 'none', 
            color: 'inherit',
            fontWeight: 600,
          }}>
            BlackHole
          </Typography>
        </Logo>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <NavButton
            component={Link}
            to="/"
            startIcon={<Dashboard />}
            color={location.pathname === '/' ? 'primary' : 'inherit'}
          >
            Dashboard
          </NavButton>

          <NavButton
            component={Link}
            to="/scripts"
            startIcon={<Code />}
            color={location.pathname === '/scripts' ? 'primary' : 'inherit'}
          >
            Scripts
          </NavButton>

          <StyledIconButton color="inherit" onClick={onNotificationClick}>
            <Badge badgeContent={notifications.length} color="error">
              <Notifications />
            </Badge>
          </StyledIconButton>

          <StyledIconButton onClick={onThemeToggle}>
            {isDarkMode ? <LightMode /> : <DarkMode />}
          </StyledIconButton>

          <StyledIconButton color="inherit">
            <Settings />
          </StyledIconButton>

          <StyledIconButton
            color="inherit"
            onClick={() => window.open('/import', 'Import Torrent', 'width=500,height=600')}
            title="Import Torrent"
          >
            <CloudUpload />
          </StyledIconButton>

          <Avatar 
            sx={{ 
              width: 35, 
              height: 35,
              ml: 1,
              cursor: 'pointer',
              transition: 'transform 0.2s ease-in-out',
              '&:hover': {
                transform: 'scale(1.1)',
              }
            }}
          />
        </Box>
      </Toolbar>
    </GlassAppBar>
  );
};

export default Navbar; 