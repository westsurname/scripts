import React, { Component, ErrorInfo } from 'react';
import { Box, Button, Typography, Paper } from '@mui/material';
import { styled } from '@mui/system';
import { Error as ErrorIcon, Refresh } from '@mui/icons-material';

const ErrorContainer = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: theme.spacing(2),
  textAlign: 'center',
  borderRadius: 16,
  background: 'rgba(255, 255, 255, 0.05)',
  backdropFilter: 'blur(10px)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  '& .MuiSvgIcon-root': {
    fontSize: 48,
    color: theme.palette.error.main,
    marginBottom: theme.spacing(2),
  },
}));

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <Box sx={{ p: 3, maxWidth: 600, mx: 'auto' }}>
          <ErrorContainer>
            <ErrorIcon />
            <Typography variant="h5" gutterBottom>
              Something went wrong
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              {this.state.error?.message || 'An unexpected error occurred'}
            </Typography>
            <Button
              variant="contained"
              startIcon={<Refresh />}
              onClick={this.handleReset}
              sx={{ borderRadius: 2 }}
            >
              Try Again
            </Button>
          </ErrorContainer>
        </Box>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary; 