FROM node:20-alpine

WORKDIR /app

# Copy package files first
COPY package.json ./
COPY yarn.lock ./

# Install dependencies (remove --frozen-lockfile for development flexibility)
RUN yarn install --network-timeout 100000

# Copy application code
COPY . .

# Build the application
RUN yarn build

# Install serve to run the production build
RUN yarn global add serve

# Expose port
EXPOSE 3000

# Run the application
CMD ["serve", "-s", "build", "-l", "3000"]
