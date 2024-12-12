export interface Notification {
  type: 'error' | 'success' | 'info' | 'warning';
  title: string;
  message: string;
  timestamp: number;
}

export interface ArrInfo {
  movie?: {
    title: string;
    year: number;
    tmdbId?: number;
    images: {
      coverType: string;
      remoteUrl: string;
    }[];
    quality?: {
      quality: {
        name: string;
        source: string;
        resolution: number;
      };
    };
    mediaInfo?: {
      audioCodec: string;
      videoCodec: string;
      videoDynamicRange: string;
    };
  };
  series?: {
    title: string;
    seasonNumber: number;
    episodeNumbers: number[];
    tmdbId?: number;
    images: {
      coverType: string;
      remoteUrl: string;
    }[];
    quality?: {
      quality: {
        name: string;
        source: string;
        resolution: number;
      };
    };
    mediaInfo?: {
      audioCodec: string;
      videoCodec: string;
      videoDynamicRange: string;
    };
  };
}

export interface ProcessingItem {
  id: string;
  title: string;
  type: 'movie' | 'series';
  status: {
    cached: boolean;
    added: boolean;
    mounted: boolean;
    symlinked: boolean;
    imported: boolean;
    status: string;
    error?: boolean;
    errorTime?: number;
    errorMessage?: string;
    progress: number;
    parsedInfo?: {
      parsedMovieInfo?: {
        movieTitle?: string;
        year?: number;
        tmdbId?: number;
        quality?: {
          quality?: {
            id?: number;
            name?: string;
            source?: string;
            resolution?: number;
          };
        };
        movieFile?: {
          mediaInfo?: {
            audioCodec?: string;
            videoCodec?: string;
            videoDynamicRange?: string;
            resolution?: string;
          };
        };
      };
      parsedEpisodeInfo?: {
        seriesTitle?: string;
        seasonNumber?: number;
        episodeNumbers?: number[];
        tmdbId?: number;
        quality?: {
          quality?: {
            id?: number;
            name?: string;
            source?: string;
            resolution?: number;
          };
        };
        mediaInfo?: {
          audioCodec?: string;
          videoCodec?: string;
          videoDynamicRange?: string;
          resolution?: string;
        };
      };
      movie?: {
        tmdbId?: number;
        images?: {
          coverType?: string;
          remoteUrl?: string;
        }[];
      };
      series?: {
        tmdbId?: number;
        images?: {
          coverType?: string;
          remoteUrl?: string;
        }[];
      };
    };
  };
  progress: number;
  debridProvider: string;
  fileInfo: {
    name: string;
    resolution: string[];
    codec: string[];
    year?: number;
    season?: number[] | null;
    episode?: number[] | null;
    mediaInfo: {
      dynamicRange?: ('DV' | 'HDR' | 'Plus' | 'DV-HDR' | 'DV-Plus')[];
      audioFormat?: ('DigitalPlus' | 'DTS-HD' | 'DTS-X' | 'TrueHD' | 'Atmos' | 'TrueHD-Atmos')[];
      combinedFormat?: string[];
      resolution?: ('2160p' | '1080p' | 'Ultra-HD')[];
      edition?: string[];
    };
  };
  arrInfo?: ArrInfo;
}

export interface TMDBImageResponse {
  id: number;
  backdrops: {
    aspect_ratio: number;
    height: number;
    iso_639_1: string;
    file_path: string;
    vote_average: number;
    vote_count: number;
    width: number;
  }[];
  logos: {
    aspect_ratio: number;
    height: number;
    iso_639_1: string;
    file_path: string;
    vote_average: number;
    vote_count: number;
    width: number;
  }[];
  posters: {
    aspect_ratio: number;
    height: number;
    iso_639_1: string;
    file_path: string;
    vote_average: number;
    vote_count: number;
    width: number;
  }[];
} 