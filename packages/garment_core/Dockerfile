# garment_core — üretim imajı (Node 20, TypeScript derlemesi)
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json ./
RUN npm install
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY package.json ./
RUN npm install --omit=dev
COPY --from=builder /app/dist ./dist
COPY VERSION ./

ENV PORT=8080
EXPOSE 8080

USER node
CMD ["node", "dist/index.js"]
