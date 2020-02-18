# Download base image Ubuntu 18.04
FROM ubuntu:18.04

# Variable arguments to populate labels
ARG USER=dexbot

# Set ENV variables
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV HOME_PATH /home/$USER
ENV SRC_PATH $HOME_PATH/dexbot
ENV PATH $HOME_PATH/.local/bin:$PATH
ENV LOCAL_DATA $HOME_PATH/.local/share
ENV CONFIG_DATA $HOME_PATH/.config

RUN set -xe ;\
    apt-get update ;\
    # Prepare dependencies
    apt-get install -y --no-install-recommends iputils-ping gcc make libssl-dev python3-pip python3-dev python3-setuptools \
        python3-async whiptail git ;\
    apt-get clean ;\
    rm -rf /var/lib/apt/lists/*

RUN set -xe ;\
    # Create user
    groupadd -r $USER ;\
    useradd -m -g $USER $USER ;\
    # Configure permissions (directories must be created with proper owner before VOLUME directive)
    mkdir -p $SRC_PATH $LOCAL_DATA $CONFIG_DATA ;\
    chown -R $USER:$USER $HOME_PATH

WORKDIR $SRC_PATH

RUN python3 -m pip install pipenv

# Copy project files
COPY dexbot $SRC_PATH/dexbot/
COPY *.py *.cfg Makefile README.md Pipfile Pipfile.lock $SRC_PATH/

# Build the project
RUN pipenv install --deploy --system

# Drop priveleges
USER $USER

VOLUME ["$LOCAL_DATA", "$CONFIG_DATA"]
