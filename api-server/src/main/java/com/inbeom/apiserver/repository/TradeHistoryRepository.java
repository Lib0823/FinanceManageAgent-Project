package com.inbeom.apiserver.repository;

import com.inbeom.apiserver.domain.TradeHistory;
import com.inbeom.apiserver.domain.User;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface TradeHistoryRepository extends JpaRepository<TradeHistory, Long> {

    List<TradeHistory> findByUserOrderByExecutedAtDesc(User user);

    Page<TradeHistory> findByUserOrderByExecutedAtDesc(User user, Pageable pageable);

    List<TradeHistory> findByUserAndStockCodeOrderByExecutedAtDesc(User user, String stockCode);

    List<TradeHistory> findByUserAndExecutedAtBetweenOrderByExecutedAtDesc(
        User user,
        LocalDateTime startDate,
        LocalDateTime endDate
    );

    @Query("SELECT DISTINCT th.stockCode FROM TradeHistory th WHERE th.user = :user AND th.orderType = 'buy'")
    List<String> findCurrentHoldingStockCodes(@Param("user") User user);

    List<TradeHistory> findByUserIdOrderByOrderedAtDesc(Long userId);

    void deleteByUserId(Long userId);
}
