from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy, rm, rmdir
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version
import os

required_conan_version = ">=2.1"


class CzmqConan(ConanFile):
    name = "czmq"
    description = "High-level C binding for ZeroMQ"
    license = "MPL-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/zeromq/czmq"
    topics = ("zmq", "libzmq", "message-queue", "asynchronous")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_drafts": [True, False],
        "with_libcurl": [True, False],
        "with_lz4": [True, False],
        "with_libuuid": [True, False],
        "with_libmicrohttpd": [True, False],
        "with_systemd": [True, False],
    }
    default_options = {
        "shared": False,
        "enable_drafts": False,
        "fPIC": True,
        "with_libcurl": True,
        "with_lz4": True,
        "with_libuuid": True,
        "with_libmicrohttpd": True,
        "with_systemd": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            # libuuid is not available on Windows
            del self.options.with_libuuid
        if self.settings.os == "Linux":
            del self.options.with_systemd

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.enable_drafts:
            del self.options.with_libcurl
            del self.options.with_libmicrohttpd

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zeromq/4.3.5", transitive_headers=True)
        if self.options.get_safe("with_libmicrohttpd"):
            self.requires("libmicrohttpd/0.9.75")
        if self.options.get_safe("with_libcurl"):
            self.requires("libcurl/[>=7.78.0 <9]")
        if self.options.with_lz4:
            self.requires("lz4/1.9.4")
        if self.options.get_safe("with_libuuid"):
            self.requires("util-linux-libuuid/2.39.2")
        if self.options.get_safe("with_systemd"):
            self.requires("libsystemd/253.10")

    def validate(self):
        if is_apple_os(self) and self.options.shared and self.settings.build_type == "Debug":
            raise ConanInvalidConfiguration(f"{self.ref} can not be built as shared and debug on apple-clang.")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_DRAFTS"] = self.options.enable_drafts
        tc.variables["CZMQ_BUILD_SHARED"] = self.options.shared
        tc.variables["CZMQ_BUILD_STATIC"] = not self.options.shared
        tc.variables["CZMQ_WITH_UUID"] = self.options.get_safe("with_libuuid", False)
        tc.variables["CZMQ_WITH_SYSTEMD"] = self.options.get_safe("with_systemd", False)
        tc.variables["CZMQ_WITH_LZ4"] = self.options.with_lz4
        tc.variables["CZMQ_WITH_LIBCURL"] = self.options.get_safe("with_libcurl", False)
        tc.variables["CZMQ_WITH_LIBMICROHTTPD"] = self.options.get_safe("with_libmicrohttpd", False)
        if Version(self.version) >= "4.2.1":
            tc.variables["CZMQ_WITH_NSS"] = False
        if is_msvc(self):
            tc.preprocessor_definitions["_NOEXCEPT"] = "noexcept"
        # Relocatable shared libs on macOS
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0042"] = "NEW"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        if Version(self.version) > "4.2.1": # pylint: disable=conan-unreachable-upper-version
            raise ConanException("CMAKE_POLICY_VERSION_MINIMUM hardcoded to 3.5, check if new version supports CMake 4")
        tc.generate()

        dpes = CMakeDeps(self)
        dpes.generate()

    def build(self):
        apply_conandata_patches(self)
        # remove custom Finduuid.cmake to use cci Finduuid.cmake
        rm(self, "Finduuid.cmake", self.source_folder)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "CMake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    @property
    def _czmq_target(self):
        return "czmq" if self.options.shared else "czmq-static"

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "czmq")
        self.cpp_info.set_property("cmake_target_name", self._czmq_target)
        self.cpp_info.set_property("pkg_config_name", "libczmq")

        prefix = "lib" if is_msvc(self) and not self.options.shared else ""
        self.cpp_info.libs = [f"{prefix}czmq"]
        if not self.options.shared:
            self.cpp_info.defines.append("CZMQ_STATIC")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["pthread", "m"])
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs.append("rpcrt4")


