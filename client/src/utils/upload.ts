const handleFileUpload = async (file: File) => {
  const formData = new FormData();
  formData.append('torrentFile', file);
  
  return fetch('/api/torrent/upload', {
    method: 'POST',
    body: formData,
  });
};

const handleMagnetUpload = async (magnetUrl: string) => {
  return fetch('/api/torrent/magnet', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ magnetUrl }),
  });
};

export { handleFileUpload, handleMagnetUpload }; 