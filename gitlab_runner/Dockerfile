FROM gitlab/gitlab-runner:alpine-v19.3.2

USER root

# CVE-2026-60002: use-after-free in the OpenSSH client when a server changes
# its host key during key re-exchange. Fixed in Alpine by openssh 10.3_p1-r1.
RUN apk update \
  && apk upgrade --no-cache openssh-client-common openssh-client-default openssh-keygen \
  && rm -rf /var/cache/apk/*
