import React, { useState } from 'react';
import { 
  Typography, 
  Box, 
  Button, 
  TextField,
  Switch,
  FormControlLabel,
  Collapse,
  IconButton,
  Stack,
  Divider
} from '@mui/material';
import { PlayArrow, ExpandMore, Code } from '@mui/icons-material';
import GlassCard from './shared/GlassCard.tsx';

export type ArgType = {
  name: string;
  type: "string" | "number" | "boolean";
  required: boolean;
};

interface ScriptCardProps {
  name: string;
  description: string;
  script: string;
  args: ArgType[];
  onExecute?: (script: string, args: Record<string, any>) => void;
}

const ScriptCard: React.FC<ScriptCardProps> = ({
  name,
  description,
  script,
  args,
  onExecute
}) => {
  const [expanded, setExpanded] = useState(false);
  const [argValues, setArgValues] = useState<Record<string, any>>({});

  const handleExecute = () => {
    onExecute?.(script, argValues);
  };

  return (
    <GlassCard>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Code sx={{ mr: 1, color: 'primary.main' }} />
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          {name}
        </Typography>
        <IconButton
          onClick={() => setExpanded(!expanded)}
          sx={{
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.3s'
          }}
        >
          <ExpandMore />
        </IconButton>
      </Box>

      <Typography color="text.secondary" sx={{ mb: 2 }}>
        {description}
      </Typography>

      <Collapse in={expanded}>
        <Divider sx={{ my: 2 }} />
        <Stack spacing={2}>
          {args.map((arg) => (
            <Box key={arg.name}>
              {arg.type === 'boolean' ? (
                <FormControlLabel
                  control={
                    <Switch
                      checked={!!argValues[arg.name]}
                      onChange={(e) => 
                        setArgValues({
                          ...argValues,
                          [arg.name]: e.target.checked
                        })
                      }
                    />
                  }
                  label={arg.name}
                />
              ) : (
                <TextField
                  fullWidth
                  label={arg.name}
                  required={arg.required}
                  type={arg.type === 'number' ? 'number' : 'text'}
                  value={argValues[arg.name] || ''}
                  onChange={(e) => 
                    setArgValues({
                      ...argValues,
                      [arg.name]: e.target.value
                    })
                  }
                  variant="outlined"
                  size="small"
                />
              )}
            </Box>
          ))}
        </Stack>

        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained"
            startIcon={<PlayArrow />}
            onClick={handleExecute}
            sx={{ borderRadius: '8px' }}
          >
            Execute
          </Button>
        </Box>
      </Collapse>
    </GlassCard>
  );
};

export default ScriptCard; 