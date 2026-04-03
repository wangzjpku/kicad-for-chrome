/**
 * Structured Logging Utility for Frontend
 *
 * Phase 3.2: Replaces console.log with structured logging
 *
 * Features:
 * - Log levels: debug, info, warn, error
 * - Production builds auto-strip debug logs
 * - Structured format with timestamp, module, level
 * - Optional remote logging support (future)
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  module: string;
  message: string;
  data?: Record<string, unknown>;
}

interface LoggerConfig {
  level: LogLevel;
  enabled: boolean;
  remoteEndpoint?: string;
  maxRemoteLogs?: number;
}

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

// Default config - can be overridden
let config: LoggerConfig = {
  level: 'info',
  enabled: true,
};

// Check if we're in production mode
const isProduction = import.meta.env?.PROD === true ||
  String(import.meta.env?.MODE) === 'production';

// In production, default to 'warn' level
if (isProduction) {
  config.level = 'warn';
}

/**
 * Configure the logger
 */
export function configureLogger(newConfig: Partial<LoggerConfig>): void {
  config = { ...config, ...newConfig };
}

/**
 * Get current log level
 */
export function getLogLevel(): LogLevel {
  return config.level;
}

/**
 * Check if a log level should be output
 */
function shouldLog(level: LogLevel): boolean {
  if (!config.enabled) return false;
  return LOG_LEVELS[level] >= LOG_LEVELS[config.level];
}

/**
 * Format a log entry for output
 */
function formatEntry(level: LogLevel, module: string, message: string, data?: Record<string, unknown>): LogEntry {
  return {
    timestamp: new Date().toISOString(),
    level,
    module,
    message,
    ...(data && { data }),
  };
}

/**
 * Create a module-specific logger
 */
export function createLogger(module: string) {
  const log = (level: LogLevel, message: string, data?: Record<string, unknown>) => {
    if (!shouldLog(level)) return;

    const entry = formatEntry(level, module, message, data);
    const prefix = `[${entry.timestamp}] [${level.toUpperCase()}] [${module}]`;

    switch (level) {
      case 'debug':
        console.debug(prefix, message, data ?? '');
        break;
      case 'info':
        console.info(prefix, message, data ?? '');
        break;
      case 'warn':
        console.warn(prefix, message, data ?? '');
        break;
      case 'error':
        console.error(prefix, message, data ?? '');
        break;
    }

    // Future: Send to remote logging endpoint
    // if (config.remoteEndpoint && level !== 'debug') {
    //   sendToRemote(entry);
    // }
  };

  return {
    debug: (message: string, data?: Record<string, unknown>) => log('debug', message, data),
    info: (message: string, data?: Record<string, unknown>) => log('info', message, data),
    warn: (message: string, data?: Record<string, unknown>) => log('warn', message, data),
    error: (message: string, data?: Record<string, unknown>) => log('error', message, data),

    /**
     * Log with timing information
     */
    time: (label: string) => {
      if (!shouldLog('debug')) return () => {};
      const start = performance.now();
      return () => {
        const duration = performance.now() - start;
        log('debug', `${label} completed`, { duration: `${duration.toFixed(2)}ms` });
      };
    },

    /**
     * Create a child logger with extended module name
     */
    child: (submodule: string) => createLogger(`${module}:${submodule}`),
  };
}

/**
 * Global logger instance
 */
export const logger = createLogger('app');

// Default export
export default logger;

// Pre-defined loggers for common modules
export const apiLogger = createLogger('api');
export const storeLogger = createLogger('store');
export const editorLogger = createLogger('editor');
export const hookLogger = createLogger('hooks');
export const componentLogger = createLogger('component');
