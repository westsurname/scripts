import React from 'react';
import { Button, TextField, Box, Typography } from '@mui/material';
import { styled } from '@mui/system';
import { Theme } from '@mui/material/styles';

const ImportBox = styled(Box)(({ theme }: { theme?: Theme }) => ({
  padding: theme?.spacing(3),
  borderRadius: theme?.shape.borderRadius,
  backgroundColor: theme?.palette.background.paper,
  boxShadow: theme?.shadows[1],
}));

const HiddenInput = styled('input')({
  display: 'none',
});

interface TorrentImportProps {
  onTorrentImport: (file: File | string) => void;
}

export const TorrentImport: React.FC<TorrentImportProps> = ({ onTorrentImport }) => {
  const [magnetLink, setMagnetLink] = React.useState('');

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.name.endsWith('.torrent')) {
      onTorrentImport(file);
    }
  };

  const handleMagnetSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (magnetLink.startsWith('magnet:')) {
      onTorrentImport(magnetLink);
      setMagnetLink('');
    }
  };

  return (
    <ImportBox>
      <Typography variant="h6" gutterBottom>Import Torrent</Typography>
      <Box display="flex" flexDirection="column" gap={2}>
        <Box>
          <label htmlFor="torrent-file">
            <HiddenInput
              id="torrent-file"
              type="file"
              accept=".torrent"
              onChange={handleFileChange}
            />
            <Button variant="contained" component="span">
              Upload Torrent File
            </Button>
          </label>
        </Box>
        
        <Box component="form" onSubmit={handleMagnetSubmit}>
          <TextField
            fullWidth
            label="Magnet Link"
            value={magnetLink}
            onChange={(e) => setMagnetLink(e.target.value)}
            placeholder="magnet:?xt=urn:btih:..."
            margin="normal"
          />
          <Button 
            type="submit"
            variant="contained"
            disabled={!magnetLink.startsWith('magnet:')}
          >
            Add Magnet Link
          </Button>
        </Box>
      </Box>
    </ImportBox>
  );
}; 