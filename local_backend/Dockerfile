FROM node:22-alpine AS three-deps
WORKDIR /deps
RUN npm install --no-save three@0.180.0

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY . .
COPY --from=three-deps /deps/node_modules/three ./vendor/three
EXPOSE 8000
CMD ["python", "local_backend/server.py"]
