import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
export function parseDotEnv(text) {
    const parsed = {};
    for (const rawLine of text.split(/\r?\n/)) {
        const line = rawLine.trim();
        if (!line || line.startsWith("#")) {
            continue;
        }
        const equalsIndex = line.indexOf("=");
        if (equalsIndex < 0) {
            continue;
        }
        const key = line.slice(0, equalsIndex).trim();
        const value = line.slice(equalsIndex + 1).trim();
        if (key) {
            parsed[key] = value;
        }
    }
    return parsed;
}
function loadSkillEnv(skillDir) {
    const envPath = path.join(skillDir, ".env");
    if (!existsSync(envPath)) {
        return {};
    }
    return parseDotEnv(readFileSync(envPath, "utf8"));
}
function cleanHost(host) {
    return host.replace(/\/+$/, "");
}
export function loadRuntimeContext(options) {
    const env = options.env ?? process.env;
    const skillEnv = loadSkillEnv(options.skillDir);
    const fallbackTokenEnvName = options.fallbackTokenEnvName ?? "AUTODL_TOKEN";
    const host = env[options.hostEnvName] ??
        skillEnv[options.hostEnvName] ??
        options.defaultHost;
    const token = env[options.tokenEnvName] ??
        env[fallbackTokenEnvName] ??
        skillEnv[options.tokenEnvName] ??
        skillEnv[fallbackTokenEnvName];
    return {
        host: cleanHost(host),
        ...(token ? { token } : {}),
    };
}
