FROM node:18-alpine

WORKDIR /usr/src/app

COPY package.json ./

RUN npm install

COPY signaling-server.js ./

EXPOSE 8080

CMD [ "node", "signaling-server.js" ]