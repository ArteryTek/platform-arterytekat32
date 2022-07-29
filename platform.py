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

import json
import os

from platform import system

from platformio.managers.platform import PlatformBase
from platformio.util import get_systype

class At32Platform(PlatformBase):

    def configure_default_packages(self, variables, targets):
        board = variables.get("board")
        board_config = self.board_config(board)

        default_protocol = board_config.get("upload.protocol") or ""

        # configure J-LINK tool
        jlink_conds = [
            "jlink" in variables.get(option, "")
            for option in ("upload_protocol", "debug_tool")
        ]
        if board:
            jlink_conds.extend([
                "jlink" in board_config.get(key, "")
                for key in ("debug.default_tools", "upload.protocol")
            ])
        jlink_pkgname = "tool-jlink"
        if not any(jlink_conds) and jlink_pkgname in self.packages:
            del self.packages[jlink_pkgname]

        return PlatformBase.configure_default_packages(self, variables,
                                                       targets)

    def get_boards(self, id_=None):
        result = PlatformBase.get_boards(self, id_)
        if not result:
            return result
        if id_:
            return self._add_default_debug_tools(result)
        else:
            for key, value in result.items():
                result[key] = self._add_default_debug_tools(result[key])
        return result

    def _add_default_debug_tools(self, board):
        debug = board.manifest.get("debug", {})
        upload_protocols = board.manifest.get("upload", {}).get(
            "protocols", [])
        if "tools" not in debug:
            debug['tools'] = {}

        for link in ("cmsis-dap", "atlink", "atlink_dap_v2"):
            if link not in upload_protocols or link in debug['tools']:
                continue

            server_args = ["-s", "$PACKAGE_DIR/scripts"]
            if debug.get("openocd_board"):
                server_args.extend([
                    "-f", "board/%s.cfg" % debug.get("openocd_board")
                ])
            else:
                assert debug.get("openocd_target"), (
                    "Missed target configuration for %s" % board.id)
                server_args.extend([
                    "-f", "interface/%s.cfg" % link,
                    "-c", "transport select swd",
                    "-f", "target/%s.cfg" % debug.get("openocd_target")
                ])
                server_args.extend(debug.get("openocd_extra_args", []))

            debug['tools'][link] = {
                "server": {
                    "package": "tool-openocd-at32",
                    "executable": "bin/openocd",
                    "arguments": server_args
                }
            }
            debug['tools'][link]['onboard'] = link in debug.get("onboard_tools", [])
            debug['tools'][link]['default'] = link in debug.get("default_tools", [])

        board.manifest['debug'] = debug
        return board
