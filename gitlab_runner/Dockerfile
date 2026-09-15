FROM gitlab/gitlab-runner:alpine-v19.3.2

USER root

# CVE-2026-60002: use-after-free in the OpenSSH client when a server changes
# its host key during key re-exchange. Fixed in Alpine by openssh 10.3_p1-r1.
#
# Alpine v3.24 (this base) tops out at openssh 10.3_p1-r1, so the newer client
# is pulled from the edge branch. The constraint is a floor rather than a pin:
# edge currently serves 10.5_p1-r1, and 10.4 was superseded there.
RUN apk update \
  && apk add --no-cache --upgrade \
       --repository https://dl-cdn.alpinelinux.org/alpine/edge/main \
       'openssh-client-common>=10.4_p1' \
       'openssh-client-default>=10.4_p1' \
       'openssh-keygen>=10.4_p1' \
  && rm -rf /var/cache/apk/*
