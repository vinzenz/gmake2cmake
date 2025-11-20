cmake_minimum_required(VERSION 3.20)
project(TS24 LANGUAGES c)
add_subdirectory("src")
include("${CMAKE_CURRENT_LIST_DIR}/Packaging.cmake")
