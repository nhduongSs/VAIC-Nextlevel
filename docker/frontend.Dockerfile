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

# NEXT_PUBLIC_* được Next.js nướng vào bundle lúc `next build`, nên phải có mặt
# NGAY TRONG build. Railway truyền service-variable vào build qua build-arg;
# khai báo ARG + ENV để `next build` nhìn thấy. Thiếu dòng này -> frontend luôn
# gọi mặc định http://localhost:8000.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Copy source rồi build ra .next (nên có frontend/.dockerignore loại node_modules/.next)
COPY . .
RUN npm run build

EXPOSE 3000

# Nghe trên $PORT do nền tảng cấp (Railway/Cloud Run), mặc định 3000 khi chạy local.
# -H 0.0.0.0 bắt buộc: mặc định next start bind vào localhost -> proxy Railway
# không với tới được (502 Bad Gateway).
CMD ["sh", "-c", "npm start -- -H 0.0.0.0 -p ${PORT:-3000}"]
