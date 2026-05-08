package com.inbeom.apiserver.repository;

import com.inbeom.apiserver.domain.RefreshToken;
import com.inbeom.apiserver.domain.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface RefreshTokenRepository extends JpaRepository<RefreshToken, Long> {

    Optional<RefreshToken> findByToken(String token);

    Optional<RefreshToken> findByUserAndRevokedAtIsNull(User user);

    void deleteByUser(User user);

    void deleteByUserId(Long userId);
}
