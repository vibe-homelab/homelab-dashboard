# Homelab Dashboard

모든 vibe-homelab 서비스의 상태를 모니터링하고 관리하는 대시보드입니다.

## Features

- **서비스 모니터링**: Vision Insight, Voice Insight 등 서비스 상태 실시간 확인
- **워커 제어**: 워커 시작/중지/강제종료
- **메모리 모니터링**: 시스템 메모리 사용량 확인
- **실시간 업데이트**: WebSocket 기반 실시간 상태 반영

## Quick Start

### Docker (권장)

```bash
# 빌드 및 실행
make build
make start

# 브라우저에서 http://localhost:3000 접속
```

### Development

```bash
# 의존성 설치
make install

# Backend 실행 (터미널 1)
make dev-backend

# Frontend 실행 (터미널 2)
make dev-frontend

# 브라우저에서 http://localhost:3000 접속
```

## Configuration

`backend/config.yaml`에서 모니터링할 서비스를 설정합니다:

```yaml
services:
  vision-insight:
    name: "Vision Insight API"
    gateway:
      host: "localhost"
      port: 8000
    worker_manager:
      host: "localhost"
      port: 8100
    workers:
      - alias: "vlm-fast"
        name: "Vision LM (Fast)"
        type: "vlm"
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Browser (:3000)                    │
└─────────────────────────┬───────────────────────────┘
                          │
          ┌───────────────▼───────────────┐
          │     Frontend (React)          │
          │     - Dashboard UI            │
          │     - WebSocket Client        │
          └───────────────┬───────────────┘
                          │
          ┌───────────────▼───────────────┐
          │     Backend (FastAPI) :8080   │
          │     - REST API                │
          │     - WebSocket Server        │
          │     - Health Checker          │
          └───────────────┬───────────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
    ▼                     ▼                     ▼
┌───────────┐      ┌───────────┐        ┌───────────┐
│  Vision   │      │   Voice   │        │  Future   │
│  Insight  │      │  Insight  │        │  Service  │
│  :8000    │      │  :8001    │        │           │
└───────────┘      └───────────┘        └───────────┘
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | 대시보드 헬스체크 |
| `/api/v1/services` | GET | 서비스 목록 및 상태 |
| `/api/v1/services/{id}` | GET | 특정 서비스 상세 정보 |
| `/api/v1/services/{id}/workers/{alias}/spawn` | POST | 워커 시작 |
| `/api/v1/services/{id}/workers/{alias}/stop` | POST | 워커 중지 |
| `/api/v1/system/overview` | GET | 시스템 개요 |
| `/ws` | WebSocket | 실시간 업데이트 |

## Tech Stack

- **Backend**: Python 3.12, FastAPI, WebSocket
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Zustand
- **Container**: Docker, docker-compose

## License

MIT
