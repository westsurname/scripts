export function extractResolution(filename: string): string[] {
  const resolutions = ['2160p', '1080p', '720p', '480p'];
  return resolutions.filter(res => filename.toLowerCase().includes(res.toLowerCase()));
}

export function extractCodec(filename: string): string[] {
  const codecs = ['x265', 'x264', 'HEVC', 'AVC', 'H264', 'H.264'];
  return codecs.filter(codec => filename.toLowerCase().includes(codec.toLowerCase()));
}

export function extractYear(filename: string): number | undefined {
  const match = filename.match(/(?:19|20)\d{2}/);
  return match ? parseInt(match[0]) : undefined;
}

export function extractSeason(filename: string): number[] | undefined {
  const matches = filename.match(/S(\d{1,2})(?:E\d{1,2})?/gi);
  return matches ? matches.map(m => parseInt(m.substring(1))) : undefined;
}

export function extractEpisode(filename: string): number[] | undefined {
  const matches = filename.match(/E(\d{1,2})/gi);
  return matches ? matches.map(m => parseInt(m.substring(1))) : undefined;
} 