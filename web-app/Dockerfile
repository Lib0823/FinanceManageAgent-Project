# 1단계: Vue 빌드 (Node.js 환경)
FROM node:lts-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# 컨테이너에서는 nginx가 /api 를 api-server로 프록시하므로 상대경로(/api)로 빌드
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# 2단계: 배포 (Nginx 환경)
FROM nginx:stable-alpine as production-stage
# Nginx 설정 파일 복사
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Vue 빌드 결과물 복사
COPY --from=build-stage /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]