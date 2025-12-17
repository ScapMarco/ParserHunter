#!/bin/sh
# Copyright (C) 2010-2012 OpenWrt.org

list_alldir(){  
	for file in `ls $1 | grep [^a-zA-Z]\.manifest$`  
	do  
		if [ -f $1/$file ];then
			status=$(grep -n "^status " $1/$file | cut -d'=' -f2 | cut -d'"' -f2)
			echo "status is $status"
			plugin_id=$(grep "plugin_id" $1/$file | cut -d'=' -f2 | cut -d'"' -f2)
			echo "plugin_id is $plugin_id"
			#/usr/sbin/pluginControllor -k $plugin_id
			/usr/sbin/chroot_umout.sh $2/xiaomi_router/appdata/$plugin_id
		fi  
	done  
}

killAllPluginFromCfg(){
	for id in $(cat /tmp/plugin_id_info.cfg | awk -F'_' '{print $3}' | awk '{print $1}');
	do
		/usr/sbin/pluginControllor -k $id
	done

}

#kill all plugins which have binary
killAllPluginFromCfg

list_alldir  $1/xiaomi_router/appdata/app_infos $1

#删除记录插件pid的文件
rm /tmp/plugin_id_info.cfg -f
