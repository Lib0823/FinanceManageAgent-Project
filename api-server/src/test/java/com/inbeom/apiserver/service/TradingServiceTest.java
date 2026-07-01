package com.inbeom.apiserver.service;

import com.inbeom.apiserver.client.KisApiClient;
import com.inbeom.apiserver.domain.TradeHistory;
import com.inbeom.apiserver.domain.User;
import com.inbeom.apiserver.domain.UserKisAccount;
import com.inbeom.apiserver.dto.kis.KisDailyCcldResponse;
import com.inbeom.apiserver.dto.trade.TradeHistoryResponse;
import com.inbeom.apiserver.repository.TradeHistoryRepository;
import com.inbeom.apiserver.repository.UserRepository;
import com.inbeom.apiserver.service.KisAuthService.KisCredentials;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("TradingService 단위 테스트")
class TradingServiceTest {

    @Mock
    private KisAuthService kisAuthService;

    @Mock
    private KisApiClient kisApiClient;

    @Mock
    private TradeHistoryRepository tradeHistoryRepository;

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private TradingService tradingService;

    private User mockUser;
    private KisCredentials mockCredentials;
    private String mockKisToken;
    private Long userId;
    private Long kisAccountId;

    @BeforeEach
    void setUp() {
        userId = 1L;
        kisAccountId = 1L;
        mockKisToken = "MOCK_KIS_ACCESS_TOKEN";
        mockCredentials = new KisCredentials(
                "MOCK_APP_KEY",
                "MOCK_APP_SECRET",
                "12345678-01",
                "01"
        );

        mockUser = User.builder()
                .id(userId)
                .username("testuser")
                .email("test@example.com")
                .name("Test User")
                .build();
    }

    @Test
    @DisplayName("executeBuy - 매수 주문 실행 및 trade_history 저장 성공")
    void executeBuy_Success() {
        // Given
        String stockCode = "005930";
        String stockName = "삼성전자";
        Integer quantity = 10;
        BigDecimal orderPrice = new BigDecimal("70000");

        Map<String, Object> kisResponse = new HashMap<>();
        kisResponse.put("output", Map.of("ODNO", "ORDER123456"));
        kisResponse.put("rt_cd", "0");
        kisResponse.put("msg1", "주문이 완료되었습니다.");

        when(kisAuthService.getKisAccessToken(kisAccountId)).thenReturn(mockKisToken);
        when(kisAuthService.getKisCredentials(kisAccountId)).thenReturn(mockCredentials);
        when(userRepository.findById(userId)).thenReturn(Optional.of(mockUser));
        when(kisApiClient.post(
                eq("/uapi/domestic-stock/v1/trading/order-cash"),
                eq("VTTC0802U"),
                eq(mockKisToken),
                eq("MOCK_APP_KEY"),
                eq("MOCK_APP_SECRET"),
                anyMap(),
                eq(Map.class)
        )).thenReturn(new ResponseEntity<>(kisResponse, HttpStatus.OK));

        ArgumentCaptor<TradeHistory> tradeHistoryCaptor = ArgumentCaptor.forClass(TradeHistory.class);
        when(tradeHistoryRepository.save(any(TradeHistory.class))).thenAnswer(invocation -> invocation.getArgument(0));

        // When
        Map<String, Object> result = tradingService.executeBuy(userId, kisAccountId, stockCode, stockName, quantity, orderPrice);

        // Then
        assertThat(result).isNotNull();
        assertThat(result.get("rt_cd")).isEqualTo("0");

        verify(tradeHistoryRepository, times(1)).save(tradeHistoryCaptor.capture());
        TradeHistory savedHistory = tradeHistoryCaptor.getValue();

        assertThat(savedHistory.getUser()).isEqualTo(mockUser);
        assertThat(savedHistory.getOrderNumber()).isEqualTo("ORDER123456");
        assertThat(savedHistory.getStockCode()).isEqualTo(stockCode);
        assertThat(savedHistory.getStockName()).isEqualTo(stockName);
        assertThat(savedHistory.getOrderType()).isEqualTo("BUY");
        assertThat(savedHistory.getOrderStatus()).isEqualTo("PENDING");
        assertThat(savedHistory.getQuantity()).isEqualTo(quantity);
        assertThat(savedHistory.getOrderPrice()).isEqualTo(orderPrice);
        assertThat(savedHistory.getOrderedAt()).isNotNull();
    }

    @Test
    @DisplayName("executeSell - 매도 주문 실행 및 trade_history 저장 성공")
    void executeSell_Success() {
        // Given
        String stockCode = "005930";
        String stockName = "삼성전자";
        Integer quantity = 5;
        BigDecimal orderPrice = new BigDecimal("75000");

        Map<String, Object> kisResponse = new HashMap<>();
        kisResponse.put("output", Map.of("ODNO", "ORDER789012"));
        kisResponse.put("rt_cd", "0");

        when(kisAuthService.getKisAccessToken(kisAccountId)).thenReturn(mockKisToken);
        when(kisAuthService.getKisCredentials(kisAccountId)).thenReturn(mockCredentials);
        when(userRepository.findById(userId)).thenReturn(Optional.of(mockUser));
        when(kisApiClient.post(
                eq("/uapi/domestic-stock/v1/trading/order-cash"),
                eq("VTTC0801U"),
                anyString(),
                anyString(),
                anyString(),
                anyMap(),
                eq(Map.class)
        )).thenReturn(new ResponseEntity<>(kisResponse, HttpStatus.OK));

        ArgumentCaptor<TradeHistory> tradeHistoryCaptor = ArgumentCaptor.forClass(TradeHistory.class);
        when(tradeHistoryRepository.save(any(TradeHistory.class))).thenAnswer(invocation -> invocation.getArgument(0));

        // When
        Map<String, Object> result = tradingService.executeSell(userId, kisAccountId, stockCode, stockName, quantity, orderPrice);

        // Then
        assertThat(result).isNotNull();

        verify(tradeHistoryRepository, times(1)).save(tradeHistoryCaptor.capture());
        TradeHistory savedHistory = tradeHistoryCaptor.getValue();

        assertThat(savedHistory.getOrderType()).isEqualTo("SELL");
        assertThat(savedHistory.getOrderStatus()).isEqualTo("PENDING");
        assertThat(savedHistory.getOrderNumber()).isEqualTo("ORDER789012");
    }

    @Test
    @DisplayName("executeBuy - 사용자 없을 때 예외 발생")
    void executeBuy_UserNotFound_ThrowsException() {
        // Given
        when(kisAuthService.getKisAccessToken(kisAccountId)).thenReturn(mockKisToken);
        when(kisAuthService.getKisCredentials(kisAccountId)).thenReturn(mockCredentials);
        when(userRepository.findById(userId)).thenReturn(Optional.empty());

        Map<String, Object> kisResponse = new HashMap<>();
        kisResponse.put("output", Map.of("ODNO", "ORDER123"));
        when(kisApiClient.post(anyString(), anyString(), anyString(), anyString(), anyString(), anyMap(), eq(Map.class)))
                .thenReturn(new ResponseEntity<>(kisResponse, HttpStatus.OK));

        // When & Then
        assertThatThrownBy(() ->
                tradingService.executeBuy(userId, kisAccountId, "005930", "삼성전자", 10, new BigDecimal("70000"))
        )
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("User not found: 1");
    }

    @Test
    @DisplayName("getTradeHistory - 사용자 거래 내역 조회 성공 (KIS inquire-daily-ccld 직접 조회)")
    void getTradeHistory_Success() {
        // Given: 거래내역은 DB가 아니라 KIS API(VTTC0081R)를 직접 조회해 TradeHistoryResponse 로 매핑한다.
        UserKisAccount kisAccount = mock(UserKisAccount.class);
        User userWithKis = mock(User.class);
        when(userWithKis.getKisAccount()).thenReturn(kisAccount);
        when(kisAccount.getId()).thenReturn(kisAccountId);

        KisDailyCcldResponse.DailyCcldItem item1 = new KisDailyCcldResponse.DailyCcldItem();
        item1.setOdno("ORDER001");
        item1.setPdno("005930");
        item1.setPrdtName("삼성전자");
        item1.setSllBuyDvsnCd("02");  // 02: 매수 → BUY
        item1.setOrdDt("20260601");
        item1.setOrdTmd("093000");
        item1.setOrdQty("10");
        item1.setOrdUnpr("70000");
        item1.setTotCcldQty("10");
        item1.setTotCcldAmt("700000");
        item1.setAvgPrvs("70000");

        KisDailyCcldResponse.DailyCcldItem item2 = new KisDailyCcldResponse.DailyCcldItem();
        item2.setOdno("ORDER002");
        item2.setPdno("000660");
        item2.setPrdtName("SK하이닉스");
        item2.setSllBuyDvsnCd("01");  // 01: 매도 → SELL
        item2.setOrdDt("20260601");
        item2.setOrdTmd("100500");
        item2.setOrdQty("5");
        item2.setOrdUnpr("120000");
        item2.setTotCcldQty("5");
        item2.setTotCcldAmt("600000");
        item2.setAvgPrvs("120000");

        KisDailyCcldResponse kisResponse = new KisDailyCcldResponse();
        kisResponse.setRtCd("0");
        kisResponse.setOutput1(List.of(item1, item2));

        when(userRepository.findById(userId)).thenReturn(Optional.of(userWithKis));
        when(kisAuthService.getKisAccessToken(kisAccountId)).thenReturn(mockKisToken);
        when(kisAuthService.getKisCredentials(kisAccountId)).thenReturn(mockCredentials);
        when(kisApiClient.get(
                anyString(), anyString(), anyString(), anyString(), anyString(),
                anyMap(), eq(KisDailyCcldResponse.class)
        )).thenReturn(new ResponseEntity<>(kisResponse, HttpStatus.OK));

        // When
        List<TradeHistoryResponse> result = tradingService.getTradeHistory(userId);

        // Then
        assertThat(result).hasSize(2);
        assertThat(result.get(0).getStockCode()).isEqualTo("005930");
        assertThat(result.get(0).getOrderType()).isEqualTo("BUY");
        assertThat(result.get(0).getId()).isEqualTo("ORDER001");
        assertThat(result.get(1).getStockCode()).isEqualTo("000660");
        assertThat(result.get(1).getOrderType()).isEqualTo("SELL");

        verify(kisApiClient, times(1)).get(
                anyString(), anyString(), anyString(), anyString(), anyString(),
                anyMap(), eq(KisDailyCcldResponse.class));
    }

    @Test
    @DisplayName("extractOrderNumber - KIS 응답에서 주문번호 추출 성공")
    void extractOrderNumber_Success() {
        // Given
        Map<String, Object> kisResponse = new HashMap<>();
        kisResponse.put("output", Map.of("ODNO", "ORDER999888"));

        when(kisAuthService.getKisAccessToken(kisAccountId)).thenReturn(mockKisToken);
        when(kisAuthService.getKisCredentials(kisAccountId)).thenReturn(mockCredentials);
        when(userRepository.findById(userId)).thenReturn(Optional.of(mockUser));
        when(kisApiClient.post(anyString(), anyString(), anyString(), anyString(), anyString(), anyMap(), eq(Map.class)))
                .thenReturn(new ResponseEntity<>(kisResponse, HttpStatus.OK));

        ArgumentCaptor<TradeHistory> tradeHistoryCaptor = ArgumentCaptor.forClass(TradeHistory.class);
        when(tradeHistoryRepository.save(any(TradeHistory.class))).thenAnswer(invocation -> invocation.getArgument(0));

        // When
        tradingService.executeBuy(userId, kisAccountId, "005930", "삼성전자", 10, new BigDecimal("70000"));

        // Then
        verify(tradeHistoryRepository).save(tradeHistoryCaptor.capture());
        assertThat(tradeHistoryCaptor.getValue().getOrderNumber()).isEqualTo("ORDER999888");
    }
}
