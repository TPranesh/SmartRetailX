# Frontend Dockerfile
FROM nginx:alpine

# Copy static frontend files to NGINX root directory
COPY . /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
