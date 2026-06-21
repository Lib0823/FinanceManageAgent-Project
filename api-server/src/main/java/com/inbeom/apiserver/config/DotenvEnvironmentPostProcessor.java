package com.inbeom.apiserver.config;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.boot.EnvironmentPostProcessor;
import org.springframework.boot.SpringApplication;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.MapPropertySource;

/**
 * Loads a {@code .env} file from the working directory and registers its entries as a Spring
 * property source. This lets {@code ${KIS_QUOTE_APP_KEY:}}, {@code ${DART_API_KEY:}} etc. in
 * application.yml resolve from {@code .env} on ANY launch (IntelliJ, {@code ./gradlew bootRun},
 * java -jar) without requiring run-local.sh to export the variables first.
 *
 * <p>Precedence: the property source is added with the LOWEST priority (addLast), so real OS
 * environment variables and JVM system properties always override {@code .env} values. This keeps
 * run-local.sh's exported variables authoritative.
 *
 * <p>A missing or unreadable {@code .env} file is ignored and never breaks startup.
 */
public class DotenvEnvironmentPostProcessor implements EnvironmentPostProcessor {

    private static final String PROPERTY_SOURCE_NAME = "dotenvFile";
    private static final String DEFAULT_ENV_FILE = ".env";

    @Override
    public void postProcessEnvironment(ConfigurableEnvironment environment, SpringApplication application) {
        try {
            Path envPath = resolveEnvFile();
            if (envPath == null) {
                return;
            }

            Map<String, Object> values = parse(Files.readAllLines(envPath, StandardCharsets.UTF_8));
            if (values.isEmpty()) {
                return;
            }

            // addLast: OS env vars / system properties take precedence over .env values.
            environment.getPropertySources().addLast(new MapPropertySource(PROPERTY_SOURCE_NAME, values));
            // EnvironmentPostProcessor runs before logging is initialized; use stderr for a single,
            // non-secret confirmation line.
            System.err.println("[dotenv] loaded " + values.size() + " entr"
                    + (values.size() == 1 ? "y" : "ies") + " from " + envPath);
        } catch (IOException | RuntimeException ex) {
            // Never let .env loading break application startup.
            System.err.println("[dotenv] skipped .env loading: " + ex.getClass().getSimpleName()
                    + ": " + ex.getMessage());
        }
    }

    /**
     * Locate the {@code .env} file regardless of the launch working directory (IntelliJ often runs
     * from the repo root, gradlew/run-local.sh from the module dir). Tries, in order:
     * an explicit {@code -Ddotenv.path=...} override, the working dir, the {@code api-server/}
     * subdir, then walks up to 6 ancestor directories checking both {@code <dir>/.env} and
     * {@code <dir>/api-server/.env}. Returns the first regular, readable file, or null.
     */
    private Path resolveEnvFile() {
        String override = System.getProperty("dotenv.path");
        if (override != null && !override.isBlank()) {
            Path p = Paths.get(override);
            return (Files.isRegularFile(p) && Files.isReadable(p)) ? p : null;
        }

        Path cwd = Paths.get("").toAbsolutePath();
        Path dir = cwd;
        for (int depth = 0; depth <= 6 && dir != null; depth++) {
            Path direct = dir.resolve(DEFAULT_ENV_FILE);
            if (Files.isRegularFile(direct) && Files.isReadable(direct)) {
                return direct;
            }
            Path module = dir.resolve("api-server").resolve(DEFAULT_ENV_FILE);
            if (Files.isRegularFile(module) && Files.isReadable(module)) {
                return module;
            }
            dir = dir.getParent();
        }
        return null;
    }

    private Map<String, Object> parse(List<String> lines) {
        Map<String, Object> values = new LinkedHashMap<>();
        for (String rawLine : lines) {
            String line = rawLine.trim();
            if (line.isEmpty() || line.startsWith("#")) {
                continue;
            }
            // Support an optional leading "export " (as written in shell-sourced .env files).
            if (line.startsWith("export ")) {
                line = line.substring("export ".length()).trim();
            }
            int eq = line.indexOf('=');
            if (eq <= 0) {
                continue;
            }
            String key = line.substring(0, eq).trim();
            String value = line.substring(eq + 1).trim();
            if (key.isEmpty()) {
                continue;
            }
            value = stripQuotes(value);
            values.put(key, value);
        }
        return values;
    }

    private String stripQuotes(String value) {
        if (value.length() >= 2) {
            char first = value.charAt(0);
            char last = value.charAt(value.length() - 1);
            if ((first == '"' && last == '"') || (first == '\'' && last == '\'')) {
                return value.substring(1, value.length() - 1);
            }
        }
        return value;
    }
}
