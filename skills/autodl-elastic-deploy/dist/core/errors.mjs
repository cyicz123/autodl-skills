export class ApiError extends Error {
    errorType;
    details;
    exitCode;
    constructor(errorType, message, details = {}, exitCode = 3) {
        super(message);
        this.name = "ApiError";
        this.errorType = errorType;
        this.details = details;
        this.exitCode = exitCode;
    }
}
export function toApiError(error, fallbackMessage = "API request failed") {
    if (error instanceof ApiError) {
        return error;
    }
    const message = error instanceof Error ? error.message : String(error);
    return new ApiError("api_error", `${fallbackMessage}: ${message}`, {}, 3);
}
