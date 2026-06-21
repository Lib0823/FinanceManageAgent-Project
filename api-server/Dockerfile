# syntax=docker/dockerfile:1

# 1단계: Gradle 빌드 (JDK 21) — 프로젝트의 gradle wrapper 사용
FROM eclipse-temurin:21-jdk AS build
WORKDIR /app
COPY . .
RUN chmod +x gradlew && ./gradlew bootJar --no-daemon -x test

# 2단계: 실행 (JRE 21)
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /app/build/libs/*.jar app.jar
EXPOSE 7070
ENTRYPOINT ["java", "-jar", "app.jar"]
