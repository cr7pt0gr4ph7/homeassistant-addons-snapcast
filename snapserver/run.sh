#!/usr/bin/env bashio

mkdir -p /share/snapfifo
mkdir -p /share/snapcast

config=/etc/snapserver.conf

if ! bashio::fs.file_exists "${config}"; then
    touch "${config}" ||
        bashio::exit.nok "Could not create ${config} file on filesystem"
fi
bashio::log.info "Populating ${config}..."

# Start creation of configuration

echo "[stream]" > "${config}"
for stream in $(bashio::config 'streams'); do
    echo "stream = ${stream}" >> "${config}"
done
echo "buffer = $(bashio::config 'stream_buffer_size' '1000')" >> "${config}"
echo "codec = $(bashio::config 'stream_codec' 'flac')" >> "${config}"
echo "sampleformat = $(bashio::config 'stream_sampleformat' '48000:16:2')" >> "${config}"
echo "send_to_muted = $(bashio::config 'send_to_muted' 'true')" >> "${config}"

echo "[http]" >> "${config}"
echo "enabled = $(bashio::config 'http_enabled' 'true')" >> "${config}"
echo "doc_root = $(bashio::config 'http_docroot' '')" >> "${config}"

echo "[tcp]" >> "${config}"
echo "enabled = $(bashio::config 'tcp_enabled' 'true')" >> "${config}"

echo "[logging]" >> "${config}"
echo "debug = $(bashio::config 'logging_enabled' 'true')" >> "${config}"

echo "[server]" >> "${config}"
echo "threads = $(bashio::config 'server_threads' '-1')" >> "${config}"

echo "[server]" >> "${config}"
echo "datadir = $(bashio::config 'server_datadir' '/share/snapcast/')" >> "${config}"

bashio::log.info "Starting Snapserver..."
/usr/bin/snapserver -c "${config}"
