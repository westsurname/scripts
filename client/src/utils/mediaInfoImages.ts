// Dynamic Range Images
const dvImage = '/static/images/mediainfo/codec/DV.png';
const hdrImage = '/static/images/mediainfo/codec/HDR.png';
const plusImage = '/static/images/mediainfo/codec/Plus.png';
const dvHdrImage = '/static/images/mediainfo/codec/DV-HDR.png';
const dvPlusImage = '/static/images/mediainfo/codec/DV-Plus.png';

// Audio Format Images
const digitalPlusImage = '/static/images/mediainfo/codec/DigitalPlus.png';
const dtsHdImage = '/static/images/mediainfo/codec/DTS-HD.png';
const dtsXImage = '/static/images/mediainfo/codec/DTS-X.png';
const trueHdImage = '/static/images/mediainfo/codec/TrueHD.png';
const atmosImage = '/static/images/mediainfo/codec/Atmos.png';
const trueHdAtmosImage = '/static/images/mediainfo/codec/TrueHD-Atmos.png';

// Combined Format Images
const dvDigitalPlusImage = '/static/images/mediainfo/codec/DV-DigitalPlus.png';
const hdrDigitalPlusImage = '/static/images/mediainfo/codec/HDR-DigitalPlus.png';
const plusDigitalPlusImage = '/static/images/mediainfo/codec/Plus-DigitalPlus.png';
const dvHdrDigitalPlusImage = '/static/images/mediainfo/codec/DV-HDR-DigitalPlus.png';
const dvPlusDigitalPlusImage = '/static/images/mediainfo/codec/DV-Plus-DigitalPlus.png';

// Resolution Images
const res2160pImage = '/static/images/mediainfo/resolution/Ultra-HD.png';
const res1080pImage = '/static/images/mediainfo/resolution/1080P.png';

// Edition Images
const imaxImage = '/static/images/mediainfo/edition/IMAX.png';
const extendedImage = '/static/images/mediainfo/edition/Extended-Edition.png';
const extendedCutImage = '/static/images/mediainfo/edition/Extended-Cut.png';
const theatricalImage = '/static/images/mediainfo/edition/Theatrical.png';
const directorsImage = '/static/images/mediainfo/edition/Directors-Cut.png';
const specialImage = '/static/images/mediainfo/edition/Special-Edition.png';
const unratedImage = '/static/images/mediainfo/edition/Unrated-Edition.png';
const ultimateImage = '/static/images/mediainfo/edition/Ultimate-Edition.png';

export const dynamicRangeImages: Record<string, string> = {
  'DV': dvImage,
  'HDR': hdrImage,
  'Plus': plusImage,
  'DV-HDR': dvHdrImage,
  'DV-Plus': dvPlusImage,
};

export const audioFormatImages: Record<string, string> = {
  'DigitalPlus': digitalPlusImage,
  'DTS-HD': dtsHdImage,
  'DTS-X': dtsXImage,
  'TrueHD': trueHdImage,
  'Atmos': atmosImage,
  'TrueHD-Atmos': trueHdAtmosImage,
};

export const combinedFormatImages: Record<string, string> = {
  'DV-DigitalPlus': dvDigitalPlusImage,
  'HDR-DigitalPlus': hdrDigitalPlusImage,
  'Plus-DigitalPlus': plusDigitalPlusImage,
  'DV-HDR-DigitalPlus': dvHdrDigitalPlusImage,
  'DV-Plus-DigitalPlus': dvPlusDigitalPlusImage,
};

export const resolutionImages: Record<string, string> = {
  'Ultra-HD': res2160pImage,
  '1080p': res1080pImage,
  '2160p': res2160pImage,
};

export const editionImages: Record<string, string> = {
  'IMAX': imaxImage,
  'Extended': extendedImage,
  'Extended-Cut': extendedCutImage,
  'Theatrical': theatricalImage,
  'Directors': directorsImage,
  'Special': specialImage,
  'Unrated': unratedImage,
  'Ultimate-Edition': ultimateImage,
};

export const getMediaInfoImage = (
  type: 'dynamicRange' | 'audioFormat' | 'resolution' | 'edition' | 'combinedFormat',
  key: string
): string => {
  const imageMap = {
    dynamicRange: dynamicRangeImages,
    audioFormat: audioFormatImages,
    resolution: resolutionImages,
    edition: editionImages,
    combinedFormat: combinedFormatImages,
  }[type];

  if (!imageMap) {
    console.error(`Invalid image type: ${type}`);
    return '';
  }

  const normalizedKey = Object.keys(imageMap).find(
    k => k.toLowerCase() === key.toLowerCase()
  );

  const imagePath = normalizedKey ? imageMap[normalizedKey] : undefined;
  if (!imagePath) {
    console.error(`No image found for type ${type} and key ${key}`);
    return '';
  }

  return imagePath;
}; 