# USAGE

api-server 모듈을 로컬에서 실행·빌드·테스트하는 방법을 코드(`build.gradle`, `application.yml`, `.env.example`, `run-local.sh`) 기준으로 정리한다. 추측한 설정은 포함하지 않는다.

서버는 **포트 `7070`**, context-path **`/api`** 로 동작한다. 따라서 모든 엔드포인트의 실제 URL은 `http://localhost:7070/api/...` 형태다.

## 목차
1. [사전 요구사항](#1-사전-요구사항)
2. [환경 변수](#2-환경-변수)
3. [데이터베이스 준비](#3-데이터베이스-준비)
4. [실행](#4-실행)
5. [빌드 및 JAR 실행](#5-빌드-및-jar-실행)
6. [테스트](#6-테스트)
7. [Liquibase 마이그레이션](#7-liquibase-마이그레이션)
8. [개발용 테스트 계정](#8-개발용-테스트-계정)
9. [헬스 체크](#9-헬스-체크)
10. [트러블슈팅](#10-트러블슈팅)

---

## 1. 사전 요구사항

| 항목 | 요구 사항 | 근거 |
|------|-----------|------|
| JDK | Java 21 (LTS) | `build.gradle`의 `toolchain { languageVersion = JavaLanguageVersion.of(21) }` |
| 빌드 도구 | Gradle Wrapper(`./gradlew`) — 별도 설치 불필요 | 프로젝트 동봉 `gradlew` |
| 데이터베이스 | PostgreSQL (기본 `localhost:5432`, DB `financemanage`) | `application.yml`의 `spring.datasource` |

> Spring Boot 버전이 `4.1.0-SNAPSHOT`이므로 빌드 시 `repo.spring.io/snapshot` 저장소에서 의존성을 받는다(`build.gradle`에 등록됨). 네트워크 접근이 필요하다.

---

## 2. 환경 변수

부팅 시 `.env`(git-ignored)는 `DotenvEnvironmentPostProcessor`가 로드하며, OS 환경 변수가 `.env`보다 우선한다. `.env.example`를 복사해 `.env`를 작성한다.

```bash
cd api-server
cp .env.example .env
```

### `.env.example`에 정의된 변수

| 변수 | 필수 | 설명 | 비우면 |
|------|------|------|--------|
| `DART_API_KEY` | 선택 | DART(금융감독원 전자공시) Open API 키. 공시·회사개황 연동 활성화 | DART 연동 비활성, 해당 필드 null |
| `KIS_QUOTE_APP_KEY` | 선택 | KIS 시세/재무 전용 실전 도메인 app key | (둘 중 하나라도 비면) 시세/재무 연동 비활성 + notice |
| `KIS_QUOTE_APP_SECRET` | 선택 | KIS 시세/재무 전용 실전 도메인 app secret | 위와 동일 |
| `KIS_QUOTE_BASE_URL` | 선택 | KIS 시세/재무 호출 도메인. 기본값 실전 도메인 | `application.yml` 기본값(`https://openapi.koreainvestment.com:9443`) |

### `application.yml`이 참조하지만 `.env.example`에 없는 변수

아래 두 변수는 `application.yml`에서 기본값과 함께 참조된다. 기본값은 개발 편의용 placeholder이므로 **실사용 시 반드시 자체 값으로 지정**한다.

| 변수 | 권장 | 설명 |
|------|------|------|
| `JWT_SECRET` | 256bit(32자) 이상 | JWT 서명 키. 기본값은 placeholder(`financemanage-secret-key-...`)이며 운영 부적합 |
| `JASYPT_PASSWORD` | 32자 이상 | KIS appKey/appSecret 양방향 암호화(Jasypt) 비밀번호. 기본값은 placeholder |

DB 접속 정보(`spring.datasource.url/username/password`)는 `application.yml`에 하드코딩(`localhost:5432`, `admin`/`admin1234`)되어 있으며 환경 변수로 분리되어 있지 않다. 변경하려면 `application.yml`을 직접 수정한다.

`.env`, `JWT_SECRET`, `JASYPT_PASSWORD`, KIS/DART 자격증명은 절대 커밋하지 않는다.

---

## 3. 데이터베이스 준비

PostgreSQL에 `application.yml` 기본값과 일치하는 DB·계정을 만든다.

```bash
# 예시: psql로 DB/계정 생성
createdb -h localhost -p 5432 -U postgres financemanage
psql -h localhost -p 5432 -U postgres -c "CREATE USER admin WITH PASSWORD 'admin1234';"
psql -h localhost -p 5432 -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE financemanage TO admin;"
```

스키마(테이블·시드 데이터)는 직접 생성할 필요가 없다. 부팅 시 **Liquibase가 자동 적용**한다([7번 참고](#7-liquibase-마이그레이션)). JPA는 `ddl-auto: validate`로 동작하므로 엔티티-스키마 불일치가 있으면 부팅이 실패한다.

---

## 4. 실행

### 권장: `run-local.sh`

`.env`를 로드한 뒤 `./gradlew bootRun`을 실행하는 보조 스크립트다.

```bash
cd api-server
./run-local.sh
```

스크립트는 `.env` 존재 여부와 `DART_API_KEY`/`KIS_QUOTE_APP_KEY` 설정 여부를 로그로 알려준다. `.env`가 없으면 시세/재무·DART 연동이 비활성화된다는 경고를 출력하고 진행한다.

### 직접 실행

```bash
cd api-server
./gradlew bootRun
```

이 경우 `JWT_SECRET`·`JASYPT_PASSWORD` 등은 미리 `export` 하거나 `application.yml` 기본값으로 동작한다.

기동 후 기본 주소는 `http://localhost:7070/api` 다.

---

## 5. 빌드 및 JAR 실행

```bash
cd api-server
./gradlew build      # 컴파일 + 테스트 + 패키징 → build/libs/*.jar
./gradlew clean      # 빌드 산출물 정리
```

산출 JAR을 직접 실행할 수 있다(`group=com.inbeom`, `version=0.0.1-SNAPSHOT`).

```bash
# 환경 변수를 함께 주입하는 예시
JWT_SECRET=... JASYPT_PASSWORD=... \
java -jar build/libs/api-server-0.0.1-SNAPSHOT.jar
```

> `build`는 `test`를 포함한다. 테스트가 DB·외부 연동에 의존해 실패할 경우 `./gradlew build -x test`로 테스트를 건너뛸 수 있으나, 통과 가능 여부 확인을 권장한다.

---

## 6. 테스트

```bash
cd api-server
./gradlew test
```

JUnit 5(`useJUnitPlatform()`) 기반이며, 서비스 레이어 단위 테스트 위주다(자세한 테스트 현황은 [STATUS.md](./STATUS.md)의 "자동화 테스트 현황" 참고). 컨트롤러(MockMvc)·리포지토리 통합 테스트는 미작성이다.

---

## 7. Liquibase 마이그레이션

스키마는 Liquibase가 부팅 시 자동 적용한다. 별도 마이그레이션 명령을 수동 실행할 필요가 없다.

| 항목 | 값 | 근거 |
|------|-----|------|
| master changelog | `classpath:db/changelog/db.changelog-master.yaml` | `application.yml` `spring.liquibase.change-log` |
| 활성 context | `mvp` | `spring.liquibase.contexts: mvp` |
| drop-first | `false` (운영 안전) | `spring.liquibase.drop-first: false` |

`mvp` context의 changelog는 `src/main/resources/db/changelog/mvp/`에 단계별로 분리되어 있다.

| 파일 | 내용 |
|------|------|
| `v1.0-users-auth.yaml` | 사용자 인증·설정 |
| `v1.1-analysis-tables.yaml` | AI 분석 데이터 테이블 |
| `v1.2-trade-history.yaml` | 매매 실행 이력 |
| `v1.3-schema-updates.yaml` | KIS 연동·스키마 보정 |
| `v1.4-test-data.yaml` | MVP 개발용 테스트 시드 데이터 |
| `v1.5-user-settings.yaml` | 사용자 설정 테이블 |
| `v1.6-stage4-5-enhancements.yaml` | 안전 필터·매매 실행 보강 |
| `v1.7-web-display-tables.yaml` | 웹 표시용 테이블(시장 요약·실시간 시세·보유종목) |

`product` context(멀티유저·감사 로그 등)는 master 파일에 주석으로만 예약되어 있으며 아직 활성화되지 않았다.

---

## 8. 개발용 테스트 계정

`v1.4-test-data.yaml`가 MVP 개발용 시드 계정을 삽입한다(`context: mvp`에서만).

| 항목 | 값 |
|------|-----|
| username | `testuser` |
| password | `password123` (DB에는 BCrypt 해시로 저장) |
| email | `test@example.com` |
| name | 테스트유저 |

연결된 KIS 계정(`user_kis_accounts`)과 매매 설정(`user_trade_config`, `is_active=false`), 샘플 거래 이력(`trade_history`)도 함께 적재된다. KIS app_key/app_secret은 placeholder(`ENC(...)`)이므로 실제 KIS 호출은 동작하지 않는다. 운영 환경에서는 이 시드 데이터를 사용하지 않는다.

---

## 9. 헬스 체크

context-path가 `/api`이므로 actuator 포함 모든 경로는 `/api` 접두사를 가진다.

| 엔드포인트 | 설명 |
|-----------|------|
| `GET http://localhost:7070/api/health` | 애플리케이션 헬스 체크 |
| `GET http://localhost:7070/api/health/db` | DB 연결 헬스 체크 |
| `GET http://localhost:7070/api/actuator/health` | Spring Boot Actuator health (show-details: always) |
| `GET http://localhost:7070/api/actuator/info` | Actuator info |

Actuator 노출 엔드포인트는 `application.yml` `management.endpoints.web.exposure.include: health,info`로 제한되어 있다.

```bash
curl http://localhost:7070/api/health
```

---

## 10. 트러블슈팅

| 증상 | 원인 / 확인 | 조치 |
|------|-------------|------|
| 부팅 시 DB 연결 실패 | PostgreSQL 미기동 또는 `financemanage` DB/계정 불일치 | [3번](#3-데이터베이스-준비) 기준으로 DB·계정 생성. HikariCP는 `initialization-fail-timeout: 60000`으로 60초 재시도 |
| 부팅 시 스키마 validate 실패 | `ddl-auto: validate`인데 Liquibase 적용 전/엔티티 불일치 | Liquibase가 master changelog를 적용했는지, 엔티티-테이블 매핑이 맞는지 확인 |
| 시세/재무 필드가 모두 null | `KIS_QUOTE_APP_KEY`/`KIS_QUOTE_APP_SECRET` 미설정 | `.env`에 둘 다 입력. `run-local.sh` 로그의 `KIS_QUOTE_APP_KEY set: yes` 확인 |
| 공시 데이터가 비어 있음 | `DART_API_KEY` 미설정 | `.env`에 `DART_API_KEY` 입력 |
| KIS appKey/appSecret 복호화 실패 | Jasypt `JASYPT_PASSWORD`가 암호문 생성 시점과 불일치 | 동일 `JASYPT_PASSWORD` 사용. (현 MVP는 복호화 실패 시 평문 fallback이 남아 있음 — `STATUS.md` 참고) |
| JWT 검증 실패 | `JWT_SECRET` 불일치 또는 placeholder 사용 | 일관된 `JWT_SECRET`(32자 이상)을 환경 변수로 고정 |
| 로그에 KIS 자격증명 평문 노출 | `org.springframework.web` 로깅을 DEBUG로 올림 | INFO 유지. 디버깅 시에만 일시적으로 올린다(`application.yml` 주석 참고) |
| 스냅샷 의존성 다운로드 실패 | `repo.spring.io/snapshot` 접근 불가 | 네트워크/프록시 확인. Spring Boot 4.1 SNAPSHOT 사용으로 인한 제약 |

---

## 관련 문서
- [README.md](./README.md) — 문서 인덱스
- [ARCHITECTURE.md](./ARCHITECTURE.md) — 구조·레이어·외부 연동·보안
- [STATUS.md](./STATUS.md) — 구현 진행 상황·테스트 현황
- [API_DESIGN.md](./API_DESIGN.md) — 엔드포인트 명세
- [AUTHENTICATION_FLOW.md](./AUTHENTICATION_FLOW.md) — JWT 인증 흐름
- [KIS_API_GUIDE.md](./KIS_API_GUIDE.md) — KIS·DART 연동
