import subprocess, os, time
import sys

class Ipmi():
    '''
    this assumes CygWin is installed along with ipmi, as per the automation tools install instructions :
    ipmitools : download & extract from http://sourceforge.net/projects/ipmitool/files/
        ./configure --enable-intf-lanplus
        check the output contains : 
        Interfaces
        lan : yes
        lanplus : yes
        if not, check the log output, and fix the missing dependencies etc.
        make
        make install
        Add c:\cygwin\bin and c:\cygwin\usr\local\bin to your path (or the relevant paths for your setup)
        make sure you can talk to one of your servers :
        in cygwin :   ipmitool -I lanplus -H idracIp -U user -P password  power status 
    '''

    def __init__ (self, cygWinLocation, ipmi_user, ipmi_password, idracIp):
        '''
        @param cygWinLocation: cygwin bin directory
        '''
        self.cygwin_loc = cygWinLocation
        self.ipmi_user = ipmi_user
        self.ipmi_password = ipmi_password
        self.idracIp = idracIp
        
    def power_on(self):
        print "powering on"
        self.__exec_ipmi_command("power on")
        while self.get_power_state() != Power_State.POWER_ON:
            print "give it time to wake up"
            time.sleep(5)           
    
    def power_off(self):
        print "powering off"
        self.__exec_ipmi_command("power off")
        while self.get_power_state() != Power_State.POWER_OFF:
            print "give it time to turn off"
            time.sleep(5)    
        
    def power_reset(self):
        return self.__exec_ipmi_command( "power reset")
    
    def get_power_state(self):
        state = self.__exec_ipmi_command("power status").strip()
        print "power state: " + state
        return state
    
    def set_boot_to_pxe(self):
        print "setting boot to pxe"
        self.__exec_ipmi_command("chassis bootdev pxe")
       
    def set_boot_to_disk(self):
        print "setting boot to disk"
        self.__exec_ipmi_command("chassis bootdev disk")

    def __exec_ipmi_command(self, command):

        cmd = "ipmitool.exe"
	if sys.platform.startswith('linux'):
            cmd = "ipmitool"

        cmdLine = cmd + " -I lanplus -H " +  self.idracIp + " -U "+self.ipmi_user +" -P "+self.ipmi_password +" " + command
        try:
            out= subprocess.check_output(cmdLine,stderr=subprocess.STDOUT, shell=True)
            return out
                
        except subprocess.CalledProcessError as e:
            raise IOError("failed to execute ipmi command " + str(cmdLine) + e.output)
        #os.remove(fpath)
        
class Power_State:
    POWER_ON = 'Chassis Power is on'
    POWER_OFF = 'Chassis Power is off'

        
    
        
