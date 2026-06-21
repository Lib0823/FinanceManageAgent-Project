# USAGE — web-app 사용·개발 방법

`web-app`(Vue 3 SPA)를 로컬에서 실행하고, 빌드하고, 배포하는 방법을 정리한다. 모든 명령어·설정값은 `package.json`·`vite.config.js`·`nginx.conf`·`Dockerfile`·`src/services/api.js`·`src/router/index.js`를 직접 확인한 사실 기준이다.

> 구조·라우팅·연동 흐름은 [ARCHITECTURE.md](./ARCHITECTURE.md), 화면별 기능은 [SCREENS.md](./SCREENS.md), 진행 상황은 [STATUS.md](./STATUS.md) 참조.

## 1. 사전 요구사항 (Prerequisites)

| 항목 | 요구 | 근거 |
|------|------|------|
| Node.js | `^20.19.0 || >=22.12.0` | `package.json` `engines` |
| npm | Node 동봉 버전 | 별도 패키지 매니저 설정 없음 (`package-lock.json` 사용) |
| 백엔드(선택) | api-server(7070) 구동 시 실데이터 연동 | `services/api.js` 기본 baseURL |

- Node 20 LTS 이상이면 동작한다. lockfile은 `package-lock.json`이므로 `npm`을 사용한다(yarn/pnpm 설정 없음).
- 백엔드 없이도 dev 모드에서 화면을 띄울 수 있다(아래 §6 dev 인증 우회 + 일부 화면 Mock 폴백 참조). 실데이터를 보려면 `api-server`(7070)가 떠 있어야 한다.

## 2. 설치 (Install)

```bash
cd web-app
npm install        # 의존성 설치 (package-lock.json 기준)
```

## 3. 환경 변수 (Environment Variables)

이 모듈이 읽는 환경 변수는 **`VITE_API_BASE_URL` 하나**다(`services/api.js`). 그 외 변수는 코드상 사용되지 않는다.

| 변수 | 기본값 (미설정 시) | 용도 |
|------|------|------|
| `VITE_API_BASE_URL` | `http://localhost:7070/api` | axios 인스턴스 baseURL. 모든 백엔드 호출의 접두 경로 |

- 기본값은 api-server `application.yml`의 `server.port: 7070` + context-path `/api`와 일치한다. 즉 **api-server를 로컬 기본 설정으로 띄우면 환경 변수 없이도 그대로 연동된다.**
- 리포지터리에 `.env`/`.env.example` 파일은 **없다**(확인됨). 값을 바꾸려면 `web-app/` 아래에 `.env`를 직접 만든다. Vite 규칙상 `VITE_` 접두 변수만 클라이언트 번들에 노출된다.

```bash
# web-app/.env (예시, 기본값과 다르게 쓰고 싶을 때만)
VITE_API_BASE_URL=http://localhost:7070/api
```

> 배포 시 주의: 빌드 시점에 `VITE_*` 값이 번들에 박힌다. 운영 도메인으로 호출하려면 **빌드 전에** `VITE_API_BASE_URL`을 지정해야 한다.

## 4. 개발 서버 (Development)

```bash
npm run dev        # Vite dev server
```

| 항목 | 값 | 근거 |
|------|------|------|
| 주소 | `http://localhost:5173` | `vite.config.js` `server.port: 5173` |
| LAN 접근 | 허용 | `server.host: true` → `http://<LAN-IP>:5173`로도 접속 가능 |
| 진입 경로 | `/`(Splash) → `/welcome` | `src/router/index.js` |

- HMR(핫 리로드) 기본 활성. `vite-plugin-vue-devtools`로 Vue DevTools 통합.

## 5. 빌드·미리보기 (Build & Preview)

```bash
npm run build      # 프로덕션 빌드 → dist/
npm run preview    # dist/ 결과를 로컬에서 정적 서빙 (빌드 검증용)
```

- 산출물은 `dist/`에 생성된다(`.gitignore`에 포함되어 커밋되지 않음).
- `preview`는 빌드 결과 확인용이며, 실제 운영 서빙은 Nginx(§7)가 담당한다.

## 6. 린트·포맷 (Lint & Format)

```bash
npm run lint       # ESLint, .을 대상으로 --fix --cache
npm run format     # Prettier, src/ 대상 --write
```

| 도구 | 설정 파일 | 비고 |
|------|------|------|
| ESLint 9 | `eslint.config.js` (flat config) | `eslint . --fix --cache` (`.eslintcache` 생성, gitignore됨) |
| Prettier 3 | `.prettierrc.json` | `src/`만 포맷. `--experimental-cli` 플래그 사용 |

- 코드 스타일: JS/Vue **2-space 들여쓰기, 작은따옴표(`'`)**.
- 자동화 테스트 스크립트(`npm test` 등)는 **없다**(`package.json`에 test·Vitest 미정의 — [STATUS.md](./STATUS.md) §3 참조).

## 7. 배포 (PWA / Nginx / Docker)

빌드된 정적 자산을 Nginx로 서빙하는 **2-stage Docker** 구성이다.

**`Dockerfile` (2-stage):**
1. `node:lts-alpine` (build-stage): `npm install` → `npm run build` → `/app/dist` 생성.
2. `nginx:stable-alpine` (production-stage): `nginx.conf`를 `/etc/nginx/conf.d/default.conf`로, `dist/`를 `/usr/share/nginx/html`로 복사. `EXPOSE 80`.

```bash
cd web-app
docker build -t web-app .
docker run -p 3000:80 web-app   # 호스트 3000 → 컨테이너 80 (모노레포 compose 매핑 기준)
```

**`nginx.conf` 핵심:**
- **SPA fallback**: `location / { try_files $uri $uri/ /index.html; }` — 모든 라우트를 `index.html`로 폴백(Vue Router history 모드 지원).
- **정적 캐싱**: js/css/이미지/폰트는 `expires 1y` + `immutable`.
- **PWA 무캐시**: `manifest.webmanifest`·`sw.js`·`workbox-*.js`는 `no-cache`로 강제(자동 업데이트 보장).
- **gzip** 및 보안 헤더(`X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`) 적용.
- API 프록시 블록(`location /api { proxy_pass ... }`)은 **주석 처리된 상태**다. 현재 프런트는 `VITE_API_BASE_URL`로 직접 백엔드를 호출하므로 Nginx 프록시는 사용하지 않는다. 같은 도메인에서 `/api`를 프록시하려면 이 블록을 해제·수정한다(주석 예시의 `backend:8000`은 api-server 포트 **7070**으로 정정 필요).

**PWA:**
- `vite-plugin-pwa`(`registerType: 'autoUpdate'`)로 service worker 자동 생성·갱신. manifest 앱 이름 `F. Finance App`, `display: standalone`, 아이콘 `logo.png`(192/512). 설치형 앱으로 동작(실기기 설치 검증은 [STATUS.md](./STATUS.md) 미확인 항목).

## 8. 개발 모드 인증 우회 (Dev Auth Bypass)

`src/router/index.js`의 네비게이션 가드는 `import.meta.env.DEV`일 때 인증 검사를 건너뛴다.

```js
if (import.meta.env.DEV) { next(); return }   // dev: 모든 화면 토큰 없이 접근
// production: authRequired && !token → /welcome 리다이렉트
```

- `npm run dev`(DEV=true): 토큰 없이 모든 보호 화면 접근 가능.
- 프로덕션 빌드(DEV=false): 공개 경로(`/`, `/welcome`, `/login`, `/register`, `/register/finance`, `/terms`, `/reset-password`) 외에는 `localStorage`의 `accessToken`이 없으면 `/welcome`으로 리다이렉트.

## 9. 트러블슈팅 (Troubleshooting)

| 증상 | 원인 | 조치 |
|------|------|------|
| API 호출이 전부 실패/CORS 오류 | api-server(7070) 미구동 또는 baseURL 불일치 | api-server 기동 확인. 포트가 다르면 `VITE_API_BASE_URL` 설정 후 dev 재시작 |
| 화면은 뜨는데 데이터가 Mock | 백엔드 미연동 화면이거나 폴백 동작 | [STATUS.md](./STATUS.md) §1에서 화면별 실데이터/Mock 여부 확인 |
| 401 후 `/login`으로 튕김 | refresh token 만료/부재 → 인터셉터가 `localStorage.clear()` 후 리다이렉트 | 재로그인. dev에서는 가드 우회되나 API 401은 그대로 발생 |
| 거래내역 요청 타임아웃 | KIS 응답 지연 | 거래내역은 25s 타임아웃 적용됨(`tradingApi.getHistory`). 그래도 실패 시 백엔드/KIS 상태 확인 |
| `npm install` 또는 빌드 실패 | Node 버전 미달 | Node `^20.19.0 || >=22.12.0` 사용(`package.json` engines) |
| 환경 변수 변경이 반영 안 됨 | Vite는 빌드/기동 시점에 `VITE_*`를 주입 | `.env` 수정 후 dev 서버 재시작, 운영은 재빌드 |
| 라우트 새로고침 시 404 (배포) | SPA fallback 미설정 | Nginx `try_files ... /index.html` 확인(`nginx.conf`에 포함됨) |

## 10. 명령어 한눈에 (Quick Reference)

| 명령어 | 설명 | 결과 |
|------|------|------|
| `npm install` | 의존성 설치 | `node_modules/` |
| `npm run dev` | 개발 서버 | `http://localhost:5173` |
| `npm run build` | 프로덕션 빌드 | `dist/` |
| `npm run preview` | 빌드 결과 미리보기 | 로컬 정적 서빙 |
| `npm run lint` | ESLint(--fix --cache) | 코드 수정 |
| `npm run format` | Prettier(src/) | 코드 포맷 |
| `docker build -t web-app .` | 2-stage 이미지 빌드 | Nginx 이미지 |
| `docker run -p 3000:80 web-app` | 컨테이너 실행 | `http://localhost:3000` |
