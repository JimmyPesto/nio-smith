# To build the image, run `docker build` command from the root of the
# repository:
#
#    docker build -f docker/Dockerfile .
#
# There is an optional PYTHON_VERSION build argument which sets the
# version of python to build against. For example:
#
#    docker build -f docker/Dockerfile --build-arg PYTHON_VERSION=3.8 .
#
# An optional LIBOLM_VERSION build argument which sets the
# version of libolm to build against. For example:
#
#    docker build -f docker/Dockerfile --build-arg LIBOLM_VERSION=3.1.4 .
#


##
## Creating a builder container
##

# We use an initial docker container to build all of the runtime dependencies,
# then transfer those dependencies to the container we're going to ship,
# before throwing this one away
ARG PYTHON_VERSION=3.10
ARG SOURCE_DIR=/home/nio-smith
FROM docker.io/python:${PYTHON_VERSION}-alpine as builder

ARG SOURCE_DIR

##
## Build libolm for matrix-nio e2e support
##

# Install libolm build dependencies
ARG LIBOLM_VERSION=3.2.14
RUN apk add --no-cache \
    make \
    cmake \
    gcc \
    g++ \
    git \
    libffi-dev \
    yaml-dev \
    python3-dev

# Build libolm
#
# Also build the libolm python bindings and place them at /python-libs
# We will later copy contents from both of these folders to the runtime
# container
COPY docker/build_and_install_libolm.sh /scripts/
RUN /scripts/build_and_install_libolm.sh ${LIBOLM_VERSION} /python-libs

# Install Pillow build dependencies
# https://pillow.readthedocs.io/en/latest/installation.html#building-on-linux
# (Pillow) make sure Python’s development libraries installed in Alpine:
RUN apk add  --no-cache \
    python3-dev
#     \
#    py3-setuptools
# Pillow prerequisites are installed for Alpine with:
RUN apk add --no-cache \
    tiff-dev \
    jpeg-dev \
    openjpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    libwebp-dev \
    tcl-dev \
    tk-dev \
    harfbuzz-dev \
    fribidi-dev \
    libimagequant-dev \
    libxcb-dev \
    libpng-dev

# Install python runtime modules. We do this before copying the source code
# such that these dependencies can be cached
# This speeds up subsequent image builds when the source code is changed
RUN mkdir -p ${SOURCE_DIR}

# Build bot main dependencies
COPY requirements.txt ${SOURCE_DIR}/requirements.txt
RUN pip install --prefix="/python-libs" --no-warn-script-location -r "${SOURCE_DIR}/requirements.txt"

# Copy (selected) plugins?
# Build all plugin requirements (specified in each plugin's `requirements.txt`)
# Copy full plugin directories
# TODO only copy requirements.txt
COPY plugins/ ${SOURCE_DIR}/plugins/
# Install all plugin requirements (specified in each plugin's `requirements.txt`)
RUN find ${SOURCE_DIR}/plugins/ -iname requirements.txt -exec pip install --prefix="/python-libs" --no-warn-script-location -r {} \;

##
## Creating the runtime container
##

# Create the container we'll actually ship. We need to copy libolm and any
# python dependencies that we built above to this container
FROM docker.io/python:${PYTHON_VERSION}-alpine
#FROM docker.io/python:${PYTHON_VERSION}-slim
ARG SOURCE_DIR

# Install any native runtime dependencies
RUN apk add --no-cache \
    libstdc++

# Install Pillow dependencies (TODO copy from build container?)
RUN apk add --no-cache \
    tiff-dev \
    jpeg-dev \
    openjpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    libwebp-dev \
    tcl-dev \
    tk-dev \
    harfbuzz-dev \
    fribidi-dev \
    libimagequant-dev \
    libxcb-dev \
    libpng-dev

#RUN apt-get update
#RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
# libstdc++6
#RUN useradd --create-home nio-smith
RUN adduser -D -h ${SOURCE_DIR} nio-smith
# [How do I add a user when I'm using Alpine as a base image?](https://stackoverflow.com/questions/49955097/how-do-i-add-a-user-when-im-using-alpine-as-a-base-image#)
# [Setting up a new user](https://wiki.alpinelinux.org/wiki/Setting_up_a_new_user)
WORKDIR ${SOURCE_DIR}
RUN mkdir -p ${SOURCE_DIR}/data/state
RUN chown nio-smith:nio-smith /home/nio-smith/data/state
RUN mkdir -p ${SOURCE_DIR}/plugins/
COPY plugins/ ${SOURCE_DIR}/plugins/
RUN chown -R nio-smith:nio-smith ${SOURCE_DIR}/plugins/
USER nio-smith

# Now copy the full source code
COPY main.py README.md ${SOURCE_DIR}/
COPY core/*.py ${SOURCE_DIR}/core/
RUN mkdir -p ${SOURCE_DIR}/plugins
#COPY plugins/*.py ${SOURCE_DIR}/plugins/ # maybe later only copy py files?
#COPY plugins/ ${SOURCE_DIR}/plugins/ # was working before

# Copy python dependencies from the "builder" container
COPY --from=builder /python-libs /usr/local

# Copy libolm from the "builder" container
COPY --from=builder /usr/local/lib/libolm* /usr/local/lib/

# Start the bot
CMD ["python", "main.py", "/home/nio-smith/data/config/config.yaml"]