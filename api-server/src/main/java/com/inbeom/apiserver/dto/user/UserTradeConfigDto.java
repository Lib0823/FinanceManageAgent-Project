package com.inbeom.apiserver.dto.user;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserTradeConfigDto {

    @NotNull
    @Min(value = 100000, message = "Order amount must be at least 100,000")
    private Long orderAmount;

    @NotNull
    @Min(value = 1, message = "Max holdings must be at least 1")
    private Integer maxHoldings;

    @NotNull
    private String orderType;

    @NotNull
    private Boolean isActive;

    public static class Request {
        @Getter
        @NoArgsConstructor
        @AllArgsConstructor
        @Builder
        public static class Update {
            private Long orderAmount;
            private Integer maxHoldings;
            private String orderType;
            private Boolean isActive;
        }
    }

    public static class Response {
        @Getter
        @NoArgsConstructor
        @AllArgsConstructor
        @Builder
        public static class Detail {
            private Long orderAmount;
            private Integer maxHoldings;
            private String orderType;
            private Boolean isActive;
        }
    }
}
