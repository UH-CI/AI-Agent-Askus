FROM node:18-alpine

# Install necessary packages for crypto support
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install all dependencies (not just production)
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

# Start the application
CMD ["npm", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]
