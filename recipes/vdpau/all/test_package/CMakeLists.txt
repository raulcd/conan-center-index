cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(PkgConfig)

pkg_check_modules(VDPAU REQUIRED IMPORTED_TARGET vdpau)
find_package(xorg REQUIRED CONFIG)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE PkgConfig::VDPAU xorg::xorg)
