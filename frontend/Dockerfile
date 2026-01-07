FROM 10.47.0.221:5000/messenger-client:v1

COPY default.conf /etc/nginx/conf.d/default.conf
COPY prod9.keytab /etc/example.keytab
RUN mkdir -p /etc/frontend/html
COPY build /etc/nginx/html
