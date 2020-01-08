from core.config.globalimport import *
import weakref
from os import (
    system, path, getcwd,
    popen, listdir, mkdir, chown
)
from pwd import getpwnam
from grp import getgrnam
from time import asctime
from subprocess import check_output,Popen,PIPE,STDOUT,CalledProcessError,call
from core.controls.threads import ProcessHostapd, ProcessThread
from core.wirelessmode.wirelessmode import Mode
from core.common.uimodel import *
from core.utility.printer import display_messages


class Static(Mode):
    ConfigRoot = "Static"
    SubConfig = "Static"
    ID = "Static"
    Name = "Static AP Mode"

    def __init__(self, parent=0):
        super(Static, self).__init__(parent)
        self.confgSecurity = []

    @property
    def Settings(self):
        return StaticSettings.getInstance()

    def getSettings(self):
        return self.Settings

    def Initialize(self):

        self.check_Wireless_Security()
        self.Settings.Configure()
        self.Settings.checkNetworkAP()


        ignore = ('interface=','ssid=','channel=','essid=')
        with open(C.HOSTAPDCONF_PATH,'w') as apconf:
            for i in self.Settings.SettingsAP['hostapd']:apconf.write(i)
            apconf.close()

        # ignore = ('interface=', 'ssid=', 'channel=', 'essid=')
        # with open(C.HOSTAPDCONF_PATH, 'w') as apconf:
        #     for i in self.parent.SettingsAP['hostapd']:
        #         apconf.write(i)
        #     for config in str(self.FSettings.ListHostapd.toPlainText()).split('\n'):
        #         if not config.startswith('#') and len(config) > 0:
        #             if not config.startswith(ignore):
        #                 apconf.write(config + '\n')
        #     apconf.close()

    def boot(self):
        # create thread for hostapd and connect get_Hostapd_Response function
        # self.reactor = ProcessHostapd(
        #     {self.hostapd_path: [C.HOSTAPDCONF_PATH]}, self.parent.currentSessionID)
        # self.reactor.setObjectName('StaticHostapd')
        # self.reactor.statusAP_connected.connect(self.LogOutput)
        # self.reactor.statusAPError.connect(self.Shutdown)

        self.hostapd_path = self.conf.get('accesspoint', 'hostapd_path')
        #self.Thread_hostapd = ProcessHostapd([self.hostapd_path,C.HOSTAPDCONF_PATH], 'MDSNjD')
        self.reactor = ProcessHostapd({self.hostapd_path :[C.HOSTAPDCONF_PATH]}, 'MDSNjD')
        self.reactor.setObjectName('hostapd')
        self.reactor.statusAP_connected.connect(self.get_Hostapd_Response)
        self.reactor.statusAPError.connect(self.get_error_hostapdServices)


    def get_Hostapd_Response(self,data):
        print(data)

    def get_error_hostapdServices(self,data):
        if  self.conf.get('accesspoint','statusAP',format=bool):
            print(display_messages('Hostapd Error',error=True))
            print(data)


    def check_Wireless_Security(self):
        '''check if user add security password on AP'''
        # New Implementation after refactored
        pass

    # def LogOutput(self, data):
    #     if self.parent.Home.DHCP.ClientTable.APclients != {}:
    #         if data in self.parent.Home.DHCP.ClientTable.APclients.keys():
    #             self.parent.StationMonitor.addRequests(
    #                 data, self.parent.Home.DHCP.ClientTable.APclients[data], False)
    #         self.parent.Home.DHCP.ClientTable.delete_item(data)
    #         self.parent.connectedCount.setText(
    #             str(len(self.parent.Home.DHCP.ClientTable.APclients.keys())))



    def setNetworkManager(self, interface=str,Remove=False):
        ''' mac address of interface to exclude '''
        networkmanager = C.NETWORKMANAGER
        config  = configparser.RawConfigParser()
        MAC     = Linux.get_interface_mac(interface)
        exclude = {'MAC': 'mac:{}'.format(MAC),'interface': 'interface-name:{}'.format(interface)}
        if  not Remove:
            if path.exists(networkmanager):
                config.read(networkmanager)
                try:
                    config.add_section('keyfile')
                except configparser.DuplicateSectionError:
                    config.set('keyfile','unmanaged-devices','{}'.format(
                        exclude['interface'] if MAC != None else exclude['MAC']))
                else:
                    config.set('keyfile','unmanaged-devices','{}'.format(
                        exclude['interface'] if MAC != None else exclude['MAC']))
                finally:
                    with open(networkmanager, 'wb') as configfile:
                        config.write(configfile)
                return True
            return False
        elif Remove:
            if path.exists(networkmanager):
                config.read(networkmanager)
                try:
                    config.remove_option('keyfile','unmanaged-devices')
                    with open(networkmanager, 'wb') as configfile:
                        config.write(configfile)
                        return True
                except configparser.NoSectionError:
                    return True
            return False


class StaticSettings(CoreSettings):
    Name = "Static"
    ID = "Static"
    Category = "Wireless"
    instances = []

    def __init__(self, parent):
        super(StaticSettings, self).__init__(parent)
        self.__class__.instances.append(weakref.proxy(self))
        self.conf = SettingsINI.getInstance()

        self.title = self.__class__.__name__
        self.SettingsAP = {}
        
        self.interfaces = Linux.get_interfaces()
        self.ifaceHostapd   = self.conf.get('accesspoint','interfaceAP')
        self.DHCP           = self.getDHCPConfig()


    def getDHCPConfig(self):
        DHCP ={}
        DHCP['leasetimeDef'] = self.conf.get('dhcpdefault','leasetimeDef')
        DHCP['leasetimeMax'] = self.conf.get('dhcpdefault','leasetimeMax')
        DHCP['subnet'] = self.conf.get('dhcpdefault','subnet')
        DHCP['router'] = self.conf.get('dhcpdefault','router')
        DHCP['netmask'] = self.conf.get('dhcpdefault','netmask')
        DHCP['broadcast'] = self.conf.get('dhcpdefault','broadcast')
        DHCP['range'] = self.conf.get('dhcpdefault','range')
        return DHCP


    def Configure(self):
        ''' configure interface and dhcpd for mount Access Point '''
        self.SettingsAP = {
        'interface':
            [
                'ifconfig %s up'%(self.ifaceHostapd),
                'ifconfig %s %s netmask %s'%(self.ifaceHostapd,self.DHCP['router'],self.DHCP['netmask']),
                'ifconfig %s mtu 1400'%(self.ifaceHostapd),
                'route add -net %s netmask %s gw %s'%(self.DHCP['subnet'],
                self.DHCP['netmask'],self.DHCP['router'])
            ],
        'kill':
            [
                'iptables -w --flush',
                'iptables -w --table nat --flush',
                'iptables -w --delete-chain',
                'iptables -w --table nat --delete-chain',
                'killall dhpcd 2>/dev/null',
                'ifconfig {} down'.format(self.ifaceHostapd),
                'ifconfig {} up'.format(self.ifaceHostapd),
                'ifconfig {} 0'.format(self.ifaceHostapd),
            ],
        'hostapd':
            [
                'interface={}\n'.format(self.ifaceHostapd),
                'ssid={}\n'.format(self.conf.get('accesspoint','ssid')),
                'channel={}\n'.format(self.conf.get('accesspoint','channel')),
                'bssid={}\n'.format(self.conf.get('accesspoint','bssid')),
            ],
        'dhcp-server':
            [
                'authoritative;\n',
                'default-lease-time {};\n'.format(self.DHCP['leasetimeDef']),
                'max-lease-time {};\n'.format(self.DHCP['leasetimeMax']),
                'subnet %s netmask %s {\n'%(self.DHCP['subnet'],self.DHCP['netmask']),
                'option routers {};\n'.format(self.DHCP['router']),
                'option subnet-mask {};\n'.format(self.DHCP['netmask']),
                'option broadcast-address {};\n'.format(self.DHCP['broadcast']),
                'option domain-name \"%s\";\n'%(self.conf.get('accesspoint','ssid')),
                'option domain-name-servers {};\n'.format('8.8.8.8'),
                'range {};\n'.format(self.DHCP['range'].replace('/',' ')),
                '}',
            ],
        }
        print(display_messages('enable forwarding in iptables...',sucess=True))
        Linux.set_ip_forward(1)
        # clean iptables settings
        for line in self.SettingsAP['kill']: exec_bash(line)
        # set interface using ifconfig
        for line in self.SettingsAP['interface']: exec_bash(line)
        # check if dhcp option is enabled.
        if self.conf.get('accesspoint','dhcp_server',format=bool):
            with open(C.DHCPCONF_PATH,'w') as dhcp:
                for line in self.SettingsAP['dhcp-server']: dhcp.write(line)
                dhcp.close()
                if not path.isdir('/etc/dhcp/'): mkdir('/etc/dhcp')
                move(C.DHCPCONF_PATH, '/etc/dhcp/')


    def checkNetworkAP(self):
        # check if interface has been support AP mode (necessary for hostapd)
        if self.conf.get('accesspoint','check_support_ap_mode',format=bool):
            if not 'AP' in self.get_supported_interface(self.ifaceHostapd)['Supported']:
                print(display_messages('No Network Supported failed',error=True))
                print('failed AP ode: warning interface, the feature\n'
                'Access Point Mode is Not Supported By This Device ->({}).\n'
                'Your adapter does not support for create Access Point Network.\n'.format(self.ifaceHostapd))
                return False

        # check if Wireless interface is being used
        if self.ifaceHostapd == self.interfaces['activated'][0]:
            iwconfig = Popen(['iwconfig'], stdout=PIPE,shell=False,stderr=PIPE)
            for line in iwconfig.stdout.readlines():
                if self.ifaceHostapd in str(line,encoding='ascii'):
                    print(display_messages('Wireless interface is busy',error=True))
                    print('Connection has been detected, this {} is joined the correct Wi-Fi network\n'
                    'Device or resource busy\n{}\nYou may need to another Wi-Fi USB Adapter\n'
                    'for create AP or try use with local connetion(Ethernet).\n'
                    ''.format(self.ifaceHostapd,str(line,encoding='ascii')))
                    return False

        # check if range ip class is same
        gateway_wp, gateway = self.DHCP['router'],self.interfaces['gateway']
        if gateway != None:
            if gateway_wp[:len(gateway_wp)-len(gateway_wp.split('.').pop())] == \
                gateway[:len(gateway)-len(gateway.split('.').pop())]:
                print(display_messages('DHCP Server settings',error=True))
                print('The DHCP server check if range ip class is same.\n'
                    'it works, but not share internet connection in some case.\n'
                    'for fix this, You need change on tab (settings -> Class Ranges)\n'
                    'now you have choose the Class range different of your network.\n')
                return False
        return True

    def check_StatusWPA_Security(self):
        '''simple connect for get status security wireless click'''
        self.FSettings.Settings.set_setting('accesspoint',
                                            'enable_security', self.WSLayout.isChecked())

    def setAP_essid_random(self):
        ''' set random mac 3 last digits  '''
        prefix = []
        for item in [x for x in str(self.EditBSSID.text()).split(':')]:
            prefix.append(int(item, 16))
        self.EditBSSID.setText(Refactor.randomMacAddress(
            [prefix[0], prefix[1], prefix[2]]).upper())

    def update_security_settings(self):
        if 1 <= self.WPAtype_spinbox.value() <= 2:
            self.set_security_type_text('WPA')
            if 8 <= len(self.editPasswordAP.text()) <= 63 and is_ascii(str(self.editPasswordAP.text())):
                self.editPasswordAP.setStyleSheet(
                    "QLineEdit { border: 1px solid green;}")
            else:
                self.editPasswordAP.setStyleSheet(
                    "QLineEdit { border: 1px solid red;}")
            self.wpa_pairwiseCB.setEnabled(True)
            if self.WPAtype_spinbox.value() == 2:
                self.set_security_type_text('WPA2')
        if self.WPAtype_spinbox.value() == 0:
            self.set_security_type_text('WEP')
            if (len(self.editPasswordAP.text()) == 5 or len(self.editPasswordAP.text()) == 13) and \
                    is_ascii(str(self.editPasswordAP.text())) or (len(self.editPasswordAP.text()) == 10 or len(self.editPasswordAP.text()) == 26) and \
                    is_hexadecimal(str(self.editPasswordAP.text())):
                self.editPasswordAP.setStyleSheet(
                    "QLineEdit { border: 1px solid green;}")
            else:
                self.editPasswordAP.setStyleSheet(
                    "QLineEdit { border: 1px solid red;}")
            self.wpa_pairwiseCB.setEnabled(False)


    def get_supported_interface(self,dev):
        ''' get all support mode from interface wireless  '''
        _iface = {'info':{},'Supported': []}
        try:
            output = check_output(['iw',dev,'info'],stderr=STDOUT, universal_newlines=True)
            for line in output.split('\n\t'):
                _iface['info'][line.split()[0]] = line.split()[1]
            rulesfilter = '| grep "Supported interface modes" -A 10 | grep "*"'
            supportMode = popen('iw phy{} info {}'.format(_iface['info']['wiphy'],rulesfilter)).read()
            for mode in supportMode.split('\n\t\t'):
                _iface['Supported'].append(mode.split('* ')[1])
        except CalledProcessError:
            return _iface
        return _iface

    def set_security_type_text(self, string=str):
        self.lb_type_security.setText(string)
        self.lb_type_security.setFixedWidth(60)
        self.lb_type_security.setStyleSheet("QLabel {border-radius: 2px;"
                                            "padding-left: 10px; background-color: #3A3939; color : silver; } "
                                            "QWidget:disabled{ color: #404040;background-color: #302F2F; } ")

    @classmethod
    def getInstance(cls):
        return cls.instances[0]