# Packaging for TS24
install(TARGETS ts24_libpkg EXPORT TS24Targets)
install(EXPORT TS24Targets NAMESPACE TS24:: DESTINATION lib/cmake/TS24 FILE TS24Targets.cmake)
export(EXPORT TS24Targets FILE "${CMAKE_CURRENT_BINARY_DIR}/TS24Targets.cmake" NAMESPACE TS24::)
install(FILES ${CMAKE_CURRENT_LIST_DIR}/TS24Config.cmake ${CMAKE_CURRENT_LIST_DIR}/TS24ConfigVersion.cmake DESTINATION lib/cmake/TS24)
