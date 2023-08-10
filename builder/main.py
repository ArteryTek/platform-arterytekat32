import sys
from platform import system
from os import makedirs
from os.path import basename, isdir, join
from platformio.util import get_systype

from SCons.Script import (ARGUMENTS, COMMAND_LINE_TARGETS, AlwaysBuild,
                          Builder, Default, DefaultEnvironment)

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()

env.Replace(
    AR="arm-none-eabi-gcc-ar",
    AS="arm-none-eabi-as",
    CC="arm-none-eabi-gcc",
    CXX="arm-none-eabi-g++",
    GDB="arm-none-eabi-gdb",
    OBJCOPY="arm-none-eabi-objcopy",
    OBJDUMP="arm-none-eabi-objdump",
    RANLIB="arm-none-eabi-gcc-ranlib",
    SIZETOOL="arm-none-eabi-size",
    NMTOOL="arm-none-eabi-nm",

    ARFLAGS=["rc"],

    SIZEPROGREGEXP=r"^(?:\.isr_vector|\.text|\.data|\.rodata|\.text.align|\.init_array|\.fini_array|\.ARM.exidx)\s+(\d+).*",
    SIZEDATAREGEXP=r"^(?:\.data|\.bss|\.noinit)\s+(\d+).*",
    SIZECHECKCMD="$SIZETOOL -A -d $SOURCES",
    SIZEPRINTCMD='$SIZETOOL -B -d $SOURCES',

    PROGSUFFIX=".elf"
)

# Allow user to override via pre:script
if env.get("PROGNAME", "program") == "program":
    env.Replace(PROGNAME="firmware")

env.Append(
    BUILDERS=dict(
        ElfToBin=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "binary",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".bin"
        ),
        ElfToHex=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "ihex",
                "-R",
                ".eeprom",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".hex"
        ),
        ElfToAsm=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJDUMP",
                "-d",
                "-S",
                "$SOURCES",
                ">",
                "$TARGET"
            ]), "Disassmbling to $TARGET"),
            suffix=".asm"
        )
    )
)

if not env.get("PIOFRAMEWORK"):
    env.SConscript("frameworks/_bare.py")

#
# Target: Build executable and linkable firmware
#

target_elf = None
if "nobuild" in COMMAND_LINE_TARGETS:
    target_elf = join("$BUILD_DIR", "${PROGNAME}.elf")
    target_firm = join("$BUILD_DIR", "${PROGNAME}.bin")
    target_hex = join("$BUILD_DIR", "${PROGNAME}.hex")
    target_asm = join("$BUILD_DIR", "${PROGNAME}.asm")
else:
    target_elf = env.BuildProgram()
    target_firm = env.ElfToBin(join("$BUILD_DIR", "${PROGNAME}"), target_elf)
    target_hex = env.ElfToHex(join("$BUILD_DIR", "${PROGNAME}"), target_elf)
    target_asm = env.ElfToAsm(join("$BUILD_DIR", "${PROGNAME}"), target_elf)

AlwaysBuild(env.Alias("nobuild", target_firm))
target_buildprog = env.Alias("buildprog", target_firm, target_firm)
target_buildhex = env.Alias("buildhex", target_hex, target_hex)
target_buildasm = env.Alias("disassembling", target_asm, target_asm)

#
# Target: Export Symbols
#
target_symbols = env.Alias(
    "symbols", target_elf,
    env.VerboseAction(" ".join([
        "$NMTOOL",
        "--print-size",
        "--size-sort",
        "-gC",
        "$SOURCES",
        ">",
        join("$BUILD_DIR","symbols_${PROGNAME}.txt")
    ]),"Exporting Symbols"))
AlwaysBuild(target_symbols)

#
# Target: Print binary size
#

target_size = env.Alias(
    "size", target_elf,
    env.VerboseAction("$SIZEPRINTCMD", "Calculating size $SOURCE"))
AlwaysBuild(target_size)

#
# Target: Upload by default .bin file
#

upload_protocol = env.subst("$UPLOAD_PROTOCOL")
debug_tools = board.get("debug.tools", {})
upload_source = target_firm
upload_actions = []

if upload_protocol in debug_tools:
    openocd_args = [
        "-d%d" % (2 if int(ARGUMENTS.get("PIOVERBOSE", 0)) else 1)
    ]
    openocd_args.extend(
        debug_tools.get(upload_protocol).get("server").get("arguments", []))
    openocd_args.extend([
        "-c", "program {$SOURCE} %s verify reset; shutdown;" %
        board.get("upload.offset_address", "")
    ])
    openocd_args = [
        f.replace("$PACKAGE_DIR",
                  platform.get_package_dir("tool-openocd-at32") or "")
        for f in openocd_args
    ]
    env.Replace(
        UPLOADER=join(
            platform.get_package_dir("tool-openocd-at32") or "",
            "bin-"+ get_systype(), "openocd.exe" if system()=="Windows" else "openocd"),
        UPLOADERFLAGS=openocd_args,
        UPLOADCMD="$UPLOADER $UPLOADERFLAGS")

    if not board.get("upload").get("offset_address"):
        upload_source = target_elf
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]

elif upload_protocol == "dfu":
    hwids = board.get("build.hwids", [["0x2E3C", "0xDF11"]])
    vid = hwids[0][0]
    pid = hwids[0][1]

    # default tool for all boards with embedded DFU bootloader over USB
    _upload_tool = '"%s"' % join(platform.get_package_dir(
        "tool-dfuutil") or "", "bin", "dfu-util")
    _upload_flags = [
        "-d", ",".join(["%s:%s" % (hwid[0], hwid[1]) for hwid in hwids]),
        "-a", "0", "-s",
        "%s:leave" % board.get("upload.offset_address", "0x08000000"), "-D"
    ]

    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]

    # Add special DFU header to the binary image
    env.AddPostAction(
        join("$BUILD_DIR", "${PROGNAME}.bin"),
        env.VerboseAction(
            " ".join([
                '"%s"' % join(platform.get_package_dir("tool-dfuutil") or "",
                        "bin", "dfu-suffix"),
                "-v %s" % vid,
                "-p %s" % pid,
                "-d 0xffff", "-a", "$TARGET"
            ]), "Adding dfu suffix to ${PROGNAME}.bin"))
    
    env.Replace(
        UPLOADER=_upload_tool,
        UPLOADERFLAGS=_upload_flags,
        UPLOADCMD='$UPLOADER $UPLOADERFLAGS "${SOURCE.get_abspath()}"')

    upload_source = target_firm

# custom upload tool
elif upload_protocol == "custom":
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]

else:
    sys.stderr.write("Warning! Unknown upload protocol %s\n" % upload_protocol)

AlwaysBuild(env.Alias("upload", upload_source, upload_actions))

#
# Information about obsolete method of specifying linker scripts
#

if any("-Wl,-T" in f for f in env.get("LINKFLAGS", [])):
    print("Warning! '-Wl,-T' option for specifying linker scripts is deprecated. "
          "Please use 'board_build.ldscript' option in your 'platformio.ini' file.")

#
# Default targets
#

Default([target_buildprog, target_buildhex, target_symbols, target_size])
