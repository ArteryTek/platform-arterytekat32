#
# Default flags for bare-metal programming (without any framework layers)
#

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()

board = env.BoardConfig()
cpu_type = board.get("build.cpu", "cortex-m4") # 默认为cortex-m4，如果是cortex-m0+，则使用cm0plus目录
gcc_cpu = "cortex-m0plus" if cpu_type == "cortex-m0+" else cpu_type

env.Append(
    CCFLAGS=[
        "-Os",  # optimize for size
        "-ffunction-sections",  # place each function in its own section
        "-fdata-sections",
        "-Wall",
        "-mthumb",
        "-mcpu=%s" % gcc_cpu,
        "-save-temps=obj" # 生成中间文件供检查优化
    ],

    CXXFLAGS=[
        "-fno-rtti",
        "-fno-exceptions"
    ],

    CPPDEFINES=[
        ("F_CPU", "$BOARD_F_CPU")
    ],

    LINKFLAGS=[
        "-Os",
        "-Wl,--gc-sections,--relax",
        "--specs=nano.specs",
        "--specs=nosys.specs",
        "-mthumb",
        "-mcpu=%s" % gcc_cpu,
        "-Wl,-Map,%s/linkmap.map" % env.get("BUILD_DIR")
    ],

    LIBS=["c", "gcc", "m", "stdc++"]
)

if "BOARD" in env:
    env.Append(
        CPPDEFINES=[
            board.get("build.variant", "").upper()
        ]
    )

# Copy CCFLAGS (mcpu, mthumb, …) into ASFLAGS so they are available to
# ``$ASPPCOM`` (which runs ``$CC -x assembler-with-cpp …`` for .S files).
# Do NOT put ``-x assembler-with-cpp`` into ASFLAGS – it is a gcc flag,
# not a gas flag, so it breaks if ever passed to the plain assembler.
env.Append(ASFLAGS=env.get("CCFLAGS", [])[:])

# ArteryTek official firmware libs ship startup files with .s (lowercase)
# extension.  SCons runs ``$AS $ASFLAGS`` for .s files, but the plain
# assembler does not know about cpu/flags that should come from CCFLAGS.
# Override ASCOM so that .s files go through the C preprocessor (just
# like .S files) via ``$CC -x assembler-with-cpp …``.
env["ASCOM"] = env["ASPPCOM"]
