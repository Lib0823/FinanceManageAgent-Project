# web-app 문서 (Documentation Index)

`web-app`은 AI 주식 자동매매 시스템의 **Vue 3 SPA 프런트엔드**다. 모바일 우선(mobile-first) PWA로, KOSPI 종목 분석 결과·보유 자산·AI 매매 판단을 사용자에게 보여주고, 회원가입 시 KIS(한국투자증권) 계좌를 연동한다.

이 디렉터리(`web-app/_docs/`)는 **하네스 문서**다. AI 에이전트와 사람이 이 문서들만 읽어도 모듈의 전체 구조·진행 상황·화면별 기능을 파악할 수 있도록 작성됐다. 모든 내용은 실제 소스 코드(`web-app/src/`, 설정 파일)를 직접 읽어 확인한 사실이며, 확인하지 못한 항목은 [STATUS.md](./STATUS.md)에 `미확인/TODO`로 표시했다.

## 문서 지도 (Document Map)

| 문서 | 내용 |
|------|------|
| [README.md](./README.md) | (이 문서) 모듈 소개, 문서 인덱스, 개발 명령어, 빠른 시작 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 디렉터리 구조, 라우팅 표, 상태관리(Pinia), API 레이어(axios 인터셉터·토큰), 빌드/PWA, 백엔드·AI 연동 흐름 |
| [STATUS.md](./STATUS.md) | 화면/기능별 진행 상황(완료·진행중·미착수), 실데이터 연동 현황, 미확인/TODO 항목 |
| [USAGE.md](./USAGE.md) | 설치·환경변수·개발 서버·빌드·배포(PWA/Nginx)·트러블슈팅 (사용 방법) |
| [SCREENS.md](./SCREENS.md) | 화면별 기능 설계서 — 목적, 주요 컴포넌트, 호출 API, 데이터 흐름, 실데이터/Mock 여부 |

## 기술 스택 (한눈에)

| 분류 | 기술 |
|------|------|
| Framework | Vue 3.5 (Composition API, `<script setup>`) |
| Build | Vite 7.3 + `vite-plugin-pwa` |
| Routing | Vue Router 4 (lazy-loaded views) |
| State | Pinia 2 (`stores/auth.js`) + `localStorage` (토큰) |
| HTTP | axios 1.13 (`services/api.js`, 인터셉터로 토큰 자동 주입·refresh) |
| UI | Vant 4 (모바일 컴포넌트), Tailwind CSS 4.1, v-calendar |
| Charts | Chart.js 4 + vue-chartjs (일부 화면), 그 외는 CSS/inline SVG 직접 렌더 |
| Lint/Format | ESLint 9 (flat config) + Prettier 3 |
| Deploy | Docker multi-stage → Nginx (정적 서빙, SPA fallback) |

상세 버전은 `web-app/package.json` 참조.

## 개발 명령어 (Development Commands)

```bash
cd web-app
npm install        # 의존성 설치
npm run dev        # 개발 서버 (http://localhost:5173, host:true → LAN 접근 허용)
npm run build      # 프로덕션 빌드 → dist/
npm run preview    # 빌드 결과 미리보기
npm run lint       # ESLint (--fix --cache)
npm run format     # Prettier (src/ 대상)
```

- Node: `^20.19.0 || >=22.12.0` (`package.json` engines).
- 들여쓰기: JS/Vue 2-space, 작은따옴표(`'`) 사용.

## 빠른 시작 (Quick Start)

1. **백엔드 URL 설정**: API는 `VITE_API_BASE_URL` 환경 변수로 지정한다. 미설정 시 기본값은 `http://localhost:7070/api`다 (`services/api.js`).
   ```bash
   # web-app/.env (예시)
   VITE_API_BASE_URL=http://localhost:7070/api
   ```
   > api-server는 `application.yml`의 `server.port: 7070` + context-path `/api`로 동작하며, 프런트엔드 기본값(`http://localhost:7070/api`)과 일치한다. 자세한 내용은 [ARCHITECTURE.md](./ARCHITECTURE.md#api-레이어) 참조.
2. **개발 모드 인증 우회**: `import.meta.env.DEV`일 때 라우터 가드는 인증 검사를 건너뛴다. 따라서 `npm run dev` 환경에서는 토큰 없이 모든 화면에 접근 가능하다.
3. `npm run dev` 실행 후 브라우저에서 `http://localhost:5173` 접속. 진입 경로는 `/`(Splash) → `/welcome`이다.

## 모듈 경계

- 이 문서와 디렉터리는 **`web-app` 모듈만** 다룬다. `api-server`(Spring Boot, 7070)·`ai-agent`(FastAPI, 8000)·`database`는 각 모듈 문서를 참조하라.
- 프런트엔드는 단일 axios 인스턴스로 백엔드와 통신하며, 코드상 AI 서버(8000)에 직접 호출하는 경로는 확인되지 않았다 (모두 `VITE_API_BASE_URL` 경유). 상세는 [ARCHITECTURE.md](./ARCHITECTURE.md#백엔드ai-연동-흐름).
