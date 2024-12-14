import React from 'react';
import { Box, Typography } from '@mui/material';
import { TorrentImport } from '../components/TorrentImport.tsx';
import { handleFileUpload, handleMagnetUpload } from '../utils/upload.ts';

const Import: React.FC = () => {
  const handleTorrentImport = async (fileOrMagnet: File | string) => {
    try {
      if (fileOrMagnet instanceof File) {
        await handleFileUpload(fileOrMagnet);
      } else {
        await handleMagnetUpload(fileOrMagnet);
      }
    } catch (error) {
      console.error('Failed to import torrent:', error);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Import Torrent
      </Typography>
      <TorrentImport onTorrentImport={handleTorrentImport} />
    </Box>
  );
};

export default Import; 