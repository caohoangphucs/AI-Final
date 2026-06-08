const { spawnSync, spawn } = require("child_process");
const path = require("path");

const ROOT = __dirname;
const NODE = process.execPath;
const args = new Set(process.argv.slice(2));

function runStep(label, scriptFile, extraArgs = []) {
  console.log(`\n== ${label} ==`);

  const result = spawnSync(NODE, [path.join(ROOT, scriptFile), ...extraArgs], {
    cwd: ROOT,
    stdio: "inherit",
  });

  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
}

function startViewer() {
  console.log(`\n== Start Viewer ==`);

  const child = spawn(NODE, [path.join(ROOT, "viewer-server.js")], {
    cwd: ROOT,
    stdio: "inherit",
  });

  child.on("exit", (code) => {
    process.exit(code || 0);
  });
}

function main() {
  const dryRun = args.has("--dry-run");
  const skipView = args.has("--no-view") || dryRun;

  runStep("Backfill Missing Tiles", "backfill-panorama-tiles.js", dryRun ? ["--dry-run"] : []);

  if (!dryRun) {
    runStep("Build Panorama Faces", "stitch-panoramas.js");
  }

  if (!skipView) {
    startViewer();
    return;
  }

  console.log("\nDone.");
}

main();
