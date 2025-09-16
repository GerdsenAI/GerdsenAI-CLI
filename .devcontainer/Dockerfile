FROM python:3.11-slim

ARG TZ
ENV TZ="$TZ"

ARG PYTHON_VERSION=3.11
ARG SECURITY_LEVEL=strict

# Install system dependencies for development and security
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essential development tools
    git \
    build-essential \
    gcc \
    g++ \
    make \
    curl \
    wget \
    unzip \
    # Terminal and shell tools
    zsh \
    fzf \
    less \
    nano \
    vim \
    # Network and security tools
    iptables \
    ipset \
    iproute2 \
    dnsutils \
    aggregate \
    jq \
    # Python development essentials
    pkg-config \
    libffi-dev \
    libssl-dev \
    # System utilities
    procps \
    sudo \
    man-db \
    # GitHub CLI (for CI integration)
    gnupg2 \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install gh -y \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create python user with proper permissions
ARG USERNAME=python
RUN useradd --create-home --shell /bin/zsh $USERNAME \
    && mkdir -p /home/$USERNAME/.cache/pip \
    && mkdir -p /home/$USERNAME/.config/gerdsenai-cli \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME

# Set up sudo access for firewall management
RUN echo "$USERNAME ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/$USERNAME-firewall \
    && chmod 0440 /etc/sudoers.d/$USERNAME-firewall

# Persist bash/zsh history
RUN mkdir /commandhistory \
    && touch /commandhistory/.bash_history \
    && touch /commandhistory/.zsh_history \
    && chown -R $USERNAME /commandhistory

# Set `DEVCONTAINER` environment variable for runtime detection
ENV DEVCONTAINER=true

# Create workspace and set permissions
RUN mkdir -p /workspace && chown -R $USERNAME:$USERNAME /workspace
WORKDIR /workspace

# Install git delta for better diffs
ARG GIT_DELTA_VERSION=0.18.2
RUN ARCH=$(dpkg --print-architecture) && \
    wget "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
    dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
    rm "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"

# Switch to python user for remaining setup
USER $USERNAME

# Set up zsh with modern features
ARG ZSH_IN_DOCKER_VERSION=1.2.0
RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v${ZSH_IN_DOCKER_VERSION}/zsh-in-docker.sh)" -- \
    -p git \
    -p fzf \
    -p python \
    -a "source /usr/share/doc/fzf/examples/key-bindings.zsh" \
    -a "source /usr/share/doc/fzf/examples/completion.zsh" \
    -a "export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
    -a "export SAVEHIST=1000 && export HISTFILE=/commandhistory/.zsh_history" \
    -x

# Upgrade pip and install core Python tools
RUN python -m pip install --upgrade pip setuptools wheel

# Install core dependencies (stable ones that don't change often)
RUN pip install --no-cache-dir \
    # Core CLI framework
    "typer>=0.9.0" \
    "rich>=13.7.0" \
    # HTTP and async
    "httpx>=0.25.2" \
    # Data validation
    "pydantic>=2.5.0" \
    "python-dotenv>=1.0.0" \
    # Development tools
    "ruff>=0.1.0" \
    "black>=23.0.0" \
    "mypy>=1.7.0" \
    # Testing
    "pytest>=7.4.0" \
    "pytest-asyncio>=0.21.0" \
    # Cross-platform support
    "colorama>=0.4.6"

# Set the default shell and editor
ENV SHELL=/bin/zsh
ENV EDITOR=nano
ENV VISUAL=nano

# Python environment configuration
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_CACHE_DIR=/home/python/.cache/pip

# Copy firewall script and set up permissions
COPY init-firewall.sh /usr/local/bin/
USER root
RUN chmod +x /usr/local/bin/init-firewall.sh
USER $USERNAME

# Copy post-create script
COPY post-create.sh /usr/local/bin/
USER root  
RUN chmod +x /usr/local/bin/post-create.sh
USER $USERNAME
