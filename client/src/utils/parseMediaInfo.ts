import { ProcessingItem } from '../types/ProcessingItem.ts';

const regexPatterns = [
  { key: 'DV', value: /\[(?!.*HDR)(DV)\]/i },
  { key: 'HDR', value: /\[(HDR10)\]/i },
  { key: 'Plus', value: /\[(HDR10Plus)\]/i },
  { key: 'DigitalPlus', value: /\[(EAC3( 5\.1)?)\]/i },
  { key: 'DTS-HD', value: /\[(DTS-HD MA(?: 5\.1| 7\.1)?)\]/i },
  { key: 'DTS-X', value: /\[(DTS-X(?: 5\.1| 7\.1)?)\]/i },
  { key: 'TrueHD', value: /\[(?![^\]]*Atmos)[^\]]*TrueHD( 7\.1)?\]/i },
  { key: 'Atmos', value: /\[(EAC3 Atmos( 5\.1)?)\]/i },
  { key: 'TrueHD-Atmos', value: /\[(TrueHD Atmos( 7\.1)?)\]/i },
  { key: 'DV-HDR', value: /\[(DV HDR10)\]/i },
  { key: 'DV-Plus', value: /\[(DV HDR10Plus)\]/i },
  
  // Combined formats
  { key: 'DV-DigitalPlus', value: /\[(?!.*HDR)(DV)\].*\[(EAC3|DD\+|E-AC-3)( 5\.1| 7\.1)?\]/i },
  { key: 'HDR-DigitalPlus', value: /\[(HDR10)\].*\[(EAC3|DD\+|E-AC-3)( 5\.1| 7\.1)?\]/i },
  { key: 'Plus-DigitalPlus', value: /\[(HDR10\+)\].*\[(EAC3|DD\+|E-AC-3)( 5\.1| 7\.1)?\]/i },
  { key: 'DV-HDR-DigitalPlus', value: /\[(DV HDR10)\].*\[(EAC3|DD\+|E-AC-3)( 5\.1| 7\.1)?\]/i },
  { key: 'DV-Plus-DigitalPlus', value: /\[(DV HDR10\+)\].*\[(EAC3|DD\+|E-AC-3)( 5\.1| 7\.1)?\]/i },
  { key: 'DV-DTS-HD', value: /\[(?!.*HDR)(DV)\].*\[(DTS-HD MA(?: 5\.1| 7\.1)?)\]/i },
  { key: 'HDR-DTS-HD', value: /\[(HDR10)\].*\[(DTS-HD MA(?: 5\.1| 7\.1)?)\]/i },
  { key: 'Plus-DTS-HD', value: /\[(HDR10Plus)\].*\[(DTS-HD MA(?: 5\.1| 7\.1)?)\]/i },
  { key: 'DV-HDR-DTS-HD', value: /\[(DV HDR10)\].*\[(DTS-HD MA(?: 5\.1| 7\.1)?)\]/i },
  { key: 'DV-Plus-DTS-HD', value: /\[(DV HDR10Plus)\].*\[(DTS-HD MA(?: 5\.1| 7\.1)?)\]/i },
  { key: 'DV-DTS-X', value: /\[(?!.*HDR)(DV)\].*\[(DTS-X(?: 5\.1| 7\.1)?)\]/i },
  { key: 'HDR-DTS-X', value: /\[(HDR10)\].*\[(DTS-X(?: 5\.1| 7\.1)?)\]/i },
  { key: 'Plus-DTS-X', value: /\[(HDR10Plus)\].*\[(DTS-X(?: 5\.1| 7\.1)?)\]/i },
  { key: 'DV-HDR-DTS-X', value: /\[(DV HDR10)\].*\[(DTS-X(?: 5\.1| 7\.1)?)\]/i },
  { key: 'DV-Plus-DTS-X', value: /\[(DV HDR10Plus)\].*\[(DTS-X(?: 5\.1| 7\.1)?)\]/i },
  { key: 'DV-Atmos', value: /\[(?!.*HDR)(DV)\].*\[(EAC3 Atmos( 5\.1)?)\]/i },
  { key: 'HDR-Atmos', value: /\[(HDR10)\].*\[(EAC3 Atmos( 5\.1)?)\]/i },
  { key: 'Plus-Atmos', value: /\[(HDR10Plus)\].*\[(EAC3 Atmos( 5\.1)?)\]/i },
  { key: 'DV-HDR-Atmos', value: /\[(DV HDR10)\].*\[(EAC3 Atmos( 5\.1)?)\]/i },
  { key: 'DV-Plus-Atmos', value: /\[(DV HDR10Plus)\].*\[(EAC3 Atmos( 5\.1)?)\]/i },
  { key: 'DV-TrueHD', value: /\[(?!.*HDR)(DV)\].*\[(?![^\]]*Atmos)[^\]]*TrueHD( 7\.1)?\]/i },
  { key: 'HDR-TrueHD', value: /\[(HDR10)\].*\[(?![^\]]*Atmos)[^\]]*TrueHD( 7\.1)?\]/i },
  { key: 'Plus-TrueHD', value: /\[(HDR10Plus)\].*\[(?![^\]]*Atmos)[^\]]*TrueHD( 7\.1)?\]/i },
  { key: 'DV-HDR-TrueHD', value: /\[(DV HDR10)\].*\[(?![^\]]*Atmos)[^\]]*TrueHD( 7\.1)?\]/i },
  { key: 'DV-Plus-TrueHD', value: /\[(DV HDR10Plus)\].*\[(?![^\]]*Atmos)[^\]]*TrueHD( 7\.1)?\]/i },
  { key: 'DV-TrueHD-Atmos', value: /\[(?!.*HDR)(DV)\].*\[(TrueHD Atmos( 7\.1)?)\]/i },
  { key: 'HDR-TrueHD-Atmos', value: /\[(HDR10)\].*\[(TrueHD Atmos( 7\.1)?)\]/i },
  { key: 'Plus-TrueHD-Atmos', value: /\[(HDR10Plus)\].*\[(TrueHD Atmos( 7\.1)?)\]/i },
  { key: 'DV-HDR-TrueHD-Atmos', value: /\[(DV HDR10)\].*\[(TrueHD Atmos( 7\.1)?)\]/i },
  { key: 'DV-Plus-TrueHD-Atmos', value: /\[(DV HDR10Plus)\].*\[(TrueHD Atmos( 7\.1)?)\]/i },

  // Resolution patterns
  { key: '1080P', value: /1080p/i },
  { key: 'Ultra-HD', value: /(?:4k|2160p)/i },

  // Edition patterns
  { key: 'IMAX', value: /\{edition-IMAX[^}]*\}/i },
  { key: 'Unrated-Edition', value: /\{edition-Unrated[^}]*\}/i },
  { key: 'Directors-Cut', value: /\{edition-(Director|Ultimate Director)[^}]*\}/i },
  { key: 'Special-Edition', value: /\{edition-Special[^}]*\}/i },
  { key: 'Anniversary-Edition', value: /\{edition-\d+th Anniversary[^}]*\}/i },
  { key: 'Collectors-Edition', value: /\{edition-Collector[^}]*\}/i },
  { key: 'Minus-Color', value: /\{edition-Minus Color[^}]*\}/i },
  { key: 'Extended-Cut', value: /\{edition-Extended Cut[^}]*\}/i },
  { key: 'Extended-Edition', value: /\{edition-Extended(?! Cut)[^}]*\}/i },
  { key: 'Open-Matte', value: /\{edition-Open Matte[^}]*\}/i },
  { key: 'Final-Cut', value: /\{edition-Final Cut[^}]*\}/i },
  { key: 'Remastered', value: /\{edition-Remastered[^}]*\}/i },
  { key: 'Restored', value: /\{edition-Restored[^}]*\}/i },
  { key: 'Signature-Edition', value: /\{edition-Signature[^}]*\}/i },
  { key: 'Theatrical', value: /\{edition-Theatrical(?! Cut)[^}]*\}/i },
  { key: 'Theatrical-Cut', value: /\{edition-Theatrical Cut[^}]*\}/i },
  { key: 'Uncut', value: /\{edition-Uncut[^}]*\}/i },
  { key: 'Ultimate-Edition', value: /\{edition-Ultimate(?! Director)[^}]*\}/i },
];

export function parseMediaInfo(relativePath: string): ProcessingItem['fileInfo']['mediaInfo'] {
  const mediaInfo = {
    dynamicRange: [] as ProcessingItem['fileInfo']['mediaInfo']['dynamicRange'],
    audioFormat: [] as ProcessingItem['fileInfo']['mediaInfo']['audioFormat'],
    combinedFormat: [] as ProcessingItem['fileInfo']['mediaInfo']['combinedFormat'],
    resolution: [] as ProcessingItem['fileInfo']['mediaInfo']['resolution'],
    edition: [] as ProcessingItem['fileInfo']['mediaInfo']['edition'],
  };

  // Check for all formats (no break statement)
  for (const pattern of regexPatterns) {
    if (pattern.value.test(relativePath)) {
      if (pattern.key.includes('-')) {
        mediaInfo.combinedFormat?.push(pattern.key);
      } else if (['DV', 'HDR', 'Plus'].includes(pattern.key)) {
        mediaInfo.dynamicRange?.push(pattern.key as 'DV' | 'HDR' | 'Plus' | 'DV-HDR' | 'DV-Plus');
      } else if (['1080P', 'Ultra-HD'].includes(pattern.key)) {
        mediaInfo.resolution?.push(pattern.key as '2160p' | '1080p' | 'Ultra-HD');
      } else {
        const validAudioFormats = ['DigitalPlus', 'DTS-HD', 'DTS-X', 'TrueHD', 'Atmos', 'TrueHD-Atmos'] as const;
        if (validAudioFormats.includes(pattern.key as any)) {
          mediaInfo.audioFormat?.push(pattern.key as typeof validAudioFormats[number]);
        }
      }
    }
  }

  return mediaInfo;
} 