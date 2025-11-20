# Project global configuration
set(CFLAGS "-O3" CACHE STRING "Global var from Make")
set(CPPFLAGS "-Ishared -DSHARED_DEF" CACHE STRING "Global var from Make")
set(CMAKE_C_FLAGS_INIT "-O3 -Ishared -DSHARED_DEF")
add_library(ts25_global_options INTERFACE)
target_include_directories(ts25_global_options INTERFACE "shared")
target_compile_definitions(ts25_global_options INTERFACE SHARED_DEF)
target_compile_options(ts25_global_options INTERFACE -DSHARED_DEF -Ishared -O3)
add_library(TS25::GlobalOptions ALIAS ts25_global_options)
