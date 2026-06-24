package com.inbeom.apiserver.dto.favorite;

import jakarta.validation.constraints.NotBlank;
import lombok.*;

/**
 * 관심 종목 추가 요청 (관심종목 화면 - FavoritesView).
 * POST /favorites
 */
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AddFavoriteRequest {

    @NotBlank(message = "Stock code is required")
    private String stockCode;
}
