FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ARG EMANE_VERSION=1.5.3-release-1

RUN apt-get update && apt-get install -y --no-install-recommends \
        wget ca-certificates iproute2 iputils-ping iperf3 net-tools \
        python3 python3-lxml python3-protobuf python3-networkx procps \
    && rm -rf /var/lib/apt/lists/*

RUN cd /tmp \
    && wget -q https://adjacentlink.com/downloads/emane/emane-${EMANE_VERSION}.ubuntu-22_04.amd64.tar.gz \
    && tar xzf emane-${EMANE_VERSION}.ubuntu-22_04.amd64.tar.gz \
    && (dpkg -i emane-${EMANE_VERSION}/debs/ubuntu-22_04/amd64/*.deb || true) \
    && apt-get update && apt-get install -f -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* /tmp/emane-*

WORKDIR /work
