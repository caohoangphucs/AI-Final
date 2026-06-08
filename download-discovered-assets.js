const fs = require("fs");
const path = require("path");

const DISCOVERY_FILE = path.join(__dirname, "discovered-assets.json");
const OUTPUT_DIR = path.join(__dirname, "downloaded_images");
const DEFAULT_CONCURRENCY = 6;
const REQUEST_TIMEOUT_MS = 30000;

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function localPathFromUrl(rawUrl) {
  const url = new URL(rawUrl);
  const relativePath = [url.hostname, ...decodeURIComponent(url.pathname).split("/").filter(Boolean)];
  return path.join(OUTPUT_DIR, ...relativePath);
}

async function runWithConcurrency(items, worker, concurrency) {
  let cursor = 0;

  async function runner() {
    while (cursor < items.length) {
      const current = cursor;
      cursor += 1;
      await worker(items[current], current);
    }
  }

  const runners = Array.from({ length: Math.min(concurrency, items.length) }, () => runner());
  await Promise.all(runners);
}

async function download(url, filePath) {
  ensureDir(path.dirname(filePath));
  const response = await fetch(url, {
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const buffer = Buffer.from(await response.arrayBuffer());
  fs.writeFileSync(filePath, buffer);
}

async function main() {
  if (!fs.existsSync(DISCOVERY_FILE)) {
    console.error(`Missing ${DISCOVERY_FILE}. Run npm run discover:assets first.`);
    process.exit(1);
  }

  const dryRun = process.argv.includes("--dry-run");
  const discovery = JSON.parse(fs.readFileSync(DISCOVERY_FILE, "utf8"));
  const categories = ["media_res", "media_map", "skin", "loading", "misc", "locale"];
  const urls = categories.flatMap((category) => discovery.assets[category] || []);
  const tasks = urls
    .map((url) => ({
      url,
      filePath: localPathFromUrl(url),
    }))
    .filter((task) => !fs.existsSync(task.filePath));

  console.log(`Discovered asset URLs: ${urls.length}`);
  console.log(`Missing local files: ${tasks.length}`);

  if (dryRun || tasks.length === 0) {
    if (dryRun) {
      console.log("Dry run only.");
    }
    return;
  }

  let ok = 0;
  let fail = 0;

  await runWithConcurrency(
    tasks,
    async (task, index) => {
      try {
        await download(task.url, task.filePath);
        ok += 1;
        console.log(`[${index + 1}/${tasks.length}] Saved ${task.filePath}`);
      } catch (error) {
        fail += 1;
        console.warn(`[${index + 1}/${tasks.length}] Skip ${task.url}: ${error.message}`);
      }
    },
    DEFAULT_CONCURRENCY
  );

  console.log(`\nDone. Saved: ${ok}, Failed: ${fail}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
