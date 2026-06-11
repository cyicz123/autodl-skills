import { ApiError, toApiError } from "./errors.mjs";
function joinUrl(host, requestPath) {
    const cleanHost = host.replace(/\/+$/, "");
    const cleanPath = requestPath.startsWith("/") ? requestPath : `/${requestPath}`;
    return `${cleanHost}${cleanPath}`;
}
async function parseResponseJson(response) {
    try {
        return (await response.json());
    }
    catch (error) {
        throw new ApiError("api_error", `Invalid JSON response: ${error instanceof Error ? error.message : String(error)}`, { status: response.status }, 3);
    }
}
export async function requestJson(options) {
    const fetchImpl = options.fetchImpl ?? fetch;
    const init = {
        method: options.method,
        headers: {
            Authorization: options.token,
            "Content-Type": "application/json",
        },
    };
    let requestPath = options.path;
    if (options.body !== undefined) {
        if (options.method === "GET") {
            const params = new URLSearchParams();
            for (const [key, value] of Object.entries(options.body)) {
                params.append(key, String(value));
            }
            const separator = requestPath.includes("?") ? "&" : "?";
            requestPath = `${requestPath}${separator}${params.toString()}`;
        }
        else {
            init.body = JSON.stringify(options.body);
        }
    }
    let response;
    try {
        response = await fetchImpl(joinUrl(options.host, requestPath), init);
    }
    catch (error) {
        throw toApiError(error);
    }
    const json = await parseResponseJson(response);
    if (!response.ok) {
        throw new ApiError("api_error", `API request failed: HTTP ${response.status}`, { status: response.status, response: json }, 3);
    }
    if (json.code !== "Success") {
        throw new ApiError("api_error", `AutoDL API returned ${String(json.code ?? "unknown")}: ${String(json.msg ?? "")}`.trim(), json, 3);
    }
    return json;
}
