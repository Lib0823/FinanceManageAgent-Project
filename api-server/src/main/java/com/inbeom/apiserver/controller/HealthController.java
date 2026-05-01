package com.inbeom.apiserver.controller;

import com.inbeom.apiserver.dto.common.ApiResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/health")
public class HealthController {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @GetMapping
    public ApiResponse<Map<String, Object>> health() {
        Map<String, Object> healthInfo = new HashMap<>();
        healthInfo.put("status", "UP");
        healthInfo.put("timestamp", LocalDateTime.now());
        healthInfo.put("service", "api-server");
        healthInfo.put("version", "0.0.1");

        return ApiResponse.success("API server is running", healthInfo);
    }

    @GetMapping("/db")
    public ApiResponse<Map<String, Object>> dbHealth() {
        Map<String, Object> dbInfo = new HashMap<>();

        try {
            Integer result = jdbcTemplate.queryForObject("SELECT 1", Integer.class);
            dbInfo.put("status", "UP");
            dbInfo.put("database", "PostgreSQL");
            dbInfo.put("connection", "OK");
            dbInfo.put("testQuery", result);

            return ApiResponse.success("Database connection is healthy", dbInfo);
        } catch (Exception e) {
            dbInfo.put("status", "DOWN");
            dbInfo.put("error", e.getMessage());

            return ApiResponse.error("Database connection failed");
        }
    }
}
