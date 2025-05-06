import esp32
from esp32 import NVS
import ubinascii

class DeviceConfig:
    def __init__(self):
        self.nvs = NVS("device_cfg")
        self.default_config = {
            'device_id': 1,
            'wifi_ssid': "aa_aa",
            'wifi_pass': "elbichojake",
            'osc_server1_ip': "192.168.1.81",
            'osc_server1_port': 8001,
            'osc_server2_ip': "192.168.1.81",
            'osc_server2_port': 8002,
            'ntp_server': "pool.ntp.org",
            'ntp_sync_interval': 3600,  # Sync every hour
            'timezone_offset': 0  # UTC offset in seconds
        }
        self._init_config()
    
    def _init_config(self):
        """Initialize configuration in NVS if not exists"""
        try:
            # Check if config exists by trying to read device_id
            self.nvs.get_i32('device_id')
        except:
            # If not exists, write default config
            self._write_default_config()
    
    def _write_default_config(self):
        """Write default configuration to NVS"""
        self.nvs.set_i32('device_id', self.default_config['device_id'])
        self.nvs.set_str('wifi_ssid', self.default_config['wifi_ssid'])
        self.nvs.set_str('wifi_pass', self.default_config['wifi_pass'])
        self.nvs.set_str('osc_server1_ip', self.default_config['osc_server1_ip'])
        self.nvs.set_i32('osc_server1_port', self.default_config['osc_server1_port'])
        self.nvs.set_str('osc_server2_ip', self.default_config['osc_server2_ip'])
        self.nvs.set_i32('osc_server2_port', self.default_config['osc_server2_port'])
        self.nvs.set_str('ntp_server', self.default_config['ntp_server'])
        self.nvs.set_i32('ntp_sync_interval', self.default_config['ntp_sync_interval'])
        self.nvs.set_i32('timezone_offset', self.default_config['timezone_offset'])
        self.nvs.commit()
    
    def get_device_id(self):
        """Get device ID from NVS"""
        return self.nvs.get_i32('device_id')
    
    def set_device_id(self, device_id):
        """Set device ID in NVS"""
        self.nvs.set_i32('device_id', device_id)
        self.nvs.commit()
    
    def get_wifi_config(self):
        """Get WiFi configuration"""
        return {
            'ssid': self.nvs.get_str('wifi_ssid'),
            'password': self.nvs.get_str('wifi_pass')
        }
    
    def set_wifi_config(self, ssid, password):
        """Set WiFi configuration"""
        self.nvs.set_str('wifi_ssid', ssid)
        self.nvs.set_str('wifi_pass', password)
        self.nvs.commit()
    
    def get_osc_servers(self):
        """Get OSC server configuration"""
        return [
            {
                'ip': self.nvs.get_str('osc_server1_ip'),
                'port': self.nvs.get_i32('osc_server1_port')
            },
            {
                'ip': self.nvs.get_str('osc_server2_ip'),
                'port': self.nvs.get_i32('osc_server2_port')
            }
        ]
    
    def set_osc_servers(self, servers):
        """Set OSC server configuration"""
        if len(servers) >= 1:
            self.nvs.set_str('osc_server1_ip', servers[0]['ip'])
            self.nvs.set_i32('osc_server1_port', servers[0]['port'])
        if len(servers) >= 2:
            self.nvs.set_str('osc_server2_ip', servers[1]['ip'])
            self.nvs.set_i32('osc_server2_port', servers[1]['port'])
        self.nvs.commit()
    
    def get_unique_id(self):
        """Get unique device identifier from ESP32"""
        return ubinascii.hexlify(esp32.idf.get_unique_id()).decode()
    
    def factory_reset(self):
        """Reset configuration to default values"""
        self.nvs.erase_all()
        self._write_default_config()
    
    def get_ntp_config(self):
        """Get NTP configuration"""
        return {
            'server': self.nvs.get_str('ntp_server'),
            'sync_interval': self.nvs.get_i32('ntp_sync_interval'),
            'timezone_offset': self.nvs.get_i32('timezone_offset')
        }
    
    def set_ntp_config(self, server, sync_interval, timezone_offset):
        """Set NTP configuration"""
        self.nvs.set_str('ntp_server', server)
        self.nvs.set_i32('ntp_sync_interval', sync_interval)
        self.nvs.set_i32('timezone_offset', timezone_offset)
        self.nvs.commit() 