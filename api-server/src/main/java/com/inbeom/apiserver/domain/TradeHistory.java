package com.inbeom.apiserver.domain;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "trade_history")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class TradeHistory {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "order_number", length = 50)
    private String orderNumber;

    @Column(name = "stock_code", nullable = false, length = 10)
    private String stockCode;

    @Column(name = "stock_name", nullable = false, length = 50)
    private String stockName;

    @Column(name = "order_type", nullable = false, length = 10)
    private String orderType;

    @Builder.Default
    @Column(name = "order_status", nullable = false, length = 20)
    private String orderStatus = "PENDING";

    @Column(nullable = false)
    private Integer quantity;

    @Column(name = "order_price", nullable = false, precision = 12, scale = 2)
    private BigDecimal orderPrice;

    @Column(name = "executed_price", precision = 12, scale = 2)
    private BigDecimal executedPrice;

    @Column(name = "executed_quantity")
    private Integer executedQuantity;

    @Column(name = "ordered_at", nullable = false)
    private LocalDateTime orderedAt;

    @Column(name = "executed_at")
    private LocalDateTime executedAt;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    /**
     * Update order status to EXECUTED
     */
    public void markAsExecuted(BigDecimal executedPrice, Integer executedQuantity) {
        this.orderStatus = "EXECUTED";
        this.executedPrice = executedPrice;
        this.executedQuantity = executedQuantity;
        this.executedAt = LocalDateTime.now();
    }

    /**
     * Update order status to CANCELLED
     */
    public void markAsCancelled() {
        this.orderStatus = "CANCELLED";
    }

    /**
     * Update order status to FAILED
     */
    public void markAsFailed() {
        this.orderStatus = "FAILED";
    }
}
