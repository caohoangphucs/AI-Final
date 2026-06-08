const fs = require("fs");
const os = require("os");
const path = require("path");
const sharp = require("sharp");

const INPUT_DIR = path.join(__dirname, "downloaded_images");
const OUTPUT_DIR = path.join(__dirname, "panorama_build");
const CPU_COUNT = Math.max(1, os.cpus().length);
const SHARP_CONCURRENCY = Number.parseInt(process.env.SHARP_CONCURRENCY || String(CPU_COUNT), 10);
const PANORAMA_BUILD_WORKERS = Number.parseInt(
  process.env.PANORAMA_BUILD_WORKERS || String(Math.max(1, Math.min(CPU_COUNT, 4))),
  10
);

sharp.concurrency(Number.isNaN(SHARP_CONCURRENCY) ? CPU_COUNT : SHARP_CONCURRENCY);
const FACES = ["f", "b", "l", "r", "u", "d"];
const FACE_NAMES = {
  f: "front",
  b: "back",
  l: "left",
  r: "right",
  u: "up",
  d: "down",
};
const DIRECTION_TO_FACE = {
  forward: "f",
  backward: "b",
  left: "l",
  right: "r",
};
const OPPOSITE_FACE = {
  f: "b",
  b: "f",
  l: "r",
  r: "l",
};
const TRANSFORMS = [
  { name: "identity", map: (col, row, maxCol, maxRow) => ({ col, row }) },
  { name: "flipX", map: (col, row, maxCol, maxRow) => ({ col: maxCol - col, row }) },
  { name: "flipY", map: (col, row, maxCol, maxRow) => ({ col, row: maxRow - row }) },
  { name: "rotate180", map: (col, row, maxCol, maxRow) => ({ col: maxCol - col, row: maxRow - row }) },
  { name: "transpose", map: (col, row) => ({ col: row, row: col }) },
  { name: "transposeFlipX", map: (col, row, maxCol, maxRow) => ({ col: maxRow - row, row: col }) },
  { name: "transposeFlipY", map: (col, row, maxCol, maxRow) => ({ col: row, row: maxCol - col }) },
  { name: "antiTranspose", map: (col, row, maxCol, maxRow) => ({ col: maxRow - row, row: maxCol - col }) },
];

function getPanoramaDirs() {
  if (!fs.existsSync(INPUT_DIR)) {
    return [];
  }

  return fs
    .readdirSync(INPUT_DIR)
    .filter((name) => name.startsWith("panorama_"))
    .map((name) => path.join(INPUT_DIR, name))
    .filter((fullPath) => fs.statSync(fullPath).isDirectory())
    .sort();
}

function pickBestLevel(faceDir) {
  if (!fs.existsSync(faceDir)) {
    return null;
  }

  const levels = fs
    .readdirSync(faceDir)
    .filter((name) => fs.statSync(path.join(faceDir, name)).isDirectory())
    .map((name) => {
      const dir = path.join(faceDir, name);
      const files = fs.readdirSync(dir).filter((file) => /\.(png|jpe?g|webp|avif)$/i.test(file));
      const levelValue = Number.parseInt(name, 10);
      return {
        name,
        dir,
        files,
        count: files.length,
        levelValue: Number.isNaN(levelValue) ? -1 : levelValue,
      };
    })
    .filter((level) => level.count > 0)
    .sort((a, b) => {
      if (b.count !== a.count) return b.count - a.count;
      return b.levelValue - a.levelValue;
    });

  return levels[0] || null;
}

function parseTileName(fileName) {
  const match = /^(\d+)_(\d+)\.[^.]+$/i.exec(fileName);
  if (!match) {
    return null;
  }

  return {
    col: Number.parseInt(match[1], 10),
    row: Number.parseInt(match[2], 10),
  };
}

function getLevelInfo(faceDir, levelName) {
  const dir = path.join(faceDir, levelName);
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
    return null;
  }

  const files = fs.readdirSync(dir).filter((file) => /\.(png|jpe?g|webp|avif)$/i.test(file));
  if (files.length === 0) {
    return null;
  }

  return {
    name: levelName,
    dir,
    files,
  };
}

function getTilesForLevel(levelInfo) {
  return levelInfo.files
    .map((fileName) => {
      const coords = parseTileName(fileName);
      if (!coords) {
        return null;
      }

      return {
        ...coords,
        input: path.join(levelInfo.dir, fileName),
      };
    })
    .filter(Boolean);
}

function getGridSize(tiles) {
  return {
    maxCol: Math.max(...tiles.map((tile) => tile.col)),
    maxRow: Math.max(...tiles.map((tile) => tile.row)),
  };
}

async function buildCompositeBuffer(tiles, tileWidth, tileHeight, transform) {
  const { maxCol, maxRow } = getGridSize(tiles);
  const width = (maxCol + 1) * tileWidth;
  const height = (maxRow + 1) * tileHeight;

  const composites = await Promise.all(
    tiles.map(async (tile) => {
      const mapped = transform.map(tile.col, tile.row, maxCol, maxRow);
      return {
        input: await sharp(tile.input).ensureAlpha().toBuffer(),
        left: mapped.col * tileWidth,
        top: mapped.row * tileHeight,
      };
    })
  );

  return sharp({
    create: {
      width,
      height,
      channels: 4,
      background: { r: 0, g: 0, b: 0, alpha: 1 },
    },
  })
    .composite(composites)
    .webp({ quality: 95 })
    .toBuffer();
}

async function scoreTransform(tiles, tileWidth, tileHeight, transform, referenceBuffer, referenceMeta) {
  const compositeBuffer = await buildCompositeBuffer(tiles, tileWidth, tileHeight, transform);
  const candidate = await sharp(compositeBuffer)
    .resize(referenceMeta.width, referenceMeta.height, { fit: "fill" })
    .raw()
    .toBuffer();
  const reference = await sharp(referenceBuffer).raw().toBuffer();

  let diff = 0;
  for (let i = 0; i < candidate.length; i += 4) {
    diff += Math.abs(candidate[i] - reference[i]);
    diff += Math.abs(candidate[i + 1] - reference[i + 1]);
    diff += Math.abs(candidate[i + 2] - reference[i + 2]);
  }

  return { diff, compositeBuffer };
}

async function detectBestTransform(faceDir, tiles, tileWidth, tileHeight) {
  const referenceLevel = getLevelInfo(faceDir, "3");
  if (!referenceLevel) {
    return { transform: TRANSFORMS[0], compositeBuffer: null };
  }

  const referenceFile = path.join(referenceLevel.dir, referenceLevel.files[0]);
  const referenceBuffer = fs.readFileSync(referenceFile);
  const referenceMeta = await sharp(referenceBuffer).metadata();

  let best = null;

  for (const transform of TRANSFORMS) {
    const scored = await scoreTransform(
      tiles,
      tileWidth,
      tileHeight,
      transform,
      referenceBuffer,
      referenceMeta
    );

    if (!best || scored.diff < best.diff) {
      best = {
        diff: scored.diff,
        transform,
        compositeBuffer: scored.compositeBuffer,
      };
    }
  }

  return best;
}

async function stitchFace(faceDir, outputFile) {
  const bestLevel = pickBestLevel(faceDir);
  if (!bestLevel) {
    return null;
  }

  const tiles = getTilesForLevel(bestLevel);

  if (tiles.length === 0) {
    return null;
  }

  const metadata = await sharp(tiles[0].input).metadata();
  const tileWidth = metadata.width || 0;
  const tileHeight = metadata.height || 0;
  const { maxCol, maxRow } = getGridSize(tiles);
  const bestTransform = await detectBestTransform(faceDir, tiles, tileWidth, tileHeight);
  const compositeBuffer =
    bestTransform.compositeBuffer ||
    (await buildCompositeBuffer(tiles, tileWidth, tileHeight, bestTransform.transform));

  fs.mkdirSync(path.dirname(outputFile), { recursive: true });
  fs.writeFileSync(outputFile, compositeBuffer);

  return {
    level: bestLevel.name,
    tileCount: tiles.length,
    grid: { cols: maxCol + 1, rows: maxRow + 1 },
    tile: { width: tileWidth, height: tileHeight },
    outputFile,
    transform: bestTransform.transform.name,
  };
}

async function createFaceSignature(filePath) {
  const { data, info } = await sharp(filePath)
    .resize(64, 64, { fit: "fill" })
    .removeAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });

  return {
    width: info.width,
    height: info.height,
    channels: info.channels,
    data,
  };
}

function compareSignatures(left, right) {
  let diff = 0;

  for (let i = 0; i < left.data.length; i += 1) {
    diff += Math.abs(left.data[i] - right.data[i]);
  }

  return diff / left.data.length;
}

async function detectNeighbors(panoramas) {
  const signatures = {};

  for (const panorama of panoramas) {
    signatures[panorama.name] = {};

    for (const face of Object.values(DIRECTION_TO_FACE)) {
      const relativeFile = panorama.faces[face];
      const absoluteFile = path.join(OUTPUT_DIR, relativeFile);
      signatures[panorama.name][face] = await createFaceSignature(absoluteFile);
    }
  }

  const preferred = {};

  for (const panorama of panoramas) {
    preferred[panorama.name] = {};

    for (const [direction, face] of Object.entries(DIRECTION_TO_FACE)) {
      const oppositeFace = OPPOSITE_FACE[face];
      let best = null;

      for (const candidate of panoramas) {
        if (candidate.name === panorama.name) {
          continue;
        }

        const score = compareSignatures(
          signatures[panorama.name][face],
          signatures[candidate.name][oppositeFace]
        );

        if (!best || score < best.score) {
          best = {
            panorama: candidate.name,
            score,
          };
        }
      }

      preferred[panorama.name][direction] = best;
    }
  }

  for (const panorama of panoramas) {
    panorama.neighbors = {};
  }

  for (const panorama of panoramas) {
    for (const [direction, oppositeDirection] of [
      ["forward", "backward"],
      ["backward", "forward"],
      ["left", "right"],
      ["right", "left"],
    ]) {
      const candidate = preferred[panorama.name][direction];
      if (!candidate) {
        continue;
      }

      const reciprocal = preferred[candidate.panorama]?.[oppositeDirection];
      if (!reciprocal || reciprocal.panorama !== panorama.name) {
        continue;
      }

      panorama.neighbors[direction] = {
        panorama: candidate.panorama,
        score: Number(candidate.score.toFixed(3)),
      };
    }
  }
}

async function runWithConcurrency(items, worker, concurrency) {
  let cursor = 0;

  async function runner() {
    while (cursor < items.length) {
      const currentIndex = cursor;
      cursor += 1;
      await worker(items[currentIndex], currentIndex);
    }
  }

  const runners = Array.from(
    { length: Math.min(Math.max(1, concurrency), items.length) },
    () => runner()
  );

  await Promise.all(runners);
}

async function buildPanorama(panoramaDir) {
  const panoramaName = path.basename(panoramaDir);
  const panoramaOutputDir = path.join(OUTPUT_DIR, panoramaName);
  const faces = {};
  let fallbackFaceSize = null;

  for (const face of FACES) {
    const faceDir = path.join(panoramaDir, face);
    const outputFile = path.join(panoramaOutputDir, `${face}.webp`);
    const result = await stitchFace(faceDir, outputFile);

    if (!result) {
      continue;
    }

    faces[face] = {
      face,
      faceName: FACE_NAMES[face] || face,
      level: result.level,
      tileCount: result.tileCount,
      grid: result.grid,
      tile: result.tile,
      transform: result.transform,
      relativeOutput: path.relative(OUTPUT_DIR, outputFile).split(path.sep).join("/"),
    };
    fallbackFaceSize = fallbackFaceSize || {
      width: result.grid.cols * result.tile.width,
      height: result.grid.rows * result.tile.height,
    };

    console.log(`Built ${panoramaName}/${face} from level ${result.level} (${result.tileCount} tiles)`);
  }

  if (Object.keys(faces).length === 0) {
    return null;
  }

  if (fallbackFaceSize) {
    for (const face of FACES) {
      if (faces[face]) {
        continue;
      }

      const outputFile = path.join(panoramaOutputDir, `${face}.webp`);
      fs.mkdirSync(path.dirname(outputFile), { recursive: true });
      await sharp({
        create: {
          width: fallbackFaceSize.width,
          height: fallbackFaceSize.height,
          channels: 4,
          background: { r: 0, g: 0, b: 0, alpha: 1 },
        },
      })
        .webp({ quality: 95 })
        .toFile(outputFile);

      faces[face] = {
        face,
        faceName: FACE_NAMES[face] || face,
        level: null,
        tileCount: 0,
        grid: null,
        tile: null,
        relativeOutput: path.relative(OUTPUT_DIR, outputFile).split(path.sep).join("/"),
        placeholder: true,
      };
    }
  }

  const manifest = {
    panorama: panoramaName,
    builtAt: new Date().toISOString(),
    faces,
  };

  fs.mkdirSync(panoramaOutputDir, { recursive: true });
  fs.writeFileSync(
    path.join(panoramaOutputDir, "manifest.json"),
    JSON.stringify(manifest, null, 2)
  );

  return {
    name: panoramaName,
    faces: Object.fromEntries(
      Object.entries(faces).map(([face, info]) => [face, info.relativeOutput])
    ),
  };
}

async function main() {
  const panoramaDirs = getPanoramaDirs();

  if (panoramaDirs.length === 0) {
    console.log("No panorama folders found in downloaded_images.");
    return;
  }

  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  console.log(
    `Building ${panoramaDirs.length} panorama(s) with ${Math.max(1, PANORAMA_BUILD_WORKERS)} worker(s) across ${CPU_COUNT} CPU core(s).`
  );

  const panoramas = new Array(panoramaDirs.length);

  await runWithConcurrency(
    panoramaDirs,
    async (panoramaDir, index) => {
      const result = await buildPanorama(panoramaDir);
      panoramas[index] = result;
    },
    Number.isNaN(PANORAMA_BUILD_WORKERS) ? Math.max(1, Math.min(CPU_COUNT, 4)) : PANORAMA_BUILD_WORKERS
  );

  const builtPanoramas = panoramas.filter(Boolean);

  await detectNeighbors(builtPanoramas);

  fs.writeFileSync(
    path.join(OUTPUT_DIR, "index.json"),
    JSON.stringify(
      {
        builtAt: new Date().toISOString(),
        panoramas: builtPanoramas,
      },
      null,
      2
    )
  );

  console.log(`\nBuilt ${builtPanoramas.length} panorama(s) into ${OUTPUT_DIR}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
