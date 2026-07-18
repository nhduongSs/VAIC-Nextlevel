# Frontend Next.js 14.
#
# Build context PHẢI là ./frontend (nơi có package.json + source), Dockerfile này
# chỉ nằm ở docker/ cho đồng bộ. Cách build:
#   compose : context: ./frontend, dockerfile: ../docker/frontend.Dockerfile
#   CLI     : docker build -f docker/frontend.Dockerfile -t frontend ./frontend
#   Railway : Root Directory = frontend + RAILWAY_DOCKERFILE_PATH = docker/frontend.Dockerfile
FROM node:20-slim

WORKDIR /app

# Cài dependencies theo lock file để build tái lập
COPY package*.json ./
RUN npm ci

# Copy source rồi build ra .next (nên có frontend/.dockerignore loại node_modules/.next)
COPY . .
RUN npm run build

EXPOSE 3000

# Next.js lắng nghe cổng do nền tảng cấp qua $PORT (Railway/Cloud Run);
# mặc định 3000 khi chạy local/compose.
CMD ["sh", "-c", "npm start -- -p ${PORT:-3000}"]
