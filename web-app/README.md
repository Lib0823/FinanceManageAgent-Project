# web-app

AI 주식 자동매매 시스템의 **Vue 3 SPA 프런트엔드** (모바일 우선 PWA). KOSPI 종목 분석 결과·보유 자산·AI 매매 판단을 사용자에게 보여주고, 회원가입 시 KIS(한국투자증권) 계좌를 연동한다.

## 문서

전체 구조·진행 상황·화면 설계는 **[`_docs/`](./_docs/README.md)** 를 참조하라.

| 문서 | 내용 |
|------|------|
| [_docs/README.md](./_docs/README.md) | 문서 인덱스, 기술 스택, 개발 명령어, 빠른 시작 |
| [_docs/ARCHITECTURE.md](./_docs/ARCHITECTURE.md) | 디렉터리 구조, 라우팅 표, 상태관리, API 레이어, 빌드/PWA, 연동 흐름 |
| [_docs/SCREENS.md](./_docs/SCREENS.md) | 화면별 기능 설계서(목적·컴포넌트·API·데이터 흐름) |
| [_docs/STATUS.md](./_docs/STATUS.md) | 화면/기능별 진행 상황, 실데이터 연동 현황, 미확인/TODO |

## 개발 명령어

```bash
npm install        # 의존성 설치
npm run dev        # 개발 서버 (http://localhost:5173)
npm run build      # 프로덕션 빌드 → dist/
npm run preview    # 빌드 결과 미리보기
npm run lint       # ESLint (--fix --cache)
npm run format     # Prettier (src/)
```

## 핵심 스택

Vue 3.5 (Composition API) · Vite 7.3 + PWA · Vue Router 4 · Pinia 2 · axios · Vant 4 · Tailwind CSS 4.1 · Chart.js. 배포는 Docker(multi-stage) → Nginx.

- API 베이스 URL: `VITE_API_BASE_URL` (코드 기본값 `http://localhost:7070/api`).
- 개발 모드(`import.meta.env.DEV`)에서는 라우터 인증 가드가 우회된다.

상세 버전·설정은 [`_docs/ARCHITECTURE.md`](./_docs/ARCHITECTURE.md)와 `package.json` 참조.
