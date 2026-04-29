FROM ubuntu:24.04

LABEL maintainer="@MR_ARMAN_08"
LABEL org.opencontainers.image.title="TeamDev X Terminal"
LABEL org.opencontainers.image.description="TeamDev Terminal – Root + ubuntu"
LABEL org.opencontainers.image.url="https://t.me/Team_X_Og"
LABEL org.opencontainers.image.version="2.4.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    TERM=xterm-256color \
    COLORTERM=truecolor \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7681 \
    KEEPALIVE_URL="" \
    SHELL=/bin/bash \
    HOME=/root \
    TZ=UTC

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        # Core utils
        bash \
        curl \
        wget \
        git \
        vim \
        nano \
        htop \
        procps \
        net-tools \
        iputils-ping \
        dnsutils \
        build-essential \
        gcc \
        g++ \
        make \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        zip \
        unzip \
        tar \
        gzip \
        locales \
        sudo \
        openssh-client \
        ca-certificates \
        gnupg \
        lsb-release \
        tree \
        jq \
        tmux \
        less \
        file \
    && locale-gen en_US.UTF-8 \
    && update-locale LANG=en_US.UTF-8 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN curl -fsSL https://railway.app/install.sh | sh 2>/dev/null || true

WORKDIR /app

COPY terminal_server.py   ./terminal_server.py
COPY teamdev_terminal_ui.html ./teamdev_terminal_ui.html

RUN mkdir -p /tmp/teamdev_uploads && chmod 777 /tmp/teamdev_uploads

RUN echo "root ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    echo "teamdev ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers 2>/dev/null || true

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE ${PORT}

CMD ["python3", "terminal_server.py"]
