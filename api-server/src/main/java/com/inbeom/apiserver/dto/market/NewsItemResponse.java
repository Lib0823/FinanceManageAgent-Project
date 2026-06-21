package com.inbeom.apiserver.dto.market;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 홈 화면 "속보" 위젯용 뉴스 항목.
 * 한국경제/매일경제/연합뉴스 경제 RSS 피드를 병합·정렬해 최신 항목을 전달한다.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NewsItemResponse {

    @JsonProperty("id")
    private String id;

    @JsonProperty("title")
    private String title;

    @JsonProperty("description")
    private String description;

    @JsonProperty("source")
    private String source;

    @JsonProperty("date")
    private String date;

    @JsonProperty("link")
    private String link;

    @JsonProperty("image")
    private String image;
}
