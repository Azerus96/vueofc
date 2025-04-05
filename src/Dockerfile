# Stage 1: Build the application
FROM node:18-alpine as builder
WORKDIR /app
COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./
# Улучшенная установка зависимостей
RUN if [ -f pnpm-lock.yaml ]; then npm install -g pnpm && pnpm install --frozen-lockfile; \
    elif [ -f yarn.lock ]; then yarn install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; \
    else npm install; fi
COPY . .
# Запускаем сборку Vite (которая вызовет vite-plugin-singlefile)
RUN npm run build

# Stage 2: Serve the application using Nginx
FROM nginx:1.25-alpine
# Копируем собранный index.html (и другие возможные статические файлы из dist, если есть)
COPY --from=builder /app/dist /usr/share/nginx/html
# Убедимся, что Nginx отдает index.html для любых путей (важно для SPA)
COPY <<EOF /etc/nginx/conf.d/default.conf
server {
    listen       80;
    server_name  localhost;
    # Включаем gzip сжатие для ускорения загрузки
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/xml+rss application/atom+xml image/svg+xml;

    location / {
        root   /usr/share/nginx/html;
        index  index.html index.htm;
        try_files \$uri \$uri/ /index.html; # Отдавать index.html если файл не найден
    }

    error_page   500 502 503 504  /50x.html;
    location = /50x.html {
        root   /usr/share/nginx/html;
    }
}
EOF

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
