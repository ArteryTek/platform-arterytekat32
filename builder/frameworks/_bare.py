#
# Default flags for bare-metal programming (without any framework layers)
#

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()

board = env.BoardConfig()
cpu_type = board.get("build.cpu", "cortex-m4") # 默认为cortex-m4，如果是cortex-m0+，则使用cm0plus目录
gcc_cpu = "cortex-m0plus" if cpu_type == "cortex-m0+" else cpu_type

env.Append(
    ASFLAGS=["-x", "assembler-with-cpp"],

    CCFLAGS=[
        "-Os",  # optimize for size
        "-ffunction-sections",  # place each function in its own section
        "-fdata-sections",
        "-Wall",
        "-mthumb",
        "-mcpu=%s" % gcc_cpu,  # <-- 已更改: 获取动态 CPU 类型
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
        "-mcpu=%s" % gcc_cpu,  # <-- 已更改: 获取动态 CPU 类型
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

env.Append(ASFLAGS=env.get("CCFLAGS", [])[:])
