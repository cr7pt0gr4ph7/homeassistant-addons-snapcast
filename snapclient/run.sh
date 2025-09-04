#!/usr/bin/env bashio

server_url=$(bashio::config 'url' 'tcp://bluefin.fritz.box:1704')
additional_args=$(bashio::config 'additional_args' '')
options=()

function add_cli_option() {
    if bashio::config.exists $2; then
        options+=($1 "$(bashio::config $2)")
    fi
}

function always_add_cli_option() {
    options+=($1 "$(bashio::config $2 $3)")
}

add_cli_option '--hostID' 'client.host_id'
add_cli_option '--instance' 'client.instance_id'
add_cli_option '--Soundcard' 'audio.card'
add_cli_option '--Latency' 'audio.latency'
add_cli_option '--player' 'audio.player'
add_cli_option '--mixer' 'audio.mixer'

if ! bashio::config.false 'logging.enabled'; then
    options+=(--logsink stdout)
    options+=(--logfilter "*:$(bashio::config 'logging.level' 'info')")
else
    options+=(--logsink null)
fi

bashio::log.info "Starting Snapclient..."
/usr/bin/snapclient "${options[@]}" ${additional_args} "${server_url}"
