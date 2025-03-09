# Use the official Node.js 14 image as the base image
FROM node:20.16.0

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code to the working directory
COPY . .

# Start the Next.js app and set port to environment variable SITE_PORT
CMD ["npm", "run", "dev"]