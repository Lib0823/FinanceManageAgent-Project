package com.inbeom.apiserver.domain;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;

import java.time.LocalDateTime;

@Entity
@Table(name = "user_settings")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserSettings {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false, unique = true)
    private Long userId;

    @Column(name = "asset_order", columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    private String assetOrder;

    @Builder.Default
    @Column(name = "dark_mode", nullable = false)
    private Boolean darkMode = false;

    @Builder.Default
    @Column(name = "auto_login", nullable = false)
    private Boolean autoLogin = false;

    @Column(name = "notifications", columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    private String notifications;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
