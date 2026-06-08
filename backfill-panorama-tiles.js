const fs = require("fs");
const path = require("path");

const OUTPUT_DIR = path.join(__dirname, "downloaded_images");
const FACES = ["f", "b", "l", "r", "u", "d"];
const LEVEL_GRIDS = {
  "1": { cols: 4, rows: 4 },
  "2": { cols: 2, rows: 2 },
  "3": { cols: 1, rows: 1 },
};
const DEFAULT_CONCURRENCY = 6;
const REQUEST_TIMEOUT_MS = 30000;

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function findBaseMediaUrl() {
  const override = process.env.PANORAMA_MEDIA_BASE_URL;
  if (override) {
    return override.replace(/\/+$/, "");
  }

  const hostRoot = path.join(OUTPUT_DIR, "cloud.3dvista.com");
  if (!fs.existsSync(hostRoot)) {
    throw new Error(
      "Cannot infer media base URL. Set PANORAMA_MEDIA_BASE_URL or keep downloaded_images/cloud.3dvista.com/.../media."
    );
  }

  let mediaDir = null;

  function walk(currentDir) {
    if (path.basename(currentDir) === "media") {
      mediaDir = currentDir;
      return true;
    }

    for (const entry of fs.readdirSync(currentDir, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      if (walk(path.join(currentDir, entry.name))) {
        return true;
      }
    }

    return false;
  }

  walk(hostRoot);

  if (!mediaDir) {
    throw new Error("Cannot find downloaded_images/cloud.3dvista.com/.../media to infer base URL.");
  }

  const relativeParts = path.relative(OUTPUT_DIR, mediaDir).split(path.sep);
  const [host, ...rest] = relativeParts;
  return `https://${host}/${rest.join("/")}`;
}

function getPanoramaDirs() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    return [];
  }

  return fs
    .readdirSync(OUTPUT_DIR)
    .filter((name) => name.startsWith("panorama_"))
    .map((name) => path.join(OUTPUT_DIR, name))
    .filter((fullPath) => fs.statSync(fullPath).isDirectory())
    .sort();
}

function expectedTileNames(level) {
  const grid = LEVEL_GRIDS[level];
  const results = [];

  for (let col = 0; col < grid.cols; col += 1) {
    for (let row = 0; row < grid.rows; row += 1) {
      results.push(`${col}_${row}.webp`);
    }
  }

  return results;
}

function buildMissingTasks(baseMediaUrl) {
  const tasks = [];

  for (const panoramaDir of getPanoramaDirs()) {
    const panoramaName = path.basename(panoramaDir);

    for (const face of FACES) {
      for (const level of Object.keys(LEVEL_GRIDS)) {
        const levelDir = path.join(panoramaDir, face, level);
        const existing = new Set(
          fs.existsSync(levelDir)
            ? fs.readdirSync(levelDir).filter((file) => file.toLowerCase().endsWith(".webp"))
            : []
        );

        for (const fileName of expectedTileNames(level)) {
          if (existing.has(fileName)) {
            continue;
          }

          const filePath = path.join(levelDir, fileName);
          const relativeUrl = `${panoramaName}/${face}/${level}/${fileName}`;
          tasks.push({
            panoramaName,
            face,
            level,
            fileName,
            filePath,
            url: `${baseMediaUrl}/${relativeUrl}`,
          });
        }
      }
    }
  }

  return tasks;
}

async function downloadTask(task) {
  ensureDir(path.dirname(task.filePath));
  const response = await fetch(task.url, {
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.startsWith("image/")) {
    throw new Error(`Unexpected content-type: ${contentType}`);
  }

  const arrayBuffer = await response.arrayBuffer();
  fs.writeFileSync(task.filePath, Buffer.from(arrayBuffer));
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
    { length: Math.min(concurrency, items.length) },
    () => runner()
  );

  await Promise.all(runners);
}

async function main() {
  const dryRun = process.argv.includes("--dry-run");
  const concurrencyArg = process.argv.find((arg) => arg.startsWith("--concurrency="));
  const concurrency = concurrencyArg
    ? Number.parseInt(concurrencyArg.split("=")[1], 10)
    : DEFAULT_CONCURRENCY;
  const baseMediaUrl = findBaseMediaUrl();
  const tasks = buildMissingTasks(baseMediaUrl);

  console.log(`Base media URL: ${baseMediaUrl}`);
  console.log(`Missing tile count: ${tasks.length}`);

  if (tasks.length === 0) {
    console.log("No missing panorama tiles found.");
    return;
  }

  const groupedByPanorama = new Map();
  for (const task of tasks) {
    groupedByPanorama.set(task.panoramaName, (groupedByPanorama.get(task.panoramaName) || 0) + 1);
  }

  for (const [panoramaName, count] of groupedByPanorama.entries()) {
    console.log(`- ${panoramaName}: ${count} missing tile(s)`);
  }

  if (dryRun) {
    console.log("\nDry run only. Re-run without --dry-run to download missing tiles.");
    return;
  }

  let ok = 0;
  let fail = 0;

  await runWithConcurrency(
    tasks,
    async (task, index) => {
      try {
        await downloadTask(task);
        ok += 1;
        console.log(`[${index + 1}/${tasks.length}] Saved ${task.panoramaName}/${task.face}/${task.level}/${task.fileName}`);
      } catch (error) {
        fail += 1;
        console.warn(
          `[${index + 1}/${tasks.length}] Skip ${task.panoramaName}/${task.face}/${task.level}/${task.fileName}: ${error.message}`
        );
      }
    },
    Number.isNaN(concurrency) || concurrency < 1 ? DEFAULT_CONCURRENCY : concurrency
  );

  console.log(`\nDone. Saved: ${ok}, Failed: ${fail}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
