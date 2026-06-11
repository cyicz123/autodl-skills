import { readFile } from "node:fs/promises";
import { ApiError } from "./errors.mjs";
export function printJson(data, io = process) {
    io.stdout.write(`${JSON.stringify(data, null, 2)}\n`);
}
export function printErrorAndExit(error, io = process) {
    const structured = error instanceof ApiError
        ? error
        : new ApiError("api_error", error instanceof Error ? error.message : String(error), {}, 3);
    printJson({
        status: "error",
        error_type: structured.errorType,
        message: structured.message,
        details: structured.details ?? {},
    }, io);
    return structured.exitCode;
}
export async function readJsonFile(filePath) {
    try {
        return JSON.parse(await readFile(filePath, "utf8"));
    }
    catch (error) {
        throw new ApiError("config_error", `Failed to read JSON file: ${error instanceof Error ? error.message : String(error)}`, { path: filePath }, 1);
    }
}
export function getFlagValue(args, flag) {
    const index = args.indexOf(flag);
    if (index < 0) {
        return undefined;
    }
    return args[index + 1];
}
export function hasFlag(args, flag) {
    return args.includes(flag);
}
export function getNumberFlag(args, flag, defaultValue) {
    const value = getFlagValue(args, flag);
    if (value === undefined) {
        return defaultValue;
    }
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
        throw new ApiError("config_error", `${flag} must be a number`, { value }, 1);
    }
    return parsed;
}
export function requireValue(value, name) {
    if (!value) {
        throw new ApiError("config_error", `Missing required argument: ${name}`, {}, 1);
    }
    return value;
}
