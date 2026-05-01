package com.inbeom.apiserver.repository;

import com.inbeom.apiserver.domain.User;
import com.inbeom.apiserver.domain.UserKisAccount;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface UserKisAccountRepository extends JpaRepository<UserKisAccount, Long> {

    Optional<UserKisAccount> findByUser(User user);

    Optional<UserKisAccount> findByAccountNumber(String accountNumber);

    boolean existsByAccountNumber(String accountNumber);
}
