import React from 'react';
import { Container, Grid, Typography } from '@mui/material';
import { styled } from '@mui/system';
import ScriptCard from '../components/ScriptCard.tsx';
import { ArgType } from '../components/ScriptCard.tsx';

const ScriptsContainer = styled(Container)({
  marginTop: '2rem',
  marginBottom: '2rem',
});

const availableScripts: Array<{
  name: string;
  description: string;
  script: string;
  args: ArgType[];
}> = [
  {
    name: 'Import Torrent Folder',
    description: 'Import media files from a specified torrent folder',
    script: 'import_torrent_folder.py',
    args: [
      { name: '--directory', type: 'string', required: false },
      { name: '--custom-regex', type: 'string', required: false },
      { name: '--dry-run', type: 'boolean', required: false },
      { name: '--no-confirm', type: 'boolean', required: false },
      { name: '--radarr', type: 'boolean', required: false },
      { name: '--sonarr', type: 'boolean', required: false },
      { name: '--symlink-directory', type: 'string', required: false },
    ],
  },
  {
    name: 'Delete Non-Linked Folders',
    description: 'Remove folders that are not symbolically linked',
    script: 'delete_non_linked_folders.py',
    args: [
      { name: 'dst_folder', type: 'string', required: true },
      { name: '--src-folder', type: 'string', required: false },
      { name: '--dry-run', type: 'boolean', required: false },
      { name: '--no-confirm', type: 'boolean', required: false },
      { name: '--only-delete-files', type: 'boolean', required: false },
    ],
  },
];

const Scripts = () => {
  return (
    <ScriptsContainer>
      <Typography variant="h4" gutterBottom>
        Available Scripts
      </Typography>
      <Grid container spacing={3}>
        {availableScripts.map((script) => (
          <Grid item xs={12} sm={6} md={4} key={script.name}>
            <ScriptCard {...script} />
          </Grid>
        ))}
      </Grid>
    </ScriptsContainer>
  );
};

export default Scripts; 