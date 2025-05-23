from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir, save
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version
import os
import textwrap

required_conan_version = ">=2.1"


class LZ4Conan(ConanFile):
    name = "lz4"
    description = "Extremely Fast Compression algorithm"
    license = ("BSD-2-Clause", "BSD-3-Clause")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/lz4/lz4"
    topics = ("compression")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["LZ4_BUILD_CLI"] = False
        if Version(self.version) < "1.10.0":
            tc.variables["LZ4_BUILD_LEGACY_LZ4C"] = False
        tc.variables["LZ4_BUNDLED_MODE"] = False
        tc.variables["LZ4_POSITION_INDEPENDENT_LIB"] = self.options.get_safe("fPIC", True)
        # Generate a relocatable shared lib on Macos
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0042"] = "NEW"
        # Honor BUILD_SHARED_LIBS (see https://github.com/conan-io/conan/issues/11840)
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        if Version(self.version) < "1.10.0":
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        tc.generate()

    @property
    def _cmakelists_folder(self):
        subfolder = os.path.join("build", "cmake")
        return os.path.join(self.source_folder, subfolder)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=self._cmakelists_folder)
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        if Version(self.version) >= "1.9.4":
            rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    @property
    def _lz4_target(self):
        return f"LZ4::{'lz4_shared' if self.options.shared else 'lz4_static'}"

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "lz4")
        self.cpp_info.set_property("cmake_target_name", self._lz4_target)
        self.cpp_info.set_property("cmake_target_aliases", ["lz4::lz4"]) # old unofficial target in CCI for lz4, kept for the moment to not break consumers
        self.cpp_info.set_property("pkg_config_name", "liblz4")
        self.cpp_info.libs = ["lz4"]
        if is_msvc(self) and self.options.shared:
            self.cpp_info.defines.append("LZ4_DLL_IMPORT=1")
