import express from 'express';
import editly from 'editly';
import axios from 'axios';
import tmp from 'tmp-promise';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';

const app = express();
app.use(express.json({ limit: '50mb' }));

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3000;

app.post('/generate-video', async (req, res) => {
  const { editSpec } = req.body; // Full Editly spec + remote URLs in layers.path / audioFilePath etc.
  if (!editSpec) return res.status(400).json({ error: 'editSpec required' });

  const tempDir = await tmp.dir({ unsafeCleanup: true });
  const assetsDir = path.join(tempDir.path, 'assets');
  await fs.ensureDir(assetsDir);

  // Download all remote assets (images, videos, audio)
  const download = async (url, filename) => {
    const filepath = path.join(assetsDir, filename);
    const response = await axios({ url, responseType: 'arraybuffer' });
    await fs.writeFile(filepath, response.data);
    return filepath;
  };

  // Replace remote URLs with local paths in spec
  const processedSpec = { ...editSpec, outPath: path.join(tempDir.path, 'output.mp4') };
  if (processedSpec.clips) {
    for (const clip of processedSpec.clips) {
      if (clip.layers) {
        for (const layer of clip.layers) {
          if (layer.path && layer.path.startsWith('http')) {
            const ext = path.extname(layer.path) || '.jpg';
            layer.path = await download(layer.path, `layer-${Date.now()}${ext}`);
          }
        }
      }
    }
  }
  if (processedSpec.audioFilePath && processedSpec.audioFilePath.startsWith('http')) {
    processedSpec.audioFilePath = await download(processedSpec.audioFilePath, 'bg.mp3');
  }
  // Add voiceover as detached track if provided in audioTracks
  if (processedSpec.audioTracks) {
    for (const track of processedSpec.audioTracks) {
      if (track.asset && track.asset.startsWith('http')) {
        track.asset = await download(track.asset, 'voice.mp3');
      }
    }
  }

  try {
    await editly(processedSpec);
    res.download(processedSpec.outPath, 'faceless-video.mp4', async (err) => {
      await fs.remove(tempDir.path); // Cleanup
    });
  } catch (err) {
    await fs.remove(tempDir.path);
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => console.log(`🚀 Editly API running on port ${PORT}`));
