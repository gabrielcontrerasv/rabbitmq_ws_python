# Etapa de compilación
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN npm run build

# Etapa de exposición
FROM node:20-alpine
WORKDIR /app
COPY --from=build /app/dist /app/dist
RUN npm install -g serve
EXPOSE 5000
CMD ["serve", "-s", "dist", "-l", "5000"]
