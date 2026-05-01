package com.inbeom.apiserver.repository;

import com.inbeom.apiserver.domain.User;
import com.inbeom.apiserver.domain.UserTradeConfig;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface UserTradeConfigRepository extends JpaRepository<UserTradeConfig, Long> {

    Optional<UserTradeConfig> findByUser(User user);

    Optional<UserTradeConfig> findByUserId(Long userId);
}
