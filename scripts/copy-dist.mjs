import { cp, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SRC = path.join(ROOT, "dist");
const DEST = path.join(ROOT, "skills", "autodl", "dist");

await rm(DEST, { recursive: true, force: true });
await cp(SRC, DEST, { recursive: true });

process.stdout.write(`copied dist -> ${path.relative(ROOT, DEST)}\n`);
