# PlatformIO platform package for ArteryTek AT32 MCUs

### Installation:
1. Click "PlatformIO Core CLI" from VSCode PlatformIO Panel -> Quick Access -> Miscellaneous.
2. Enter below install commands:
``` 
pio pkg install -g -p https://github.com/ArteryTek/platform-arterytekat32
```

### When you are using under Linux, before using, you need to install the udev rules for OpenOCD
1. Copy the 60-openocd.rules file under tool-openocd-at32 package to /etc/udev/rules.d/ directory.
```
sudo cp ~/.platformio/packages/tool-openocd-at32/contrib/60-openocd.rules  /etc/udev/rules.d/
```
2. Refresh the udev rules.
```
sudo udevadm control --reload-rules && sudo udevadm trigger
```