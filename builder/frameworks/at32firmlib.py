import json
import os
import re
import subprocess
import sys
from os.path import exists, isdir, isfile, join

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()
mcu = board.get("build.mcu", "")
product_line = board.get("build.product_line", "")
bsp = board.get("build.bsp", "")

cpu_type = board.get("build.cpu", "cortex-m4")
cmsis_core_dir = "cm0plus" if cpu_type == "cortex-m0+" else "cm4"

env.SConscript("_bare.py")

# ---------------------------------------------------------------------------
# BSP → package name → git URL resolution
# ---------------------------------------------------------------------------

BSP_PACKAGE_MAP = {
    "AT32A403A": "AT32A403A_Firmware_Library",
    "AT32A423": "AT32A423_Firmware_Library",
    "AT32F011": "AT32F011_Firmware_Library",
    "AT32F402_405": "AT32F402_405_Firmware_Library",
    "AT32F403": "AT32F403_Firmware_Library",
    "AT32F403A_407": "AT32F403A_407_Firmware_Library",
    "AT32F413": "AT32F413_Firmware_Library",
    "AT32F415": "AT32F415_Firmware_Library",
    "AT32F421": "AT32F421_Firmware_Library",
    "AT32F422_426": "AT32F422_426_Firmware_Library",
    "AT32F423": "AT32F423_Firmware_Library",
    "AT32F425": "AT32F425_Firmware_Library",
    "AT32F435_437": "AT32F435_437_Firmware_Library",
    "AT32F45x": "AT32F45x_Firmware_Library",
    "AT32F490": "AT32F490_Firmware_Library",
    "AT32L021": "AT32L021_Firmware_Library",
    "AT32M412_416": "AT32M412_416_Firmware_Library",
    "AT32WB415": "AT32WB415_Firmware_Library",
}

PACKAGE_GIT_URLS = {
    "AT32A403A_Firmware_Library": "https://github.com/ArteryTek/AT32A403A_Firmware_Library.git",
    "AT32A423_Firmware_Library": "https://github.com/ArteryTek/AT32A423_Firmware_Library.git",
    "AT32F011_Firmware_Library": "https://github.com/ArteryTek/AT32F011_Firmware_Library.git",
    "AT32F402_405_Firmware_Library": "https://github.com/ArteryTek/AT32F402_405_Firmware_Library.git",
    "AT32F403_Firmware_Library": "https://github.com/ArteryTek/AT32F403_Firmware_Library.git",
    "AT32F403A_407_Firmware_Library": "https://github.com/ArteryTek/AT32F403A_407_Firmware_Library.git",
    "AT32F413_Firmware_Library": "https://github.com/ArteryTek/AT32F413_Firmware_Library.git",
    "AT32F415_Firmware_Library": "https://github.com/ArteryTek/AT32F415_Firmware_Library.git",
    "AT32F421_Firmware_Library": "https://github.com/ArteryTek/AT32F421_Firmware_Library.git",
    "AT32F422_426_Firmware_Library": "https://github.com/ArteryTek/AT32F422_426_Firmware_Library.git",
    "AT32F423_Firmware_Library": "https://github.com/ArteryTek/AT32F423_Firmware_Library.git",
    "AT32F425_Firmware_Library": "https://github.com/ArteryTek/AT32F425_Firmware_Library.git",
    "AT32F435_437_Firmware_Library": "https://github.com/ArteryTek/AT32F435_437_Firmware_Library.git",
    "AT32F45x_Firmware_Library": "https://github.com/ArteryTek/AT32F45x_Firmware_Library.git",
    "AT32F490_Firmware_Library": "https://github.com/ArteryTek/AT32F490_Firmware_Library.git",
    "AT32L021_Firmware_Library": "https://github.com/ArteryTek/AT32L021_Firmware_Library.git",
    "AT32M412_416_Firmware_Library": "https://github.com/ArteryTek/AT32M412_416_Firmware_Library.git",
    "AT32WB415_Firmware_Library": "https://github.com/ArteryTek/AT32WB415_Firmware_Library.git",
}

# Gitee mirror URLs for the same repos — used as fallback when
# GitHub is unreachable (common for users in China).
PACKAGE_GIT_URLS_GITEE = {
    k: v.replace("github.com/ArteryTek", "gitee.com/arterytek")
    for k, v in PACKAGE_GIT_URLS.items()
}

package_name = BSP_PACKAGE_MAP.get(bsp)
if not package_name:
    sys.stderr.write(
        "Error! Unknown BSP '%s'. No matching firmware library package found.\n" % bsp
    )
    sys.exit(1)


def _extract_fw_version(pkg_dir, bsp_name):
    """Extract firmware version (MAJOR.MIDDLE.MINOR) from the device support header."""
    header_name = bsp_name.lower() + ".h"
    for root, _dirs, files in os.walk(join(pkg_dir, "libraries", "cmsis")):
        if header_name in files:
            hpath = join(root, header_name)
            break
    else:
        return None

    prefix = bsp_name  # macro prefix matches the BSP name verbatim (e.g. AT32F45x keeps lowercase x)
    pat = re.compile(
        r'#define\s+__' + re.escape(prefix)
        + r'_LIBRARY_VERSION_(MAJOR|MIDDLE|MINOR)\s+\((0x[0-9a-fA-F]+)\)'
    )
    parts = {}
    with open(hpath) as f:
        for line in f:
            m = pat.match(line)
            if m:
                parts[m.group(1)] = int(m.group(2), 16)
    if len(parts) == 3:
        return "%d.%d.%d" % (parts["MAJOR"], parts["MIDDLE"], parts["MINOR"])
    return None


_MIRROR_CACHE_FILE = None  # set on first call


def _preferred_mirror():
    """Return 'github' or 'gitee'.

    Auto-detects by probing both mirrors in parallel and picking
    the one that responds first.  The result is cached so the
    test runs only once.
    """
    global _MIRROR_CACHE_FILE

    # Cached result
    if _MIRROR_CACHE_FILE and isfile(_MIRROR_CACHE_FILE):
        with open(_MIRROR_CACHE_FILE) as f:
            return f.read().strip()

    known_pkg = platform.get_package_dir("toolchain-gccarmnoneeabi")
    pio_packages_dir = os.path.dirname(known_pkg)
    _MIRROR_CACHE_FILE = join(pio_packages_dir, ".at32_git_mirror")

    # Probe both mirrors in parallel — pick the fastest responder
    import socket
    import threading

    result = {"mirror": None}

    def _probe(host, label):
        try:
            socket.create_connection((host, 443), timeout=5).close()
            if result["mirror"] is None:
                result["mirror"] = label
        except OSError:
            pass

    threads = [
        threading.Thread(target=_probe, args=("github.com", "github")),
        threading.Thread(target=_probe, args=("gitee.com", "gitee")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    mirror = result["mirror"] or "github"  # fallback if both fail

    with open(_MIRROR_CACHE_FILE, "w") as f:
        f.write(mirror)
    return mirror


def _ensure_framework_package(pkg_name):
    """
    Ensure the firmware library package is available locally.

    The official ArteryTek firmware library repos do NOT include a
    PlatformIO-compatible package.json, so we cannot list them in
    platform.json's ``packages`` section.  Instead we clone them on
    demand here and inject a package.json with the real version
    extracted from the device-support header.
    """
    known_pkg = platform.get_package_dir("toolchain-gccarmnoneeabi")
    pio_packages_dir = os.path.dirname(known_pkg)
    pkg_dir = join(pio_packages_dir, pkg_name)

    if isdir(pkg_dir) and isfile(join(pkg_dir, "package.json")):
        return pkg_dir

    mirror = _preferred_mirror()
    url_map = PACKAGE_GIT_URLS if mirror == "github" else PACKAGE_GIT_URLS_GITEE
    git_url = url_map.get(pkg_name)
    if not git_url:
        sys.stderr.write(
            "Error! No git URL configured for package '%s'.\n" % pkg_name
        )
        sys.exit(1)

    if isdir(pkg_dir):
        # Directory exists but package.json is missing —
        # user deleted it to trigger an update.  Pull latest.
        print("Updating %s (git pull --ff-only) ..." % pkg_name)
        try:
            subprocess.check_call(
                ["git", "-C", pkg_dir, "pull", "--ff-only"],
                stdout=sys.stdout, stderr=sys.stderr,
            )
        except subprocess.CalledProcessError as e:
            sys.stderr.write(
                "Warning! Failed to update %s: %s\n" % (pkg_name, e)
            )
            sys.stderr.write(
                "Proceeding with existing local copy.\n"
            )
    else:
        print("Fetching %s ..." % git_url)
        try:
            subprocess.check_call(
                ["git", "clone", "--depth=1", git_url, pkg_dir],
                stdout=sys.stdout, stderr=sys.stderr,
            )
        except subprocess.CalledProcessError:
            # If GitHub failed, flip the cache and try Gitee once
            if mirror == "github" and _MIRROR_CACHE_FILE:
                with open(_MIRROR_CACHE_FILE, "w") as f:
                    f.write("gitee")
            git_url = PACKAGE_GIT_URLS_GITEE.get(pkg_name)
            print("Retrying from Gitee mirror ...")
            try:
                subprocess.check_call(
                    ["git", "clone", "--depth=1", git_url, pkg_dir],
                    stdout=sys.stdout, stderr=sys.stderr,
                )
            except subprocess.CalledProcessError as e:
                sys.stderr.write(
                    "Error! Failed to clone from both GitHub and Gitee: %s\n" % e
                )
                sys.exit(1)

    # Generate package.json once — only when missing
    pkg_json_path = join(pkg_dir, "package.json")
    if not isfile(pkg_json_path):
        version = _extract_fw_version(pkg_dir, bsp)
        if not version:
            version = "0.0.0"
        print("Detected %s version %s" % (pkg_name, version))
        with open(pkg_json_path, "w") as f:
            json.dump({
                "name": pkg_name,
                "version": version,
                "description": "ArteryTek %s - auto-managed by platform-arterytekat32" % pkg_name,
            }, f, indent=2)

    return pkg_dir


FRAMEWORK_DIR = _ensure_framework_package(package_name)
FRAMEWORK_LIB_DIR = join(FRAMEWORK_DIR, "libraries")
assert isdir(FRAMEWORK_LIB_DIR), (
    "Cannot find 'libraries' directory in %s" % FRAMEWORK_DIR
)

FRAMEWORK_MIDDLEWARE_DIR = join(FRAMEWORK_DIR, "middlewares")
env.Append(FMD=[FRAMEWORK_MIDDLEWARE_DIR])


def get_linker_script():
    ldscript = join(FRAMEWORK_LIB_DIR, "cmsis", cmsis_core_dir, "device_support", "startup", "gcc",
                    "linker", product_line + "_FLASH.ld")

    if isfile(ldscript):
        return ldscript

    sys.stderr.write("Warning! Cannot find a linker script for the required board! "+ldscript)


env.Append(
    CPPPATH=[
        join(FRAMEWORK_LIB_DIR, "cmsis", cmsis_core_dir, "core_support"),
        join(FRAMEWORK_LIB_DIR, "cmsis", cmsis_core_dir, "device_support"),
        join(FRAMEWORK_LIB_DIR, "drivers", "inc"),
        join(FRAMEWORK_LIB_DIR, "drivers", "src")
    ]
)

env.Append(
    CPPDEFINES=[
        "USE_STDPERIPH_DRIVER"
    ]
)

env.Append(
    CPPDEFINES=[
        env["BUILD_TYPE"].upper()
    ]
)

if not board.get("build.ldscript", ""):
    env.Replace(LDSCRIPT_PATH=get_linker_script())

#
# Target: Build Firmware Library
#

extra_flags = board.get("build.extra_flags", "")

libs = []

if board.get("build.at32firmlib.custom_system_setup", "no") == "no":
    libs.append(env.BuildLibrary(
        join("$BUILD_DIR", "cmsis"),
        join(FRAMEWORK_LIB_DIR, "cmsis", cmsis_core_dir, "device_support"),
        src_filter=[
            "+<*.c>",
            "+<startup/gcc/startup_%s.[Ss]>" % bsp.lower()
        ]
    ))

libs.append(env.BuildLibrary(
    join("$BUILD_DIR", "driver"),
    join(FRAMEWORK_LIB_DIR, "drivers", "src"),
    src_filter=["+<*.c>"]
))

middlewares = env.GetProjectOption("middlewares","")
if(middlewares):
    for x in middlewares.split(","):
        x = x.strip()
        print("Middleware %s referenced." % x)
        if x == "i2c_application_library":
            env.Append(
                CPPPATH=[
                    join(FRAMEWORK_MIDDLEWARE_DIR, x.strip())
                ]
            )
            libs.append(env.BuildLibrary(
                join("$BUILD_DIR", "middleware", x.strip()),
                join(FRAMEWORK_MIDDLEWARE_DIR, x.strip()),
                src_filter=["+<*.c>"]
            ))
        elif x == "freertos":
            # Determine FreeRTOS portable dir based on CPU type and FPU
            fpu = board.get("build.fpu", "No")
            if cpu_type == "cortex-m0+":
                freertos_port_dir = "ARM_CM0"
            elif cpu_type == "cortex-m4" and fpu == "Yes":
                freertos_port_dir = "ARM_CM4F"
            else:
                freertos_port_dir = "ARM_CM3"

            env.Append(
                CPPPATH=[
                    join(FRAMEWORK_MIDDLEWARE_DIR, x.strip(), "source", "include"),
                    join(FRAMEWORK_MIDDLEWARE_DIR, x.strip(), "source", "portable", "GCC", freertos_port_dir)
                ]
            )
            # Read heap manager from project option (default: heap_4).
            # Usage in platformio.ini:
            #   board_build.freertos_heap = heap_2.c    # built-in heap
            #   board_build.freertos_heap = ""          # skip heap (user provides own)
            freertos_heap = board.get("build.freertos_heap", "heap_4.c")
            src_filter = [
                "+<*.c>",
                "+<portable/common/*.c>",
                "+<portable/gcc/" + freertos_port_dir + "/*.c>",
            ]
            if freertos_heap:
                src_filter.append("+<portable/memmang/" + freertos_heap + ">")
                print("FreeRTOS heap: %s\r\n" % freertos_heap)
            else:
                print("FreeRTOS heap: skipped (user-provided)\r\n")

            libs.append(env.BuildLibrary(
                join("$BUILD_DIR", "middleware", x.strip()),
                join(FRAMEWORK_MIDDLEWARE_DIR, x.strip(), "source"),
                src_filter=src_filter
            ))
        elif x in ("usbd_drivers", "usbh_drivers"):
            is_host = x == "usbh_drivers"
            mode = "Host" if is_host else "Device"
            print("Building USB %s Drivers for %s.\r\n" % (mode, bsp))

            # Detect USB driver directory structure at build time
            usb_driver_dir = join(FRAMEWORK_MIDDLEWARE_DIR, "usb_drivers")
            usbd_driver_dir = join(FRAMEWORK_MIDDLEWARE_DIR, "usbd_drivers")

            if isdir(usb_driver_dir):
                src_filter = ["+<usb_core.c>"]
                src_filter.append("+<usbd_*.c>" if not is_host else "+<usbh_*.c>")
                env.Append(
                    CPPPATH=[join(usb_driver_dir, "inc")]
                )
                libs.append(env.BuildLibrary(
                    join("$BUILD_DIR", "middleware", "usb_drivers"),
                    join(usb_driver_dir, "src"),
                    src_filter=src_filter
                ))
            elif isdir(usbd_driver_dir) and not is_host:
                env.Append(
                    CPPPATH=[join(usbd_driver_dir, "inc")]
                )
                libs.append(env.BuildLibrary(
                    join("$BUILD_DIR", "middleware", "usbd_drivers"),
                    join(usbd_driver_dir, "src"),
                    src_filter=["+<*.c>"]
                ))
            else:
                sys.stderr.write(
                    "USB %s drivers not available for BSP '%s'.\r\n" % (mode, bsp)
                )
        else:
            sys.stderr.write("Middleware %s not supported.\r\n" % x)

env.Append(LIBS=libs)
