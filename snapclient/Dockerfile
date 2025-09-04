ARG BUILD_FROM
FROM $BUILD_FROM

# Add env
ENV LANG=C.UTF-8

# Install snapcast
#
# If you are running PulseAudio (as is the default in Home Assistant OS),
# use alsa-plugins-pulse (and mount the necessary files into the container):
#
#     docker run ... \
#         -e PULSE_SERVER=unix:${XDG_RUNTIME_DIR}/pulse/native \
#         -v ${XDG_RUNTIME_DIR}/pulse/native:${XDG_RUNTIME_DIR}/pulse/native \
#         -v ~/.config/pulse/cookie:/root/.config/pulse/cookie \
#         ...
#
# If you are running PipeWire, replace the alsa-plugins with pipewire-alsa,
# and mount the PipeWire socket into the container:
#
#     docker run ... /run/user/<uid>/pipewire-0:/tmp/pipewire-0 -e XDG_RUNTIME_DIR=/tmp ...
#
RUN sed -i -e 's/v[[:digit:]]\..*\//edge\//g' /etc/apk/repositories && apk add --no-cache snapcast alsa-plugins-pulse

# Copy data for add-on
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
