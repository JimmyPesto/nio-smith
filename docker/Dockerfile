# Its recommended to build with docker compose, see PLUGINS.md

# We use an initial docker container to build all of the runtime dependencies,
# then transfer those dependencies to the container we're going to ship,
# before throwing the build container away.

ARG PYTHON_VERSION=3.10
ARG SOURCE_DIR=/home/assistantnio
ARG LIBOLM_VERSION=3.2.15


##
## Creating a builder container
##

FROM docker.io/python:${PYTHON_VERSION}-alpine as builder
ARG LIBOLM_VERSION

RUN apk add --no-cache \
    make \
    cmake \
    gcc \
    g++ \
    git \
    python3-dev

##
## Build libolm for matrix-nio e2e support
##
# Also build the libolm python bindings and place them at /python-libs
# We will later copy contents from both of these folders to the runtime
# container
COPY docker/build_and_install_libolm.sh /scripts/
RUN chmod +x /scripts/build_and_install_libolm.sh
RUN ./scripts/build_and_install_libolm.sh ${LIBOLM_VERSION} /python-libs

# Install python runtime modules. We do this before copying the source code
# such that these dependencies can be cached
# This speeds up subsequent image builds when the source code is changed
WORKDIR ${SOURCE_DIR}
# Build bot main dependencies
COPY requirements.txt ${SOURCE_DIR}
# Copy the whole plugins subdirectories (as we need to keep the subdir structure to avoid name clashes)
COPY plugins/ ${SOURCE_DIR}/plugins/
# Build global and all plugin requirements (specified in all `requirements.txt`)
RUN find ${SOURCE_DIR} -iname requirements.txt -exec pip install --prefix="/python-libs" --no-warn-script-location -r {} \;

##
## Creating the runtime container
##

# Create the container we'll actually ship. We need to copy libolm and any
# python dependencies that we built above to this container
FROM docker.io/python:${PYTHON_VERSION}-alpine

ARG SOURCE_DIR

# Copy python dependencies from the "builder" container
COPY --from=builder /python-libs /usr/local

# Copy libolm from the "builder" container
COPY --from=builder /usr/local/lib/libolm* /usr/local/lib/

# Install dependencies
RUN apk add --no-cache  \
    # olm
    libstdc++ \
    # Pillow
    zlib-dev \
    jpeg-dev

RUN adduser -D -h ${SOURCE_DIR} assistantnio
# [How do I add a user when I'm using Alpine as a base image?](https://stackoverflow.com/questions/49955097/how-do-i-add-a-user-when-im-using-alpine-as-a-base-image#)
# [Setting up a new user](https://wiki.alpinelinux.org/wiki/Setting_up_a_new_user)
WORKDIR ${SOURCE_DIR}
RUN mkdir -p ${SOURCE_DIR}/data/state
RUN mkdir -p ${SOURCE_DIR}/data/config
RUN chown -R assistantnio:assistantnio /home/assistantnio/data/
RUN mkdir -p ${SOURCE_DIR}/plugins/
RUN chown -R assistantnio:assistantnio ${SOURCE_DIR}/plugins/

# Now copy the full source code
COPY main.py README.md ${SOURCE_DIR}/
COPY core/*.py ${SOURCE_DIR}/core/
# copy everything within plugins dir
COPY  plugins/ ${SOURCE_DIR}/plugins/
# remove the stuff that does not belong here
RUN find plugins/ -type f -not -name '*.py' -print0 | xargs -0 rm
RUN chown -R assistantnio:assistantnio ${SOURCE_DIR}/
USER assistantnio


# Start the bot
CMD ["python", "main.py", "/home/assistantnio/data/config/config.yaml"]
