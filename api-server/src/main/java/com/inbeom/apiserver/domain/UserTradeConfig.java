package com.inbeom.apiserver.domain;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "user_trade_config")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserTradeConfig {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false, unique = true)
    private User user;

    @Column(name = "order_amount", nullable = false)
    private Long orderAmount = 1000000L;

    @Column(name = "max_holdings", nullable = false)
    private Integer maxHoldings = 10;

    @Column(name = "order_type", nullable = false, length = 20)
    private String orderType = "market";

    @Column(name = "is_active", nullable = false)
    private Boolean isActive = false;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
