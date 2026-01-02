FROM temporalio/admin-tools:1.29.1-tctl-1.18.4-cli-1.5.0

USER root

RUN sed -i -e 's/v3.22/v3.23/g' /etc/apk/repositories \
  && apk update \
  && apk upgrade sqlite sqlite-libs
