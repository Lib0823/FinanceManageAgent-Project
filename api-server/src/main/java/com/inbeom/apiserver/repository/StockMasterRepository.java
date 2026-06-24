package com.inbeom.apiserver.repository;

import com.inbeom.apiserver.domain.StockMaster;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface StockMasterRepository extends JpaRepository<StockMaster, Long> {

    /**
     * 종목 검색: 종목 코드 prefix 또는 종목명 부분일치(대소문자 무시), 최대 30건.
     */
    List<StockMaster> findTop30ByStockCodeStartingWithOrStockNameContainingIgnoreCase(
            String stockCode, String stockName);
}
