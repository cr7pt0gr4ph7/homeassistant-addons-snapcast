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

# Client settings
add_cli_option '--hostID' 'host_id'
add_cli_option '--instance' 'instance_id'

# Soundcard settings
add_cli_option '--Soundcard' 'card'
add_cli_option '--Latency' 'latency'
add_cli_option '--player' 'player'
add_cli_option '--mixer' 'mixer'

if ! bashio::config.false 'logging_enabled'; then
    options+=(--logsink stdout)
    options+=(--logfilter "*:$(bashio::config 'logging_level' 'info')")
else
    options+=(--logsink null)
fi

bashio::log.info "Starting Snapclient..."
/usr/bin/snapclient "${options[@]}" ${additional_args} "${server_url}"
