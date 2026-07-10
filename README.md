# PlatformIO platform package for ArteryTek AT32 MCUs

## Installation

```bash
pio pkg install -g -p https://github.com/ArteryTek/platform-arterytekat32
```

## Quick Start

Create a `platformio.ini` in your project directory:

```ini
[env:myboard]
platform = arterytekat32
board = genericAT32F403ZGT6
framework = at32firmlib
```

### Board selection

Boards are named after the MCU part number with a `generic` prefix.  
Find your chip under `boards/` or list available boards:

```bash
pio boards --platform arterytekat32
```

Example: `genericAT32F403ZGT6`, `genericAT32F435CMT7`, `genericAT32L021C8T7`.

## Supported MCU series

25 product series, 283 MCU part numbers.

| Series   | Core       | FPU  | Speed   |
|----------|------------|------|---------|
| AT32A403A| Cortex-M4  | Yes  | 200MHz  |
| AT32A423 | Cortex-M4  | Yes  | 150MHz  |
| AT32F011 | Cortex-M0+ | No   | 80MHz   |
| AT32F402 | Cortex-M4  | Yes  | 216MHz  |
| AT32F403 | Cortex-M4  | Yes  | 200MHz  |
| AT32F403A| Cortex-M4  | Yes  | 240MHz  |
| AT32F405 | Cortex-M4  | Yes  | 216MHz  |
| AT32F407 | Cortex-M4  | Yes  | 240MHz  |
| AT32F413 | Cortex-M4  | Yes  | 200MHz  |
| AT32F415 | Cortex-M4  | No   | 150MHz  |
| AT32F421 | Cortex-M4  | No   | 120MHz  |
| AT32F422 | Cortex-M4  | Yes  | 180MHz  |
| AT32F423 | Cortex-M4  | Yes  | 150MHz  |
| AT32F425 | Cortex-M4  | No   | 96MHz   |
| AT32F426 | Cortex-M4  | Yes  | 180MHz  |
| AT32F435 | Cortex-M4  | Yes  | 288MHz  |
| AT32F437 | Cortex-M4  | Yes  | 288MHz  |
| AT32F455 | Cortex-M4  | Yes  | 192MHz  |
| AT32F456 | Cortex-M4  | Yes  | 192MHz  |
| AT32F457 | Cortex-M4  | Yes  | 192MHz  |
| AT32F490 | Cortex-M4  | Yes  | 216MHz  |
| AT32L021 | Cortex-M0+ | No   | 80MHz   |
| AT32M412 | Cortex-M4  | Yes  | 180MHz  |
| AT32M416 | Cortex-M4  | Yes  | 180MHz  |
| AT32WB415| Cortex-M4  | No   | 150MHz  |

## Framework Options

### Build type

```ini
build_type = debug    ; or release (default: debug)
```

### Middlewares

```ini
middlewares = freertos
; multiple: middlewares = freertos, usbd_drivers
```

#### FreeRTOS

The FreeRTOS port is selected automatically based on the board's CPU type and FPU:

| Core       | FPU  | FreeRTOS port |
|------------|------|---------------|
| Cortex-M0+ | No   | ARM_CM0       |
| Cortex-M4  | No   | ARM_CM3       |
| Cortex-M4  | Yes  | ARM_CM4F      |

Select the heap manager with `board_build.freertos_heap` (default: `heap_4.c`):

```ini
board_build.freertos_heap = heap_2.c    ; built-in heap_2
board_build.freertos_heap =             ; skip, user provides own implementation
```

#### USB device drivers

```ini
middlewares = usbd_drivers
```

The framework auto-detects the USB driver directory structure
(`usb_drivers/` or `usbd_drivers/`) in the BSP package — no manual
configuration needed.

**Supported chips** (with USB peripheral): AT32A403A, AT32A423, AT32F402,
AT32F403, AT32F403A, AT32F405, AT32F407, AT32F413, AT32F415, AT32F423,
AT32F425, AT32F435, AT32F437, AT32F455, AT32F456, AT32F457, AT32F490,
AT32WB415.

Chips without USB (AT32F011, AT32F421, AT32F422, AT32F426, AT32L021,
AT32M412, AT32M416) will print a warning and skip USB gracefully.

#### USB host drivers

```ini
middlewares = usbh_drivers
```

(Only available in BSPs with the new `usb_drivers/` directory structure.)

### Upload protocols

Default: `atlink` (on-board AT-Link).

```ini
upload_protocol = cmsis-dap    ; CMSIS-DAP compatible probes
upload_protocol = atlink       ; AT-Link (default)
upload_protocol = atlink_dap_v2
upload_protocol = jlink        ; J-Link
upload_protocol = stlink       ; ST-Link
upload_protocol = dfu          ; USB DFU bootloader
upload_protocol = custom       ; custom upload command
```

### Debugging

```ini
debug_tool = cmsis-dap
debug_tool = atlink
debug_tool = atlink_dap_v2
debug_tool = jlink
debug_tool = stlink
```

## Advanced Options

### Custom linker script

By default the platform picks the linker script matching your MCU
from the BSP package. Override it with `board_build.ldscript`:

```ini
board_build.ldscript = custom_AT32F403.ld
```

The path is relative to the project root. Using `-Wl,-T` in
`build_flags` for this purpose is deprecated.

### Custom system setup

When `board_build.at32firmlib.custom_system_setup` is set to `"yes"`,
the platform skips building the CMSIS system startup code (`system_*.c`,
startup assembly) from the BSP. Use this when you provide your own
`SystemInit()` and vector table:

```ini
board_build.at32firmlib.custom_system_setup = yes
```

This is useful for bare-metal projects that bring their own runtime
initialisation, or when porting existing code that already includes
a system setup file.

## Linux udev rules

Before using OpenOCD on Linux, install the udev rules:

```bash
sudo cp ~/.platformio/packages/tool-openocd-at32/contrib/60-openocd.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## How it works (v2.0.0+)

Each board references a specific "BSP" firmware library package.  
On first build, the platform:

1. Clones the matching official ArteryTek repo (`git clone --depth=1`)
2. Extracts the real firmware version from the device-support header
3. Injects a minimal `package.json` so PlatformIO recognises the package
4. Compiles `libraries/` and `middlewares/` from that package

The clone is cached in `~/.platformio/packages/` — subsequent builds
use the local copy directly.

```mermaid
flowchart LR
    A[platformio.ini] -->|board| B[board.json]
    B -->|bsp field| C{BSP_PACKAGE_MAP}
    C -->|AT32F403| D[AT32F403_Firmware_Library}
    D -->|git clone| E[~/.platformio/packages/]
    E --> F[Compile libraries + middlewares]
```

### Automatic GitHub / Gitee mirror fallback

The platform probes both `github.com:443` and `gitee.com:443` in
parallel and picks whichever responds first.

- Users in mainland China → Gitee (faster / more reliable)
- Users elsewhere → GitHub (faster / more reliable)

The choice is cached in `~/.platformio/packages/.at32_git_mirror`
so subsequent builds do not repeat the test.  Delete that file to
force re-detection.

## Updating the firmware library

The BSP package is cloned once and cached.  When ArteryTek publishes
a new firmware library version, you can update your local copy in
either of these ways:

### Delete the whole package folder (clean slate)

```bash
# Find which BSP your board uses and delete it
rm -rf ~/.platformio/packages/AT32F403_Firmware_Library
```

The next build re-clones the latest version.  This also fixes any
corrupted checkout.

### Delete just package.json (fast-forward pull)

```bash
rm ~/.platformio/packages/AT32F403_Firmware_Library/package.json
```

The next build runs `git pull --ff-only` on the existing checkout
and re-extracts the version from the device-support header.  This is
faster than a full re-clone when you only need the latest commit.

### Identify which BSP package your board uses

Look up the `bsp` field in the board's JSON file under `boards/`:

```bash
python3 -c "import json; print(json.load(open('boards/genericAT32F403ZGT6.json'))['build']['bsp'])"
```

## v2.0.0 migration notes

Previously (v1.x) all firmware libraries were bundled into a single
monolithic `framework-at32firmlib` package that required manual
upkeep to stay in sync with ArteryTek releases. v2.0.0+
references each official repo individually, so support for new
chips is available as soon as ArteryTek publishes the BSP.
