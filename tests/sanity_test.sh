cinder create --display-name $VOLUME_NAME 1"
     execute_command "cinder list"
  fi

 server_id=$(nova list | grep $NOVA_INSTANCE_NAME| head -n 1 | awk '{print $2}')
 volume_id=$(cinder list | grep $VOLUME_NAME| head -n -1 | awk '{print $2}')

 execute_command "nova volume-attach $server_id $volume_id /dev/vdb"

 info "Volume attached, ssh into instance $NOVA_INSTANCE_NAME and verify"

}

radosgw_test(){
 info "### RadosGW test"""
 
 execute_command "swift post container"

 execute_command "swift list"

 execute_command "swift upload container keystonerc_admin"

 execute_command "swift list container"

}

radosgw_cleanup(){
 info "### RadosGW test"""
 
 execute_command "swift delete container keystonerc_admin"

 execute_command "swift list container"

 execute_command "swift delete container"

 execute_command "swift list"

}

setup_project(){
  info "### Setting up new project"

  pro_exists=$(keystone tenant-list | grep $PROJECT_NAME |  head -n 1  | awk '{print $4}')
  if [ "$pro_exists" != "$PROJECT_NAME" ]
  then
       execute_command "keystone tenant-create --name $PROJECT_NAME"
       execute_command "keystone user-create --name $USER_NAME --tenant $PROJECT_NAME --pass $PASSWORD --email $EMAIL"
  else
      info "#Project $PROJECT_NAME exists ---- Skipping"
  fi
}

end(){
 
   info "#####VALIDATION SUCCESS#####" 
}


info "###Appendix-C Openstack Operations Functional Test ###"

####

init

set_unique_names
echo $NAME is the new set

###
setup_project

### Setting up Networks

create_the_networks


##

setup_glance

setup_nova

setup_cinder

radosgw_test

radosgw_cleanup
 

end 

info "##### Done #####"

exit

