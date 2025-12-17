#!/bin/sh
# Copyright (C) 2016 Xiaomi

################### VARIABLES #############
host_apple="captive.apple.com captive.g.aaplimg.com"

portal_ipset="captive_portal"
portal_ipset_v6="captive_portal_v6"
portal_ipset_windows="captive_portal_windows"
portal_ipset_ios="captive_portal_ios"
portal_ipset_android="captive_portal_android"

portal_dnsmasq_conf_file="/var/etc/dnsmasq.d/${portal_ipset}.conf"
portal_nat_device_table="portal_nat_prerouting"
portal_nat_device_cp_windows="portal_nat_pre_cp_windows"
portal_nat_device_cp_ios="portal_nat_pre_cp_ios"
portal_nat_device_cp_android="portal_nat_pre_cp_android"
portal_mangle_device_table_v6="portal_mangle_prerouting_v6"

#############################################
# add log
captive_portal_log()
{
    logger -p warn -t capitveportal "$1"
}

#############################################
# get local config
get_portal_local_config()
{
    config_uci_md5=`uci get captive_portal.global.config_md5`
    local_disabled_status=`uci get captive_portal.global.disabled`
    local_blocked_hosts=`uci get captive_portal.global.blocked_hosts`
    local_interval=`uci get captive_portal.global.default_interval`
    local_timeout=`uci get captive_portal.global.timeout`
    local_hitcount=`uci get captive_portal.global.hitcount`
    local_checkpoint=`uci get captive_portal.global.checkopint`
    local_hosts_windows=`uci get captive_portal.global.hosts_windows`
    local_hosts_ios=`uci get captive_portal.global.hosts_ios`
    local_hosts_android=`uci get captive_portal.global.hosts_android`
}

#############################################
# dnsmasq functions
captive_portal_dnsmasq_add()
{
    for _host in $1
    do
        echo "ipset=/!${_host}/$2" >> ${portal_dnsmasq_conf_file}
    done
}

captive_portal_dnsmasq_init()
{
    rm ${portal_dnsmasq_conf_file} > /dev/null 2>&1
    touch ${portal_dnsmasq_conf_file}
    captive_portal_dnsmasq_add "${local_blocked_hosts}" "${portal_ipset}"
    captive_portal_dnsmasq_add "${local_blocked_hosts}" "${portal_ipset_v6}"
    captive_portal_dnsmasq_add "${local_hosts_windows}" "${portal_ipset_windows}"
    captive_portal_dnsmasq_add "${local_hosts_ios}" "${portal_ipset_ios}"
    captive_portal_dnsmasq_add "${local_hosts_android}" "${portal_ipset_android}"
    /etc/init.d/dnsmasq restart
}

###############################################
# ipset functions
portal_ipset_create()
{
    _rule_ipset=$1
    _family=$2
    [ "${_rule_ipset}" == "" ] && return;
    ipset flush   $_rule_ipset >/dev/null 2>&1
    ipset destroy $_rule_ipset >/dev/null 2>&1
    if [ -z "${_family}" ] ; then
        ipset create ${_rule_ipset} hash:net >/dev/null 2>&1
    else
        ipset create ${_rule_ipset} hash:net family ${_family} >/dev/null 2>&1
    fi
}

portal_ipset_destroy()
{
    _rule_ipset=$1
    [ "$_rule_ipset" == "" ] && return;
    ipset flush   $_rule_ipset >/dev/null 2>&1
    ipset destroy $_rule_ipset >/dev/null 2>&1
}

################### iptables ###################
# flush, delete and create a custom iptables chain
ipt_table_create()
{
    iptables -t $1 -F $2 >/dev/null 2>&1
    iptables -t $1 -X $2 >/dev/null 2>&1
    iptables -t $1 -N $2 >/dev/null 2>&1
}

ipt_table_destroy()
{
    iptables -t $1 -F $2 >/dev/null 2>&1
    iptables -t $1 -X $2 >/dev/null 2>&1
}

ipt6_table_create()
{
    ip6tables -t $1 -F $2 >/dev/null 2>&1
    ip6tables -t $1 -X $2 >/dev/null 2>&1
    ip6tables -t $1 -N $2 >/dev/null 2>&1
}

ipt6_table_destroy()
{
    ip6tables -t $1 -F $2 >/dev/null 2>&1
    ip6tables -t $1 -X $2 >/dev/null 2>&1
}

###############################################
# get server config, if not defined, use default definition
get_server_config(){
    # curl config api
    local config_json_file="/tmp/captive_portal_conf.json"
    # if server is not reachable, use local config
    if ! (curl --connect-timeout 2 http://api.miwifi.com/data/portal/portal_config > ${config_json_file}) ; then
        echo "cannot get server config, use local config, resume local portal status"
        resume_local_status
        return 0
    fi
    config_json_md5=`md5sum ${config_json_file} | cut -d " " -f 1`
    if [ "${config_json_md5}" = "${config_uci_md5}" ] ; then
        # md5 is the same, server config is not changed
        echo "server config is the same with local config, resume local portal status"
        resume_local_status
        return 0
    fi
    # use jshn lib in openwrt to phase json
    source /usr/share/libubox/jshn.sh
    json_content=$(cat ${config_json_file})
    json_load "${json_content}"

    # get server switch status
    json_get_var server_disabled_status disabled
    if [ "${server_disabled_status}" != "false" ] ; then
        server_disabled_status="true"
    fi

    # get server blocked hosts
    json_get_var server_blocked_hosts blocked_hosts
    server_blocked_hosts=${server_blocked_hosts:-"$local_blocked_hosts"}

    # get server default interval
    json_get_var server_interval default_interval
    server_interval=${server_interval:-"$local_interval"}

    # get server timeout
    json_get_var server_timeout timeout
    server_timeout=${server_timeout:-"$local_timeout"}

    # get server hitcount
    json_get_var server_hitcount hitcount
    server_hitcount=${server_hitcount:-"$local_hitcount"}

    # get server checkpoint
    json_get_var server_checkpoint checkpoint
    server_checkpoint=${server_checkpoint:-"$local_checkpoint"}

    # get server hosts_windows
    json_get_var server_hosts_windows hosts_windows
    server_hosts_windows=${server_hosts_windows:-"$local_hosts_windows"}

    # get server hosts_ios
    json_get_var server_hosts_io hosts_ios
    server_hosts_ios=${server_hosts_ios:-"$local_hosts_ios"}

    # get server hosts_android
    json_get_var server_hosts_android hosts_android
    server_hosts_android=${server_hosts_android:-"$local_hosts_android"}

    rm ${config_json_file}
uci -q batch <<-EOF >/dev/null
    set captive_portal.global.blocked_hosts="${server_blocked_hosts}"
    set captive_portal.global.config_md5="${config_json_md5}"
    set captive_portal.global.default_interval="${server_interval}"
    set captive_portal.global.timeout="${server_timeout}"
    set captive_portal.global.hitcount="${server_hitcount}"
    set captive_portal.global.checkpoint="${server_checkpoint}"
    set captive_portal.global.hosts_windows="${server_hosts_windows}"
    set captive_portal.global.hosts_ios="${server_hosts_ios}"
    set captive_portal.global.hosts_android="${server_hosts_android}"
EOF
    if [ "${server_disabled_status}" = "true" ] ; then
        uci set captive_portal.global.disabled="${server_disabled_status}"
    fi
    update_captive_portal_status
}

update_captive_portal_status(){
    get_portal_local_config
    if [ "${local_disabled_status}" = "false" ] ; then
        enable_captive_portal
    else
        disable_captive_portal
    fi
}

# when sysapihttpd is reloaded, eg router is rebooted, the ipset and iptables are gone
# need to resume previous status
resume_local_status(){
    update_captive_portal_status
    local date_now=`date +%s`
    # get all allowed devices which are saved in uci config
    for device in `uci show captive_portal | grep device | grep -o -E "[0-9a-fA-F]{12}"` ; do
        # get device allowed stop time
        _start=`uci get captive_portal.${device}.start`
        _stop=`uci get captive_portal.${device}.stop`
        _mac_with_colon=`echo ${device} | sed 's/..\B/&:/g'`
        remove_allowed_device_by_mac ${_mac_with_colon}
        # if time now is beyond allowed time, the device entry is useless, delete it
        if [ "${date_now}" -ge "${_stop}" ] ; then
            uci delete captive_portal.${device}
        else
            captive_portal_iptables_add_device ${_mac_with_colon} ${_start} ${_stop}
        fi
    done
    uci commit
}

###############################################
# universal switch
enable_captive_portal(){
    #if in ft_mode, do not start!
    ft_mode=`cat /proc/xiaoqiang/ft_mode`
    if [ "$ft_mode" -ne "0" ]; then
        return 0
    fi
    
    # add dnsmasq config file
    captive_portal_dnsmasq_init
    # create ipset
    portal_ipset_create ${portal_ipset}
    portal_ipset_create ${portal_ipset_v6} inet6
    portal_ipset_create ${portal_ipset_windows}
    portal_ipset_create ${portal_ipset_ios}
    portal_ipset_create ${portal_ipset_android}

    # remove old chain in prerouting
    remove_chain_in_prerouting
    # destory old custom iptable and create empty custom iptables chain
    ipt_table_create nat ${portal_nat_device_table}
    ipt6_table_create mangle ${portal_mangle_device_table_v6}
    ipt_table_create nat ${portal_nat_device_cp_windows}
    ipt_table_create nat ${portal_nat_device_cp_ios}
    ipt_table_create nat ${portal_nat_device_cp_android}

    # if normal condition
    if [ "${local_checkpoint}" = "false" ] ; then
        # update ipv4 iptables
        # nat table PREROUTING chain: if flow matches the portal_ipset, jump to portal_nat_device_table
        iptables -t nat -I PREROUTING -i br-lan -m set --match-set ${portal_ipset} dst -p tcp --dport 80 -j ${portal_nat_device_table} >/dev/null 2>&1
        # nat table portal_nat_device_table chain:set redirected pkg in recent module
        iptables -t nat -I ${portal_nat_device_table} -m recent --set --name CPT --rsource >/dev/null 2>&1
        # nat table portal_nat_device_table chain: add recent module, if hit 4 times in 100s, accept
        # iptables -t nat -A ${portal_nat_device_table} -m recent --rcheck --seconds 100 --hitcount 4 --name CPT --rsource -j LOG --log-prefix "Captive Portal: " >/dev/null 2>&1
        iptables -t nat -A ${portal_nat_device_table} -m recent --rcheck --seconds ${local_timeout} --hitcount ${local_hitcount} --name CPT --rsource -j ACCEPT >/dev/null 2>&1
        # nat table portal_nat_device_table chain: redirect all flows to port 8777
        iptables -t nat -A ${portal_nat_device_table} -p tcp -j REDIRECT --to-ports 8777 >/dev/null 2>&1

        # update ipv6 ip6tables, drop all ipv6 requests
        ip6tables -t mangle -I PREROUTING -i br-lan -m set --match-set ${portal_ipset_v6} dst -j portal_mangle_prerouting_v6
        ip6tables -t mangle -I ${portal_mangle_device_table_v6} -j DROP
    # if checkpoint requirements
    else
        iptables -t nat -I PREROUTING -i br-lan -m set --match-set ${portal_ipset_windows} dst -p tcp --dport 80 -j ${portal_nat_device_cp_windows} >/dev/null 2>&1
        iptables -t nat -I PREROUTING -i br-lan -m set --match-set ${portal_ipset_ios} dst -p tcp --dport 80 -j ${portal_nat_device_cp_ios} >/dev/null 2>&1
        iptables -t nat -I PREROUTING -i br-lan -m set --match-set ${portal_ipset_android} dst -p tcp --dport 80 -j ${portal_nat_device_cp_android} >/dev/null 2>&1

        add_cp_iptables ${portal_nat_device_cp_windows} 8778
        add_cp_iptables ${portal_nat_device_cp_ios} 8779
        add_cp_iptables ${portal_nat_device_cp_android} 8780
    fi

    # update uci status
    uci set captive_portal.global.disabled=false
    uci commit
}

add_cp_iptables(){
    local _ip_tables=$1
    local _port=$2
    if [ -n "${_ip_tables}" ] && [ -n "${_port}" ] ; then
        iptables -t nat -I ${_ip_tables} -m recent --set --name CPT --rsource >/dev/null 2>&1
        # nat table chain: add recent module, if hit 4 times in 100s, accept
        iptables -t nat -A ${_ip_tables} -m recent --rcheck --seconds ${local_timeout} --hitcount ${local_hitcount} --name CPT --rsource -j ACCEPT >/dev/null 2>&1
        # nat table chain: redirect all flows to port
        iptables -t nat -A ${_ip_tables} -p tcp -j REDIRECT --to-ports ${_port} >/dev/null 2>&1
    fi
}

disable_captive_portal(){
    remove_chain_in_prerouting
    ipt_table_destroy nat ${portal_nat_device_table}
    ipt_table_destroy nat ${portal_nat_device_cp_windows}
    ipt_table_destroy nat ${portal_nat_device_cp_ios}
    ipt_table_destroy nat ${portal_nat_device_cp_android}
    ipt6_table_destroy mangle ${portal_mangle_device_table_v6}
    portal_ipset_destroy ${portal_ipset}
    portal_ipset_destroy ${portal_ipset_v6}
    portal_ipset_destroy ${portal_ipset_windows}
    portal_ipset_destroy ${portal_ipset_ios}
    portal_ipset_destroy ${portal_ipset_android}

    uci set captive_portal.global.disabled=true
    for device in `uci show captive_portal | grep device | grep -o -E "[0-9a-fA-F]{12}"` ; do
        uci delete captive_portal.${device} >/dev/null 2>&1
    done
    uci commit
}

remove_chain_in_prerouting(){
    local _iptables_nat_count=`iptables-save | grep ${portal_nat_device_table} | wc -l`
    if [ "${_iptables_nat_count}" -gt 1 ] ; then
        # remove old iptables chain refer from PREROUTING
        iptables -t nat -D PREROUTING -i br-lan -m set --match-set ${portal_ipset} dst -p tcp --dport 80 -j ${portal_nat_device_table} >/dev/null 2>&1
    fi
    local _iptables_nat_cp_count=`iptables-save | grep portal_nat_pre_cp | wc -l`
    if [ "${_iptables_nat_cp_count}" -gt 1 ] ; then
        # remove old iptables chain refer from PREROUTING
        iptables -t nat -D PREROUTING -i br-lan -m set --match-set ${portal_ipset_windows} dst -p tcp --dport 80 -j ${portal_nat_device_cp_windows} >/dev/null 2>&1
        iptables -t nat -D PREROUTING -i br-lan -m set --match-set ${portal_ipset_ios} dst -p tcp --dport 80 -j ${portal_nat_device_cp_ios} >/dev/null 2>&1
        iptables -t nat -D PREROUTING -i br-lan -m set --match-set ${portal_ipset_android} dst -p tcp --dport 80 -j ${portal_nat_device_cp_android} >/dev/null 2>&1
    fi
    local _ip6tables_mangle_count=`ip6tables-save | grep ${portal_mangle_device_table_v6} | wc -l`
    if [ "${_ip6tables_mangle_count}" -gt 1 ] ; then
        # remove old iptables chain refer from PREROUTING
        ip6tables -t mangle -D PREROUTING -i br-lan -m set --match-set ${portal_ipset_v6} dst -j ${portal_mangle_device_table_v6} >/dev/null 2>&1
    fi
}

###############################################
# dns hosts file
#update_blocked_hosts(){
#    remove_blocked_hosts
#    add_blocked_hosts
#}
#
#add_blocked_hosts(){
#    for _host in ${server_blocked_hosts} ; do
#        echo "127.0.0.1 ${server_blocked_hosts}" >> /etc/hosts
#    done
#}
#
#remove_blocked_hosts(){
#    for _host in ${local_blocked_hosts} ; do
#        sed -i "/${_host}/d" /etc/hosts
#    done
#}

###############################################
# add captive_portal to firewall uci config
add_firewall_uci(){
uci -q batch <<-EOF >/dev/null
    set firewall.captive_portal=include
    set firewall.captive_portal.path="/usr/sbin/captive_portal.sh reload"
    set firewall.captive_portal.reload=1
EOF
    uci commit
}

###############################################
# allow device based on mac and interval
captive_portal_allow(){
    # if checkpoint only, do not allow
    [ "${local_checkpoint}" != "false" ] && return 0;
    local _src_mac=$1
    local _interval=$2
    [ "${_src_mac}" == "" ] && return 1;
    # change mac to upper case
    _src_mac=`echo ${_src_mac} | tr [a-f] [A-F]`
    # if _interval is not a number, set it to local interval
    if [ -z "${_interval}" ] || ! [ "${_interval}" -eq "${_interval}" 2> /dev/null ] ; then
        _interval=${local_interval}
    elif [ "${_interval}" -lt 60 ] ; then
        _interval=${local_interval}
    elif [ "${_interval}" -gt 2592000 ] ; then
        _interval=2592000
    fi
    date_start_stamp=`date +%s`
    date_stop_stamp=`expr ${date_start_stamp} + ${_interval}`

    # remove old entry by mac
    remove_allowed_device_by_mac ${_src_mac}

    captive_portal_iptables_add_device ${_src_mac} ${date_start_stamp} ${date_stop_stamp}
    uci commit

    logger -p info -t captiveportal "stat_points_none captiveportal=$_src_mac|$date_start_stamp|$date_stop_stamp"
}

remove_allowed_device_by_mac(){
    local _mac=$1
    local _old_entry=`iptables-save -t nat | grep "${_mac}" | sed 's/-A /-D /'`
    [ -n "${_old_entry}" ] && iptables -t nat ${_old_entry} >/dev/null 2>&1
}

captive_portal_iptables_add_device(){
    local _mac_with_colon=$1
    local _start_stamp=$2
    local _stop_stamp=$3
    local _date_start=`date -u +%Y-%m-%dT%T -d @"$_start_stamp"`
    local _date_stop=`date -u +%Y-%m-%dT%T -d @"$_stop_stamp"`
    local _mac_no_colon=`echo ${_mac_with_colon} | sed 's/://g'`

    # add new rule to all access
    iptables -t nat -I ${portal_nat_device_table} -m mac --mac-source ${_mac_with_colon} -m time --datestart ${_date_start} --datestop ${_date_stop} -m set --match-set ${portal_ipset} dst -p tcp --dport 80 -j ACCEPT >/dev/null 2>&1

    # save allowed device entry to uci
    uci set captive_portal.${_mac_no_colon}=device
    uci set captive_portal.${_mac_no_colon}.start="${_start_stamp}"
    uci set captive_portal.${_mac_no_colon}.stop="${_stop_stamp}"
}

get_on_off_status(){
    if [ "${local_disabled_status}" = "false" ] ; then
        echo "1"
    else
        echo "0"
    fi
}

usage(){
    echo "$0:"
    echo "    on     : turn on captive portal function."
    echo "    off    : turn off captive portal function."
    echo "    allow  : allow a device."
    echo "        format: $0 allow mac_address [interval]"
    echo "        eg    : $0 allow 01:12:34:ab:cd:ef 86400"
    echo "    reload : reload captive portal status."
    echo "    other  : usage."
}

OPT=$1

captive_portal_log "$OPT"
get_portal_local_config

case ${OPT} in
    on)
        enable_captive_portal
        return $?
    ;;
    off)
        disable_captive_portal
        return $?
    ;;
    status)
        get_on_off_status
        return $?
    ;;
    allow)
        captive_portal_allow $2 $3
        return $?
    ;;
    reload)
        captive_portal_log "$OPT begin"
        get_server_config
        captive_portal_log "$OPT end"
        return $?
    ;;
    *)
        usage
        return 0
esac
