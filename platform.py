# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from platformio.public import PlatformBase
from platformio import util


class Intel_mcs85Platform(PlatformBase):

    # Per-host prebuilt toolchain packages. Add linux/macOS branches here as
    # they are published; the platform otherwise works unchanged.
    toolchain_i8085 = {
        "windows_amd64": "https://github.com/maxgerhardt/toolchain-llvm-i8085.git#windows_x64",
    }

    def is_embedded(self):
        return True

    def configure_default_packages(self, variables, targets):
        # Point the toolchain package at the correct prebuilt for this host,
        # unless the user has overridden it (e.g. a local `symlink://` package
        # via `platform_packages` for development).
        sys_type = util.get_systype()
        url = Intel_mcs85Platform.toolchain_i8085.get(sys_type)
        current = str(self.packages["toolchain-llvm-i8085"].get("version", ""))
        is_local_override = current.startswith(
            ("symlink://", "file://")
        ) or os.path.isdir(current)
        if url and not is_local_override:
            self.packages["toolchain-llvm-i8085"]["version"] = url

        return super().configure_default_packages(variables, targets)
