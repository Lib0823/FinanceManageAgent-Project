package com.inbeom.apiserver.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import javax.xml.stream.XMLInputFactory;
import javax.xml.stream.XMLStreamConstants;
import javax.xml.stream.XMLStreamReader;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * DART (금융감독원 전자공시) Open API 클라이언트.
 *
 * 포팅 출처: ai-agent/collectors/dart_client.py
 *  - download_corp_code_list / get_corp_code : corpCode.xml(ZIP) → stock_code→corp_code 매핑
 *  - company.json : 회사개황
 *  - list.json    : 공시검색
 *
 * 키(dart.api-key)가 비어있으면 DART 연동 전체를 skip 하고 호출 측은 null 을 받는다.
 * corp_code 매핑은 최초 사용 시 1회 lazy 다운로드 후 메모리 캐시.
 */
@Slf4j
@Component
public class DartApiClient {

    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${dart.api-key:}")
    private String dartApiKey;

    @Value("${dart.base-url:https://opendart.fss.or.kr/api}")
    private String dartBaseUrl;

    // stock_code(6-digit) → corp_code(8-digit)
    private final Map<String, String> corpCodeMap = new ConcurrentHashMap<>();
    private final AtomicBoolean corpCodeLoaded = new AtomicBoolean(false);

    /**
     * DART API 사용 가능 여부 (키 설정 여부)
     */
    public boolean isEnabled() {
        return dartApiKey != null && !dartApiKey.isBlank();
    }

    /**
     * stock_code → corp_code 해석. 매핑이 없거나 DART 비활성이면 null.
     */
    public String getCorpCode(String stockCode) {
        if (!isEnabled() || stockCode == null) {
            return null;
        }
        ensureCorpCodeLoaded();
        // 6자리 zero-pad 후 조회
        String normalized = normalizeStockCode(stockCode);
        return corpCodeMap.get(normalized);
    }

    private String normalizeStockCode(String stockCode) {
        String trimmed = stockCode.trim();
        if (trimmed.length() >= 6) {
            return trimmed;
        }
        return String.format("%6s", trimmed).replace(' ', '0');
    }

    /**
     * corpCode.xml(ZIP) 다운로드 + 파싱 (최초 1회). 실패해도 throw 하지 않고
     * 빈 매핑을 유지하여 호출 측이 null corp_code 로 degrade 하도록 한다.
     */
    private void ensureCorpCodeLoaded() {
        if (corpCodeLoaded.get()) {
            return;
        }
        synchronized (corpCodeMap) {
            if (corpCodeLoaded.get()) {
                return;
            }
            try {
                String url = UriComponentsBuilder.fromUriString(dartBaseUrl + "/corpCode.xml")
                        .queryParam("crtfc_key", dartApiKey)
                        .build()
                        .toUriString();

                log.info("Downloading DART corpCode.xml ...");
                ResponseEntity<byte[]> response =
                        restTemplate.getForEntity(url, byte[].class);

                byte[] body = response.getBody();
                if (body == null || body.length == 0) {
                    log.warn("DART corpCode.xml response empty; corp_code mapping unavailable");
                    corpCodeLoaded.set(true);
                    return;
                }

                parseCorpCodeZip(body);
                log.info("DART corp_code mapping complete: {} listed companies", corpCodeMap.size());
            } catch (Exception e) {
                log.warn("Failed to load DART corp_code mapping (DART features will degrade to null): {}",
                        e.getMessage());
            } finally {
                corpCodeLoaded.set(true);
            }
        }
    }

    /**
     * ZIP 안의 CORPCODE.xml 을 StAX 로 스트리밍 파싱하여
     * stock_code 가 있는(상장) 회사만 corpCodeMap 에 적재.
     */
    private void parseCorpCodeZip(byte[] zipBytes) throws Exception {
        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(zipBytes))) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                if (entry.getName().toUpperCase().endsWith("CORPCODE.XML")) {
                    parseCorpCodeXml(zis);
                    return;
                }
            }
            log.warn("CORPCODE.xml not found inside DART ZIP response");
        }
    }

    private void parseCorpCodeXml(InputStream xmlStream) throws Exception {
        XMLInputFactory factory = XMLInputFactory.newFactory();
        // XXE 방지
        factory.setProperty(XMLInputFactory.IS_SUPPORTING_EXTERNAL_ENTITIES, false);
        factory.setProperty(XMLInputFactory.SUPPORT_DTD, false);

        XMLStreamReader reader = factory.createXMLStreamReader(xmlStream);

        String corpCode = null;
        String stockCode = null;
        String currentElement = null;

        try {
            while (reader.hasNext()) {
                int event = reader.next();
                switch (event) {
                    case XMLStreamConstants.START_ELEMENT:
                        currentElement = reader.getLocalName();
                        if ("list".equals(currentElement)) {
                            corpCode = null;
                            stockCode = null;
                        }
                        break;
                    case XMLStreamConstants.CHARACTERS:
                        if (currentElement != null && !reader.isWhiteSpace()) {
                            String text = reader.getText();
                            if ("corp_code".equals(currentElement)) {
                                corpCode = append(corpCode, text);
                            } else if ("stock_code".equals(currentElement)) {
                                stockCode = append(stockCode, text);
                            }
                        }
                        break;
                    case XMLStreamConstants.END_ELEMENT:
                        if ("list".equals(reader.getLocalName())) {
                            if (corpCode != null && stockCode != null) {
                                String sc = stockCode.trim();
                                String cc = corpCode.trim();
                                if (!sc.isEmpty() && !cc.isEmpty()) {
                                    corpCodeMap.put(sc, cc);
                                }
                            }
                        }
                        currentElement = null;
                        break;
                    default:
                        break;
                }
            }
        } finally {
            reader.close();
        }
    }

    private String append(String existing, String text) {
        return existing == null ? text : existing + text;
    }

    /**
     * 회사개황 (company.json). 실패/비정상 시 null.
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getCompanyProfile(String corpCode) {
        if (!isEnabled() || corpCode == null || corpCode.isBlank()) {
            return null;
        }
        try {
            String url = UriComponentsBuilder.fromUriString(dartBaseUrl + "/company.json")
                    .queryParam("crtfc_key", dartApiKey)
                    .queryParam("corp_code", corpCode)
                    .build()
                    .toUriString();

            ResponseEntity<Map> response =
                    restTemplate.exchange(url, HttpMethod.GET, null, Map.class);
            Map<String, Object> body = response.getBody();
            if (body == null) {
                return null;
            }
            String status = String.valueOf(body.get("status"));
            if (!"000".equals(status)) {
                log.warn("DART company.json status={} for corp_code={}", status, corpCode);
                return null;
            }
            return body;
        } catch (Exception e) {
            log.warn("DART company.json call failed for corp_code={}: {}", corpCode, e.getMessage());
            return null;
        }
    }

    /**
     * 공시검색 (list.json). status 000=정상, 013=데이터없음(빈 결과).
     * 실패 시 null (호출 측에서 빈 리스트로 처리).
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getDisclosureList(String corpCode, String beginDate, String endDate, int pageCount) {
        if (!isEnabled() || corpCode == null || corpCode.isBlank()) {
            return null;
        }
        try {
            String url = UriComponentsBuilder.fromUriString(dartBaseUrl + "/list.json")
                    .queryParam("crtfc_key", dartApiKey)
                    .queryParam("corp_code", corpCode)
                    .queryParam("bgn_de", beginDate)
                    .queryParam("end_de", endDate)
                    .queryParam("page_count", pageCount)
                    .build()
                    .toUriString();

            ResponseEntity<Map> response =
                    restTemplate.exchange(url, HttpMethod.GET, null, Map.class);
            Map<String, Object> body = response.getBody();
            if (body == null) {
                return null;
            }
            String status = String.valueOf(body.get("status"));
            if ("013".equals(status)) {
                // 데이터 없음 → 빈 결과로 처리
                return body;
            }
            if (!"000".equals(status)) {
                log.warn("DART list.json status={} for corp_code={}", status, corpCode);
                return null;
            }
            return body;
        } catch (Exception e) {
            log.warn("DART list.json call failed for corp_code={}: {}", corpCode, e.getMessage());
            return null;
        }
    }
}
