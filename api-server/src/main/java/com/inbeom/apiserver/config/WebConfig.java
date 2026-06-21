package com.inbeom.apiserver.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
            .allowedOriginPatterns(
                "http://localhost:5173",       // Vue3 dev server (default)
                "http://localhost:5174",       // Vue3 dev server (alternative port)
                "http://localhost:3000",       // Nginx production
                "http://192.168.*.*:5173",     // LAN devices (phone on same WiFi) — dev only
                "http://10.*.*.*:5173",        // LAN devices (private range) — dev only
                "http://172.16.*.*:5173"       // LAN devices (private range) — dev only
            )
            .allowedMethods("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS")
            .allowedHeaders("*")
            .allowCredentials(true)
            .maxAge(3600);
    }
}
