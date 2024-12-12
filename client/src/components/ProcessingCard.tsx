import React, { useEffect, useState } from 'react';
import { Typography, LinearProgress, Box, Chip, Stack, alpha, useTheme, IconButton } from '@mui/material';
import { styled } from '@mui/material/styles';
import { Movie, Tv, Check, CloudDownload, Error, Pending, Delete } from '@mui/icons-material';
import GlassCard from './shared/GlassCard.tsx';
import { ProcessingItem } from '../types/ProcessingItem.ts';
import { getMediaInfoImage } from '../utils/mediaInfoImages.ts';

const StyledChip = styled(Chip)(({ theme }) => ({
  borderRadius: '6px',
  '& .MuiChip-label': {
    fontWeight: 500,
  },
}));

const ProgressBar = styled(LinearProgress)(({ theme }) => ({
  height: 8,
  borderRadius: 4,
  backgroundColor: alpha(theme.palette.primary.main, 0.1),
  '& .MuiLinearProgress-bar': {
    borderRadius: 4,
  },
}));

interface ProcessingCardProps {
  item: ProcessingItem;
  setProcessingItems: React.Dispatch<React.SetStateAction<ProcessingItem[]>>;
}

const cardStyle = {
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  position: 'relative'
} as const;

const getStatusIcon = (status: string) => {
  switch (status.toLowerCase()) {
    case 'completed': return <Check />;
    case 'downloading': return <CloudDownload />;
    case 'error': return <Error />;
    default: return <Pending />;
  }
};

// Create a cache Map outside the component to persist across renders
const logoCache = new Map<string, string>();

const ProcessingCard = ({ item, setProcessingItems }: ProcessingCardProps) => {
  const theme = useTheme();
  const [logoUrl, setLogoUrl] = useState<string | null>(logoCache.get(item.id) || null);

  useEffect(() => {
    const fetchData = async () => {
      const tmdbId = item.status.parsedInfo?.parsedMovieInfo?.tmdbId || 
                     item.status.parsedInfo?.parsedEpisodeInfo?.tmdbId || 
                     item.status.parsedInfo?.movie?.tmdbId ||
                     item.status.parsedInfo?.series?.tmdbId ||
                     (item.type === 'movie' && item.status.parsedInfo?.movie?.tmdbId);
      
      if (tmdbId) {
        const isMovie = item.type === 'movie';
        try {
          // First try to get arrInfo
          const arrResponse = await fetch('/arrinfo');
          if (arrResponse.ok) {
            const arrData = await arrResponse.json();
            const mediaInfo = isMovie ? arrData.movie?.mediaInfo : arrData.series?.mediaInfo;
            const quality = isMovie ? arrData.movie?.quality : arrData.series?.quality;
            
            // Update mediaInfo if available from arrInfo
            if (mediaInfo) {
              item.fileInfo.mediaInfo = {
                ...item.fileInfo.mediaInfo, // Keep existing mediaInfo as fallback
                dynamicRange: mediaInfo.videoDynamicRange || item.fileInfo.mediaInfo?.dynamicRange,
                audioFormat: mediaInfo.audioCodec || item.fileInfo.mediaInfo?.audioFormat,
              };
            }
            
            // Update resolution if available from arrInfo
            if (quality?.resolution) {
              const arrResolution = `${quality.resolution}p`;
              // Only use arrInfo resolution if it's valid
              if (['2160p', '1080p', '720p', '480p'].includes(arrResolution)) {
                item.fileInfo.resolution = [arrResolution];
              }
            }
          }

          // Fetch logo
          const response = await fetch(`/api/tmdb/${isMovie ? 'movie' : 'tv'}/${tmdbId}/images`);
          if (response.ok) {
            const data = await response.json();
            if (data.logo_path) {
              setLogoUrl(`https://image.tmdb.org/t/p/w200${data.logo_path}`);
              logoCache.set(item.id, `https://image.tmdb.org/t/p/w200${data.logo_path}`);
            }
          }
        } catch (error) {
          console.error('Error fetching data:', error);
          // File processing info remains as fallback
        }
      }
    };

    if (item.status.parsedInfo) {
      fetchData();
    }
  }, [item.status.parsedInfo, item.type, item.fileInfo, item.id]);

  // Clean up cache when item is removed
  useEffect(() => {
    if (item.status.imported && 
        item.status.status === 'Complete' && 
        item.status.cached && 
        item.status.added && 
        item.status.mounted && 
        item.status.symlinked &&
        item.status.progress === 100) {
      const timer = setTimeout(() => {
        setProcessingItems(prevItems => {
          const newItems = prevItems.filter(i => i.id !== item.id);
          if (newItems.length < prevItems.length) {
            logoCache.delete(item.id);
          }
          return newItems;
        });
      }, 10000); // Increase delay to 10 seconds to ensure all updates are visible
      return () => clearTimeout(timer);
    }
  }, [item.status.imported, item.status.status, item.status.cached, 
      item.status.added, item.status.mounted, item.status.symlinked,
      item.status.progress, item.id, setProcessingItems]);

  const handleDelete = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    ws.onopen = () => {
      ws.send(JSON.stringify({
        type: 'delete_item',
        itemId: item.id
      }));
    };
    setProcessingItems(prevItems => prevItems.filter(i => i.id !== item.id));
  };

  if (!logoUrl) {
    return <div>Loading...</div>;
  }

  const isError = item.status.error;
  const fanartUrl = item.status.parsedInfo?.movie?.images?.find(img => img.coverType === 'fanart')?.remoteUrl 
    || item.status.parsedInfo?.series?.images?.find(img => img.coverType === 'fanart')?.remoteUrl;
  const posterUrl = item.status.parsedInfo?.movie?.images?.find(img => img.coverType === 'poster')?.remoteUrl
    || item.status.parsedInfo?.series?.images?.find(img => img.coverType === 'poster')?.remoteUrl;

  // Get the parsed title based on media type
  const getParsedTitle = () => {
    if (item.status.parsedInfo) {
      if (item.type === 'movie' && item.status.parsedInfo.parsedMovieInfo) {
        const { movieTitle: title, year } = item.status.parsedInfo.parsedMovieInfo;
        return year ? `${title} (${year})` : title;
      } else if (item.type === 'series' && item.status.parsedInfo.parsedEpisodeInfo) {
        const { seriesTitle: title, seasonNumber, episodeNumbers } = item.status.parsedInfo.parsedEpisodeInfo;
        if (seasonNumber !== undefined && episodeNumbers?.length) {
          return `${title} S${seasonNumber.toString().padStart(2, '0')}E${episodeNumbers[0].toString().padStart(2, '0')}`;
        }
        return title;
      }
    }
    return item.title;
  };

  return (
    <GlassCard 
      elevation={2} 
      sx={{
        ...cardStyle,
        background: fanartUrl ? `linear-gradient(to bottom, ${alpha(theme.palette.background.paper, 0.8)}, ${alpha(theme.palette.background.paper, 0.8)}), url(${fanartUrl})` : undefined,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        '&:hover .delete-button': {
          opacity: 1,
        },
      }}
    >
      <IconButton
        className="delete-button"
        onClick={handleDelete}
        sx={{
          position: 'absolute',
          top: 8,
          right: 8,
          opacity: 0,
          transition: 'opacity 0.2s ease-in-out',
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          '&:hover': {
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
          },
          zIndex: 1,
        }}
      >
        <Delete sx={{ color: 'white' }} />
      </IconButton>
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 2 }}>
          {posterUrl ? (
            <Box
              component="img"
              src={posterUrl}
              sx={{
                width: 60,
                height: 90,
                borderRadius: 1,
                mr: 2,
                objectFit: 'cover'
              }}
            />
          ) : (
            item.type === 'movie' ? <Movie sx={{ mr: 1 }} /> : <Tv sx={{ mr: 1 }} />
          )}
          {logoUrl ? (
            <Box
              component="img"
              src={logoUrl}
              sx={{
                maxHeight: 90,
                maxWidth: '100%',
                objectFit: 'contain',
                flexGrow: 1
              }}
            />
          ) : (
            <Typography variant="h6" sx={{ 
              flexGrow: 1,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}>
              {getParsedTitle()}
            </Typography>
          )}
        </Box>

        {/* File Info Images */}
        <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 2, gap: 1 }}>
          {/* Dynamic Range */}
          {item.fileInfo.mediaInfo?.dynamicRange?.map((range, index) => (
            <Box
              key={`dr-${index}`}
              component="img"
              src={getMediaInfoImage('dynamicRange', range)}
              sx={{
                height: 24,
                objectFit: 'contain'
              }}
              alt={range}
            />
          ))}

          {/* Audio Format */}
          {item.fileInfo.mediaInfo?.audioFormat?.map((format, index) => (
            <Box
              key={`af-${index}`}
              component="img"
              src={getMediaInfoImage('audioFormat', format)}
              sx={{
                height: 24,
                objectFit: 'contain'
              }}
              alt={format}
            />
          ))}

          {/* Combined Format */}
          {item.fileInfo.mediaInfo?.combinedFormat?.map((format, index) => (
            <Box
              key={`cf-${index}`}
              component="img"
              src={getMediaInfoImage('combinedFormat', format)}
              sx={{
                height: 24,
                objectFit: 'contain'
              }}
              alt={format}
            />
          ))}

          {/* Resolution */}
          {item.fileInfo.resolution.map((res, index) => (
            <Box
              key={`res-${index}`}
              component="img"
              src={getMediaInfoImage('resolution', res)}
              sx={{
                height: 24,
                objectFit: 'contain'
              }}
              alt={res}
            />
          ))}
        </Stack>

        {/* Status and Progress */}
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              {getStatusIcon(item.status.status)}
              <Typography variant="body2" sx={{ ml: 1 }}>
                {item.status.status}
              </Typography>
            </Box>
            {item.debridProvider && (
              <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto' }}>
                {item.debridProvider}
              </Typography>
            )}
          </Box>
          <ProgressBar 
            variant="determinate" 
            value={item.progress}
            sx={isError ? {
              '& .MuiLinearProgress-bar': {
                backgroundColor: theme.palette.error.main
              }
            } : {}}
          />
        </Box>

        {/* Status Chips */}
        <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ gap: 1 }}>
          <StyledChip
            label="Added"
            size="small"
            color={item.status.added ? "success" : "default"}
            variant={item.status.added ? "filled" : "outlined"}
          />
          <StyledChip
            label="Cached"
            size="small"
            color={item.status.cached ? "success" : "default"}
            variant={item.status.cached ? "filled" : "outlined"}
          />
          <StyledChip
            label="Mounted"
            size="small"
            color={item.status.mounted ? "success" : "default"}
            variant={item.status.mounted ? "filled" : "outlined"}
          />
          <StyledChip
            label="Symlinked"
            size="small"
            color={item.status.symlinked ? "success" : "default"}
            variant={item.status.symlinked ? "filled" : "outlined"}
          />
        </Stack>

        {/* Media Info Icons */}
        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
          {item.fileInfo.mediaInfo?.dynamicRange?.map((range, index) => (
            <img 
              key={`dr-${index}`}
              src={getMediaInfoImage('dynamicRange', range)} 
              alt={range}
              height="20"
            />
          ))}
          {item.fileInfo.mediaInfo?.audioFormat?.map((format, index) => (
            <img 
              key={`af-${index}`}
              src={getMediaInfoImage('audioFormat', format)} 
              alt={format}
              height="20"
            />
          ))}
          {item.fileInfo.mediaInfo?.combinedFormat?.map((format, index) => (
            <img 
              key={`cf-${index}`}
              src={getMediaInfoImage('combinedFormat', format)} 
              alt={format}
              height="20"
            />
          ))}
          {item.fileInfo.mediaInfo?.resolution?.map((res, index) => (
            <img 
              key={`res-${index}`}
              src={getMediaInfoImage('resolution', res)} 
              alt={res}
              height="20"
            />
          ))}
        </Stack>

        {process.env.NODE_ENV === 'development' && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Debug Info:
              {item.fileInfo.mediaInfo?.dynamicRange?.map((range, index) => (
                <div key={index}>Dynamic Range Path: {getMediaInfoImage('dynamicRange', range)}</div>
              ))}
              {item.fileInfo.mediaInfo?.audioFormat?.map((format, index) => (
                <div key={index}>Audio Format Path: {getMediaInfoImage('audioFormat', format)}</div>
              ))}
              {item.fileInfo.resolution.map((res, index) => (
                <div key={index}>Resolution Path: {getMediaInfoImage('resolution', res)}</div>
              ))}
            </Typography>
          </Box>
        )}

        {/* Torrent Name */}
        <Typography 
          variant="caption" 
          color="text.secondary" 
          sx={{ 
            mt: 2,
            display: 'block',
            textAlign: 'right',
            fontStyle: 'italic',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap'
          }}
        >
          {item.fileInfo.name}
        </Typography>
      </Box>
    </GlassCard>
  );
};

export default ProcessingCard; 