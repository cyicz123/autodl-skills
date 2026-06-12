import path from "node:path";
import { fileURLToPath } from "node:url";
import { ApiError } from "../core/errors.mjs";
import { printErrorAndExit } from "../core/cli.mjs";
import { main as elasticMain } from "../elastic/cli.mjs";
import { main as proMain } from "../pro/cli.mjs";
const HELP = `AutoDL skills CLI

Usage:
  node autodl.mjs elastic <command> [...]   Private cloud elastic deployment
  node autodl.mjs pro <command> [...]       Public cloud container instance Pro

Run a namespace with --help for its commands:
  node autodl.mjs elastic --help
  node autodl.mjs pro --help

Sync (local <-> container over SSH) is documentation-driven with rclone;
see sync-reference.md. It is not a CLI subcommand.
`;
export async function main(argv = process.argv.slice(2), io = process) {
    try {
        if (argv.length === 0 || argv[0] === "--help" || argv[0] === "-h") {
            io.stdout.write(HELP);
            return 0;
        }
        const namespace = argv[0];
        const rest = argv.slice(1);
        switch (namespace) {
            case "elastic":
                return await elasticMain(rest, io);
            case "pro":
                return await proMain(rest, io);
            default:
                throw new ApiError("config_error", `Unknown namespace: ${String(namespace)}. Use "elastic" or "pro".`, {}, 1);
        }
    }
    catch (error) {
        return printErrorAndExit(error, io);
    }
}
if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
    process.exitCode = await main();
}
