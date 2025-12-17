#!/bin/sh /etc/rc.common
# Copyright (C) 2010-2012 OpenWrt.org

STOP=20

usbDeployRootPathConf=/tmp/usbDeployRootPath.conf
start()
{
	netmode=$(uci get xiaoqiang.common.NETMODE)
	if [ "$netmode"x != "lanapmode"x ] && [ "$netmode"x != "wifiapmode"x ]
	then
		# decrese current priority and throw myself to mem cgroup
		# so all plugins inherit those attributes
		renice -n+10 -p $$
		echo $$ > /dev/cgroup/mem/group1/tasks
		if [ -n "$1" ]
		then
			usbDeployRootPath=$1
		elif [ -f "$usbDeployRootPathConf" ]
		then
			usbDeployRootPath=$(cat $usbDeployRootPathConf)
		fi
		$usbDeployRootPath/xiaomi_router/bin/plugin_start_impl_R1CM.sh $usbDeployRootPath &
	fi
}

stop()
{
	if [ -n "$1" ]
	then
		usbDeployRootPath=$1
	elif [ -f "$usbDeployRootPathConf" ]
	then
		usbDeployRootPath=$(cat $usbDeployRootPathConf)
	fi
	/usr/sbin/plugin_stop_impl_R1CM.sh $usbDeployRootPath &
}
