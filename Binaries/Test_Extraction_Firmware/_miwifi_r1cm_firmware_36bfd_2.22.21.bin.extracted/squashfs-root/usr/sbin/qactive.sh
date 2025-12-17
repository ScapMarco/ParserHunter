#!/bin/sh
#get active time every one hour

if [ -e /usr/share/libubox/jshn.sh ]; then
	. /usr/share/libubox/jshn.sh
	timval=`date +%s`
	count=`ps |grep trafficd |grep -v "grep" |wc -l`
	if [ 0 == $count ];then
		return 0
	fi

	json_load "$(ubus call trafficd wan)"

	json_get_var downstream rx_rate
	json_get_var upstream tx_rate

	quark active "$timval,$upstream,$downstream"
fi
