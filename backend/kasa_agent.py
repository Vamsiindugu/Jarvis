import asyncio
from kasa import Discover, SmartDevice, SmartBulb, SmartPlug

class KasaAgent:
    def __init__(self):
        self.devices = {}

    async def discover_devices(self):
        """Discovers devices on the local network."""
        print("Discovering Kasa devices...")
        found_devices = await Discover.discover()
        
        device_list = []
        self.devices = {}
        
        for ip, dev in found_devices.items():
            await dev.update()
            self.devices[ip] = dev
            
            # Determine type and capabilities
            dev_type = "unknown"
            if dev.is_bulb:
                dev_type = "bulb"
            elif dev.is_plug:
                dev_type = "plug"
            elif dev.is_strip:
                dev_type = "strip"
            elif dev.is_dimmer:
                dev_type = "dimmer"

            device_info = {
                "ip": ip,
                "alias": dev.alias,
                "model": dev.model,
                "type": dev_type,
                "is_on": dev.is_on,
                "brightness": dev.brightness if dev.is_bulb or dev.is_dimmer else None,
                "hsv": dev.hsv if dev.is_bulb and dev.is_color else None,
                "has_color": dev.is_color if dev.is_bulb else False,
                "has_brightness": dev.is_dimmable if dev.is_bulb or dev.is_dimmer else False
            }
            device_list.append(device_info)
            
        print(f"Found {len(device_list)} Kasa devices.")
        return device_list

    async def turn_on(self, ip):
        """Turns on the device at the given IP."""
        if ip in self.devices:
            dev = self.devices[ip]
            await dev.turn_on()
            await dev.update()
            return True
        else:
            # Try to connect if not in cache (e.g. after restart)
            try:
                dev = await Discover.discover_single(ip)
                if dev:
                    self.devices[ip] = dev
                    await dev.turn_on()
                    await dev.update()
                    return True
            except Exception as e:
                print(f"Error turning on {ip}: {e}")
        return False

    async def turn_off(self, ip):
        """Turns off the device at the given IP."""
        if ip in self.devices:
            dev = self.devices[ip]
            await dev.turn_off()
            await dev.update()
            return True
        else:
            try:
                dev = await Discover.discover_single(ip)
                if dev:
                    self.devices[ip] = dev
                    await dev.turn_off()
                    await dev.update()
                    return True
            except Exception as e:
                print(f"Error turning off {ip}: {e}")
        return False

    async def set_brightness(self, ip, brightness):
        """Sets brightness (0-100)."""
        if ip in self.devices:
            dev = self.devices[ip]
            if dev.is_dimmable:
                await dev.set_brightness(int(brightness))
                await dev.update()
                return True
        return False

    async def set_hsv(self, ip, h, s, v):
        """Sets HSV color."""
        if ip in self.devices:
            dev = self.devices[ip]
            if dev.is_color:
                await dev.set_hsv(int(h), int(s), int(v))
                await dev.update()
                return True
        return False

# Standalone test
if __name__ == "__main__":
    async def main():
        agent = KasaAgent()
        devices = await agent.discover_devices()
        print(devices)
    
    asyncio.run(main())
