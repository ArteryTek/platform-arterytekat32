#
# Default flags for bare-metal programming (without any framework layers)
#

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()

env.Append(
    ASFLAGS=["-x", "assembler-with-cpp"],

    CCFLAGS=[
        "-Os",  # optimize for size
        "-ffunction-sections",  # place each function in its own section
        "-fdata-sections",
        "-Wall",
        "-mthumb",
        "-mcpu=cortex-m4",
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
        "-mcpu=cortex-m4",
        "-Wl,-Map,%s/linkmap.map" % env.get("BUILD_DIR")
    ],

    LIBS=["c", "gcc", "m", "stdc++"]
)

if "BOARD" in env:
    env.Append(
        CPPDEFINES=[
            env.BoardConfig().get("build.variant", "").upper()
        ]
    )

env.Append(ASFLAGS=env.get("CCFLAGS", [])[:])
